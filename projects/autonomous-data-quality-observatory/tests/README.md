# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (5): csv connector profiles real content; rules cover schema volume null uniqueness range freshness and business expression; safe expression rejects calls and attribute access; drift detects schema volume and distribution changes; empty profile is valid evidence.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (3): seed drift deduplicate and resolve journey; real inline source and rule validation; connector errors are explicit and not fabricated.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
