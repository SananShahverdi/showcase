# Security Policy

These are full viable local portfolio products and should remain on trusted local interfaces unless a deployment receives authentication, TLS, secret management, security review, monitoring, backup, and project-specific hardening.

## Supported Scope

Security notes cover:

- prompt injection and tool abuse in LLM projects,
- secrets handling and environment configuration,
- scraping safety and rate limits,
- Docker and dependency scanning,
- access control and audit logging,
- unsafe automation and human approval gates.

## Reporting

For public repository use, open a private security advisory or contact the repository owner directly. Do not publish exploit details before a fix is available.

## Baseline Controls

- Never commit real API keys, tokens, cookies, or private datasets.
- Keep `.env.example` values non-sensitive.
- Prefer read-only demos and synthetic data.
- Require human approval for operational remediation.
- Log enough context for auditability without exposing secrets or personal data.
