# Testing Strategy

## Test Pyramid

- Unit tests for pure algorithms and data structures.
- Contract tests for API schemas and persisted records.
- Integration tests for the main workflow.
- Demo smoke test that runs with seeded data and no private credentials.

## Quality Gates

- Failed checks store sample evidence and baseline comparison.
- Issue automation includes owners, severity, and suggested remediation.
- Data samples in reports must obey configured redaction rules.

## Suggested Commands

```bash
# To be finalized when implementation starts.
pytest
docker compose up --build
```

## Test Data

Use synthetic or public data only. Keep deterministic seeds and small fixtures under `tests/fixtures/` once implementation begins.
