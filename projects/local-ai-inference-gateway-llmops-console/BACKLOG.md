# Delivery status and extensions

## Shipped local product

- [x] OpenAI-compatible chat/models/embeddings, real Ollama and generic HTTP adapters, deterministic demo provider, privacy-aware fallback, attempt logs, hashed scoped keys, rate/token quotas, PII redaction, prompt versions/activation, metrics, probes, seeded demo, and console.
- [x] Unit/integration coverage and Docker/Vite execution.

## Deployment extensions

- [ ] Move key/quota/circuit state to PostgreSQL/Redis for atomic multi-instance operation.
- [ ] Add operator OIDC/RBAC, tenant isolation, egress allowlists, and managed secret references.
- [ ] Implement cancellation-aware SSE streaming and prompt test-case evaluation.
- [ ] Add OpenTelemetry/Prometheus exporters and contract CI against supported provider versions.
