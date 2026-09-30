# Testing strategy

```bash
PYTHONPATH=src python3 -m pytest -q
cd frontend && npm run lint && npm run build
```

| Suite | What it checks |
|---|---|
| `tests/unit/test_algorithms.py` | Excessive-agency and data-leakage attack/control pairs; payload-dependent vulnerable verdicts; HTML encoding; role denial and admin approval gating for tickets; read-only SQL. |
| `tests/unit/test_persistence.py` | SQL adapter round-trips, namespace isolation, redacted URLs. |
| `tests/integration/test_api.py` | Catalog, both modes, the 12-check assessment and its counts, export, full-width Unicode injection, the approval lifecycle and replay refusal, run history, assessment listing order. |
| `tests/integration/test_persistence_restart.py` | State written by one process is served by a fresh one when a database URL is set. |

The portfolio browser check (`tools/verify_frontend_workflows.mjs`) compares both modes and runs the full assessment.

All payloads and tool effects are synthetic fixtures.
