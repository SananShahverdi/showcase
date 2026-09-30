# Source layout

The application lives in the `process_mining_workflow_automation_analyzer` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `utc_now`, `Event`, `AnalysisConfig`, `Transition`, `Variant`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `ai_assistant.py` | Defines `EvidenceAssistant` |
| `engine.py` | Defines `percentile`, `ProcessEngine` |
| `importers.py` | Defines `parse_csv_events`, `parse_xes_events` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `analyzer_service.py` | Defines `AnalyzerService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `database.py` | Optional SQL persistence for the in-process repositories |
| `orm.py` | SQLAlchemy table for durable repository state |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `health_check` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `analyze_events`, `import_csv`, `import_xes`, `list_reports`, `get_report`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
