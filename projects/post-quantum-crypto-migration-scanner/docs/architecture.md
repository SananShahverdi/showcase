# Architecture

## System Goal

Inventory cryptographic usage across code, dependencies, and TLS endpoints, then produce migration guidance.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    repo_scanner[repo-scanner]
    tls_scanner[tls-scanner]
    dependency_scanner[dependency-scanner]
    rules_engine[rules-engine]
    report_generator[report-generator]
    dashboard[dashboard]
    api --> repo_scanner
    api --> tls_scanner
    api --> dependency_scanner
    api --> rules_engine
    api --> report_generator
    api --> dashboard
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as repo-scanner
    participant M2 as dashboard
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
    class Codebase {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Endpoint {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class CryptoFinding {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Rule {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class RiskScore {
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
    Codebase --> Endpoint
    Endpoint --> CryptoFinding
    CryptoFinding --> Rule
    Rule --> RiskScore
    RiskScore --> Recommendation
```

## Component Responsibilities

- `repo-scanner`: owns one bounded responsibility in the workflow.
- `tls-scanner`: owns one bounded responsibility in the workflow.
- `dependency-scanner`: owns one bounded responsibility in the workflow.
- `rules-engine`: owns one bounded responsibility in the workflow.
- `report-generator`: owns one bounded responsibility in the workflow.
- `dashboard`: owns one bounded responsibility in the workflow.

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
