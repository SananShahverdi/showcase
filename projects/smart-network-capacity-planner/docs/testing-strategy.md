# Testing Strategy

## Test Pyramid

- Unit tests for pure algorithms and data structures.
- Contract tests for API schemas and persisted records.
- Integration tests for the main workflow.
- Demo smoke test that runs with seeded data and no private credentials.

## Quality Gates

- Forecast outputs include uncertainty and historical error.
- Recommendations state budget, affected links, and expected risk reduction.
- Synthetic network telemetry is reproducible by seed.

## Suggested Commands

```bash
# To be finalized when implementation starts.
pytest
docker compose up --build
```

## Test Data

Use synthetic or public data only. Keep deterministic seeds and small fixtures under `tests/fixtures/` once implementation begins.
