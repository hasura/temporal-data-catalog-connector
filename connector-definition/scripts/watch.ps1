$ErrorActionPreference = "Stop"

$scriptDir = Get-Location

& ./check-reqs.ps1

Push-Location $env:HASURA_PLUGIN_CONNECTOR_CONTEXT_PATH
try {
  # Activate virtual environment if it exists
  if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
  }
  
  # Run watchdog to watch for file changes and restart the Python script
  watchmedo auto-restart --pattern="*.py" --recursive -- python3 connector-definition/template/functions.py serve --configuration ./
} finally {
  Pop-Location
}