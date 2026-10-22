#!/bin/bash
# Start the board web demo on the SDK.
#   demo/run.sh [--port 8765] [--models <package-root>]
# Env: A8_CLOCK_MS (160 | 80, default: the installed one), A8_LANG (en | zh, default en), A8_MODELS (default
#      <repo>/models), AUDIO8_ASR_LIB (default sdk/lib/libaudio8_asr.so, else sdk/build/).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
PYTHON="$ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "Missing demo virtual environment: $ROOT/.venv" >&2
  echo "From the repository root, run: python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt" >&2
  exit 1
fi
for d in "$ROOT/sdk/lib" "$ROOT/sdk/build"; do
  if [ -f "$d/libaudio8_asr.so" ]; then export LD_LIBRARY_PATH="$d${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; break; fi
done
export LD_LIBRARY_PATH="/usr/local/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$PYTHON" -u "$HERE/demo_server.py" "$@"
