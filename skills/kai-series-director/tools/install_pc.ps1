param(
  [Parameter(Mandatory=$true)][string]$ZipPath,
  [Parameter(Mandatory=$true)][string]$ExpectedSha256
)
$ErrorActionPreference = 'Stop'
$target = Join-Path $HOME '.codex\skills\kai-series-director'
if (Test-Path -LiteralPath $target) { throw 'Existing skill detected. ABORT: compare with original first.' }
$actual = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $ExpectedSha256.ToLowerInvariant()) { throw 'ZIP SHA-256 differs. ABORT.' }
$stage = Join-Path $env:TEMP ('kai-series-director-stage-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $stage -Force | Out-Null
try {
  Expand-Archive -LiteralPath $ZipPath -DestinationPath $stage
  if (!(Test-Path (Join-Path $stage 'SKILL.md'))) { throw 'Not a valid skill package' }
  $manifest = Get-Content (Join-Path $stage 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
  foreach ($entry in $manifest.files_sha256.PSObject.Properties) {
    $file = Join-Path $stage ($entry.Name.Replace('/','\'))
    if (!(Test-Path -LiteralPath $file)) { throw "Missing file: $($entry.Name)" }
    $sha = (Get-FileHash -LiteralPath $file -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($sha -ne $entry.Value.ToLowerInvariant()) { throw "File hash differs: $($entry.Name)" }
  }
  Push-Location $stage
  try {
    & python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
    & python scripts/director_gate.py fixtures/film_plan.json | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Film plan smoke failed' }
  } finally { Pop-Location }
  New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
  Move-Item -LiteralPath $stage -Destination $target
  Write-Host "Installed in $target with ZIP SHA-256 $actual"
  Write-Host 'NOTICE: independent Codex installation; not installed automatically in ChatGPT/Work.'
} finally {
  if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force }
}
