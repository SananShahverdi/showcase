# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (5): chunking has stable offsets embeddings and validates window; policy enforces status expiry role team and clearance before retrieval; hybrid retrieval exposes real lexical and vector components; citation validation requires exact retrieved quote; parsers strip active html and reject unsupported or empty files.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (2): governed api journey; upload validation and real soft delete restore.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
- `test_rag_service.py` (2): authorized unauthorized lifecycle feedback and evaluation; redaction is real and versioned.
