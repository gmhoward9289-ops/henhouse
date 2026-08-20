# Changelog

Format of `python -m henhouse` JSON is a wrapper object, not a bare list:

```json
{"schema": "henhouse.tools.v1", "calls": [ ... ]}
```

`--legacy-json` restores a bare list.

## 0.1.2

- `docs/SCHEMA.md` — frozen `henhouse.tools.v1` / `ToolCall` fields for 0.1.x
- Redacted transcript fixtures under `tests/fixtures/`

## 0.1.1

- PyPI maiden release (`pip install henhouse`)
- `load_tool_calls`, `tool_calls_from_dicts` — JSONL, `henhouse.tools.v1` envelope, legacy list

## 0.1.0

- `ToolCall`, `read_tail`, `summarize`, `iter_tool_calls`
- `iter_tool_calls` keeps every assistant `tool_use` block (Read, Bash, Write, …)
- `cost_usd` is always `None`
