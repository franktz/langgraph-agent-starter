# 使用说明

[English](usage.md)

## API

- `GET /v1/models`
- `POST /v1/chat/completions`
- `GET /health`
- `GET /health/details`

## 请求头约定

- `systemkey`
  业务系统标识，主请求头字段为 `systemkey`
- `session-id`
  会话或线程标识
- `user-id`
  调用方传入的终端用户标识

## 路由规则

- `model -> workflow`
  OpenAI 风格请求体里的 `model` 决定要调用哪个 workflow 图
  `model` 为必填，缺失时返回 `400 missing_model`
- `systemkey -> business scope`
  请求头里的 `systemkey` 用于调用方身份、业务隔离与可选校验，
  不再决定具体使用哪个 LLM 配置

## Chat Completion 行为

### Non-stream

- 普通 workflow 返回标准 assistant message
- HITL workflow 在中断时返回 `tool_calls`
- 响应中会带轻量级 `usage`

### Stream

- 第一段 chunk 返回 `role=assistant`
- 普通 workflow 会按真实内容增量持续返回 chunk，并以 `finish_reason=stop` 结束
- HITL workflow 可以先流式返回 draft 内容，再发出 `tool_calls` chunk，并以 `finish_reason=tool_calls` 结束
- 流结束时返回 `data: [DONE]`

### HITL Resume

恢复 HITL 流程时：

1. 继续使用同一个 `session-id`
2. 再次调用 `POST /v1/chat/completions`
3. 将人工确认后的内容放到最后一条 `tool` message

## 平台工程师指南

### 重点根配置项

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

### 每张图的配置映射

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

### 新增业务系统

```yaml
api:
  auth:
    enabled: true
    systemkeys:
      - reporting-system
```

然后在 workflow 自己的配置里补充默认 LLM 定义：

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

`timeout`、`retry.min_wait` 和 `retry.max_wait` 都使用毫秒单位。如果不配置 `retry`，这次上游 LLM 调用就不会重试。`headers` 是可选扩展头，只有配置时才会额外透传；运行时仍会默认带上 `Content-Type: application/json`。

### 切换 Checkpointer 后端

- `langgraph.checkpointer.backend: memory`
- `langgraph.checkpointer.backend: redis`

如果使用 Redis，再额外配置：

- `langgraph.checkpointer.redis_url`

### 启用 Langfuse

- `langfuse.enabled: true`
- `langfuse.host`
- `langfuse.public_key`
- `langfuse.secret_key`

trace 会自动带上：

- 顶层 `session_id`
- 顶层 `user_id`
- metadata 中的 `systemkey`、`workflow`
- tags 中的 `workflow:<workflow>`、`systemkey:<systemkey>`、`request_id:<request_id>`

### 推送 Nacos 配置

示例脚本：

- `scripts/push_nacos_configs.sh`

默认推送：

- `configs/local.yaml`
- `configs/workflows/demo_hitl.yaml`
- `configs/workflows/demo_summary.yaml`

### 启动方式

开发模式：

```bash
bash scripts/dev.sh
```

生产风格模式：

```bash
bash scripts/run.sh
```

默认行为：

- host 来自 `server.host`，默认 `0.0.0.0`
- port 来自 `server.port`，默认 `8080`
- worker 数来自 `server.workers`，默认 `8`

也可以通过环境变量覆盖：

```bash
HOST=0.0.0.0 PORT=18080 WORKERS=4 bash scripts/run.sh
```

## Workflow 工程师指南

### 新增 Workflow

创建：

- `src/workflows/<name>/graph.py`
- `src/workflows/<name>/state.py`
- `src/workflows/<name>/nodes/`

### 新增图级配置

- 新建 `configs/workflows/<name>.yaml`
- 在根配置的 `workflow_configs.items` 中注册

### 在 Node 中读取图配置

```python
prompt_prefix = workflow_config.get("prompts.draft_prefix", "")
```

### 在 Node 中选择 LLM

```python
llm = resolve_workflow_llm(
    workflow_config=workflow_config,
)
```

解析结果里的 `llm.name` 固定为 `default`，`llm.config` 则是该模型的完整配置。

### 注册 Workflow

在 `src/workflows/registry.py` 中注册新图。

### 暴露给调用方

调用方通过 OpenAI 风格的 `model` 选择 workflow。
如果某张图只服务部分系统，再结合 `systemkey` 做业务隔离。

## Nacos Backend 选项

根配置和图级配置都支持：

- `backend: http`
- `backend: sdk_v2`
- `backend: sdk_v3`
- `backend: auto`

## 动态配置复用

其他项目也可以直接复用动态配置能力：

```python
from dynamic_config import DynamicConfigProvider, NacosSettings
```

详细说明见 [动态配置说明](dynamic_config.zh-CN.md)。
