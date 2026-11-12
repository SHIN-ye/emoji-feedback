$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $localPython)) {
    Write-Host 'Run Python 3.15.2 to create .venv, then .venv\Scripts\python -m pip install -r requirements-lock.txt'
    exit 1
}
Write-Host 'Open http://127.0.0.1:8000 (Ctrl+C to stop)'
& $localPython -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
