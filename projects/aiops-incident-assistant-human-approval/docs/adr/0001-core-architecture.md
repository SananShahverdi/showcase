# ADR 0001: Core Architecture

## Status

Accepted and implemented for local mode.

## Context

AIOps Incident Assistant with Human Approval must be understandable, runnable locally, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- demo-services
- incident-generator
- telemetry-ingestion
- runbook-retriever
- diagnosis-agent
- approval-console

## Consequences

- Each module can be built and tested independently.
- The complete local incident-to-report slice stays modular enough to replace repository and executor adapters.
- Documentation and tests describe the implemented lifecycle and explicit deployment boundaries.
