# Product roadmap

## Delivered local product

- [x] PDF, DOCX, Markdown, HTML, and text ingestion with checksums, classification, redaction, and offset-preserving chunking.
- [x] Pre-retrieval policy on status, expiry, clearance, role, and team; no leakage of inaccessible titles or counts.
- [x] Deterministic hybrid retrieval (lexical coverage plus 64-dimension hashed vectors) with a relevance threshold.
- [x] Extractive answers with validated exact citations, or explicit abstention.
- [x] Document lifecycle, versioned redaction rules, retention preview/enforcement, feedback, and audit trail.
- [x] Golden-set evaluation of retrieval hits, citation validity, abstention accuracy, and permission leaks.
- [x] Ask/Documents/Governance/Audit/Evaluation console, JSON persistence, unit and integration tests.

## Deployment extensions

- [ ] Implement repositories with PostgreSQL/pgvector, migrations, backups, and immutable audit controls.
- [ ] Replace demo identity headers with verified OIDC/SSO claims at the boundary.
- [ ] Add malware scanning, rate limits, and encryption/key management for uploads.
- [ ] Add optional LLM synthesis restricted to permitted context and gated by the same grounding evaluation.
