# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (2): process engine; case sla resource and variant metrics.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (4): full analyzer flow; csv and xes import share the analysis pipeline; spreadsheet csv bom is accepted and parser errors are explained; xes lifecycle events are preserved during deduplication.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
