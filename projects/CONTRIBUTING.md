# Contributing Guide

This portfolio workspace follows a professional open-source workflow even when projects are developed by one person.

## Branch and Commit Style

- Use small branches per feature or project area.
- Keep commits focused and explain the behavioral change.
- Avoid mixing generated files, refactors, and feature changes in the same commit.

## Definition of Done

A project feature is done only when it has:

- documented behavior and tradeoffs,
- tests or a deterministic demo case,
- a passing backend suite and frontend production build,
- clear input/output contracts,
- accessible loading, empty, error, and success UI states where applicable,
- failure-mode notes,
- local run instructions,
- screenshots or CLI output where useful.

## Documentation Requirements

Each project should keep:

- `README.md` for business value and quick start,
- `docs/architecture.md` for components and diagrams,
- `docs/algorithms-and-data-structures.md` for core logic,
- `docs/testing-strategy.md` for verification,
- `docs/demo-script.md` for recruiter-facing demonstrations,
- `BACKLOG.md` for implementation tasks.

## AI and Automation Rules

- Do not present generated AI output as verified truth without citations, tests, or human approval.
- Keep prompts, model versions, retrieved context, and decisions auditable.
- Use synthetic or public sample data unless explicit permission exists for private data.
