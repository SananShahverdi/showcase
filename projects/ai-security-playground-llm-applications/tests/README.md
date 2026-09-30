# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (5): vulnerable app excessive agency; hardened app excessive agency; vulnerable app data leakage; hardened app data leakage; hardened output is encoded and permissions are role bound.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (2): full playground flow; custom payload audit and one time approval.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
