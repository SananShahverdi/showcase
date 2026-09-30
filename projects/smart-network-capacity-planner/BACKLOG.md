# Product roadmap

## Delivered local product

- [x] Deterministic three-link demo telemetry and validated, idempotent batch ingestion with conflict detection.
- [x] Explainable least-squares trend forecast with MAE, confidence bounds, and sparse-history warnings.
- [x] Saturation risk from bound crossing, headroom, and loss, with stated reasons.
- [x] Budget-aware actions that keep excluded upgrades visible with the reason.
- [x] Saved what-if scenarios with baseline deltas and weekly Markdown/JSON reports.
- [x] Console, JSON-file persistence, unit, repository, and integration tests.

## Deployment extensions

- [ ] Implement the repository with TimescaleDB/PostgreSQL and transactional `(link_id, timestamp)` uniqueness.
- [ ] Add seasonal and structural-break forecasting alongside the linear baseline.
- [ ] Add a read-only telemetry collector (SNMP/streaming) adapter.
- [ ] Add SSO/RBAC, payload limits, and metrics scraping at the gateway.
