# henhouse JSON schemas

Version identifiers live in `henhouse.schema`. **0.1.x treats these shapes as
stable for downstream tools** (`pytest-session-trace`, roost/leghorn link
layers). Additive fields are OK; renames or type changes require a new schema
version string.

## `henhouse.tools.v1`

Emitted by `python -m henhouse PATH.jsonl` (default).

```json
{
  "schema": "henhouse.tools.v1",
  "calls": [ { ... ToolCall ... } ]
}
```

`--legacy-json` prints a bare list of call objects (pre-v1 shape).

### `ToolCall` object

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `name` | string | yes | MCP / Claude tool name |
| `input` | object | yes | tool arguments (may be empty) |
| `id` | string | no | `tool_use` block id when present |
| `session_id` | string | no | transcript stem or sidecar id |
| `source` | string | no | `"claude"` default; `"cursor"` when tagged |
| `is_subagent` | bool | no | `true` for `agent-*.jsonl` sidecars |

## `henhouse.session.v1`

Emitted by leghorn/henhouse session dashboards (`--json` default). Row payload
keys are joined session fields — see leghorn `henhouse.py` row builder. Not
parsed by `pytest-session-trace` today; session assertions use JSONL or
`tools.v1` envelopes via `load_tool_calls`.

## Loading from disk

`load_tool_calls(path)` accepts:

1. JSONL transcript (Claude Code `assistant` records with `tool_use` blocks)
2. `henhouse.tools.v1` envelope JSON
3. Legacy bare list of `ToolCall` dicts
