"""Validate a running server without paid requests or third-party dependencies."""

import base64
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> None:
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
    password = os.environ.get("AGENT_ACCESS_PASSWORD", "")
    headers = {"Content-Type": "application/json"}
    if password:
        credentials = base64.b64encode(f"owner:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    def request(path: str, payload: dict | None = None) -> tuple[int, bytes]:
        body = json.dumps(payload).encode() if payload is not None else None
        req = Request(base + path, data=body, headers=headers)
        with urlopen(req, timeout=10) as response:
            return response.status, response.read()

    assert json.loads(request("/api/health")[1]) == {"status": "ok"}
    config = json.loads(request("/api/config")[1])
    assert config["mode"] in {"demo", "live"}
    assert b"Agent Desk" in request("/")[1]
    for asset in ("app.js", "styles.css"):
        assert request(f"/static/{asset}")[0] == 200
    try:
        request("/api/chat", {"messages": []})
    except HTTPError as exc:
        assert exc.code == 422
    else:
        raise AssertionError("Invalid chat request was accepted")
    if config["mode"] == "demo":
        payload = {"messages": [{"role": "user", "content": "Calculate 2 + 3 * 4"}]}
        result = json.loads(request("/api/chat", payload)[1])
        assert result["mode"] == "demo"
        assert result["tool_calls"][0]["result"] == "14"
        payload["messages"][0]["content"] = "What time is it in Asia/Kolkata?"
        result = json.loads(request("/api/chat", payload)[1])
        assert "+05:30" in result["tool_calls"][0]["result"]
        print(
            "PASS: homepage, assets, health, configuration, validation, demo calculator and clock"
        )
    else:
        print(
            "PASS: homepage, assets, health, configuration and validation; paid AI request not run"
        )


if __name__ == "__main__":
    main()
