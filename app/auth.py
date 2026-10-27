"""Single-owner HTTP Basic access control for the hosted assistant."""

import base64
import binascii
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import Settings


def valid_credentials(header: str, password: str) -> bool:
    if len(header) > 8192:
        return False
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "basic" or not token:
        return False
    try:
        decoded = base64.b64decode(token, validate=True).decode("utf-8")
        username, separator, supplied = decoded.partition(":")
    except (binascii.Error, UnicodeError):
        return False
    if not separator:
        return False
    user_matches = secrets.compare_digest(username.encode("utf-8"), b"owner")
    password_matches = secrets.compare_digest(supplied.encode("utf-8"), password.encode("utf-8"))
    return user_matches and password_matches


def access_error(request: Request, settings: Settings) -> JSONResponse | None:
    # A paid provider key must never silently turn a public demo into an open API.
    if settings.api_key and not settings.access_password:
        return JSONResponse(
            status_code=503,
            content={"detail": "Set AGENT_ACCESS_PASSWORD on the server before enabling live AI."},
        )
    # Render probes readiness without credentials; no model or secret is disclosed here.
    if request.url.path == "/api/health":
        return None
    if settings.access_password and not valid_credentials(
        request.headers.get("authorization", ""), settings.access_password
    ):
        return JSONResponse(
            status_code=401,
            content={"detail": "Sign in with username owner and the server access password."},
            headers={"WWW-Authenticate": 'Basic realm="Agent Desk", charset="UTF-8"'},
        )
    return None
