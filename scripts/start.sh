#!/usr/bin/env bash
set -euo pipefail
project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
env_args=()
if [[ -f .env ]]; then
  env_args=(--env-file .env)
fi
exec uv run --frozen uvicorn app.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}" "${env_args[@]}"
