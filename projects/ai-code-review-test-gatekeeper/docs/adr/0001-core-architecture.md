# ADR 0001: Core Architecture

## Status

Accepted and implemented for local mode.

## Context

AI Code Review and Test Gatekeeper must be understandable, runnable locally, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- pr-ingestion
- static-analyzers
- dependency-scanner
- coverage-runner
- llm-reviewer
- risk-dashboard

## Consequences

- Each module can be built and tested independently.
- The complete local diff-to-gate slice stays modular enough to replace analyzer, storage, and publisher adapters.
- Documentation and tests describe the implemented evidence and deployment boundaries.
