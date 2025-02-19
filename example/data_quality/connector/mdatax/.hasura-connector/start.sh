#!/usr/bin/env bash
set -eu -o pipefail

script_dir=$(pwd)

./check-reqs.sh

cd $HASURA_PLUGIN_CONNECTOR_CONTEXT_PATH

# Activate virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
fi

# Run the Python script with the serve command
python3 connector-definition/template/functions.py serve --configuration ./