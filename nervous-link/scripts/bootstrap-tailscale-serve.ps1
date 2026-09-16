$ErrorActionPreference = 'Stop'

$report = [ordered]@{
    schema = 'kai-link-tailscale-bootstrap-v1'
    timestamp = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    user = $env:USERNAME
    ok = $false
    tailscale = [ordered]@{}
    relay = [ordered]@{}
    serve = [ordered]@{}
    report_paths = @()
    error = $null
}

function Save-KaiReport {
    param([hashtable]$Data)
    $json = $Data | ConvertTo-Json -Depth 12
    $targets = New-Object System.Collections.Generic.List[string]

    $localState = 'C:\Kai\Relay\state'
    if (-not (Test-Path $localState)) { New-Item -ItemType Directory -Force -Path $localState | Out-Null }
    $targets.Add((Join-Path $localState 'KAI_LINK_TAILSCALE_BOOTSTRAP_CURRENT.json'))

    $driveRoots = @(
        (Join-Path $env:USERPROFILE 'Mi unidad'),
        (Join-Path $env:USERPROFILE 'My Drive')
    )
    foreach ($root in $driveRoots) {
        if (-not (Test-Path $root)) { continue }
        $core = Join-Path $root 'KAI\00_KAI_CORE'
        if (Test-Path $core) {
            $runtimeReports = Join-Path $core 'KAI_LINK_RUNTIME_REPORTS'
            if (-not (Test-Path $runtimeReports)) { New-Item -ItemType Directory -Force -Path $runtimeReports | Out-Null }
            $targets.Add((Join-Path $runtimeReports 'KAI_LINK_TAILSCALE_BOOTSTRAP_CURRENT.json'))
        }
    }

    foreach ($path in ($targets | Select-Object -Unique)) {
        $json | Set-Content -LiteralPath $path -Encoding utf8
        $Data.report_paths += $path
    }

    # Rewrite once so report_paths are included in the persisted report.
    $json = $Data | ConvertTo-Json -Depth 12
    foreach ($path in ($targets | Select-Object -Unique)) {
        $json | Set-Content -LiteralPath $path -Encoding utf8
    }
}

function Get-TailscaleState {
    param([string]$TailscaleExe)
    $raw = (& $TailscaleExe status --json 2>&1 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "tailscale status failed: $raw" }
    return ($raw | ConvertFrom-Json)
}

try {
    $tsCandidates = @(
        (Join-Path $env:ProgramFiles 'Tailscale\tailscale.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Tailscale\tailscale.exe')
    ) | Where-Object { $_ -and (Test-Path $_) }
    if (-not $tsCandidates) { throw 'tailscale.exe not found' }
    $ts = $tsCandidates[0]
    $report.tailscale.executable = $ts

    $state = Get-TailscaleState -TailscaleExe $ts
    if ($state.BackendState -ne 'Running') {
        $upText = (& $ts up 2>&1 | Out-String)
        $report.tailscale.up_initial_output = $upText.Trim()
        if ($upText -match '(https://login\.tailscale\.com/\S+)') {
            $authUrl = $Matches[1].TrimEnd('.', ',', ')')
            $report.tailscale.login_authorization_requested = $true
            Start-Process $authUrl
        }
        for ($i = 0; $i -lt 24; $i++) {
            Start-Sleep -Seconds 5
            $state = Get-TailscaleState -TailscaleExe $ts
            if ($state.BackendState -eq 'Running') { break }
        }
    }
    if ($state.BackendState -ne 'Running') { throw "Tailscale backend is $($state.BackendState), not Running" }

    $dnsName = [string]$state.Self.DNSName
    $dnsName = $dnsName.Trim().TrimEnd('.')
    if (-not $dnsName) { throw 'Tailscale DNSName is empty; MagicDNS/HTTPS identity is not available yet' }
    $ip4 = ((& $ts ip -4 2>&1 | Out-String).Trim())
    if ($LASTEXITCODE -ne 0) { throw 'tailscale ip -4 failed' }

    $report.tailscale.backend_state = $state.BackendState
    $report.tailscale.dns_name = $dnsName
    $report.tailscale.ipv4 = $ip4
    $report.tailscale.tailnet = $state.MagicDNSSuffix

    $localHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8788/health' -TimeoutSec 8
    $report.relay.local_health_ok = [bool]$localHealth.ok
    $report.relay.service = [string]$localHealth.service
    $report.relay.version = [string]$localHealth.version
    if (-not $localHealth.ok) { throw 'Kai Relay local /health did not return ok=true' }

    $serveOk = $false
    for ($i = 0; $i -lt 18; $i++) {
        $serveText = (& $ts serve --bg http://127.0.0.1:8788 2>&1 | Out-String)
        $serveExit = $LASTEXITCODE
        $report.serve.last_command_output = $serveText.Trim()
        $report.serve.last_exit_code = $serveExit
        if ($serveExit -eq 0) { $serveOk = $true; break }

        if ($serveText -match '(https://login\.tailscale\.com/\S+)') {
            $serveAuthUrl = $Matches[1].TrimEnd('.', ',', ')')
            if (-not $report.serve.authorization_url_opened) {
                $report.serve.authorization_url_opened = $true
                Start-Process $serveAuthUrl
            }
            Start-Sleep -Seconds 5
            continue
        }
        break
    }
    if (-not $serveOk) { throw "tailscale serve did not start: $($report.serve.last_command_output)" }

    $serveStatus = (& $ts serve status 2>&1 | Out-String).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'tailscale serve status failed' }
    $endpoint = "https://$dnsName"
    $report.serve.status = $serveStatus
    $report.serve.endpoint = $endpoint

    $remoteHealth = Invoke-RestMethod -Uri "$endpoint/health" -TimeoutSec 12
    $report.serve.https_health_ok = [bool]$remoteHealth.ok
    $report.serve.https_service = [string]$remoteHealth.service
    if (-not $remoteHealth.ok) { throw 'Tailscale Serve HTTPS /health did not return ok=true' }

    $report.ok = $true
    Write-Host "KAI LINK TAILSCALE SERVE: VERIFIED" -ForegroundColor Green
    Write-Host "Endpoint: $endpoint"
}
catch {
    $report.error = $_.Exception.Message
    Write-Host "KAI LINK TAILSCALE SERVE: NOT VERIFIED" -ForegroundColor Yellow
    Write-Host $report.error
}
finally {
    Save-KaiReport -Data $report
    Write-Host 'Report written. Kai can read the synced Drive copy when available.'
}

if (-not $report.ok) { exit 2 }
