# ADR 0001: Core architecture

## Status

Accepted and implemented.

## Context

Teams running local models need one OpenAI-compatible entry point with routing they can explain, privacy rules that cannot be silently bypassed by fallback, usage controls, and operational evidence that does not leak prompts or secrets.

## Decision

- Expose the OpenAI `/v1` chat, embeddings, and models contract so existing clients work unchanged.
- Keep routing a pure function (filter, then order) and reapply the same filters on every fallback.
- Store gateway keys only as HMAC hashes; reveal the plaintext once.
- Log every provider attempt as metadata only.
- Ship a clearly labeled deterministic provider so the project runs and is tested offline; real providers use bounded HTTP adapters.

## Consequences

- Routing and fallback behavior are unit-testable without network access.
- Per-process rate windows and open admin endpoints are acceptable locally but must change for a shared deployment.
