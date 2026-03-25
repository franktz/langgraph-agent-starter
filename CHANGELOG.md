# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [0.1.4] - 2026-03-26

### Added

- Added `input_messages` and `raw_input_messages` runtime inputs for non-conversation workflows so each request can pass current-turn messages into the graph even when conversation persistence is disabled at the workflow level.
- Added a public `last_text_from_input_messages(...)` helper for extracting the latest relevant text from request-scoped input messages with configurable roles.
- Added integration coverage to verify `raw_input_messages` preserves undeclared raw fields such as assistant `tool_calls`.
- Added support for MySQL and MongoDB LangGraph checkpointer backends alongside the existing `memory` and Redis options.
- Added Redis `cluster_mode` configuration support for the checkpointer backend.
- Added release notes for `v0.1.4`.

### Changed

- Upgraded `dynamic-config-nacos` from `0.1.2` to `0.1.3`.
- Removed `WorkflowRuntime._session_state` and simplified runtime state handling around per-request graph input assembly.
- Changed checkpointer configuration to support `backend: null` for disabling persistence, while grouping backend-specific settings under `langgraph.checkpointer.redis`, `langgraph.checkpointer.mysql`, and `langgraph.checkpointer.mongodb`.
- Changed non-conversation workflow state semantics to use schema-normalized `input_messages` plus raw-body `raw_input_messages`, and stopped populating the legacy `question` field.
- Changed non-conversation resume behavior so request-scoped `input_messages`, `raw_input_messages`, and `sys_code` overwrite prior persisted values instead of accumulating across requests.

## [0.1.3] - 2026-03-20

### Added

- Added the new `demo-chat` workflow for multi-turn chat, with both streaming and non-streaming OpenAI-compatible responses.
- Added persisted conversation history for `demo-chat` through LangGraph state plus checkpointer-backed recovery.
- Added release notes for `v0.1.3`.

### Changed

- Moved LLM ownership fully into workflow-local config under `llm.default`, including `base_url`, `apikey`, optional `headers`, `timeout`, and per-model `retry`.
- Changed request routing so `model` is required and maps directly to a workflow, while `sysCode` / `sys_code` is used only for caller identity and business isolation.
- Changed auth configuration to use `api.auth.enabled` and `api.auth.sys_codes` allowlisting, returning `401 invalid_sys_code` for missing or unauthorized callers.
- Changed LangGraph thread scoping to isolate persisted state by `workflow + sys_code + user-id + session-id` instead of plain `session-id`.
- Renamed external workflow identifiers from `demo_chat` / `demo_hitl` / `demo_summary` to `demo-chat` / `demo-hitl` / `demo-summary`, while keeping Python package directories in snake_case.
- Renamed workflow config file names and Nacos workflow `data_id` values to kebab-case.
- Upgraded `dynamic-config-nacos` from `0.1.1` to `0.1.2`.
- Added support for configuring Nacos SDK log output through `nacos.sdk_log_path`, `nacos.sdk_log_level`, `NACOS_SDK_LOG_PATH`, and `NACOS_SDK_LOG_LEVEL`.
- Stopped forwarding caller business identity headers to upstream LLM requests.
- Refreshed README and usage docs to document workflow-local LLM config, current auth behavior, workflow naming, and Nacos SDK logging.

### Fixed

- Fixed streaming behavior so node-level LLM deltas are forwarded as true SSE output rather than buffered pseudo-streaming.
- Fixed replay handling for multi-turn chat requests so previously persisted history is not appended twice when callers resend prior messages.
- Fixed Nacos publishing helper coverage by including `demo-chat` in the workflow config push script and aligning helper targets with renamed workflow config files.

## [0.1.1] - 2026-03-15

### Changed

- Upgraded `dynamic-config-nacos` from `0.1.0` to `0.1.1`.
- Pinned `nacos-sdk-python` to `2.0.11` to align the runtime with the expected `sdk_v2` import path.

### Fixed

- Improved Nacos startup compatibility for local Windows development by avoiding the `nacos-sdk-python 3.x` import mismatch (`import nacos` vs `v2.nacos`).
- Kept the package metadata and lockfile aligned for the `0.1.1` release.
