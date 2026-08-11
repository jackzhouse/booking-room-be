#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$script_dir"

if [[ -x "venv/bin/python" ]]; then
  python_bin="venv/bin/python"
elif [[ -x ".venv/bin/python" ]]; then
  python_bin=".venv/bin/python"
else
  echo "Virtual environment not found. Create it with: python3 -m venv venv" >&2
  exit 1
fi

exec "$python_bin" -m uvicorn app.main:app --reload --host 0.0.0.0 --port "${PORT:-8000}"
