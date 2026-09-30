# ADR 0001: Core architecture

## Status

Accepted and implemented.

## Context

The lab must show real LLM-application failure modes side by side with controls, reproducibly and without any risk to the machine running it or dependence on a model provider.

## Decision

- A deterministic rule engine plays both agents, so verdicts are repeatable and never depend on generated prose.
- All tools are synthetic in-memory fixtures; vulnerable mode is unsafe only in meaning.
- The hardened path records every policy decision with a stable control ID and reason.
- Destructive or external actions go through a one-time approval that cannot be replayed.
- Assessments are stored and exportable as Markdown or JSON.

## Consequences

- Results are stable enough to use as a regression suite for the controls.
- The rules are pattern-based and limited to the catalog; they illustrate controls rather than prove robustness against novel attacks.
