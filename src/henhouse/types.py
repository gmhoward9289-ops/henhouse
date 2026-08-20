from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    name: str
    input: dict[str, Any]
    id: str | None = None
    session_id: str | None = None
    source: str = "claude"  # "claude" | "cursor"
    is_subagent: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TranscriptSummary:
    status: str
    context_pct: float | None
    model: str | None
    burn_tokens: int
    files_modified: dict[str, bool]
    cost_usd: None = None
    active_subagents: int = 0
    estimate: dict[str, Any] = field(default_factory=lambda: {"verified": True})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SessionRecord:
    """One joined session row as emitted under henhouse.session.v1 ``rows``."""

    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)
