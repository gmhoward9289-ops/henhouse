from henhouse.types import SessionRecord, ToolCall, TranscriptSummary


def test_tool_call_roundtrip():
    tc = ToolCall(name="Write", input={"file_path": "a.py"}, id="t1", session_id="s1")
    d = tc.to_dict()
    assert d["name"] == "Write"
    assert d["input"]["file_path"] == "a.py"
    assert d["is_subagent"] is False


def test_transcript_summary_cost_stays_none():
    s = TranscriptSummary(
        status="idle",
        context_pct=None,
        model=None,
        burn_tokens=0,
        files_modified={},
    )
    assert s.to_dict()["cost_usd"] is None


def test_session_record_copies_payload():
    rec = SessionRecord(payload={"pid": 1, "status": "idle"})
    d = rec.to_dict()
    assert d == {"pid": 1, "status": "idle"}
    d["pid"] = 2
    assert rec.payload["pid"] == 1
