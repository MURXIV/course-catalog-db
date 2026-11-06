$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:PGCLIENTENCODING = 'UTF8'
$labPython = Join-Path (Split-Path -Parent $PSScriptRoot) 'course-catalog-api\.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $labPython)) {
    throw 'Install Python and psycopg[binary], then run: python run_bonus.py'
}
& $labPython run_bonus.py @args
if ($LASTEXITCODE -ne 0) { throw 'A Lab 6 bonus check failed. Read the error above.' }
