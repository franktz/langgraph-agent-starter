# 设计说明

[English](design.md)

## 目标

这个脚手架主要面向两类协作角色：

- 平台工程师
  负责 API、配置、日志、监控、运行时与外部集成
- workflow 工程师
  负责 workflow 图、state、node、分支和数据处理

核心目标是把协作边界做清楚，让平台侧和 workflow 侧可以相对独立演进，减少互相修改带来的摩擦。

## 核心分层

### 平台侧

- `src/app/`
- `src/application/`
- `src/infrastructure/`

### Workflow 侧

- `src/workflows/`

workflow 实现不直接依赖 FastAPI 组合根，平台侧通过 registry 和 runtime 调用 workflow。

## 配置分层

### 根配置

根配置负责平台级能力，例如：

- API 默认行为
- `systemKey -> llm profile`
- `model -> workflow`
- 日志、HTTP、Langfuse、checkpointer
- workflow 配置文件位置和 Nacos 映射关系

### 图级配置

每个 workflow 都可以有自己的独立配置文件，用来承载：

- prompt 片段
- 业务阈值
- 功能开关
- 图级外部依赖配置

当前示例：

- `demo_hitl` -> `configs/workflows/demo_hitl.yaml`
- `demo_summary` -> `configs/workflows/demo_summary.yaml`

## 动态配置复用

`langgraph-agent-starter` 通过 PyPI 包 `dynamic-config-nacos` 复用动态配置能力。

它对外暴露的核心类型包括：

- `DynamicConfigProvider`
- `NacosSettings`
- `NacosBackendType`
- `Conf`

## Nacos Backend 策略

动态配置组件支持四种 backend：

- `http`
- `sdk_v2`
- `sdk_v3`
- `auto`

策略说明：

- `http`
  通过 Nacos OpenAPI + 轮询实现动态更新
- `sdk_v2`
  强制走旧版 Python SDK
- `sdk_v3`
  强制走新版 Python SDK
- `auto`
  先探测 Nacos 主版本，再优先尝试匹配的 SDK，失败后回退到 `http`

## Workflow 配置注入

workflow node 不直接自行读取全局配置，而是由 `WorkflowConfigRegistry`
在构图时为每张图创建独立的配置 provider 并注入。

这样做的好处是：

- 每张图拥有独立配置
- 新增 workflow 只需要加配置文件和映射
- 配置更新后，后续读取会拿到新值
- node 里不需要硬编码全局配置路径

## 运行时与观测

`WorkflowRuntime` 统一负责：

- graph 构建与缓存
- checkpointer 注入
- LangGraph 执行
- 将结果转换为 OpenAI 风格的 stream / non-stream 响应
- HITL interrupt / resume

### Langfuse Trace 约定

运行时会写入：

- 顶层 `session_id`
- 顶层 `user_id`
- metadata:
  - `systemKey`
  - `session_id`
  - `user_id`
  - `workflow`
  - `llm_profile`
- tags:
  - `workflow:<workflow>`
  - `systemKey:<systemKey>`
  - `llm_profile:<profile>`

这样在 Langfuse 中可以更方便地按会话、用户、workflow 或业务系统筛选。

### `systemKey` 命名约定

接口层、请求上下文和运行时 metadata 都统一保留字段名 `systemKey`，不做别名替换。

## 真实集成状态

这套脚手架已经验证过以下真实集成能力：

- Nacos 配置拉取成功
- 图级动态配置更新成功
- Redis checkpointer 可用
- HITL resume 可用
- Langfuse 鉴权和 trace 上报成功

最终模型是否可用，仍然取决于你配置的上游模型服务和凭证。
