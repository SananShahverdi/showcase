# ADR 0001: Core architecture

## Status

Accepted and implemented.

## Context

The project needs to compare a learned routing policy with classic baselines in a way that is reproducible and easy to audit, and it must run locally without a network controller.

## Decision

- One FastAPI service with in-memory state; a React console on top of the REST API.
- A directed-graph simulator (networkx) with explicit capacity, queue, loss, and utilization-dependent delay.
- A tabular Q-learning policy instead of a neural policy, so the whole policy can be hashed, versioned, and inspected.
- Every comparison resets runtime state and replays one seeded trace for all algorithms.
- Optional adapters only: MLflow when `MLFLOW_TRACKING_URI` is set, SQL persistence of the experiment registry when a database URL is set.

## Consequences

- Results are deterministic for a given topology and seed, which makes regressions testable.
- The tabular policy only suits small graphs and must be retrained after the topology changes.
- Simulator numbers are not calibrated against real telemetry and must not be presented as network measurements.
