# Architecture

## System Goal

Combine static analysis, dependency scanning, tests, and LLM review into grounded PR feedback.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    pr_ingestion[pr-ingestion]
    static_analyzers[static-analyzers]
    dependency_scanner[dependency-scanner]
    coverage_runner[coverage-runner]
    llm_reviewer[llm-reviewer]
    risk_dashboard[risk-dashboard]
    api --> pr_ingestion
    api --> static_analyzers
    api --> dependency_scanner
    api --> coverage_runner
    api --> llm_reviewer
    api --> risk_dashboard
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as pr-ingestion
    participant M2 as risk-dashboard
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
    class Repository {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class PullRequest {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class CheckRun {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Finding {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class ReviewSummary {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class PolicyDecision {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Repository --> PullRequest
    PullRequest --> CheckRun
    CheckRun --> Finding
    Finding --> ReviewSummary
    ReviewSummary --> PolicyDecision
```

## Component Responsibilities

- `pr-ingestion`: owns one bounded responsibility in the workflow.
- `static-analyzers`: owns one bounded responsibility in the workflow.
- `dependency-scanner`: owns one bounded responsibility in the workflow.
- `coverage-runner`: owns one bounded responsibility in the workflow.
- `llm-reviewer`: owns one bounded responsibility in the workflow.
- `risk-dashboard`: owns one bounded responsibility in the workflow.

## Data and Control Boundaries

- Raw inputs are preserved before transformation.
- Validated records or decisions are separated from quarantined failures.
- Human approval or policy checks are explicit where automation can affect users, infrastructure, or security.
- Observability data is treated as a first-class output: logs, metrics, traces, decisions, and errors.

## Deployment Shape

- Local: Docker Compose with the FastAPI review API and functional React evidence dashboard.
- CI: lint, unit tests, integration smoke test, dependency scan.
- Demo: seeded data plus deterministic walkthrough from `docs/demo-script.md`.

## Tradeoffs and Failure Modes

- Local analyzers are explicit and credential-free; sandboxed scanners and SCM publication are deployment extensions.
- External API dependencies must be optional in demos.
- AI-assisted outputs require evidence, validation, or human approval.
- Data and network claims must clearly identify synthetic, simulated, or public inputs.
