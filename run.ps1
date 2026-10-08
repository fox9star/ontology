param([ValidateRange(1, 65535)][int]$Port = 5000)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:HOST = '127.0.0.1'
$env:PORT = [string]$Port
$env:ONTOLOGY_LOCAL_DOCKER = '0'
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Run setup first: powershell -ExecutionPolicy Bypass -File .\setup.ps1'
}
& $projectPython -c 'import flask, rdflib, pyshacl, owlrl, requests'
if ($LASTEXITCODE -ne 0) {
    throw 'Dependencies are missing. Run: powershell -ExecutionPolicy Bypass -File .\setup.ps1'
}

Write-Host "Open http://127.0.0.1:$Port in your browser. Press Ctrl+C to stop."
& $projectPython (Join-Path $PSScriptRoot 'app.py')
exit $LASTEXITCODE
