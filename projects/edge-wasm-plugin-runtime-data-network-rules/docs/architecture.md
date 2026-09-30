# Architecture

## System Goal

Run user-defined data, alert, and routing rules as sandboxed Wasm plugins with versioning and resource controls.

## Context Diagram

```mermaid
flowchart LR
    user[User or Operator] --> web[Web Console]
    web --> api[API Service]
    api --> db[(PostgreSQL)]
    api --> queue[(Redis or Queue)]
    plugin_sdk[plugin-sdk]
    runtime_host[runtime-host]
    upload_api[upload-api]
    version_registry[version-registry]
    policy_enforcer[policy-enforcer]
    benchmark_suite[benchmark-suite]
    api --> plugin_sdk
    api --> runtime_host
    api --> upload_api
    api --> version_registry
    api --> policy_enforcer
    api --> benchmark_suite
    api --> obs[Logs, Metrics, Traces]
    api --> reports[Reports and Exports]
```

## Main Workflow

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Web Console
    participant API as API
    participant M1 as plugin-sdk
    participant M2 as benchmark-suite
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
    class Plugin {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class PluginVersion {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class ExecutionRequest {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class ExecutionResult {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class ResourcePolicy {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    class Rollback {
    +id: UUID
    +created_at: datetime
    +status: string
    +validate()
}
    Plugin --> PluginVersion
    PluginVersion --> ExecutionRequest
    ExecutionRequest --> ExecutionResult
    ExecutionResult --> ResourcePolicy
    ResourcePolicy --> Rollback
```

## Component Responsibilities

- `plugin-sdk`: owns one bounded responsibility in the workflow.
- `runtime-host`: owns one bounded responsibility in the workflow.
- `upload-api`: owns one bounded responsibility in the workflow.
- `version-registry`: owns one bounded responsibility in the workflow.
- `policy-enforcer`: owns one bounded responsibility in the workflow.
- `benchmark-suite`: owns one bounded responsibility in the workflow.

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
