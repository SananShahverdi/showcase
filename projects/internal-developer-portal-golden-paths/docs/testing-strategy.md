# Testing strategy

```bash
PYTHONPATH=src python3 -m pytest -q
cd frontend && npm run lint && npm run build
```

| Suite | What it checks |
|---|---|
| `tests/unit/test_algorithms.py` | FastAPI and Node templates render the expected files; every golden path includes quality defaults; rendered metadata uses the requested service and owner. |
| `tests/unit/test_persistence.py` | SQL adapter round-trips, namespace isolation, redacted URLs. |
| `tests/integration/test_api.py` | Full scaffold flow including ZIP download and checksum manifest, catalog and dependency graph, admin-only template governance, and validation failures. |
| `tests/integration/test_persistence_restart.py` | Catalog and artifacts written by one process are served by a fresh one. |

The portfolio browser check (`tools/verify_frontend_workflows.mjs`) previews and generates a service, downloads the ZIP, and confirms the result is cleared when the form changes.

All inputs are synthetic service names and owners.
