# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (4): fastapi template; node template; every golden path has quality defaults; template render uses request identity.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (2): full scaffold flow; template governance and validation.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
