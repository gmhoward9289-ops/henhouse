"""Claude Code / Cursor JSONL transcript parsing.

Ported from leghorn's henhouse.py. Read-only: never writes a transcript,
registry, or git tree. Runtime is stdlib only.

cost_usd stays None on purpose. Token counts are not a subscription bill.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from henhouse.types import ToolCall

HOME = Path.home()
PROJECTS_DIR = Path(os.environ.get("CLAUDE_PROJECTS_DIR") or HOME / ".claude" / "projects")

TAIL_BYTES = 256 * 1024

# Context window per model, longest prefix wins. Sourced from the Anthropic
# model reference rather than guessed -- a wrong denominator here is exactly
# the failure mode that made claudectl's percentages untrustworthy.
CONTEXT_WINDOWS = (
    ("claude-haiku-4-5", 200_000),
    ("claude-opus-5", 1_000_000),
    ("claude-sonnet-5", 1_000_000),
    ("claude-fable-5", 1_000_000),
    ("claude-opus-4", 1_000_000),
    ("claude-sonnet-4", 1_000_000),
)
DEFAULT_WINDOW = 200_000

# Tool names whose input carries a path the session wrote to. Reads are excluded
# on purpose: opening a file says nothing about which project a session is on.
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")

# A turn is "live" if the transcript was touched this recently.
WORKING_SECS = 90

ATTENTION = ("needsinput", "waiting", "error", "failed")


def context_window(model: str | None) -> int:
    for prefix, size in CONTEXT_WINDOWS:
        if model and model.startswith(prefix):
            return size
    return DEFAULT_WINDOW


def transcript_index(projects_dir: Path | None = None) -> dict[str, Path]:
    """sessionId -> newest transcript path.

    Agent sidecars (agent-*.jsonl) are skipped here: they are subagent traces,
    not sessions. Walk them separately and pass is_subagent=True to
    iter_tool_calls.
    """
    root = projects_dir if projects_dir is not None else PROJECTS_DIR
    index: dict[str, Path] = {}
    if not root.is_dir():
        return index
    for path in root.glob("*/*.jsonl"):
        if path.name.startswith("agent-"):
            continue
        sid = path.stem
        prev = index.get(sid)
        try:
            if prev is None or path.stat().st_mtime > prev.stat().st_mtime:
                index[sid] = path
        except OSError:
            continue
    return index


def read_tail(path: str | Path, tail_bytes: int = TAIL_BYTES) -> list[dict]:
    """Whole JSON records from the last tail_bytes of a file.

    The first line of the window is dropped unless the window starts at byte 0 --
    seeking to a fixed offset lands mid-record, and a half line is not JSON.
    """
    path = Path(path)
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            start = max(0, size - tail_bytes)
            fh.seek(start)
            blob = fh.read()
        lines = blob.decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    if start and lines:
        lines = lines[1:]
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except ValueError:
            continue
    return records


def summarize(records: list[dict], mtime: float) -> dict[str, Any]:
    """One transcript's records -> the telemetry fields a dashboard consumes."""
    model = None
    context_tokens = None
    burn = 0
    files: dict[str, bool] = {}
    last_role = None
    last_had_tool = False

    for rec in records:
        kind = rec.get("type")
        msg = rec.get("message") or {}
        if kind in ("user", "assistant"):
            last_role = kind
        if kind != "assistant":
            continue
        last_had_tool = False
        usage = msg.get("usage") or {}
        if usage:
            model = msg.get("model") or model
            total = 0
            for field in ("input_tokens", "cache_read_input_tokens",
                          "cache_creation_input_tokens"):
                value = usage.get(field)
                if isinstance(value, int):
                    total += value
            # Cache reads dominate and are not cumulative across turns -- the
            # last turn's total IS the live context size, so take it rather
            # than summing.
            if total:
                context_tokens = total
            out = usage.get("output_tokens")
            if isinstance(out, int):
                burn += out
        for block in msg.get("content") or ():
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            last_had_tool = True
            if block.get("name") not in WRITE_TOOLS:
                continue
            target = (block.get("input") or {}).get("file_path")
            if isinstance(target, str) and target:
                # split_path and the INFRA filter both expect POSIX separators.
                files[target.replace("\\", "/")] = True

    idle = max(0.0, time.time() - mtime)
    if idle < WORKING_SECS:
        status = "working" if (last_role == "user" or last_had_tool) else "needsinput"
    elif last_role == "assistant" and not last_had_tool:
        status = "needsinput"
    else:
        status = "idle"

    pct = None
    if context_tokens:
        pct = 100.0 * context_tokens / context_window(model)

    return {
        "status": status,
        "context_pct": pct,
        "model": model,
        "burn_tokens": burn,
        "files_modified": files,
        # cost_usd stays unset on purpose. A token-derived API list-price
        # equivalent is unrelated to a flat subscription -- a number that
        # reads as money but never was.
        "cost_usd": None,
        "active_subagents": 0,
        "estimate": {"verified": True},
    }


def iter_tool_calls(
    records: list[dict],
    *,
    session_id: str | None = None,
    is_subagent: bool = False,
    source: str = "claude",
) -> list[ToolCall]:
    """Every assistant tool_use block, including Read. Order preserved."""
    calls: list[ToolCall] = []
    for rec in records:
        if rec.get("type") != "assistant":
            continue
        msg = rec.get("message") or {}
        content = msg.get("content") or ()
        if isinstance(content, str):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name")
            if not isinstance(name, str) or not name:
                continue
            raw_input = block.get("input")
            tool_input = raw_input if isinstance(raw_input, dict) else {}
            tool_id = block.get("id")
            calls.append(
                ToolCall(
                    name=name,
                    input=tool_input,
                    id=tool_id if isinstance(tool_id, str) else None,
                    session_id=session_id,
                    source=source,
                    is_subagent=is_subagent,
                )
            )
    return calls
