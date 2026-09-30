# Architecture

## System Goal

Answer from internal documents using permission-filtered retrieval, citations, unsupported-claim checks, and audit logs.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    document_ingestion[document-ingestion]
    chunker[chunker]
    retrieval_engine[retrieval-engine]
    access_control[access-control]
    answer_engine[answer-engine]
    evaluation_suite[evaluation-suite]
    api --> document_ingestion
    api --> chunker
    api --> retrieval_engine
    api --> access_control
    api --> answer_engine
    api --> evaluation_suite
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
    participant M2 as evaluation-suite
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
    class Document {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Chunk {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class UserRole {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Query {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Answer {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Citation {
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
    Document --> Chunk
    Chunk --> UserRole
    UserRole --> Query
    Query --> Answer
    Answer --> Citation
    Citation --> AuditEvent
```

## Component Responsibilities

- `document-ingestion`: owns one bounded responsibility in the workflow.
- `chunker`: owns one bounded responsibility in the workflow.
- `retrieval-engine`: owns one bounded responsibility in the workflow.
- `access-control`: owns one bounded responsibility in the workflow.
- `answer-engine`: owns one bounded responsibility in the workflow.
- `evaluation-suite`: owns one bounded responsibility in the workflow.

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
