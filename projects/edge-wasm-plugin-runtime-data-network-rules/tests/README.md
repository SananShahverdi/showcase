# Tests

Run from the project root:

```bash
PYTHONPATH=src python3 -m pytest tests -q
```

## `unit/`

Pure algorithm and domain checks with no HTTP layer.

- `test_algorithms.py` (4): data cleaning adapter execution is explicitly labeled; alert filter adapter and output limit; wasm validation rejects fake strings and checks exports; missing runtime never falls back to local rule logic.
- `test_persistence.py` (3): state round trips including in place edits and deletes; namespaces do not collide; urls are redacted.
- `test_wasmtime_executor.py` (8): real wasm roundtrips nested json and reports consumed fuel; infinite loop exhausts fuel without hanging; execution deadline interrupts even with large fuel budget; guest failures are bounded and explicit; wasm memory growth cannot exceed the store limit; host imports are denied even if manifest declares them; start function is also subject to fuel limit; invalid json values and excessive nesting are execution errors.

## `integration/`

End-to-end API journeys through FastAPI's test client.

- `test_api.py` (5): plugin lifecycle canary activation metrics and rollback; invalid wasm is quarantined and not simulated; seeded demo exposes three honestly labeled adapters; real wasm upload canary activation and execution; seeded real wasm transforms payload in the workbench.
- `test_persistence_restart.py` (2): state survives a restart; without a database url state stays in memory.
