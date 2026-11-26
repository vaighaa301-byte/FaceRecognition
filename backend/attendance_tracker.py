import os
import pandas as pd
from datetime import datetime

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BACKEND_DIR, "attendance_logs")
os.makedirs(LOGS_DIR, exist_ok=True)

class AttendanceTracker:
    def __init__(self):
        self.last_recognition = {"name": None, "time": None, "is_new": False}

    def get_csv_path(self, date_str=None):
        if not date_str:
            date_str = datetime.now().strftime("%Y-%m-%d")
        return os.path.join(LOGS_DIR, f"Attendance_{date_str}.csv")

    def ensure_file(self, date_str=None):
        filepath = self.get_csv_path(date_str)
        if not os.path.exists(filepath):
            df = pd.DataFrame(columns=["Name", "Date", "Time"])
            df.to_csv(filepath, index=False)
        return filepath

    def mark(self, name):
        filepath = self.ensure_file()
        try:
            df = pd.read_csv(filepath)
        except Exception:
            df = pd.DataFrame(columns=["Name", "Date", "Time"])

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        if name not in df["Name"].values:
            new_row = pd.DataFrame([{"Name": name, "Date": date_str, "Time": time_str}])
            df = pd.concat([df, new_row], ignore_index=True)
            df.to_csv(filepath, index=False)
            self.last_recognition = {
                "name": name,
                "time": time_str,
                "is_new": True
            }
            print(f"[ATTENDANCE MARKED] {name} at {time_str}")
            return True
        else:
            self.last_recognition = {
                "name": name,
                "time": time_str,
                "is_new": False
            }
            return False

    def get_records(self, date_str=None):
        filepath = self.ensure_file(date_str)
        try:
            df = pd.read_csv(filepath)
            return df.to_dict(orient="records")
        except Exception:
            return []
