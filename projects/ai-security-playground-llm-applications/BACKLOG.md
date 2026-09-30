# Product roadmap

## Delivered local product

- [x] Versioned catalog of six threats: direct injection, poisoned retrieval, active HTML, data leakage, excessive agency, and weak tool permissions.
- [x] Vulnerable and hardened execution paths over a confined synthetic tool sandbox (file, SQL, search, ticket).
- [x] Hardened policy trace: Unicode canonicalization, role/tool permission matrix, output encoding, and one-time approvals with replay prevention.
- [x] Full 12-check red-team assessment with Markdown/JSON export and metrics.
- [x] Training console, seeded scenarios, unit tests for every attack/control pair, and end-to-end API coverage.

## Deployment extensions

- [ ] Add durable storage for runs, approvals, and assessments (currently process memory).
- [ ] Add an optional real-LLM adapter whose verdicts remain decided by policy, not generated prose.
- [ ] Add OIDC roles for learner, developer, and security-admin personas.
- [ ] Add CI publishing of assessment reports as build artifacts.
