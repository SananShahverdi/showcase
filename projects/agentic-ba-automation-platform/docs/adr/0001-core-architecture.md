# ADR 0001: Core Architecture

## Status

Accepted for foundation stage.

## Context

Agentic BA Automation Platform must be understandable to recruiters, runnable locally when implemented, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- document-ingestion
- rag-indexer
- agent-orchestrator
- approval-api
- ticket-exporter
- audit-log

## Consequences

- Each module can be built and tested independently.
- The delivered product keeps parsing, retrieval, artifact generation, review state, export, and audit behind replaceable boundaries.
- Documentation and UML remain aligned with implementation milestones.
- The project can be presented honestly as designed until runnable code exists.
