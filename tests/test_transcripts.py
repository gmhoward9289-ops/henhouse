#!/usr/bin/env python3
"""Tests for transcript telemetry and tool_use extraction.

The failure modes worth pinning are all silent ones. A wrong context window
produces a plausible-looking percentage rather than an error. Summing cache
reads across turns instead of taking the last one inflates context without
ever exceeding 100%. And seeking to a fixed byte offset lands mid-record, so
the first line of the tail window is half a JSON object.

summarize() still drops Read/Bash from files_modified. iter_tool_calls is the
list that keeps every tool_use block.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from henhouse.transcripts import (
    ATTENTION,
    DEFAULT_WINDOW,
    TAIL_BYTES,
    WORKING_SECS,
    context_window,
    iter_tool_calls,
    read_tail,
    summarize,
    transcript_index,
)


def assistant(usage=None, tools=(), model="claude-sonnet-5"):
    content = [{"type": "tool_use", "name": n, "input": {"file_path": p}}
               for n, p in tools]
    msg = {"model": model, "content": content}
    if usage is not None:
        msg["usage"] = usage
    return {"type": "assistant", "message": msg}


def user(text="hi"):
    return {"type": "user", "message": {"content": text}}


USAGE = {"input_tokens": 2, "cache_read_input_tokens": 100_000,
         "cache_creation_input_tokens": 0, "output_tokens": 500}


def test_known_models():
    assert context_window("claude-opus-5") == 1_000_000
    assert context_window("claude-sonnet-5") == 1_000_000
    assert context_window("claude-haiku-4-5") == 200_000


def test_haiku_is_not_shadowed_by_a_broader_prefix():
    # Haiku's 200K window is the one value that differs. If a broader entry
    # ever matched first, its percentages would silently read 5x too low.
    assert context_window("claude-haiku-4-5-20251001") == 200_000


def test_unknown_model_falls_through():
    assert context_window("claude-nonesuch-9") == DEFAULT_WINDOW
    assert context_window(None) == DEFAULT_WINDOW


def test_context_is_the_last_turn_not_the_sum():
    # Cache reads repeat every turn. Summing them would climb without bound.
    recs = [assistant(USAGE), assistant(USAGE), assistant(USAGE)]
    out = summarize(recs, time.time())
    assert round(out["context_pct"], 4) == round(100_002 / 10_000, 4)


def test_burn_is_cumulative():
    out = summarize([assistant(USAGE), assistant(USAGE)], time.time())
    assert out["burn_tokens"] == 1000


def test_pct_uses_the_model_from_the_transcript():
    haiku = summarize([assistant(USAGE, model="claude-haiku-4-5")], time.time())
    opus = summarize([assistant(USAGE, model="claude-opus-5")], time.time())
    assert haiku["context_pct"] > opus["context_pct"]


def test_write_paths_collected_and_normalized():
    recs = [assistant(USAGE, tools=[("Edit", r"C:\Users\x\dev\proj\a.py"),
                                    ("Read", r"C:\Users\x\dev\proj\b.py")])]
    files = summarize(recs, time.time())["files_modified"]
    # Backslashes must become forward slashes or the INFRA filter and
    # split_path both fail to match on Windows.
    assert "C:/Users/x/dev/proj/a.py" in files
    # A Read says nothing about which project a session is working on.
    assert "C:/Users/x/dev/proj/b.py" not in files


def test_status_waiting_on_a_bare_assistant_turn():
    out = summarize([user(), assistant(USAGE)], time.time())
    assert out["status"] == "needsinput"
    assert out["status"] in ATTENTION


def test_status_working_while_tools_run():
    out = summarize([user(), assistant(USAGE, tools=[("Write", "/tmp/a")])],
                    time.time())
    assert out["status"] == "working"


def test_status_idle_when_the_transcript_is_cold():
    stale = time.time() - (WORKING_SECS + 60)
    out = summarize([user(), assistant(USAGE, tools=[("Write", "/tmp/a")])],
                    stale)
    assert out["status"] == "idle"


def test_empty_transcript_yields_no_context():
    out = summarize([], time.time())
    assert out["context_pct"] is None
    assert out["cost_usd"] is None


def test_cost_is_never_fabricated():
    # A token-derived dollar figure is meaningless against a flat
    # subscription; emitting one would read as money that was never spent.
    assert summarize([assistant(USAGE)], time.time())["cost_usd"] is None


def test_iter_tool_calls_keeps_read_and_write():
    recs = [assistant(USAGE, tools=[("Read", "a.py"), ("Write", "b.py")])]
    calls = iter_tool_calls(recs, session_id="s")
    assert [c.name for c in calls] == ["Read", "Write"]
    assert calls[0].session_id == "s"
    assert calls[0].is_subagent is False


def test_iter_tool_calls_keeps_bash_and_preserves_order():
    recs = [
        assistant(USAGE, tools=[("Read", "a.py")]),
        {
            "type": "assistant",
            "message": {
                "model": "claude-sonnet-5",
                "content": [
                    {"type": "tool_use", "id": "t2", "name": "Bash",
                     "input": {"command": "ls"}},
                    {"type": "tool_use", "name": "Write",
                     "input": {"file_path": "b.py"}},
                ],
            },
        },
    ]
    calls = iter_tool_calls(recs)
    assert [c.name for c in calls] == ["Read", "Bash", "Write"]
    assert calls[1].input["command"] == "ls"
    assert calls[1].id == "t2"


def test_iter_tool_calls_marks_subagent_stream():
    recs = [assistant(USAGE, tools=[("Read", "a.py")])]
    calls = iter_tool_calls(recs, session_id="agent-1", is_subagent=True)
    assert calls[0].is_subagent is True
    assert calls[0].session_id == "agent-1"


def test_transcript_index_skips_agent_sidecars(tmp_path: Path):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "sess-1.jsonl").write_text("{}\n", encoding="utf-8")
    (proj / "agent-deadbeef.jsonl").write_text("{}\n", encoding="utf-8")
    index = transcript_index(tmp_path)
    assert set(index) == {"sess-1"}
    assert index["sess-1"].name == "sess-1.jsonl"


def _write(tmp: Path, records) -> Path:
    path = tmp / "s.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records),
                    encoding="utf-8")
    return path


def test_reads_every_record_of_a_small_file(tmp_path: Path):
    path = _write(tmp_path, [user(), assistant(USAGE)])
    assert len(read_tail(path)) == 2


def test_drops_the_partial_first_line_of_a_large_file(tmp_path: Path):
    # Pad past TAIL_BYTES so the seek lands mid-record, then confirm the
    # tail still parses and keeps the final turn.
    pad = [user("x" * 4000) for _ in range(120)]
    path = _write(tmp_path, pad + [assistant(USAGE)])
    assert path.stat().st_size > TAIL_BYTES
    recs = read_tail(path)
    assert recs
    assert recs[-1]["type"] == "assistant"


def test_truncated_trailing_line_is_skipped_not_fatal(tmp_path: Path):
    # A transcript being appended to while we read it ends mid-object.
    path = tmp_path / "s.jsonl"
    path.write_text(json.dumps(user()) + "\n" + '{"type": "assis',
                    encoding="utf-8")
    assert len(read_tail(path)) == 1


def test_missing_file_is_empty_not_an_exception(tmp_path: Path):
    assert read_tail(tmp_path / "nope.jsonl") == []
