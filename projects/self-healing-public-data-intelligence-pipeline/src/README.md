# Source layout

The application lives in the `self_healing_public_data_intelligence_pipeline` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `SourceStatus`, `Source`, `ExtractionRecipe`, `CrawlRun`, `Record`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `anomaly_detection.py` | Defines `detect_freshness_anomaly` |
| `dom_fingerprinting.py` | Defines `compute_dom_fingerprint`, `detect_drift` |
| `locator_ranking.py` | Defines `rank_locators` |
| `recipe_scoring.py` | Defines `score_recipe` |
| `schema_validation.py` | Defines `validate_and_quarantine` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `pipeline_service.py` | Defines `extract_records`, `PipelineService` |
| `repair_agent.py` | Defines `RepairAgentService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `database.py` | Optional SQL persistence for the in-process repositories |
| `orm.py` | SQLAlchemy table for durable repository state |
| `repositories.py` | Defines `InMemoryRepository` |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `health_check` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `RegisterSourceRequest`, `CrawlRequest`, `ReplayProposalRequest`, `ActivateProposalRequest`, `register_source`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
