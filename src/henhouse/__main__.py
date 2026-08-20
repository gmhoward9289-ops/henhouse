"""python -m henhouse PATH.jsonl — emit henhouse.tools.v1 tool_use events."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from henhouse.schema import SCHEMA_TOOLS
from henhouse.transcripts import iter_tool_calls, read_tail


def _records(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    size = path.stat().st_size
    return read_tail(path, tail_bytes=max(size, 1))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Read a Claude Code / Cursor JSONL transcript and emit "
                    "tool_use events as JSON. Read-only.")
    ap.add_argument("path", help="transcript .jsonl file")
    ap.add_argument("--session-id", default=None,
                    help="optional session id stamped onto every call")
    ap.add_argument("--subagent", action="store_true",
                    help="mark calls as coming from an agent-*.jsonl sidecar")
    ap.add_argument("--source", default="claude", choices=("claude", "cursor"))
    ap.add_argument("--legacy-json", action="store_true",
                    help="emit a bare JSON list of calls instead of the wrapper")
    args = ap.parse_args(argv)

    path = Path(args.path)
    sid = args.session_id if args.session_id is not None else path.stem
    is_subagent = args.subagent or path.name.startswith("agent-")
    calls = [
        c.to_dict()
        for c in iter_tool_calls(
            _records(path),
            session_id=sid,
            is_subagent=is_subagent,
            source=args.source,
        )
    ]
    if args.legacy_json:
        json.dump(calls, sys.stdout, indent=2)
    else:
        json.dump({"schema": SCHEMA_TOOLS, "calls": calls}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
