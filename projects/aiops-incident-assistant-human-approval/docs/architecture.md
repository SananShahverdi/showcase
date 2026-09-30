# Architecture

## System Goal

Diagnose simulated production incidents and propose remediation actions that require explicit human approval.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    demo_services[demo-services]
    incident_generator[incident-generator]
    telemetry_ingestion[telemetry-ingestion]
    runbook_retriever[runbook-retriever]
    diagnosis_agent[diagnosis-agent]
    approval_console[approval-console]
    api --> demo_services
    api --> incident_generator
    api --> telemetry_ingestion
    api --> runbook_retriever
    api --> diagnosis_agent
    api --> approval_console
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as demo-services
    participant M2 as approval-console
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
    class Service {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Incident {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Signal {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Runbook {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class RemediationPlan {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Approval {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Service --> Incident
    Incident --> Signal
    Signal --> Runbook
    Runbook --> RemediationPlan
    RemediationPlan --> Approval
```

## Component Responsibilities

- `demo-services`: owns one bounded responsibility in the workflow.
- `incident-generator`: owns one bounded responsibility in the workflow.
- `telemetry-ingestion`: owns one bounded responsibility in the workflow.
- `runbook-retriever`: owns one bounded responsibility in the workflow.
- `diagnosis-agent`: owns one bounded responsibility in the workflow.
- `approval-console`: owns one bounded responsibility in the workflow.

## Data and Control Boundaries

- Raw inputs are preserved before transformation.
- Validated records or decisions are separated from quarantined failures.
- Human approval or policy checks are explicit where automation can affect users, infrastructure, or security.
- Observability data is treated as a first-class output: logs, metrics, traces, decisions, and errors.

## Deployment Shape

- Local: Docker Compose with the FastAPI lifecycle API and functional React operator console.
- CI: lint, unit tests, integration smoke test, dependency scan.
- Demo: seeded data plus deterministic walkthrough from `docs/demo-script.md`.

## Tradeoffs and Failure Modes

- Local adapters are explicit and credential-free; durable database and authenticated cluster adapters are deployment extensions.
- External API dependencies must be optional in demos.
- AI-assisted outputs require evidence, validation, or human approval.
- Data and network claims must clearly identify synthetic, simulated, or public inputs.
