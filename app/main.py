"""HTTP API and static web interface."""

from pathlib import Path
from typing import Literal, Self

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.agent import AgentError, demo_reply, live_reply
from app.auth import access_error
from app.config import Settings
from app.tools import TOOL_DEFINITIONS

STATIC = Path(__file__).parent / "static"


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=12000)

    @field_validator("content")
    @classmethod
    def nonempty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Messages cannot be blank.")
        return value.strip()


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    messages: list[Message] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def valid_conversation(self) -> Self:
        if self.messages[-1].role != "user":
            raise ValueError("The last message must be from the user.")
        if sum(len(message.content) for message in self.messages) > 60000:
            raise ValueError("Conversation is too long. Start a new chat.")
        return self


class ToolCall(BaseModel):
    name: str
    arguments: dict
    result: str


class ChatResponse(BaseModel):
    reply: str
    mode: Literal["demo", "live"]
    tool_calls: list[ToolCall]


def create_app(
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    settings = settings or Settings.from_environment()
    application = FastAPI(title="Agent Desk", version="0.1.0", docs_url=None, redoc_url=None)

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        response = access_error(request, settings)
        if response is None:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; base-uri 'self'; frame-ancestors 'none'"
        )
        if (
            request.url.path.startswith("/api/")
            or settings.access_password
            or response.status_code >= 400
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.get("/api/health")
    async def health():
        return {"status": "ok"}

    @application.get("/api/config")
    async def config():
        return {
            "mode": settings.mode,
            "model": settings.model if settings.api_key else "Local demo",
            "tools": [
                {"name": item["function"]["name"], "description": item["function"]["description"]}
                for item in TOOL_DEFINITIONS
            ],
        }

    @application.post("/api/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest):
        messages = [message.model_dump() for message in body.messages]
        if not settings.api_key:
            return demo_reply(messages)
        try:
            return await live_reply(messages, settings, transport)
        except AgentError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    @application.get("/", include_in_schema=False)
    async def index():
        return FileResponse(STATIC / "index.html")

    application.mount("/static", StaticFiles(directory=STATIC, check_dir=False), name="static")
    return application


app = create_app()
