#!/usr/bin/env bash

set -euo pipefail

export NACOS_SERVER_ADDR="${NACOS_SERVER_ADDR:-127.0.0.1:8848}"
export NACOS_DATA_ID="${NACOS_DATA_ID:-langgraph-agent-starter.yaml}"
export NACOS_GROUP="${NACOS_GROUP:-DEFAULT_GROUP}"
export NACOS_USERNAME="${NACOS_USERNAME:-nacos}"
export NACOS_PASSWORD="${NACOS_PASSWORD:-nacos}"

exec uv run --python 3.12 uvicorn \
  --app-dir src \
  app.main:app \
  --host "${HOST:-127.0.0.1}" \
  --port "${PORT:-8080}"
