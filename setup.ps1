$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $projectPython)) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv .venv
    } else {
        & python -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the Python virtual environment.' }
}

& $projectPython -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt') -c (Join-Path $PSScriptRoot 'requirements.lock.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check the pip output above.' }
& $projectPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Installed dependencies are incompatible.' }
& $projectPython -c 'import flask, rdflib, pyshacl, owlrl, requests'
if ($LASTEXITCODE -ne 0) { throw 'A required Python dependency could not be imported.' }
if (-not (Get-Command ffprobe -ErrorAction SilentlyContinue)) {
    Write-Warning 'ffprobe is not on PATH. Install FFmpeg before importing media.'
}
Write-Host 'Setup complete. Run: powershell -ExecutionPolicy Bypass -File .\run.ps1'
