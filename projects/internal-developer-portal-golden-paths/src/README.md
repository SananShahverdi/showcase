# Source layout

The application lives in the `internal_developer_portal_golden_paths` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `UserRole`, `Environment`, `ServiceMetadata`, `TemplateStatus`, `TemplateDefinition`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `quality_defaults.py` | Defines `QualityDefaults` |
| `template_engine.py` | Defines `TemplateEngine` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `scaffolder.py` | Defines `ScaffolderService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `artifacts.py` | Defines `LocalArtifactStore` |
| `database.py` | Optional SQL persistence for the in-process repositories |
| `orm.py` | SQLAlchemy table for durable repository state |
| `repositories.py` | Defines `CatalogStore` |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `health_check` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `get_templates`, `create_template`, `approve_template`, `preview_scaffold`, `scaffold_service`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
