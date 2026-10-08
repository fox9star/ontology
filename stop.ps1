param([ValidateRange(1, 65535)][int]$Port = 5000)

$ErrorActionPreference = 'Stop'
$projectPython = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '.venv\Scripts\python.exe'))
$appPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'app.py'))
$scriptPattern = '^\s*(?:"[^"]+"|\S+)\s+(?:"' + [regex]::Escape($appPath) + '"|' + [regex]::Escape($appPath) + ')(?:\s|$)'
$allowedPythonPaths = @($projectPython)
if (Test-Path -LiteralPath $projectPython) {
    $basePython = & $projectPython -c 'import sys; print(sys._base_executable)'
    if ($LASTEXITCODE -eq 0 -and $basePython) { $allowedPythonPaths += $basePython.Trim() }
}
$listeners = @(Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
if ($listeners.Count -eq 0) {
    Write-Host 'The ontology server is not running.'
    exit 0
}

$ownerIds = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique)
foreach ($serverProcessId in $ownerIds) {
    $serverProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $serverProcessId"
    if (-not $serverProcess -or $serverProcess.ExecutablePath -notin $allowedPythonPaths -or
        -not $serverProcess.CommandLine -or
        $serverProcess.CommandLine.IndexOf($projectPython, [StringComparison]::OrdinalIgnoreCase) -lt 0 -or
        $serverProcess.CommandLine -notmatch $scriptPattern) {
        throw "Port $Port belongs to a different process. It was not stopped."
    }
    Stop-Process -Id $serverProcessId -ErrorAction Stop
    Wait-Process -Id $serverProcessId -Timeout 5 -ErrorAction SilentlyContinue
    if (Get-Process -Id $serverProcessId -ErrorAction SilentlyContinue) {
        throw "Ontology process $serverProcessId did not terminate."
    }
}
Write-Host 'Ontology server stopped.'
