$ErrorActionPreference = "Stop"

$scriptDir = Get-Location

& ./check-reqs.ps1

Push-Location $env:HASURA_PLUGIN_CONNECTOR_CONTEXT_PATH
try {
  # Activate virtual environment if it exists
  if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
  }
  
  # Run the Python script with the serve command
  python3 connector-definition/template/functions.py serve --configuration ./
} finally {
  Pop-Location
}