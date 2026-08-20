# PyPI trusted publishing (one-time)

Register a **pending publisher** for each project at
https://pypi.org/manage/account/publishing/ before `release.yml` can upload.

Use **GitHub** as the publisher. Settings must match exactly:

| Field | henhouse | pytest-session-trace |
| --- | --- | --- |
| Owner | `gmhoward9289-ops` | `gmhoward9289-ops` |
| Repository | `henhouse` | `pytest-session-trace` |
| Workflow name | `release.yml` | `release.yml` |
| Environment name | `pypi` | `pypi` |

GitHub: each repo needs **Settings → Environments → `pypi`** (no secrets; OIDC only).

After both publishers are saved on PyPI, re-run the failed release workflow or push a patch tag:

```powershell
gh workflow run release -R gmhoward9289-ops/henhouse --ref v0.1.1
gh workflow run release -R gmhoward9289-ops/pytest-session-trace --ref v0.1.1
```

Or delete and re-push `v0.1.1` once publishers exist.

Verify:

```powershell
pip index versions henhouse
pip index versions pytest-session-trace
```
