# ADR 0001: Core Architecture

## Status

Accepted for foundation stage.

## Context

Compliance-Aware RAG Knowledge Base must be understandable to recruiters, runnable locally when implemented, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- document-ingestion
- chunker
- retrieval-engine
- access-control
- answer-engine
- evaluation-suite

## Consequences

- Each module can be built and tested independently.
- The delivered product separates ingestion, pre-retrieval policy, ranking, grounding, governance, audit, and evaluation responsibilities.
- Documentation and UML remain aligned with implementation milestones.
- The project can be presented honestly as designed until runnable code exists.
