# ADR 0001: Core architecture

## Status

Accepted and implemented for local mode.

## Context

Platform teams want new services to start from approved foundations with CI, containers, tests, and ownership metadata already in place, and they need proof of exactly what was generated.

## Decision

- Templates are code-rendered file maps with shared quality defaults, not user-supplied scripts, so nothing generated is executed.
- Every artifact is a deterministic ZIP (sorted entries, fixed timestamps) with per-file and archive SHA-256 digests.
- The archive is stored before the catalog record is written, and removed if registration fails.
- Templates must be approved by an admin role before use; new templates start as drafts.
- Catalog, artifact, and identity are adapters that can be replaced (database, object storage, OIDC, SCM) without changing the scaffold contract.

## Consequences

- The same request always yields the same archive checksum, which makes generated output reviewable.
- The local role header is a demonstration of authorization rules, not authentication.
