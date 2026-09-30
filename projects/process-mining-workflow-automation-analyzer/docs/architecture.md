# Architecture

## System Goal

Transform event logs into process maps, bottleneck analytics, SLA insights, and automation backlogs.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    event_log_importer[event-log-importer]
    case_builder[case-builder]
    process_discovery[process-discovery]
    bottleneck_analytics[bottleneck-analytics]
    ai_report_writer[ai-report-writer]
    exporter[exporter]
    api --> event_log_importer
    api --> case_builder
    api --> process_discovery
    api --> bottleneck_analytics
    api --> ai_report_writer
    api --> exporter
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as event-log-importer
    participant M2 as exporter
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
    class Event {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Case {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Activity {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Transition {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Variant {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class AutomationCandidate {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Event --> Case
    Case --> Activity
    Activity --> Transition
    Transition --> Variant
    Variant --> AutomationCandidate
```

## Component Responsibilities

- `event-log-importer`: owns one bounded responsibility in the workflow.
- `case-builder`: owns one bounded responsibility in the workflow.
- `process-discovery`: owns one bounded responsibility in the workflow.
- `bottleneck-analytics`: owns one bounded responsibility in the workflow.
- `ai-report-writer`: owns one bounded responsibility in the workflow.
- `exporter`: owns one bounded responsibility in the workflow.

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
