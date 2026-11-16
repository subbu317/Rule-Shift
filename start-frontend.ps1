# Run in a second PowerShell terminal.
Set-Location (Join-Path $PSScriptRoot 'frontend')
if (-not (Test-Path '.\node_modules')) {
  Write-Error 'Frontend dependencies not installed. Run npm.cmd install from the frontend folder.'
  exit 1
}
npm.cmd run dev
