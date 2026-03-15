#!/usr/bin/env bash

set -euo pipefail

uv run --python 3.12 ruff check .
