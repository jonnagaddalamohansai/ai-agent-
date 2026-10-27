# Agent Desk

A general AI assistant web app with a Python API and a responsive browser interface. Ask questions, keep conversations in your browser, and let the assistant use a calculator or check the current time.

The app starts in **local demo mode** when no API key is configured. This mode runs the calculator and time tools and returns a few explanatory sample replies. General AI responses require an OpenAI API key; demo replies do not call an AI model.

## Requirements

- Python 3.12 or 3.13 (3.12 is pinned for cloud sessions)
- [uv](https://docs.astral.sh/uv/) for dependency installation and commands
- Node.js for the JavaScript syntax check in `scripts/check.sh`; the frontend has no npm dependencies or build step

## Install and run

Run these commands from the repository root:

```sh
uv sync --frozen --extra dev
bash scripts/start.sh
```

The server listens on `127.0.0.1:8000` by default. `HOST` and `PORT` can override these defaults. The start script runs in the foreground, so use another terminal for checks and stop it with Ctrl+C.

For automatic backend reloads during development:

```sh
uv run --frozen uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

This is a single-user development application without account authentication. Keep the default loopback binding for local development.

## Enable live AI responses

In the cloud environment settings, add the `AGENT_API_KEY` secret for the HTTPS destination `api.openai.com`. Enter the value securely in settings, then restart the application after the binding reaches the running environment. The key stays on the server and is never part of the browser configuration.

For local development, copy `.env.example` to `.env`, enter your key in that ignored file, and start with `bash scripts/start.sh`. Do not commit the file. The start script loads `.env` when it exists. If you use the direct Uvicorn command instead, add `--env-file .env` to load that file.

| Variable | Purpose | Default |
| --- | --- | --- |
| `AGENT_API_KEY` | Server-side OpenAI API credential; leaving it empty enables local demo mode | Empty |
| `AGENT_MODEL` | OpenAI model used for live responses | `gpt-4.1-mini` |
| `HOST` | Server listen address used by the start script | `127.0.0.1` |
| `PORT` | Server port used by the start script | `8000` |

Live responses use the OpenAI chat completions API and may incur provider charges. Calculator and current-time tools run on the application server. There is no shell execution or web browsing tool.

## Validate the application

```sh
# API, tool, input-validation, and mocked-provider tests
uv run --frozen pytest

# Lint, formatting, tests, syntax checks, and distribution build
bash scripts/check.sh

# Functional HTTP check against the running server
python3 scripts/smoke.py
```

The smoke check uses `http://127.0.0.1:8000` by default. To check another local port, pass the base URL:

```sh
python3 scripts/smoke.py http://127.0.0.1:8001
```

Mocked-provider tests validate the live integration without credentials or paid API requests. They do not establish that a particular key or model is available from your cloud environment.

## Application layout

```text
app/
  config.py        Server configuration
  main.py          FastAPI application and API routes
  tools.py         Bounded arithmetic and current-time tools
  static/          HTML, CSS, and browser JavaScript
scripts/           Startup and validation commands
tests/             Automated tests
pyproject.toml     Project and dependency declarations
uv.lock            Reproducible dependency versions
```

The browser requests `/api/config` to show the active mode and sends conversation messages to `/api/chat`. Requests accept up to 30 messages, 12,000 characters per message, and 60,000 characters in total. The latest message must be from the user.

Conversation history is stored in this browser's local storage. It is not a server database and does not sync between browsers. Use the conversation controls to delete saved chats. In live mode, messages sent to the assistant are also sent to the configured AI provider.

## Cloud environment setup

Cloud tasks already run in an isolated environment. Use the existing checkout at `/workspace/ai-agent-`; no additional Git worktree is needed. Dependencies and files can be retained in the published environment snapshot, but running server processes must be started again in future tasks.

The onboarding setup saves installation and startup instructions as a configuration draft. Saving a draft does not execute those instructions, apply credentials, or publish the environment. Review and save the configuration in environment settings, then publish the prepared environment when ready. Securely provide `AGENT_API_KEY` there only if you want live AI responses.
