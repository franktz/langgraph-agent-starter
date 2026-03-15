# Usage Guide

[中文版](usage.zh-CN.md)

## API

- `GET /v1/models`
- `POST /v1/chat/completions`
- `GET /health`
- `GET /health/details`

## Header Conventions

- `systemkey`
  Business system identifier. The primary request header is `systemkey`.
- `session-id`
  Conversation or thread identifier.
- `user-id`
  End-user identifier from the caller side.

## Routing Rules

- `model -> workflow`
  The OpenAI-style `model` field selects which workflow graph to run.
  It is required; missing `model` returns `400 missing_model`.
- `systemkey -> business scope`
  The request header `systemkey` is used for caller identity, business
  isolation, and optional validation. It no longer selects the LLM
  configuration.

## Chat Completion Behavior

### Non-stream

- regular workflows return a standard assistant message
- HITL workflows return `tool_calls` when interrupted
- responses include lightweight `usage`

### Stream

- the first chunk returns `role=assistant`
- regular workflows stream real content deltas and finish with
  `finish_reason=stop`
- HITL workflows can stream draft content first, then emit `tool_calls`, and
  finish with `finish_reason=tool_calls`
- the stream terminates with `data: [DONE]`

### HITL Resume

To resume a HITL flow:

1. keep using the same `session-id`
2. call `POST /v1/chat/completions` again
3. place the human-confirmed content in the last `tool` message

## Platform Engineer Guide

### Important Root Config Fields

- `server.host`
- `server.port`
- `server.workers`
- `api.auth.enabled`
- `api.auth.systemkeys`
- `langgraph.checkpointer`
- `langfuse`
- `workflow_configs`
- `nacos.backend`
- `nacos.polling_interval_seconds`

### Per-Workflow Config Mapping

```yaml
workflow_configs:
  defaults:
    local_dir: configs/workflows
    nacos:
      group: LANGGRAPH_AGENT_STARTER_WORKFLOW
      backend: auto
      polling_interval_seconds: 2
      data_id_template: "langgraph-agent-starter.workflow.{workflow}.yaml"
  items:
    demo_hitl:
      local_path: configs/workflows/demo_hitl.yaml
      nacos:
        data_id: langgraph-agent-starter.workflow.demo_hitl.yaml
```

### Add a New Business System

```yaml
api:
  auth:
    enabled: true
    systemkeys:
      - reporting-system
```

Then add the workflow-local default LLM definition:

```yaml
llm:
  default:
    provider: openai_compatible
    base_url: https://example.com/v1
    apikey: your-key
    headers:
      X-Tenant: your-tenant
    model: your-model
    max_tokens: 2048
    timeout: 30000
    retry:
      attempts: 2
      min_wait: 200
      max_wait: 1000
```

`timeout`, `retry.min_wait`, and `retry.max_wait` all use milliseconds. If
`retry` is omitted, that upstream LLM call is not retried. `headers` is
optional and only adds extra request headers when configured. The runtime still
sends `Content-Type: application/json` by default.

### Switch the Checkpointer Backend

- `langgraph.checkpointer.backend: memory`
- `langgraph.checkpointer.backend: redis`

If you use Redis, also configure:

- `langgraph.checkpointer.redis_url`

### Enable Langfuse

- `langfuse.enabled: true`
- `langfuse.host`
- `langfuse.public_key`
- `langfuse.secret_key`

Trace metadata automatically includes:

- top-level `session_id`
- top-level `user_id`
- metadata fields such as `systemkey` and `workflow`
- tags such as `workflow:<workflow>`, `systemkey:<systemkey>`, and
  `request_id:<request_id>`

### Push Nacos Config

Example helper script:

- `scripts/push_nacos_configs.sh`

Default publish targets:

- `configs/local.yaml`
- `configs/workflows/demo_hitl.yaml`
- `configs/workflows/demo_summary.yaml`

### Startup Modes

Development mode:

```bash
bash scripts/dev.sh
```

Production-style mode:

```bash
bash scripts/run.sh
```

Defaults:

- host comes from `server.host`, default `0.0.0.0`
- port comes from `server.port`, default `8080`
- worker count comes from `server.workers`, default `8`

You can also override them through environment variables:

```bash
HOST=0.0.0.0 PORT=18080 WORKERS=4 bash scripts/run.sh
```

## Workflow Engineer Guide

### Add a New Workflow

Create:

- `src/workflows/<name>/graph.py`
- `src/workflows/<name>/state.py`
- `src/workflows/<name>/nodes/`

### Add Workflow Config

- create `configs/workflows/<name>.yaml`
- register it under `workflow_configs.items` in the root config

### Read Workflow Config in Nodes

```python
prompt_prefix = workflow_config.get("prompts.draft_prefix", "")
```

### Resolve LLM In Nodes

```python
llm = resolve_workflow_llm(
    workflow_config=workflow_config,
)
```

`llm.name` will be `default`, and `llm.config` is the full config for that
model.

### Register the Workflow

Register the graph in `src/workflows/registry.py`.

### Expose It to Callers

Callers select workflows through the OpenAI-style `model` field.
If a workflow should only serve certain systems, combine that with `systemkey`
for business isolation.

## Nacos Backend Options

Both root config and workflow config support:

- `backend: http`
- `backend: sdk_v2`
- `backend: sdk_v3`
- `backend: auto`

## Dynamic Config Reuse

Other projects can reuse the dynamic config capability directly:

```python
from dynamic_config import DynamicConfigProvider, NacosSettings
```

See [Dynamic Config](dynamic_config.md) for details.
