# ADR 0001: Core Architecture

## Status

Accepted for foundation stage.

## Context

Edge Wasm Plugin Runtime for Data and Network Rules must be understandable to recruiters, runnable locally when implemented, and defensible in a technical interview.

## Decision

Use a modular architecture with explicit boundaries:

- plugin-sdk
- runtime-host
- upload-api
- version-registry
- policy-enforcer
- benchmark-suite

## Consequences

- Each module can be built and tested independently.
- The shipped vertical slice remains replaceable without blocking future modules.
- Documentation and UML remain aligned with implementation milestones.
- The project can be presented honestly as designed until runnable code exists.
