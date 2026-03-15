# Dynamic Config Component

## What It Is

`langgraph-agent-starter` uses the published PyPI package
`dynamic-config-nacos` for reusable dynamic configuration.

The component provides:

- Nacos YAML loading
- local YAML fallback
- safe nested config access
- dynamic refresh with watcher-style updates
- backend selection across `http`, `sdk_v2`, `sdk_v3`, and `auto`

Core exports:

- `dynamic_config.DynamicConfigProvider`
- `dynamic_config.NacosSettings`
- `dynamic_config.NacosBackendType`
- `dynamic_config.Conf`

## Reuse Boundary

This component does not depend on `langgraph-agent-starter` specific runtime
layers such as:

- FastAPI
- LangGraph
- Langfuse
- workflow registry wiring

That makes it reusable from other services without pulling in the whole
application scaffold.

## Basic Example

```python
from dynamic_config import DynamicConfigProvider, NacosSettings

provider = DynamicConfigProvider(local_yaml_path="configs/service.yaml")
provider.load_initial(
    NacosSettings(
        server_addr="127.0.0.1:8848",
        namespace="public",
        data_id="service.yaml",
        group="DEFAULT_GROUP",
        username="nacos",
        password="nacos",
    )
)

timeout_s = provider.get("http.timeout_s", 5)
retry_attempts = provider.conf.http.retry.attempts.value
```

## Env Example

```python
from dynamic_config import DynamicConfigProvider

provider = DynamicConfigProvider(local_yaml_path="configs/service.yaml")
provider.load_from_env(
    default_data_id="service.yaml",
    default_group="DEFAULT_GROUP",
)
```

Supported environment variables:

- `LOCAL_CONFIG_PATH`
- `NACOS_SERVER_ADDR`
- `NACOS_NAMESPACE`
- `NACOS_DATA_ID`
- `NACOS_GROUP`
- `NACOS_USERNAME`
- `NACOS_PASSWORD`
- `NACOS_BACKEND`
- `NACOS_POLLING_INTERVAL_SECONDS`

## Access Patterns

```python
conf = provider.conf

value1 = conf["a.b[0].c"]
value2 = conf.a.b[0].c.value
value3 = conf["a"]["b"][0]["c"]
value4 = conf.get("missing.path", "fallback")
```

Missing paths do not raise exceptions:

- `conf.a.b[0].c.value` resolves to `None`
- `conf.get("a.b[0].c", "fallback")` returns the explicit default

## Backend Modes

Supported backends:

- `http`
  Uses the Nacos OpenAPI with polling-based refresh.
- `sdk_v2`
  Forces the older Python SDK integration path.
- `sdk_v3`
  Forces the newer Python SDK integration path.
- `auto`
  Detects the Nacos major version first, then prefers the matching SDK and
  falls back to `http` if needed.

Example:

```yaml
nacos:
  server_addr: 127.0.0.1:8848
  group: DEFAULT_GROUP
  backend: auto
  polling_interval_seconds: 2
```

## Dynamic Update Semantics

- `http` backend uses polling and is the most conservative option.
- `sdk_v2` and `sdk_v3` use listener-style updates when the local SDK supports them.
- When Nacos is unavailable, the provider falls back to local YAML.
- Once config changes are applied, the in-memory `Conf` view is refreshed too.

## Workflow Config Example In This Repo

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

`WorkflowConfigRegistry` then builds one `DynamicConfigProvider` per workflow.

## Notes

- `systemkey` is a business request header, not part of the config component itself.
- The config component is responsible only for loading, refreshing, and exposing config.
