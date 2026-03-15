# 设计说明

[English](design.md)

## 目标

这个脚手架面向两类角色协作：

- 平台工程师
  负责 API、配置、日志、监控、运行时和集成能力
- workflow 工程师
  负责 workflow 图、state、node、分支和数据组织

核心目标是把协作边界显式化，让平台侧与 workflow 侧尽量低耦合演进。

## 核心分离

### 平台侧

- `src/app/`
- `src/application/`
- `src/infrastructure/`

### Workflow 侧

- `src/workflows/`

Workflow 代码不依赖 FastAPI 组合根，平台层通过 registry 和 runtime 调用 workflow。

## 配置分层

### 根配置

根配置负责平台级行为：

- API 默认值
- `model -> workflow`
- logging、HTTP、Langfuse、checkpointer 初始化
- workflow 配置位置和 Nacos 映射

### Workflow 配置

每个 workflow 都可以有自己的配置文件，用来承载：

- 该 workflow 自己拥有的 LLM 提供方配置
- prompt 片段
- 业务阈值
- feature flag
- workflow 自己依赖的外部系统配置

当前示例：

- `demo_hitl` -> `configs/workflows/demo_hitl.yaml`
- `demo_summary` -> `configs/workflows/demo_summary.yaml`

## 动态配置复用

`langgraph-agent-starter` 直接复用了已经发布到 PyPI 的 `dynamic-config-nacos` 动态配置能力。

组件对外暴露：

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
  使用 Nacos OpenAPI 轮询刷新。
- `sdk_v2`
  强制走旧版 Python SDK。
- `sdk_v3`
  强制走新版 Python SDK。
- `auto`
  先探测 Nacos 大版本，再优先选择匹配 SDK，必要时回退到 `http`。

## Workflow 配置注入

Workflow node 不直接读取全局配置。`WorkflowConfigRegistry` 会为每个 workflow 创建独立的配置 provider，并在构图时注入进去。

LLM 的真正执行能力则由运行时通过共享的 `LlmGateway` 绑定到当前执行上下文。因此 graph build 阶段不再传 `llm_client`，node 在执行时读取 workflow 自己的 LLM 配置即可。当前 demo 统一使用 `llm.default` 这份上游模型配置。

这样做的好处：

- 每个 workflow 都有隔离的配置空间
- 新增 workflow 只需要增加配置文件和映射
- 配置刷新后，后续执行可以读到最新值
- node 不需要写死全局配置路径或具体 LLM 实现

## Runtime 与可观测性

`WorkflowRuntime` 负责：

- 构图和缓存 graph
- 注入 checkpointer
- 执行 LangGraph
- 把 workflow 输出转换成 stream / non-stream 的 OpenAI 风格响应
- 把 node 级别的 LLM token 增量转发成真正的 SSE 流式输出
- 处理 HITL interrupt 与 resume

### Langfuse Trace 约定

运行时 metadata 包含：

- 顶层 `session_id`
- 顶层 `user_id`
- metadata:
  - `systemkey`
  - `session_id`
  - `user_id`
  - `workflow`
- tags:
  - `workflow:<workflow>`
  - `systemkey:<systemkey>`
  - `request_id:<request_id>`

这样可以很方便地在 Langfuse 里按 session、user、workflow、业务系统过滤 trace。

### `systemkey` 命名约定

API 层使用调用方字段名 `systemkey`，Langfuse metadata、tags 以及 workflow state 里也统一使用 `systemkey`。

## 真实集成状态

这个脚手架已经验证过以下真实集成链路：

- Nacos 配置拉取成功
- workflow 级动态配置刷新成功
- Redis checkpointer 可用
- HITL resume 可用
- Langfuse 鉴权和 trace 上报可用

最终的大模型调用成功与否，仍取决于你在配置里填写的上游模型服务和凭证是否可用。
