# ADR 0001: Core Architecture

## Status

Accepted and implemented for local mode.

## Context

Real-Time Fraud and Risk Stream Analytics Platform must be understandable, runnable locally, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- event-producer
- stream-processor
- feature-store
- model-scorer
- rules-engine
- analyst-console

## Consequences

- Each module can be built and tested independently.
- The complete local event-to-decision slice stays modular enough to replace transport, state, model, and identity adapters.
- Documentation and tests describe the implemented scoring evidence and deployment boundaries.
