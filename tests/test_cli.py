from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def assistant_write():
    return {
        "type": "assistant",
        "message": {
            "model": "claude-sonnet-5",
            "content": [
                {"type": "tool_use", "id": "t1", "name": "Write",
                 "input": {"file_path": "a.py"}},
            ],
        },
    }


def test_module_cli_emits_tools_schema(tmp_path: Path):
    path = tmp_path / "sess.jsonl"
    path.write_text(json.dumps(assistant_write()) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "henhouse", str(path)],
        capture_output=True,
        text=True,
        check=True,
        cwd=str(Path(__file__).resolve().parent.parent),
        env={**{k: v for k, v in __import__("os").environ.items()},
             "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src")},
    )
    payload = json.loads(proc.stdout)
    assert payload["schema"] == "henhouse.tools.v1"
    assert [c["name"] for c in payload["calls"]] == ["Write"]
    assert payload["calls"][0]["input"]["file_path"] == "a.py"


def test_module_cli_legacy_json_is_a_bare_list(tmp_path: Path):
    path = tmp_path / "sess.jsonl"
    path.write_text(json.dumps(assistant_write()) + "\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "henhouse", "--legacy-json", str(path)],
        capture_output=True,
        text=True,
        check=True,
        env={**{k: v for k, v in __import__("os").environ.items()},
             "PYTHONPATH": str(Path(__file__).resolve().parent.parent / "src")},
    )
    payload = json.loads(proc.stdout)
    assert isinstance(payload, list)
    assert payload[0]["name"] == "Write"
