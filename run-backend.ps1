# 프로젝트 루트로 이동
Set-Location $PSScriptRoot

$venvPython = "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "Creating venv..."
    python -m venv backend\.venv
}
Write-Host "Installing/updating dependencies (backend\requirements.txt)..."
& "backend\.venv\Scripts\pip.exe" install -r backend\requirements.txt -q
Write-Host "Starting backend at http://localhost:8000"
& "backend\.venv\Scripts\uvicorn.exe" backend.main:app --reload --host 0.0.0.0 --port 8000
