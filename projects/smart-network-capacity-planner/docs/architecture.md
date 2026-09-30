# Architecture

## System Goal

Forecast utilization, detect saturation risk, and recommend capacity or rerouting actions under budget constraints.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    telemetry_generator[telemetry-generator]
    ingestion_api[ingestion-api]
    forecasting_engine[forecasting-engine]
    optimization_engine[optimization-engine]
    what_if_dashboard[what-if-dashboard]
    report_generator[report-generator]
    api --> telemetry_generator
    api --> ingestion_api
    api --> forecasting_engine
    api --> optimization_engine
    api --> what_if_dashboard
    api --> report_generator
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as telemetry-generator
    participant M2 as report-generator
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
    class Router {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Link {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class TelemetryPoint {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Forecast {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class RiskAlert {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Recommendation {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Router --> Link
    Link --> TelemetryPoint
    TelemetryPoint --> Forecast
    Forecast --> RiskAlert
    RiskAlert --> Recommendation
```

## Component Responsibilities

- `telemetry-generator`: owns one bounded responsibility in the workflow.
- `ingestion-api`: owns one bounded responsibility in the workflow.
- `forecasting-engine`: owns one bounded responsibility in the workflow.
- `optimization-engine`: owns one bounded responsibility in the workflow.
- `what-if-dashboard`: owns one bounded responsibility in the workflow.
- `report-generator`: owns one bounded responsibility in the workflow.

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
