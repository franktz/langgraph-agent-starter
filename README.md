# langgraph-agent-starter

[中文文档](README.zh-CN.md)

A production-oriented LangGraph starter for teams that want a clean separation
between platform engineering concerns and workflow implementation.

## Highlights

- FastAPI application shell with OpenAI-compatible endpoints
  - `GET /v1/models`
  - `POST /v1/chat/completions`
- LangGraph-based workflow orchestration
- True streaming and non-streaming responses
- HITL interrupt and resume support
- Langfuse callback integration for observability
- Root config plus per-workflow config layering, with workflow-owned LLM
  configuration
- Nacos-backed dynamic configuration with local YAML fallback
- Redis or in-memory LangGraph checkpointer support
- Reusable `dynamic_config` capability consumed from the published PyPI package
  `dynamic-config-nacos`

## Architecture

- `src/app/`
  FastAPI composition root and lifespan wiring.
- `src/application/`
  Request orchestration, routing, and use-case services.
- `src/domain/`
  Contracts, request context, and workflow specs.
- `src/infrastructure/`
  Config, HTTP, logging, persistence, monitoring, and LLM adapters.
- `src/presentation/`
  Transport-layer schemas.
- `src/workflows/`
  Workflow graph implementations and registry.

## Local Commands

```bash
uv sync --python 3.12 --all-extras
uv run --python 3.12 uvicorn --env-file .env --app-dir src app.main:app --reload
uv run --python 3.12 pytest
uv run --python 3.12 ruff check .
uv run --python 3.12 ruff format .
```

## Scripts

- `scripts/dev.sh`
  Starts a reload-enabled development server.
- `scripts/run.sh`
  Starts a production-style Gunicorn + Uvicorn worker process.
- `scripts/test.sh`
  Runs the test suite.
- `scripts/lint.sh`
  Runs lint checks.
- `scripts/format.sh`
  Formats the repository.
- `scripts/push_nacos_configs.sh`
  Publishes root and workflow config files to Nacos.

## Configuration

- Root config: `configs/local.yaml`
- Workflow local fallback config:
  - `configs/workflows/demo_hitl.yaml`
  - `configs/workflows/demo_summary.yaml`

The default sample configuration is safe to publish:

- Langfuse is disabled by default
- External API keys are placeholders
- Checkpointer defaults to `memory`

## Included Demo Workflows

- `demo_hitl`
  Draft generation followed by human review interrupt.
- `demo_summary`
  Simple summarization flow without interrupt.

## Documentation

- [Usage Guide](docs/usage.md)
- [Usage Guide (中文)](docs/usage.zh-CN.md)
- [Design Guide](docs/design.md)
- [Design Guide (中文)](docs/design.zh-CN.md)
- [Dynamic Config](docs/dynamic_config.md)
- [Dynamic Config (中文)](docs/dynamic_config.zh-CN.md)
- [Changelog](CHANGELOG.md)
- [Release Notes v0.1.1](docs/releases/v0.1.1.md)

## API Examples

- [cURL Examples](docs/curl_examples.md)
- [cURL Examples (中文)](docs/curl_examples.zh-CN.md)
