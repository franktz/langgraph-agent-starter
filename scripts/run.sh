#!/usr/bin/env bash

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python"
fi

CONFIG_PATH="${LOCAL_CONFIG_PATH:-configs/local.yaml}"

HOST="${HOST:-$("$PYTHON_BIN" - "$CONFIG_PATH" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
server = data.get("server", {})
print(server.get("host", "0.0.0.0"))
PY
)}"

PORT="${PORT:-$("$PYTHON_BIN" - "$CONFIG_PATH" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
server = data.get("server", {})
print(server.get("port", 8080))
PY
)}"

WORKERS="${WORKERS:-$("$PYTHON_BIN" - "$CONFIG_PATH" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
server = data.get("server", {})
print(server.get("workers", 8))
PY
)}"

exec uv run --python 3.12 gunicorn \
  --chdir src \
  --bind "${HOST}:${PORT}" \
  --workers "${WORKERS}" \
  --worker-class uvicorn.workers.UvicornWorker \
  app.main:app
