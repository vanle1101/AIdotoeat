param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('install','start','check','migrate','backup','restore','rollback')]
  [string]$Action,
  [string]$Source,
  [string]$Destination,
  [string]$ReleaseRoot,
  [string]$CurrentLink,
  [string]$Target,
  [string]$Url = 'http://127.0.0.1:8450',
  [switch]$WithBrowser
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Python = if (Test-Path -LiteralPath $VenvPython) { $VenvPython } else { 'python' }

switch ($Action) {
  'install' {
    if (-not (Test-Path -LiteralPath $VenvPython)) {
      & python -m venv (Join-Path $Root '.venv')
      if ($LASTEXITCODE -ne 0) { throw 'Could not create Python 3.12 virtual environment.' }
    }
    $Python = $VenvPython
    $PythonVersion = & $Python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    if ($PythonVersion -ne '3.12') { throw "Python 3.12 is required; found $PythonVersion." }
    $Lock = Join-Path $Root 'requirements-dev.lock.txt'
    if ($env:AUTOPROFIT_WHEELHOUSE) {
      & $Python -m pip install --require-hashes --no-index --find-links $env:AUTOPROFIT_WHEELHOUSE -r $Lock
    } else {
      & $Python -m pip install --require-hashes -r $Lock
    }
    if ($LASTEXITCODE -ne 0) { throw 'Pinned dependency installation failed.' }
    if ($WithBrowser) {
      & $Python -m playwright install chromium
      if ($LASTEXITCODE -ne 0) { throw 'Chromium installation failed.' }
    }
    $EnvFile = Join-Path $Root '.env'
    if (-not (Test-Path -LiteralPath $EnvFile)) {
      Copy-Item -LiteralPath (Join-Path $Root '.env.example') -Destination $EnvFile
      Write-Output 'Created .env from placeholders. Set owner credentials locally; this script never overwrites it.'
    }
  }
  'start' {
    Set-Location $Root
    & $Python -m uvicorn main:app --app-dir (Join-Path $Root 'backend') --host 127.0.0.1 --port 8450 --workers 1
    exit $LASTEXITCODE
  }
  'check' {
    & $Python (Join-Path $Root 'scripts\ops.py') check --url $Url
    exit $LASTEXITCODE
  }
  'migrate' {
    $CommandArgs = @((Join-Path $Root 'scripts\ops.py'), 'migrate')
    if ($Destination) { $CommandArgs += @('--backup', $Destination) }
    & $Python @CommandArgs
    exit $LASTEXITCODE
  }
  'backup' {
    if (-not $Destination) { throw '-Destination must name a new backup file in an existing directory.' }
    & $Python (Join-Path $Root 'scripts\ops.py') backup --destination $Destination
    exit $LASTEXITCODE
  }
  'restore' {
    if (-not $Source -or -not $Destination) { throw 'Use -Source backup.sqlite -Destination new-database.sqlite.' }
    & $Python (Join-Path $Root 'scripts\ops.py') restore --source $Source --destination $Destination
    exit $LASTEXITCODE
  }
  'rollback' {
    if (-not $ReleaseRoot -or -not $CurrentLink -or -not $Target) { throw 'Provide -ReleaseRoot, -CurrentLink, and exact -Target release name.' }
    & $Python (Join-Path $Root 'scripts\ops.py') rollback --releases-root $ReleaseRoot --current-link $CurrentLink --target $Target
    exit $LASTEXITCODE
  }
}
