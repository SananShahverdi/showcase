# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (3): routing policy; prompt registry; hashed scoped key quota and redaction.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (3): key chat embedding prompt and metrics; failed primary is logged before safe fallback; explicit model selects matching provider and missing model is rejected.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
