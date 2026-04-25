#!/usr/bin/env sh
# Render: must listen on $PORT and 0.0.0.0 — see https://render.com/docs/web-services#port-binding
set -e
# Always run from this script's directory (backend/) so `app` package resolves.
cd "$(dirname "$0")"
export PYTHONPATH="."
# Render sets PORT; local smoke test: PORT=8000 sh start-render.sh
if [ -z "${PORT}" ]; then
  echo "warning: PORT unset, using 8000" >&2
  export PORT=8000
fi
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
