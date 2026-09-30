# Architecture

## System Goal

Profile datasets, detect quality regressions, explain failures, and open remediation issues.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    connectors[connectors]
    profiler[profiler]
    rules_engine[rules-engine]
    drift_detector[drift-detector]
    ai_explainer[ai-explainer]
    issue_bot[issue-bot]
    api --> connectors
    api --> profiler
    api --> rules_engine
    api --> drift_detector
    api --> ai_explainer
    api --> issue_bot
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as connectors
    participant M2 as issue-bot
    participant DB as Storage
    U->>UI: Submit request or dataset
    UI->>API: Validate request
    API->>M1: Start controlled workflow
    M1->>DB: Persist raw input and metadata
    API->>M2: Generate result or decision
    M2->>DB: Store result, evidence, and status
    API-->>UI: Return traceable outcome
```

## Domain Model

```mermaid
classDiagram
    class Dataset {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Snapshot {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Expectation {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class DriftSignal {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class QualityIncident {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Issue {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Dataset --> Snapshot
    Snapshot --> Expectation
    Expectation --> DriftSignal
    DriftSignal --> QualityIncident
    QualityIncident --> Issue
```

## Component Responsibilities

- `connectors`: owns one bounded responsibility in the workflow.
- `profiler`: owns one bounded responsibility in the workflow.
- `rules-engine`: owns one bounded responsibility in the workflow.
- `drift-detector`: owns one bounded responsibility in the workflow.
- `ai-explainer`: owns one bounded responsibility in the workflow.
- `issue-bot`: owns one bounded responsibility in the workflow.

## Data and Control Boundaries

- Raw inputs are preserved before transformation.
- Validated records or decisions are separated from quarantined failures.
- Human approval or policy checks are explicit where automation can affect users, infrastructure, or security.
- Observability data is treated as a first-class output: logs, metrics, traces, decisions, and errors.

## Deployment Shape

- Local: Docker Compose with the FastAPI service, purpose-built React console, and project-specific persistence/provider dependencies.
- CI: lint, unit tests, integration smoke test, dependency scan.
- Demo: seeded data plus deterministic walkthrough from `docs/demo-script.md`.

## Tradeoffs and Failure Modes

- Foundation docs intentionally define contracts before implementation.
- External API dependencies must be optional in demos.
- AI-assisted outputs require evidence, validation, or human approval.
- Data and network claims must clearly identify synthetic, simulated, or public inputs.
