# Product roadmap

## Delivered local product

- [x] Bounded CSV, JSON, inline, file (allow-listed directory), and HTTP (allow-listed host) connectors with secret redaction.
- [x] Immutable column profiles: counts, schema, types, nulls, uniqueness, numeric statistics, top values, and content hash.
- [x] Eight rule families, including AST allow-listed business expressions.
- [x] Baseline drift detection for schema, type, volume, and numeric mean shift with scores and thresholds.
- [x] Explainable dataset health, deduplicated incidents, triage lifecycle, and Jira-compatible JSON export.
- [x] Clean and drifted demo datasets, JSON-file persistence, console, unit and integration tests.

## Deployment extensions

- [ ] Implement the repository boundary with PostgreSQL and transactional incident fingerprints for multi-replica use.
- [ ] Add read-only PostgreSQL and S3 connectors with deployment secret resolution (currently fail closed).
- [ ] Add scheduled observation workers with sampling/pushdown for large datasets.
- [ ] Add an authenticated, idempotent webhook adapter for issue delivery.
- [ ] Add SSO/RBAC, TLS, metrics collection, and retention policy before external exposure.
