# 动态配置说明

[English](dynamic_config.md)

## 它是什么

`langgraph-agent-starter` 通过 PyPI 包 `dynamic-config-nacos` 复用动态配置能力。

这个组件支持：

- 读取 Nacos YAML 配置
- 本地 YAML fallback
- 安全的多层级配置访问
- watcher 风格的动态刷新
- `http`、`sdk_v2`、`sdk_v3`、`auto` 四种 backend 策略

对外暴露的核心类型：

- `dynamic_config.DynamicConfigProvider`
- `dynamic_config.NacosSettings`
- `dynamic_config.NacosBackendType`
- `dynamic_config.Conf`

## 复用边界

这个组件不依赖 `langgraph-agent-starter` 特有的运行时层，例如：

- FastAPI
- LangGraph
- Langfuse
- workflow registry 注入逻辑

因此其他服务可以直接复用，而不需要把整个脚手架一起带上。

## 基本示例

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

## 环境变量示例

```python
from dynamic_config import DynamicConfigProvider

provider = DynamicConfigProvider(local_yaml_path="configs/service.yaml")
provider.load_from_env(
    default_data_id="service.yaml",
    default_group="DEFAULT_GROUP",
)
```

支持的环境变量：

- `LOCAL_CONFIG_PATH`
- `NACOS_SERVER_ADDR`
- `NACOS_NAMESPACE`
- `NACOS_DATA_ID`
- `NACOS_GROUP`
- `NACOS_USERNAME`
- `NACOS_PASSWORD`
- `NACOS_BACKEND`
- `NACOS_POLLING_INTERVAL_SECONDS`

## 访问方式

```python
conf = provider.conf

value1 = conf["a.b[0].c"]
value2 = conf.a.b[0].c.value
value3 = conf["a"]["b"][0]["c"]
value4 = conf.get("missing.path", "fallback")
```

当路径不存在时不会抛异常：

- `conf.a.b[0].c.value` 最终得到 `None`
- `conf.get("a.b[0].c", "fallback")` 会返回显式默认值

## Backend 模式

支持的 backend：

- `http`
  使用 Nacos OpenAPI + 轮询刷新
- `sdk_v2`
  强制走旧版 Python SDK
- `sdk_v3`
  强制走新版 Python SDK
- `auto`
  先探测 Nacos 主版本，再优先尝试匹配的 SDK，失败后回退到 `http`

示例：

```yaml
nacos:
  server_addr: 127.0.0.1:8848
  group: DEFAULT_GROUP
  backend: auto
  polling_interval_seconds: 2
```

## 动态更新语义

- `http` backend 使用轮询，行为最稳妥
- `sdk_v2` / `sdk_v3` 在本地 SDK 支持时会使用监听式更新
- 当 Nacos 不可用时，会回退到本地 YAML
- 配置内容更新后，内存中的 `Conf` 视图也会同步刷新

## 本仓库中的 Workflow 配置示例

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

随后由 `WorkflowConfigRegistry` 为每张图构造独立的 `DynamicConfigProvider`。

## 备注

- `systemKey` 是业务请求头字段，不属于动态配置组件本身
- 动态配置组件只负责加载、刷新和暴露配置，不负责业务路由和工作流执行
