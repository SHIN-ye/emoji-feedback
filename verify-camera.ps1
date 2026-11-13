param([double]$Duration = 20, [string]$Source = '0')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$aiPython = Join-Path $PSScriptRoot '.venv-ai/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $aiPython)) { throw 'AI environment .venv-ai is missing.' }
Write-Host 'Close Windows Camera and video-call apps. Look at the camera during the test.'
& $aiPython -m scripts.verify_ai_camera --duration $Duration --source $Source
$testExit = $LASTEXITCODE
$latest = Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot 'artifacts') -Directory -Filter 'ai-camera-*' | Sort-Object Name -Descending | Select-Object -First 1
if ($latest) {
    Write-Host "Result directory: $($latest.FullName)"
    if ($testExit -ne 0) { Get-Content -LiteralPath (Join-Path $latest.FullName 'worker.log') -Tail 20 }
}
exit $testExit
