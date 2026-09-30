# ADR 0001: Core Architecture

## Status

Accepted for foundation stage.

## Context

Smart Network Capacity Planner must be understandable to recruiters, runnable locally when implemented, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- telemetry-generator
- ingestion-api
- forecasting-engine
- optimization-engine
- what-if-dashboard
- report-generator

## Consequences

- Each module can be built and tested independently.
- The delivered product separates telemetry storage, forecasting, risk, recommendation, scenario, and report responsibilities.
- Documentation and UML remain aligned with implementation milestones.
- The project can be presented honestly as designed until runnable code exists.
