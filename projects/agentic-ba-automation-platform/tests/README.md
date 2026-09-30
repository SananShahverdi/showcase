# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (5): document extraction; chunking and retrieval; agent generation; every artifact type is grounded; invalid chunk configuration and empty evidence.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (3): ingest review export audit workflow; upload and generation boundaries; github export is local even when credentials are inherited.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
