param(
    [Parameter(Mandatory=$true)][string]$NodeKey,
    [Parameter(Mandatory=$true)][string]$RotationKey
)

$ErrorActionPreference = 'Stop'

function Redact-Key([string]$v) {
    if (-not $v) { return $null }
    if ($v.Length -le 18) { return $v }
    return $v.Substring(0,10) + '…' + $v.Substring($v.Length-8)
}

$report = [ordered]@{
    schema = 'kai-tailnet-lock-sign-v1'
    timestamp = (Get-Date).ToString('o')
    computer = $env:COMPUTERNAME
    user = $env:USERNAME
    target_node = (Redact-Key $NodeKey)
    rotation_key = (Redact-Key $RotationKey)
    ok = $false
    signer_status_before = $null
    sign_exit_code = $null
    sign_output = $null
    signer_status_after = $null
    error = $null
    report_paths = @()
}

function Save-Report([System.Collections.IDictionary]$Data) {
    $targets = New-Object System.Collections.Generic.List[string]
    $local = 'C:\Kai\Relay\state'
    if (-not (Test-Path $local)) { New-Item -ItemType Directory -Force -Path $local | Out-Null }
    $targets.Add((Join-Path $local 'KAI_TAILNET_LOCK_SIGN_CURRENT.json'))

    $roots = @(
        (Join-Path $env:USERPROFILE 'Mi unidad'),
        (Join-Path $env:USERPROFILE 'My Drive'),
        'G:\Mi unidad',
        'G:\My Drive'
    ) | Select-Object -Unique

    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        $core = Join-Path $root 'KAI\00_KAI_CORE'
        if (-not (Test-Path $core)) { continue }
        $dir = Join-Path $core 'KAI_LINK_RUNTIME_REPORTS'
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
        $targets.Add((Join-Path $dir 'KAI_TAILNET_LOCK_SIGN_CURRENT.json'))
    }

    foreach ($p in ($targets | Select-Object -Unique)) { $Data.report_paths += $p }
    $json = $Data | ConvertTo-Json -Depth 10
    foreach ($p in ($targets | Select-Object -Unique)) { $json | Set-Content -LiteralPath $p -Encoding utf8 }
}

try {
    $ts = Join-Path ([Environment]::GetEnvironmentVariable('ProgramFiles')) 'Tailscale\tailscale.exe'
    if (-not (Test-Path $ts)) { throw 'tailscale.exe not found' }

    $before = (& $ts lock status 2>&1 | Out-String).Trim()
    $report.signer_status_before = $before

    $out = (& $ts lock sign $NodeKey $RotationKey 2>&1 | Out-String).Trim()
    $code = $LASTEXITCODE
    $report.sign_exit_code = $code
    $report.sign_output = $out
    if ($code -ne 0) { throw "tailscale lock sign failed: $out" }

    Start-Sleep -Seconds 2
    $after = (& $ts lock status 2>&1 | Out-String).Trim()
    $report.signer_status_after = $after
    $report.ok = $true
    Write-Host 'TAILNET LOCK SIGN: VERIFIED' -ForegroundColor Green
}
catch {
    $report.error = $_.Exception.Message
    Write-Host 'TAILNET LOCK SIGN: NOT VERIFIED' -ForegroundColor Yellow
    Write-Host $report.error
}
finally {
    Save-Report $report
    Write-Host 'Report written.'
}

if (-not $report.ok) { exit 2 }
