# Usage Guide

[中文版本](usage.zh-CN.md)

## API

- `GET /v1/models`
- `POST /v1/chat/completions`
- `GET /health`
- `GET /health/details`

## Header Conventions

- `systemKey`
  Business system identifier. The field name is intentionally kept as `systemKey`.
- `session-id`
  Conversation or thread identifier.
- `user-id`
  End-user identifier from the caller side.

## Routing Rules

- `model -> workflow`
  The OpenAI-style `model` field selects which workflow graph to run.
- `systemKey -> llm profile`
  The request header `systemKey` selects the current business-facing LLM profile.

## Chat Completion Behavior

### Non-stream

- regular workflows return a standard assistant message
- HITL workflows return `tool_calls` when interrupted
- responses include lightweight `usage`

### Stream

- the first chunk returns `role=assistant`
- regular workflows stream content chunks and finish with `finish_reason=stop`
- HITL workflows stream `tool_calls` and finish with `finish_reason=tool_calls`
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
- `api.auth.systems`
- `api.defaults.workflow`
- `llm.profiles`
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
    systems:
      - key: reporting-system
        default_llm_profile: reporting-profile
```

Then add the matching LLM profile:

```yaml
llm:
  profiles:
    reporting-profile:
      provider: openai_compatible
      base_url: https://example.com/v1
      api_key: your-key
      model: your-model
      timeout_s: 30
```

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
- metadata fields such as `systemKey`, `workflow`, and `llm_profile`
- tags such as `workflow:<workflow>`, `systemKey:<systemKey>`, and `llm_profile:<profile>`

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

### Register the Workflow

Register the graph in `src/workflows/registry.py`.

### Expose It to Callers

Callers select workflows through the OpenAI-style `model` field.
If a workflow should only serve certain systems, combine that with `systemKey`
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
