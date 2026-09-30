# Testing strategy

```bash
PYTHONPATH=src python3 -m pytest -q
cd frontend && npm run lint && npm run build
```

| Suite | What it checks |
|---|---|
| `tests/unit/test_algorithms.py` | Routing by capability, privacy, and priority; prompt variable extraction and strict rendering; hashed scoped keys, rate and quota limits, redaction. |
| `tests/unit/test_persistence.py` | SQL adapter round-trips, namespace isolation, redacted URLs. |
| `tests/integration/test_api.py` | Key-authenticated chat and embeddings, templates, and metrics; a failing primary is logged before a safe fallback; explicit model selection and unknown-model rejection. |
| `tests/integration/test_persistence_restart.py` | State written by one process is served by a fresh one. |

Real provider adapters are exercised only through the deterministic provider in these tests; contract tests against a local fake HTTP server are a sensible next step before deployment. The portfolio browser check (`tools/verify_frontend_workflows.mjs`) seeds the demo and sends chat and embedding requests through the mounted routes.
