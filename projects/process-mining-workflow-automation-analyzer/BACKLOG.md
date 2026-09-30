# Product roadmap

## Delivered local product

- [x] JSON, RFC-4180 CSV (BOM-safe), and safe XES-like XML import with DTD/entity rejection and size caps.
- [x] Data-quality accounting for accepted, rejected, and duplicate events.
- [x] Directly-follows transitions, variant coverage, mean/median/p95 delays, case durations, SLA breaches, rework, resource load, and handoffs.
- [x] Evidence-bound automation recommendations and deterministic narrative.
- [x] Report history, Markdown and GitHub-Issues-compatible JSON export, console, unit and integration tests.

## Deployment extensions

- [ ] Add durable report storage (currently process memory).
- [ ] Add streaming import for logs above the 100,000-event cap.
- [ ] Add an optional prose adapter that cannot create or alter metrics.
- [ ] Add conformance checking against a reference process model.
