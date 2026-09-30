# Architecture

## System Goal

Generate transaction streams, compute risk features, detect anomalies, and support analyst review with reason codes.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    event_producer[event-producer]
    stream_processor[stream-processor]
    feature_store[feature-store]
    model_scorer[model-scorer]
    rules_engine[rules-engine]
    analyst_console[analyst-console]
    api --> event_producer
    api --> stream_processor
    api --> feature_store
    api --> model_scorer
    api --> rules_engine
    api --> analyst_console
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as event-producer
    participant M2 as analyst-console
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
    class TransactionEvent {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Account {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Device {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class RiskFeature {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Alert {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class AnalystDecision {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    TransactionEvent --> Account
    Account --> Device
    Device --> RiskFeature
    RiskFeature --> Alert
    Alert --> AnalystDecision
```

## Component Responsibilities

- `event-producer`: owns one bounded responsibility in the workflow.
- `stream-processor`: owns one bounded responsibility in the workflow.
- `feature-store`: owns one bounded responsibility in the workflow.
- `model-scorer`: owns one bounded responsibility in the workflow.
- `rules-engine`: owns one bounded responsibility in the workflow.
- `analyst-console`: owns one bounded responsibility in the workflow.

## Data and Control Boundaries

- Raw inputs are preserved before transformation.
- Validated records or decisions are separated from quarantined failures.
- Human approval or policy checks are explicit where automation can affect users, infrastructure, or security.
- Observability data is treated as a first-class output: logs, metrics, traces, decisions, and errors.

## Deployment Shape

- Local: Docker Compose with the FastAPI scoring/case API and functional React analyst console.
- CI: lint, unit tests, integration smoke test, dependency scan.
- Demo: seeded data plus deterministic walkthrough from `docs/demo-script.md`.

## Tradeoffs and Failure Modes

- Local transport/state adapters are explicit; durable streaming, storage, identity, and model-registry adapters are deployment extensions.
- External API dependencies must be optional in demos.
- AI-assisted outputs require evidence, validation, or human approval.
- Data and network claims must clearly identify synthetic, simulated, or public inputs.
