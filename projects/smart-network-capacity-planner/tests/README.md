# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (4): forecast uses observed trend and reports quality; sparse history is flat and has explicit warning; risk calculation critical from confidence bound; optimizer marks unaffordable upgrade but keeps zero cost mitigation.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.
- `test_repository.py` (2): conflicting batch does not partially update live or persisted state; batch internal conflicts are atomic and identical duplicates count once.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (3): seed forecast scenario and report journey; ingestion is idempotent and conflicts are rejected; validation and empty states are explicit.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
