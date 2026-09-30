# Source layout

The application lives in the `agentic_ba_automation_platform` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `ArtifactType`, `ArtifactStatus`, `Document`, `Chunk`, `Citation`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `agent_layer.py` | Deterministic, source-grounded artifact generation for the offline product path |
| `document_worker.py` | Defines `parse_pdf`, `parse_docx`, `parse_html`, `parse_markdown`, `extract_text` |
| `rag.py` | Defines `chunk_document`, `retrieve_chunks` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `automation_service.py` | Defines `AutomationService` |

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
| `routes.py` | Defines `GenerateRequest`, `StatusUpdateRequest`, `EditArtifactRequest`, `ExportRequest`, `upload_document`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
