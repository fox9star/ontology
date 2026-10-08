<#
.SYNOPSIS
Starts this project's local studio. Sibling MV Studio and Fuseki are opt-in.
#>
param(
    [switch]$WithFuseki,
    [switch]$WithMvStudio,
    [switch]$NoBrowser,
    [ValidateRange(1, 65535)][int]$Port = 5000,
    [string]$MvPython
)

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = '1'
$env:HOST = '127.0.0.1'
$env:PORT = [string]$Port
$env:ONTOLOGY_LOCAL_DOCKER = '0'

$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'setup.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'setup.ps1 failed.' }
}
& $projectPython -c 'import flask, rdflib, pyshacl, owlrl, requests'
if ($LASTEXITCODE -ne 0) { throw 'Dependencies are missing. Run setup.ps1.' }

$runtimePath = Join-Path $PSScriptRoot '.runtime'
New-Item -ItemType Directory -Force -Path $runtimePath | Out-Null

function Test-ServiceHealth([string]$Url, [string]$ExpectedService = '') {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 2
        if ($response.StatusCode -ne 200) { return $false }
        if ($ExpectedService) {
            $data = $response.Content | ConvertFrom-Json
            return $data.status -eq 'ok' -and $data.service -eq $ExpectedService
        }
        return $true
    } catch { return $false }
}

function Test-RecordedProcess($Record, [string]$ExpectedScript) {
    $processId = 0
    if (-not [int]::TryParse([string]$Record.ProcessId, [ref]$processId) -or $processId -le 0) { return $false }
    if ($Record.ScriptPath -ne $ExpectedScript) { return $false }
    $ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if (-not $ownedProcess -or -not $ownedProcess.CreationDate -or -not $ownedProcess.CommandLine) { return $false }
    $scriptPattern = '^\s*(?:"[^"]+"|\S+)\s+(?:"' + [regex]::Escape($ExpectedScript) + '"|' + [regex]::Escape($ExpectedScript) + ')(?:\s|$)'
    return (
        $ownedProcess.ExecutablePath -eq $Record.ExecutablePath -and
        [string]$ownedProcess.CreationDate.ToUniversalTime().Ticks -eq [string]$Record.CreationTicks -and
        $ownedProcess.CommandLine -match $scriptPattern
    )
}

function Start-LocalService {
    param(
        [string]$Name, [int]$ServicePort, [string]$ScriptPath,
        [string]$PythonExe, [string]$HealthUrl, [string]$ExpectedService = '',
        [string[]]$ExtraArgs = @()
    )
    $ScriptPath = [IO.Path]::GetFullPath($ScriptPath)
    if (-not (Test-Path -LiteralPath $ScriptPath)) { throw "$Name script not found: $ScriptPath" }
    if (-not (Test-Path -LiteralPath $PythonExe)) { throw "$Name Python not found: $PythonExe" }
    $recordPath = Join-Path $runtimePath "$Name.process.json"
    if (Test-Path -LiteralPath $recordPath) {
        $record = $null
        try { $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json } catch {}
        if ($record -and (Test-RecordedProcess $record $ScriptPath)) {
            if ($record.HealthUrl -ne $HealthUrl) {
                throw "$Name is already running at $($record.HealthUrl). Stop it before changing ports."
            }
            if (Test-ServiceHealth $HealthUrl $ExpectedService) {
                Write-Host "[ok] $Name already running and healthy (PID $($record.ProcessId))"
                return
            }
            throw "$Name has a recorded live process but is unhealthy. See .runtime/$Name.log.err."
        }
        Write-Host "[stale] $Name process record is invalid or expired; no process was stopped."
        Remove-Item -LiteralPath $recordPath -Force
    }
    $listeners = @(Get-NetTCPConnection -LocalPort $ServicePort -State Listen -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 0) {
        throw "Port $ServicePort is already occupied by an unowned process. No process was stopped."
    }
    $logPath = Join-Path $runtimePath "$Name.log"
    $arguments = @(('"' + $ScriptPath + '"')) + $ExtraArgs
    $startedProcess = Start-Process -FilePath $PythonExe -ArgumentList $arguments `
        -WorkingDirectory (Split-Path -Parent $ScriptPath) -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $logPath -RedirectStandardError "$logPath.err"
    $ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($startedProcess.Id)"
    if (-not $ownedProcess -or -not $ownedProcess.CreationDate -or -not $ownedProcess.ExecutablePath) {
        throw "$Name exited before ownership could be recorded. See $logPath.err."
    }
    $record = [ordered]@{
        ProcessId = $startedProcess.Id
        CreationTicks = [string]$ownedProcess.CreationDate.ToUniversalTime().Ticks
        ExecutablePath = $ownedProcess.ExecutablePath
        ScriptPath = $ScriptPath
        HealthUrl = $HealthUrl
    }
    $record | ConvertTo-Json | Set-Content -LiteralPath $recordPath -Encoding UTF8
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        if (Test-ServiceHealth $HealthUrl $ExpectedService) {
            Write-Host "[ok] $Name healthy at $HealthUrl (PID $($startedProcess.Id))"
            return
        }
        $startedProcess.Refresh()
        if ($startedProcess.HasExited) {
            Remove-Item -LiteralPath $recordPath -Force
            throw "$Name exited early. See $logPath.err."
        }
        Start-Sleep -Milliseconds 500
    }
    if (Test-RecordedProcess $record $ScriptPath) {
        Stop-Process -Id $startedProcess.Id -ErrorAction Stop
        Remove-Item -LiteralPath $recordPath -Force
    }
    throw "$Name did not become healthy. Its owned startup process was stopped. See $logPath.err."
}

Start-LocalService -Name 'web-studio' -ServicePort $Port -ScriptPath (Join-Path $PSScriptRoot 'app.py') `
    -PythonExe $projectPython -HealthUrl "http://127.0.0.1:$Port/api/health" -ExpectedService 'ontology-web-studio'

if ($WithMvStudio) {
    $mvPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'demo\02_maketing\web_server.py'
    if (-not $MvPython) {
        $systemPython = Get-Command python -ErrorAction SilentlyContinue
        $MvPython = if ($systemPython) { $systemPython.Source } else { $projectPython }
    }
    Start-LocalService -Name 'mv-studio' -ServicePort 8766 -ScriptPath $mvPath `
        -PythonExe $MvPython -HealthUrl 'http://127.0.0.1:8766/' -ExtraArgs @('--port', '8766')
}

if ($WithFuseki) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is required for -WithFuseki.' }
    if (-not $env:FUSEKI_ADMIN_PASSWORD) { throw 'Set FUSEKI_ADMIN_PASSWORD explicitly before requesting optional Fuseki.' }
    docker compose --project-name ontology-local -f docker-compose.yml -f compose.fuseki.yml up -d fuseki
    if ($LASTEXITCODE -ne 0) { throw 'Optional Fuseki startup failed.' }
    $fusekiHealthy = $false
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (Test-ServiceHealth 'http://127.0.0.1:3030/$/ping') { $fusekiHealthy = $true; break }
        Start-Sleep -Milliseconds 500
    }
    if (-not $fusekiHealthy) { throw 'Fuseki was requested but did not pass its local health check.' }
    Write-Host '[ok] Fuseki is healthy at http://127.0.0.1:3030'
}

if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$Port" }
Write-Host 'Stop the studio with: powershell -ExecutionPolicy Bypass -File .\stop_all.ps1'
