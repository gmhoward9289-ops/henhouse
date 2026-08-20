"""Load redacted fixture transcripts — schema smoke for downstream tools."""

from __future__ import annotations

from pathlib import Path

from henhouse.transcripts import iter_tool_calls, load_tool_calls, read_tail

FIXTURES = Path(__file__).parent / "fixtures"


def test_redacted_jsonl_yields_tool_calls():
    path = FIXTURES / "redacted_read_session.jsonl"
    names = [c.name for c in iter_tool_calls(read_tail(path))]
    assert names == ["Read", "Bash"]


def test_redacted_tools_envelope_loads():
    calls = load_tool_calls(FIXTURES / "redacted_tools_envelope.json")
    assert [c.name for c in calls] == ["Write", "Grep"]
