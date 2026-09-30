# Source layout

The application lives in the `smart_network_capacity_planner` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `utc_now`, `DeviceHealth`, `RiskLevel`, `TelemetryData`, `IngestionSummary`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `forecasting.py` | Defines `ForecastingEngine` |
| `optimizer.py` | Defines `Optimizer` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `capacity_service.py` | Defines `CapacityService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `database.py` | Optional SQL persistence for the in-process repositories |
| `orm.py` | SQLAlchemy table for durable repository state |
| `repositories.py` | Defines `TelemetryConflictError`, `TelemetryRepository` |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `request_context`, `health_check`, `readiness_check` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `ingest_telemetry`, `seed_demo`, `reset_demo`, `list_links`, `get_overview`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
