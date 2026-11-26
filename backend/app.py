import os
import cv2
import time
import joblib
import threading
import numpy as np
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, send_file, request
from attendance_tracker import AttendanceTracker

# Paths configuration
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")
TEMPLATE_DIR = os.path.join(FRONTEND_DIR, "templates")
STATIC_DIR = os.path.join(FRONTEND_DIR, "static")

MODELS_DIR = os.path.join(BACKEND_DIR, "models")
MODEL_PATH = os.path.join(MODELS_DIR, "svm_model.pkl")
ENCODER_PATH = os.path.join(MODELS_DIR, "label_encoder.pkl")

# Initialize Flask
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)

# Initialize Tracker
tracker = AttendanceTracker()

# Global AI Model State
model = None
encoder = None
embedder = None
detector = None
model_loaded = False
model_loading_error = None

def init_models():
    global model, encoder, embedder, detector, model_loaded, model_loading_error
    print("[AI] Loading FaceNet, MTCNN and SVM models...")
    try:
        model = joblib.load(MODEL_PATH)
        encoder = joblib.load(ENCODER_PATH)
        from keras_facenet import FaceNet
        from mtcnn import MTCNN
        embedder = FaceNet()
        detector = MTCNN()
        model_loaded = True
        print("[AI] All models successfully loaded!")
    except Exception as e:
        model_loading_error = str(e)
        print("[AI Error] Failed to load models:", e)

# Start model loading in background thread
threading.Thread(target=init_models, daemon=True).start()

