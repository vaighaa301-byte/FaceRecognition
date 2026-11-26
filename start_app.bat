@echo off
cd /d "%~dp0"
echo ===================================================================
echo     SmartFace AI - Face Recognition Attendance Web Application
echo ===================================================================
echo.
echo [1/2] Opening Web Dashboard at http://127.0.0.1:5000...
start http://127.0.0.1:5000
echo.
echo [2/2] Starting Backend Flask Server...
cd backend
C:\Users\HP\anaconda3\python.exe app.py
pause
