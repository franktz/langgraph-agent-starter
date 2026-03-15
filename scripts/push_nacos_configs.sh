#!/usr/bin/env bash

set -euo pipefail

NACOS_ADDR="${NACOS_ADDR:-http://127.0.0.1:8848}"
NACOS_NAMESPACE="${NACOS_NAMESPACE:-}"

publish_config() {
  local data_id="$1"
  local group="$2"
  local file_path="$3"

  if [[ ! -f "$file_path" ]]; then
    echo "missing config file: $file_path" >&2
    exit 1
  fi

  local tenant_args=()
  if [[ -n "$NACOS_NAMESPACE" ]]; then
    tenant_args+=(--data-urlencode "tenant=${NACOS_NAMESPACE}")
  fi

  curl --fail --silent --show-error \
    -X POST "${NACOS_ADDR%/}/nacos/v1/cs/configs" \
    --data-urlencode "dataId=${data_id}" \
    --data-urlencode "group=${group}" \
    "${tenant_args[@]}" \
    --data-urlencode "type=yaml" \
    --data-urlencode "content@${file_path}" >/dev/null

  echo "published ${group}/${data_id}"
}

publish_config "langgraph-agent-starter.yaml" "DEFAULT_GROUP" "configs/local.yaml"
publish_config "langgraph-agent-starter.workflow.demo_chat.yaml" "LANGGRAPH_AGENT_STARTER_WORKFLOW" "configs/workflows/demo_chat.yaml"
publish_config "langgraph-agent-starter.workflow.demo_hitl.yaml" "LANGGRAPH_AGENT_STARTER_WORKFLOW" "configs/workflows/demo_hitl.yaml"
publish_config "langgraph-agent-starter.workflow.demo_summary.yaml" "LANGGRAPH_AGENT_STARTER_WORKFLOW" "configs/workflows/demo_summary.yaml"
