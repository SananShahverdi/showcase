# Product roadmap

## Delivered local product

- [x] Bounded multi-service source, configuration, and manifest scanning with file/line evidence and redacted excerpts.
- [x] Versioned rules for weak hashes, embedded key material, classical asymmetric crypto, TLS protocols, symmetric modes, and PQC candidates.
- [x] Captured TLS observation analysis; bare endpoint names never produce findings.
- [x] Opt-in authorized live TLS probe with HTTPS-only and non-global address (SSRF) blocking.
- [x] Migration priority from severity, internet exposure, and data-retention horizon; strict quantum-safe verdict.
- [x] Stored scans, dashboard, Markdown/JSON export, console, unit and integration tests.

## Deployment extensions

- [ ] Add durable scan storage (currently process memory).
- [ ] Add language-aware AST analysis to reduce pattern-matching false positives.
- [ ] Add dependency manifest resolution against a vulnerability/crypto-library database.
- [ ] Add scheduled rescans and trend reporting across scan history.
