# henhouse

Parse Claude Code and Cursor JSONL transcripts into typed session summaries
and tool-call events. Stdlib only. Read-only: it never writes a transcript,
a registry, or a git tree.

This package is the data layer. It is not the curses dashboard (that stays in
[leghorn](https://github.com/gmhoward9289-ops/leghorn)) and it is not `top`
for sessions (that stays in [roost](https://github.com/gmhoward9289-ops/roost)).
Those products **link** this schema; they do not take a pip dependency on it.

The JSON shape can change. Treat breakage as expected until a later version
is frozen.

## Install

Python 3.10+:

```bash
pip install -e ".[dev]"
```

One-file / no-deps install is still how roost and leghorn ship: copy this
package's `src/henhouse/` tree, or keep using the vendored parser in those
repos until an optional import lands.

```python
from henhouse import iter_tool_calls, summarize, read_tail, ToolCall, SCHEMA_TOOLS
```

If a `pip install leghorn` put a top-level `henhouse.py` on `sys.path`, that
file wins over this package. Use `PYTHONPATH=src` or uninstall the leftover
module file; roost and leghorn themselves keep their vendored parser and do
not `pip install henhouse`.

## CLI

```bash
python -m henhouse path.jsonl
```

prints

```json
{"schema": "henhouse.tools.v1", "calls": [ ... ]}
```

`--legacy-json` prints a bare list of call objects.

`cost_usd` on session summaries is always `None`. Token counts are not a
subscription bill; this package will not invent money.

## Used by

- [leghorn](https://github.com/gmhoward9289-ops/leghorn) — live git/CI dashboard
- [roost](https://github.com/gmhoward9289-ops/roost) — `top` for sessions
- [pytest-session-trace](https://github.com/gmhoward9289-ops/pytest-session-trace) — CI assertions (plan 3)

## License

Apache-2.0
