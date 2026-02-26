@echo off
cd /d "%~dp0"

if not exist "backend\.venv\Scripts\python.exe" (
  echo Creating venv...
  python -m venv backend\.venv
)
call backend\.venv\Scripts\activate.bat
echo Installing/updating dependencies (backend\requirements.txt)...
pip install -r backend\requirements.txt -q
echo Starting backend at http://localhost:8000
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