# --- Rock-Solid Camera Manager (Singleton Threaded Streamer) ---
class CameraStreamer:
    def __init__(self):
        self.cap = None
        self.latest_frame = None
        self.latest_jpeg = None
        self.lock = threading.Lock()
        self.running = True
        self.camera_active = False
        self.cached_detections = []
        self.last_detection_time = 0

        # Start camera capture thread
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()

        # Start AI inference thread (runs decoupled so video never lags)
        self.ai_thread = threading.Thread(target=self._ai_inference_loop, daemon=True)
        self.ai_thread.start()

    def _open_camera(self):
        # Try DirectShow first on Windows
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(0)
        if cap.isOpened():
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            return cap
        return None

    def _create_fallback_frame(self, message="Connecting to Camera..."):
        # Dark branded placeholder frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (15, 11, 7)  # #070b0f dark background

        # Header bar
        cv2.rectangle(frame, (0, 0), (640, 4), (99, 102, 241), -1)

        # Message text
        font = cv2.FONT_HERSHEY_SIMPLEX
        (tw, th), _ = cv2.getTextSize(message, font, 0.7, 2)
        tx = (640 - tw) // 2
        ty = 240
        cv2.putText(frame, message, (tx, ty), font, 0.7, (220, 220, 220), 2, cv2.LINE_AA)

        status_sub = "Initializing SmartFace AI Core..." if not model_loaded else "AI Ready - Camera Active"
        (sw, sh), _ = cv2.getTextSize(status_sub, font, 0.5, 1)
        sx = (640 - sw) // 2
        cv2.putText(frame, status_sub, (sx, ty + 35), font, 0.5, (130, 140, 160), 1, cv2.LINE_AA)

        _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        return jpeg.tobytes()

    def _capture_loop(self):
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                self.cap = self._open_camera()
                if self.cap is None or not self.cap.isOpened():
                    self.camera_active = False
                    with self.lock:
                        self.latest_jpeg = self._create_fallback_frame("Waiting for Camera...")
                    time.sleep(1.0)
                    continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.camera_active = False
                if self.cap:
                    self.cap.release()
                    self.cap = None
                time.sleep(0.5)
                continue

            self.camera_active = True
            with self.lock:
                self.latest_frame = frame.copy()

            # Render overlay with latest cached detections
            display_frame = frame.copy()
            with self.lock:
                detections = list(self.cached_detections)

            for det in detections:
                x, y, w, h = det["box"]
                name = det["name"]
                conf = det["confidence"]
                color = det["color"]

                # Bounding box
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), color, 2)

                # Stylish badge
                label = f"{name} {int(conf * 100)}%" if name != "Unknown" else "Unknown"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                badge_y = max(th + 10, y)
                cv2.rectangle(display_frame, (x, badge_y - th - 10), (x + tw + 12, badge_y), color, -1)
                cv2.putText(display_frame, label, (x + 6, badge_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)

            # Encode frame to JPEG
            ret, jpeg = cv2.imencode('.jpg', display_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                with self.lock:
                    self.latest_jpeg = jpeg.tobytes()

            time.sleep(0.03)  # ~30 FPS

    def _ai_inference_loop(self):
        while self.running:
            if not model_loaded:
                time.sleep(0.2)
                continue

            frame = None
            with self.lock:
                if self.latest_frame is not None:
                    frame = self.latest_frame.copy()

            if frame is None:
                time.sleep(0.1)
                continue

            try:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = detector.detect_faces(rgb)
                results = []

                for face in faces:
                    x, y, w, h = face["box"]
                    x, y = max(0, x), max(0, y)
                    crop = rgb[y:y+h, x:x+w]
                    if crop.size == 0 or w < 35 or h < 35:
                        continue

                    crop_resized = cv2.resize(crop, (160, 160))
                    crop_expanded = np.expand_dims(crop_resized, axis=0)

                    embedding = embedder.embeddings(crop_expanded)[0]
                    probabilities = model.predict_proba([embedding])[0]
                    prediction = np.argmax(probabilities)
                    confidence = float(probabilities[prediction])

                    if confidence < 0.70:
                        name = "Unknown"
                        color = (0, 0, 220)  # Red
                    else:
                        name = str(encoder.inverse_transform([prediction])[0])
                        color = (0, 200, 70)  # Green
                        tracker.mark(name)

                    results.append({
                        "box": (x, y, w, h),
                        "name": name,
                        "confidence": confidence,
                        "color": color
                    })

                with self.lock:
                    self.cached_detections = results

            except Exception:
                pass

            # Pause briefly between detections to prevent CPU overload
            time.sleep(0.2)

    def get_latest_jpeg(self):
        with self.lock:
            if self.latest_jpeg is not None:
                return self.latest_jpeg
        return self._create_fallback_frame("Starting Camera...")

# Initialize camera singleton
streamer = CameraStreamer()

def gen_frames():
    while True:
        frame_bytes = streamer.get_latest_jpeg()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.033)  # 30 fps yield

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    registered_classes = []
    if encoder is not None:
        registered_classes = [str(c) for c in encoder.classes_]
    return jsonify({
        "model_loaded": model_loaded,
        "camera_active": streamer.camera_active,
        "registered_classes": registered_classes,
        "total_registered": len(registered_classes),
        "last_recognition": tracker.last_recognition
    })

@app.route('/api/attendance')
def api_attendance():
    date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    records = tracker.get_records(date_str)

    registered_classes = [str(c) for c in encoder.classes_] if encoder is not None else []
    present_names = [d["Name"] for d in records]
    absent_names = [c for c in registered_classes if c not in present_names]

    return jsonify({
        "date": date_str,
        "records": records,
        "total_present": len(records),
        "total_registered": len(registered_classes),
        "absent": absent_names
    })

@app.route('/api/manual_mark', methods=['POST'])
def api_manual_mark():
    data = request.json or {}
    name = data.get("name")
    if not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    marked = tracker.mark(name)
    return jsonify({"success": True, "marked": marked, "name": name})

@app.route('/api/download')
def api_download():
    date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d"))
    filepath = tracker.get_csv_path(date_str)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=f"Attendance_{date_str}.csv")
    return jsonify({"error": "File not found"}), 404

if __name__ == '__main__':
    tracker.ensure_file()
    print("Serving SmartFace AI on http://127.0.0.1:5000 ...")
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
