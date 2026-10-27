# Agent Desk

A general AI assistant web app with a Python API and a responsive browser interface. Ask questions, keep conversations in your browser, and let the assistant use a calculator or check the current time.

The app starts in **local demo mode** when no API key is configured. This mode runs the calculator and time tools and returns a few explanatory sample replies. General AI responses require an OpenAI API key and an access password; demo replies do not call an AI model.

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

This is a single-user application. Setting an access password enables HTTP Basic authentication with the username `owner`. Keep the default loopback binding for local development.

## Open the app in a browser through Render

The cloud onboarding workspace does not provide a browser preview. The repository includes a Render Blueprint for a hosted demo:

1. Open [Deploy to Render](https://render.com/deploy?repo=https://github.com/jonnagaddalamohansai/ai-agent-).
2. Sign in to Render and connect this GitHub repository if prompted.
3. Review the service and plan, then create the Blueprint. It uses `render.yaml` to install the locked dependencies and start the server.
4. Wait for the service to become live, then open the HTTPS URL shown on the service dashboard.

This link starts deployment setup; the app receives its URL after deployment succeeds. Render account authorization and hosting availability must be handled in Render. Free services may sleep when inactive.

The public demo leaves both `AGENT_API_KEY` and `AGENT_ACCESS_PASSWORD` empty. Add both values to enable password-protected live AI. Setting a password also protects demo mode, so you can check the login before connecting an API key.

If you create the Render service manually, choose **New → Web Service** and select Python. Use `uv sync --frozen` as the Build Command and `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the Start Command. Leave Root Directory blank and set Health Check Path to `/api/health`.

If Render reports `Publish directory build does not exist`, the service is configured as a Static Site; create a Web Service instead. If it reports `ai-agent: command not found` or exit status 127, replace the service's Start Command with the command above, save, and redeploy.

## Enable live AI responses

For an app already running on Render:

1. Open the service's **Environment** settings.
2. Add `AGENT_API_KEY` with your OpenAI API key and `AGENT_ACCESS_PASSWORD` with a strong password you choose. Enter these values securely in Render, not in chat or GitHub files.
3. Save the settings and redeploy the service.
4. Open the app URL. In the browser's login prompt, enter username **`owner`** and the password you set.
5. Confirm the page shows **Live AI mode**, then send a general question to verify your key and model access.

An OpenAI API account needs API credit or billing; a ChatGPT subscription does not include API usage. The API key stays on the server and is never part of the browser configuration.

For local development, copy `.env.example` to `.env`, set both values in that ignored file, and start with `bash scripts/start.sh`. Do not commit the file. The start script loads `.env` when it exists. If you use the direct Uvicorn command instead, add `--env-file .env` to load that file.

In the cloud environment settings, add the `AGENT_API_KEY` secret for the HTTPS destination `api.openai.com` and supply `AGENT_ACCESS_PASSWORD` as a private server environment value. The password must be available directly to the app for local authentication, rather than supplied as a network-proxy placeholder. Restart after the settings reach the running environment.

| Variable | Purpose | Default |
| --- | --- | --- |
| `AGENT_API_KEY` | Server-side OpenAI API credential; leaving it empty enables local demo mode | Empty |
| `AGENT_ACCESS_PASSWORD` | Password for HTTP Basic login as `owner`; required when an API key is set | Empty |
| `AGENT_MODEL` | OpenAI model used for live responses | `gpt-4.1-mini` |
| `HOST` | Server listen address used by the start script | `127.0.0.1` |
| `PORT` | Server port used by the start script | `8000` |

Setting `AGENT_ACCESS_PASSWORD` protects the web interface, static files, and chat API. The health endpoint remains available without a login. If an API key is set without an access password, the app returns HTTP 503, including on the health endpoint, until the password is configured. This is a shared owner login, not a multi-user account system.

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

The smoke check uses `AGENT_ACCESS_PASSWORD` from its process environment to authenticate when a password is configured. If your values are in the ignored `.env` file, load them for the check with `uv run --frozen --env-file .env python scripts/smoke.py`. Credentials do not belong in command-line arguments. In live mode, the smoke check verifies the app without sending a paid AI request; use an authenticated chat to verify the provider connection.

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

The onboarding setup saves installation and startup instructions as a configuration draft. Saving a draft does not execute those instructions, apply credentials, or publish the environment. Review and save the configuration in environment settings, then publish the prepared environment when ready. Securely provide both `AGENT_API_KEY` and `AGENT_ACCESS_PASSWORD` there only if you want live AI responses.
