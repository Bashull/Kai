param(
  [Parameter(Mandatory = $true)]
  [string]$NodeExe,

  [Parameter(Mandatory = $true)]
  [string]$AgentScript,

  [Parameter(Mandatory = $true)]
  [string]$WorkingDirectory
)

$ErrorActionPreference = 'Stop'
$taskName = 'KAI Nervous Link PC Agent'

foreach ($path in @($NodeExe, $AgentScript, $WorkingDirectory)) {
  if (-not (Test-Path -LiteralPath $path)) {
    throw "Required path does not exist: $path"
  }
}

$action = New-ScheduledTaskAction `
  -Execute $NodeExe `
  -Argument ('"' + $AgentScript + '"') `
  -WorkingDirectory $WorkingDirectory

$trigger = New-ScheduledTaskTrigger -AtLogOn
$principal = New-ScheduledTaskPrincipal `
  -UserId $env:USERNAME `
  -LogonType Interactive `
  -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
  -RestartCount 10 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -ExecutionTimeLimit (New-TimeSpan -Days 3650)

Register-ScheduledTask `
  -TaskName $taskName `
  -Action $action `
  -Trigger $trigger `
  -Principal $principal `
  -Settings $settings `
  -Force | Out-Null

Write-Host "Installed user-level task: $taskName"
Write-Host 'Run level: Limited (no silent administrator elevation).'
