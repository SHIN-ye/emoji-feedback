param(
    [Parameter(Mandatory=$true)][int]$Session,
    [string]$Source = '0',
    [string]$Url = 'http://127.0.0.1:8000',
    [double]$Interval = 3,
    [double]$Threshold = 0.6,
    [double]$Duration = 0
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$aiPython = Join-Path $PSScriptRoot '.venv-ai/Scripts/python.exe'
if (-not (Test-Path $aiPython)) { throw 'Create .venv-ai with Python 3.12 and install ai/requirements.txt first.' }
if (-not $env:AI_SERVICE_TOKEN) { throw 'Set AI_SERVICE_TOKEN to the same value as the backend before starting.' }
& $aiPython -m ai.worker --source $Source --session $Session --url $Url --interval $Interval --threshold $Threshold --duration $Duration
exit $LASTEXITCODE
