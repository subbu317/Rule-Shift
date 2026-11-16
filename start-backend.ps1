# Run in a dedicated PowerShell terminal from the extracted repository.
Set-Location (Join-Path $PSScriptRoot 'backend')
$python = Join-Path (Get-Location) '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
  Write-Error 'Backend virtual environment not found. Follow the README setup instructions first.'
  exit 1
}
& $python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
