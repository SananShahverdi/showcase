# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (6): locator ranking; schema validation; dom fingerprinting; recipe scoring; anomaly detection; real css extraction supports repeating records and attributes.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (1): extract quarantine replay and activate.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
