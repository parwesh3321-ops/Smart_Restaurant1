#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [ ! -x .venv/bin/python ]; then
  echo 'First run: bash SETUP_MAC.command'
  exit 1
fi
.venv/bin/python init_db.py
printf '\nOpen http://127.0.0.1:5001 in your browser. Press Control+C to stop.\n'
exec .venv/bin/python app.py
