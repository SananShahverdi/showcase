# Source layout

The application lives in the `aiops_incident_assistant_human_approval` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `IncidentType`, `IncidentStatus`, `IncidentSeverity`, `TelemetryData`, `EvidenceReference`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `ai_agent.py` | Deterministic, evidence-grounded incident analysis |
| `policy_engine.py` | Defines `PolicyEngine` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `incident_service.py` | Defines `IncidentService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `database.py` | Optional SQL persistence for the in-process repositories |
| `executor.py` | Defines `ExecutionResult`, `LocalSafeExecutor` |
| `orm.py` | SQLAlchemy table for durable repository state |
| `repositories.py` | Defines `InMemoryRepository` |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `health_check` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `GenerateIncidentRequest`, `ActionDecisionRequest`, `generate_incident`, `list_incidents`, `get_incident`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
