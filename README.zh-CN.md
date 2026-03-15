# langgraph-agent-starter

[English](README.md)

一个面向平台工程与 workflow 开发协作的 LangGraph 通用脚手架，重点是把平台侧通用能力和图实现尽量解耦。

## 核心能力

- 基于 FastAPI 提供 OpenAI 兼容接口：
  - `GET /v1/models`
  - `POST /v1/chat/completions`
- 基于 LangGraph 组织 workflow
- 支持 stream / non-stream 两种响应模式
- 支持 HITL 中断与恢复
- 通过 Langfuse CallbackHandler 接入观测
- 支持根配置 + 图级配置两层配置结构
- 支持 Nacos 动态配置，并提供本地 YAML fallback
- 支持 Redis / memory 两种 LangGraph checkpointer
- 通过 PyPI 包 `dynamic-config-nacos` 复用动态配置能力

## 工程分层

- `src/app/`
  FastAPI 组合根与生命周期管理。
- `src/application/`
  请求编排、路由决策和用例服务。
- `src/domain/`
  契约、请求上下文和 workflow 规格。
- `src/infrastructure/`
  配置、HTTP、日志、持久化、监控与 LLM 适配。
- `src/presentation/`
  传输层 schema。
- `src/workflows/`
  workflow 图实现与注册表。

## 本地命令

```bash
uv sync --python 3.12 --all-extras
uv run --python 3.12 uvicorn --app-dir src app.main:app --reload
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
- workflow 本地兜底配置：
  - `configs/workflows/demo_hitl.yaml`
  - `configs/workflows/demo_summary.yaml`

当前示例配置已经做过开源安全化处理：

- Langfuse 默认关闭
- 外部 API key 使用占位值
- checkpointer 默认使用 `memory`

## 内置示例 Workflow

- `demo_hitl`
  先生成草稿，再进入人工审核中断。
- `demo_summary`
  一个不带中断的简单总结流程。

## 更多文档

- [Usage Guide](docs/usage.md)
- [使用说明](docs/usage.zh-CN.md)
- [Design Guide](docs/design.md)
- [设计说明](docs/design.zh-CN.md)
- [Dynamic Config](docs/dynamic_config.md)
- [动态配置说明](docs/dynamic_config.zh-CN.md)
