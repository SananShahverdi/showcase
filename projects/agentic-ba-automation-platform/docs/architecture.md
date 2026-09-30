# Architecture

## System Goal

Convert unstructured stakeholder input into reviewed, source-backed engineering artifacts.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    document_ingestion[document-ingestion]
    rag_indexer[rag-indexer]
    agent_orchestrator[agent-orchestrator]
    approval_api[approval-api]
    ticket_exporter[ticket-exporter]
    audit_log[audit-log]
    api --> document_ingestion
    api --> rag_indexer
    api --> agent_orchestrator
    api --> approval_api
    api --> ticket_exporter
    api --> audit_log
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as document-ingestion
    participant M2 as audit-log
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
    class Workspace {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Document {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Requirement {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class AcceptanceCriterion {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Ticket {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class AuditEvent {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Workspace --> Document
    Document --> Requirement
    Requirement --> AcceptanceCriterion
    AcceptanceCriterion --> Ticket
    Ticket --> AuditEvent
```

## Component Responsibilities

- `document-ingestion`: owns one bounded responsibility in the workflow.
- `rag-indexer`: owns one bounded responsibility in the workflow.
- `agent-orchestrator`: owns one bounded responsibility in the workflow.
- `approval-api`: owns one bounded responsibility in the workflow.
- `ticket-exporter`: owns one bounded responsibility in the workflow.
- `audit-log`: owns one bounded responsibility in the workflow.

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
