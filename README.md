# SmartFace AI - Face Recognition Attendance System

A modern, full-stack Face Recognition Attendance System powered by **MTCNN**, **FaceNet**, **SVM**, **Python Flask**, and a responsive **HTML5/CSS3/JavaScript** frontend.

---

## 📁 Project Architecture

```
FaceRecognition/
├── backend/
│   ├── app.py                  # Flask REST API & Video Feed streaming
│   ├── attendance_tracker.py   # CSV Logging & Attendance business logic
│   ├── requirements.txt        # Backend dependencies
│   ├── run_backend.bat         # Direct launcher for backend
│   ├── models/                 # AI & Machine Learning weights
│   │   ├── svm_model.pkl       # Trained Support Vector Classifier
│   │   └── label_encoder.pkl   # Class Label Encoder
│   └── attendance_logs/        # Generated daily CSV attendance logs
│       └── Attendance_YYYY-MM-DD.csv
│
├── frontend/
│   ├── templates/              # HTML Templates
│   │   └── index.html          # Main Dashboard & Scanner UI
│   └── static/                 # Static Assets
│       ├── css/
│       │   └── style.css       # Dark glassmorphism styling
│       └── js/
│           └── app.js          # Live polling & UI reactivity
│
├── Dataset/                    # Training images & Jupyter Notebooks
│   ├── Mbappe/
│   ├── Messi/
│   ├── Neymar/
│   └── Ronaldo/
│
├── start_app.bat               # 1-Click launcher (Browser + Backend)
└── attendance_system.py        # Standalone OpenCV desktop script (optional)
```

---

## 🚀 How to Run

### Method 1: 1-Click Launcher (Recommended)
Simply double-click **`start_app.bat`** in the project folder. It will:
1. Open the web portal automatically in your browser at `http://127.0.0.1:5000`.
2. Start the Flask backend and begin camera face recognition.

### Method 2: Manual Terminal Execution
```bash
cd backend
python app.py
```
Then visit `http://127.0.0.1:5000` in your web browser.

---

## 🎯 Features
- **Real-Time Video Stream**: Live MJPEG video stream from your webcam with scanning animations.
- **Deep Face Recognition**: Multi-task Cascaded Convolutional Networks (MTCNN) for face detection + Google FaceNet for 128-d embeddings + SVM classifier for recognition.
- **Automated CSV Logging**: Records Candidate Name, Date, and Timestamp without duplicates.
- **Dynamic Stats**: Real-time counters for Total Enrolled, Present Today, and Absent.
- **Date Filter & Export**: View past attendance logs by date and download CSV sheets directly.
