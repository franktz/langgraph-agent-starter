# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [0.1.2] - 2026-03-16

### Added

- Added the new `demo_chat` workflow for multi-turn chat, with both streaming and non-streaming OpenAI-compatible responses.
- Added persisted conversation history for `demo_chat` through LangGraph state plus checkpointer-backed recovery.
- Added release notes for `v0.1.2`.

### Changed

- Moved LLM ownership fully into workflow-local config under `llm.default`, including `base_url`, `apikey`, optional `headers`, `timeout`, and per-model `retry`.
- Changed request routing so `model` is required and maps directly to a workflow, while `systemkey` is used only for caller identity and business isolation.
- Changed auth configuration to use `api.auth.enabled` and `api.auth.systemkeys` allowlisting, returning `401 invalid_system_key` for missing or unauthorized callers.
- Changed LangGraph thread scoping to isolate persisted state by `workflow + systemkey + user-id + session-id` instead of plain `session-id`.
- Refreshed README and cURL examples to document `demo_chat`, workflow-local LLM config, and the current auth / streaming behavior.

### Fixed

- Fixed streaming behavior so node-level LLM deltas are forwarded as true SSE output rather than buffered pseudo-streaming.
- Fixed replay handling for multi-turn chat requests so previously persisted history is not appended twice when callers resend prior messages.
- Fixed Nacos publishing helper coverage by including `demo_chat` in the workflow config push script.

## [0.1.1] - 2026-03-15

### Changed

- Upgraded `dynamic-config-nacos` from `0.1.0` to `0.1.1`.
- Pinned `nacos-sdk-python` to `2.0.11` to align the runtime with the expected `sdk_v2` import path.

### Fixed

- Improved Nacos startup compatibility for local Windows development by avoiding the `nacos-sdk-python 3.x` import mismatch (`import nacos` vs `v2.nacos`).
- Kept the package metadata and lockfile aligned for the `0.1.1` release.
