# Design Guide

[Chinese Version](design.zh-CN.md)

## Goals

This starter is designed for collaboration between two roles:

- platform engineers
  responsible for APIs, config, logging, monitoring, runtime, and integrations
- workflow engineers
  responsible for workflow graphs, state, nodes, branching, and data shaping

The goal is to keep the collaboration boundary explicit so that platform work
and workflow work can evolve with minimal coupling.

## Core Separation

### Platform Side

- `src/app/`
- `src/application/`
- `src/infrastructure/`

### Workflow Side

- `src/workflows/`

Workflow code does not depend on the FastAPI composition root. The platform
layer invokes workflows through the registry and runtime.

## Configuration Layers

### Root Config

The root config owns platform-wide behavior:

- API auth and transport conventions
- `model -> workflow`
- logging, HTTP, Langfuse, and checkpointer setup
- workflow config location and Nacos mapping

### Workflow Config

Each workflow can have its own config file for:

- LLM provider configuration owned by that workflow
- prompt fragments
- business thresholds
- feature flags
- workflow-specific external dependency settings

Current examples:

- `demo_hitl` -> `configs/workflows/demo_hitl.yaml`
- `demo_summary` -> `configs/workflows/demo_summary.yaml`

## Dynamic Config Reuse

`langgraph-agent-starter` consumes the reusable `dynamic_config` capability
from the published PyPI package `dynamic-config-nacos`.

The component exposes:

- `DynamicConfigProvider`
- `NacosSettings`
- `NacosBackendType`
- `Conf`

## Nacos Backend Strategy

The dynamic config component supports four backend modes:

- `http`
- `sdk_v2`
- `sdk_v3`
- `auto`

Strategy summary:

- `http`
  Uses the Nacos OpenAPI with polling refresh.
- `sdk_v2`
  Forces the older Python SDK path.
- `sdk_v3`
  Forces the newer Python SDK path.
- `auto`
  Detects the Nacos major version first, then prefers the matching SDK and
  falls back to `http` when needed.

## Workflow Config Injection

Workflow nodes do not look up global config directly. Instead,
`WorkflowConfigRegistry` creates one config provider per workflow and injects
it during graph construction.

LLM execution is bound later by the runtime through the shared `LlmGateway`.
That means graph builders do not receive an `llm_client`, and nodes read the
workflow-local LLM config they need during execution. The current demo keeps
that upstream model config under `llm.default`.

Benefits:

- each workflow gets isolated config
- adding a new workflow only requires a new config file and mapping
- once config changes are refreshed, subsequent reads see the updated values
- nodes do not need hard-coded global config paths or a fixed LLM implementation

## Runtime and Observability

`WorkflowRuntime` is responsible for:

- graph construction and caching
- checkpointer injection
- LangGraph execution
- converting workflow output into stream / non-stream OpenAI-style payloads
- forwarding node-level LLM token deltas to true SSE streaming responses
- HITL interrupt and resume handling

### Langfuse Trace Conventions

Runtime metadata includes:

- top-level `session_id`
- top-level `user_id`
- metadata:
  - `systemkey`
  - `session_id`
  - `user_id`
  - `workflow`
- tags:
  - `workflow:<workflow>`
  - `systemkey:<systemkey>`
  - `request_id:<request_id>`

This makes it easy to filter traces in Langfuse by session, user, workflow, or
business system.

### `systemkey` Naming Convention

The API layer uses the caller-facing field name `systemkey`.
Langfuse-facing metadata, tags, and workflow state also use `systemkey`.

## Real Integration Status

The scaffold has already been validated against real integration scenarios:

- Nacos config fetch succeeded
- workflow-level dynamic config refresh succeeded
- Redis checkpointer worked
- HITL resume worked
- Langfuse auth and trace reporting worked

Final LLM generation success still depends on the upstream model service and
credentials you configure.
