<#
.SYNOPSIS
Stops owned studio processes, verifying script, executable and creation time.
#>
param([switch]$WithFuseki, [switch]$WithMvStudio)

$ErrorActionPreference = 'Stop'
$runtimePath = Join-Path $PSScriptRoot '.runtime'
$serviceScripts = @{ 'web-studio' = (Join-Path $PSScriptRoot 'app.py') }
if ($WithMvStudio) {
    $serviceScripts['mv-studio'] = Join-Path (Split-Path -Parent $PSScriptRoot) 'demo\02_maketing\web_server.py'
}

foreach ($name in $serviceScripts.Keys) {
    $recordPath = Join-Path $runtimePath "$name.process.json"
    if (-not (Test-Path -LiteralPath $recordPath)) {
        Write-Host "[skip] ${name}: no ownership record; no process was stopped."
        continue
    }
    $record = $null
    try { $record = Get-Content -LiteralPath $recordPath -Raw | ConvertFrom-Json } catch {}
    $processId = 0
    if (-not $record -or -not [int]::TryParse([string]$record.ProcessId, [ref]$processId) -or $processId -le 0) {
        Write-Host "[stale] ${name}: invalid process record; no process was stopped."
        Remove-Item -LiteralPath $recordPath -Force
        continue
    }
    $expectedScript = [IO.Path]::GetFullPath($serviceScripts[$name])
    $scriptPattern = '^\s*(?:"[^"]+"|\S+)\s+(?:"' + [regex]::Escape($expectedScript) + '"|' + [regex]::Escape($expectedScript) + ')(?:\s|$)'
    $ownedProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if (-not $ownedProcess) {
        Write-Host "[skip] ${name}: recorded process has already stopped."
    } elseif (
        $record.ScriptPath -eq $expectedScript -and
        $ownedProcess.ExecutablePath -eq $record.ExecutablePath -and
        $ownedProcess.CreationDate -and
        [string]$ownedProcess.CreationDate.ToUniversalTime().Ticks -eq [string]$record.CreationTicks -and
        $ownedProcess.CommandLine -and
        $ownedProcess.CommandLine -match $scriptPattern
    ) {
        Stop-Process -Id $processId -ErrorAction Stop
        Wait-Process -Id $processId -Timeout 5 -ErrorAction SilentlyContinue
        if (Get-Process -Id $processId -ErrorAction SilentlyContinue) { throw "$name did not terminate." }
        Write-Host "[ok] $name stopped (PID $processId)."
    } else {
        Write-Host "[stale] ${name}: PID ownership does not match; no process was stopped."
    }
    Remove-Item -LiteralPath $recordPath -Force
}

if ($WithFuseki) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw 'Docker is required for -WithFuseki.' }
    # Filter by the exact project/service labels. Stop needs no service password.
    $containerIds = @(docker ps -q --filter 'label=com.docker.compose.project=ontology-local' --filter 'label=com.docker.compose.service=fuseki')
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect optional Fuseki containers.' }
    if ($containerIds.Count -gt 0) {
        docker stop $containerIds
        if ($LASTEXITCODE -ne 0) { throw 'Optional Fuseki stop failed.' }
        $remaining = @(docker ps -q --filter 'label=com.docker.compose.project=ontology-local' --filter 'label=com.docker.compose.service=fuseki')
        if ($LASTEXITCODE -ne 0 -or $remaining.Count -gt 0) { throw 'Fuseki did not terminate.' }
        Write-Host '[ok] Fuseki stopped.'
    } else { Write-Host '[skip] No running Fuseki container owned by ontology-local.' }
}
