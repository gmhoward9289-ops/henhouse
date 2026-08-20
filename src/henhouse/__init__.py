"""Parse Claude Code / Cursor JSONL into session summaries and tool-call events."""

from henhouse.schema import SCHEMA_SESSION, SCHEMA_TOOLS
from henhouse.transcripts import iter_tool_calls, read_tail, summarize
from henhouse.types import ToolCall

__all__ = [
    "SCHEMA_SESSION",
    "SCHEMA_TOOLS",
    "ToolCall",
    "iter_tool_calls",
    "read_tail",
    "summarize",
]

__version__ = "0.1.0"
