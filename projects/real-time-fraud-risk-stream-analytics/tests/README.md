# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (5): stream processor velocity; geo anomaly and scoring; out of order event does not mutate live state; amount spike is explainable and bounded; offsets and legacy timestamps share one event time window.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (3): full stream and analyst flow; normal and duplicate event outcomes; browser timestamp after seed and default timestamp can mix.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
