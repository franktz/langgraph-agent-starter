# AGENTS.md

## 目标

这个仓库是一个通用的 LangGraph 工程脚手架，目标是尽量解耦以下两类关注点：

- 平台 / 软件工程侧关注点
- workflow / 算法侧关注点

## 运行时

- Python 3.12
- 依赖管理：`uv`
- API：FastAPI
- 编排框架：LangGraph
- 监控：Langfuse CallbackHandler
- 配置：Nacos YAML + 本地 YAML fallback

## 分层

- `src/app/`：仅负责 FastAPI 组合根
- `src/application/`：用例、编排、协议适配
- `src/domain/`：契约、值对象、基础抽象
- `src/infrastructure/`：配置、日志、HTTP、LLM、监控、持久化适配层
- `src/presentation/`：传输层 schema
- `src/workflows/`：图实现与注册表
