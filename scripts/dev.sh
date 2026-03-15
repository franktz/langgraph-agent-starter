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
print(data.get("server", {}).get("host", "0.0.0.0"))
PY
)}"

PORT="${PORT:-$("$PYTHON_BIN" - "$CONFIG_PATH" <<'PY'
from pathlib import Path
import sys
import yaml

path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
print(data.get("server", {}).get("port", 8080))
PY
)}"

uv sync --python 3.12 --all-extras
uv run --python 3.12 uvicorn --app-dir src app.main:app --host "$HOST" --port "$PORT" --reload
