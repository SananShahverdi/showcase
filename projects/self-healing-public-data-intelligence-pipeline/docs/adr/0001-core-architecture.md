# ADR 0001: Core Architecture

## Status

Accepted for foundation stage.

## Context

Self-Healing Public Data Intelligence Pipeline must be understandable to recruiters, runnable locally when implemented, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- crawler
- extractor
- validator
- repair-agent
- recipe-registry
- health-dashboard

## Consequences

- Each module can be built and tested independently.
- The delivered product keeps source access, extraction, validation, repair replay, approval, and storage behind replaceable boundaries.
- Documentation and UML remain aligned with implementation milestones.
- The project can be presented honestly as designed until runnable code exists.
