"""Server-side settings. Credential values never form part of API responses."""

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    api_key: str = field(default="", repr=False)
    model: str = "gpt-4.1-mini"
    timeout_seconds: float = 30
    access_password: str = field(default="", repr=False)

    @classmethod
    def from_environment(cls) -> "Settings":
        return cls(
            api_key=os.environ.get("AGENT_API_KEY", "").strip(),
            model=os.environ.get("AGENT_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
            access_password=os.environ.get("AGENT_ACCESS_PASSWORD", ""),
        )

    @property
    def mode(self) -> str:
        return "live" if self.api_key else "demo"
