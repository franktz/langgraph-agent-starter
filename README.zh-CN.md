# langgraph-agent-starter

[English](README.md)

这是一个面向平台工程与 workflow 开发协作的 LangGraph 通用脚手架，重点是把平台侧通用能力和图实现尽量解耦。

## API 示例

- [cURL 示例](docs/curl_examples.zh-CN.md)
- [cURL Examples](docs/curl_examples.md)

## 核心能力

- 基于 FastAPI 提供 OpenAI 兼容接口
  - `GET /v1/models`
  - `POST /v1/chat/completions`
- 基于 LangGraph 编排 workflow
- 支持真流式与 non-stream 两种响应模式
- 支持 HITL 中断与恢复
- 通过 Langfuse CallbackHandler 接入观测
- 支持根配置与 workflow 配置分层，LLM 定义由 workflow 独立管理
- 支持 Nacos 动态配置与本地 YAML fallback
- 支持 Redis / memory 两种 LangGraph checkpointer
- 通过 PyPI 包 `dynamic-config-nacos` 复用动态配置能力

## 关键运行约定

- OpenAI 风格请求里的 `model` 为必填，并直接映射到 workflow；缺失时返回 `400 missing_model`
- `systemkey` 只负责调用方身份与业务隔离，不再参与 LLM 选型
- 当 `api.auth.enabled=true` 时，`systemkey` 必须命中 `api.auth.systemkeys` 白名单，否则返回 `401 invalid_system_key`
- 当前示例里，每个 workflow 都在自己的配置中维护 `llm.default`
  - 常用字段包括 `provider`、`base_url`、`apikey`、`headers`、`model`、`max_tokens`、`timeout`、`retry`
  - `timeout`、`retry.min_wait`、`retry.max_wait` 都使用毫秒
  - 即使没有额外 `headers`，运行时也会默认发送 `Content-Type: application/json`
- 流式接口返回的是真 SSE 增量数据，不是服务端拼好后的伪流式

## 工程分层

- `src/app/`
  FastAPI 组合根与生命周期装配。
- `src/application/`
  请求编排、路由决策与用例服务。
- `src/domain/`
  契约、请求上下文与 workflow 规格。
- `src/infrastructure/`
  配置、HTTP、日志、持久化、监控与 LLM 适配。
- `src/presentation/`
  传输层 schema。
- `src/workflows/`
  Workflow 图实现与注册表。

## 本地命令

```bash
uv sync --python 3.12 --all-extras
uv run --python 3.12 uvicorn --env-file .env --app-dir src app.main:app --reload
uv run --python 3.12 pytest
uv run --python 3.12 ruff check .
uv run --python 3.12 ruff format .
```

## 脚本

- `scripts/dev.sh`
  启动支持热重载的开发服务。
- `scripts/run.sh`
  以 Gunicorn + Uvicorn worker 方式启动生产风格服务。
- `scripts/test.sh`
  运行测试。
- `scripts/lint.sh`
  运行 lint。
- `scripts/format.sh`
  格式化仓库。
- `scripts/push_nacos_configs.sh`
  将根配置和 workflow 配置推送到 Nacos。

## 配置

- 根配置：`configs/local.yaml`
- Workflow 本地 fallback 配置：
  - `configs/workflows/demo_chat.yaml`
  - `configs/workflows/demo_hitl.yaml`
  - `configs/workflows/demo_summary.yaml`

默认示例配置可以安全公开：

- Langfuse 默认关闭
- 外部 API Key 使用占位值
- Checkpointer 默认使用 `memory`

## 内置示例 Workflow

- `demo_chat`
  基于 LangGraph state 和 checkpointer 的多轮聊天流程。
- `demo_hitl`
  先生成草稿，再进入人工审核中断。
- `demo_summary`
  一个不带中断的简单总结流程。

其中 `demo_chat` 的会话连续性由 `model`、`systemkey`、`user-id`、`session-id` 共同决定；在同一 workflow 下复用同一组 `user-id` 和 `session-id`，就会延续之前的聊天历史。

## 文档入口

- [使用说明](docs/usage.zh-CN.md)
- [Usage Guide](docs/usage.md)
- [设计说明](docs/design.zh-CN.md)
- [Design Guide](docs/design.md)
- [变更日志](CHANGELOG.md)
- [v0.1.2 发版说明](docs/releases/v0.1.2.md)
