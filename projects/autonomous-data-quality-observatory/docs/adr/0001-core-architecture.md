# ADR 0001: Core Architecture

## Status

Accepted for foundation stage.

## Context

Autonomous Data Quality Observatory must be understandable to recruiters, runnable locally when implemented, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- connectors
- profiler
- rules-engine
- drift-detector
- ai-explainer
- issue-bot

## Consequences

- Each module can be built and tested independently.
- The delivered product separates connector safety, profiling, rule evaluation, baseline drift, health, and incident lifecycle responsibilities.
- Documentation and UML remain aligned with implementation milestones.
- The project can be presented honestly as designed until runnable code exists.
