# Architecture

## System Goal

Extract public data reliably, detect schema drift, quarantine failures, and repair broken extraction recipes.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    crawler[crawler]
    extractor[extractor]
    validator[validator]
    repair_agent[repair-agent]
    recipe_registry[recipe-registry]
    health_dashboard[health-dashboard]
    api --> crawler
    api --> extractor
    api --> validator
    api --> repair_agent
    api --> recipe_registry
    api --> health_dashboard
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as crawler
    participant M2 as health-dashboard
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
    class Source {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class CrawlRun {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class ExtractionRecipe {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Record {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class ValidationFailure {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class RepairProposal {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Source --> CrawlRun
    CrawlRun --> ExtractionRecipe
    ExtractionRecipe --> Record
    Record --> ValidationFailure
    ValidationFailure --> RepairProposal
```

## Component Responsibilities

- `crawler`: owns one bounded responsibility in the workflow.
- `extractor`: owns one bounded responsibility in the workflow.
- `validator`: owns one bounded responsibility in the workflow.
- `repair-agent`: owns one bounded responsibility in the workflow.
- `recipe-registry`: owns one bounded responsibility in the workflow.
- `health-dashboard`: owns one bounded responsibility in the workflow.

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
