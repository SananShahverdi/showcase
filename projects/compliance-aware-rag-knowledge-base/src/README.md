# Source layout

The application lives in the `compliance_aware_rag_knowledge_base` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `utc_now`, `Role`, `Sensitivity`, `DocumentStatus`, `Identity`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `access_control.py` | Defines `evaluate_document_access`, `filter_chunks_by_role` |
| `chunking.py` | Defines `chunk_document` |
| `evaluation.py` | Defines `validate_citation_coverage`, `detect_unsupported_claims` |
| `evaluation_suite.py` | Defines `evaluate_retrieval_quality`, `evaluate_answer` |
| `ingestion.py` | Defines `DocumentParseError`, `parse_pdf`, `parse_docx`, `parse_html`, `parse_markdown`, … |
| `retrieval.py` | Defines `tokenize`, `embed_text`, `cosine`, `score_chunk`, `calculate_hybrid_score`, … |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `rag_service.py` | Defines `RAGService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `database.py` | Optional SQL persistence for the in-process repositories |
| `orm.py` | SQLAlchemy table for durable repository state |
| `repositories.py` | Defines `DocumentRepository`, `ChunkRepository`, `AuditRepository`, `GovernanceRepository` |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `request_context`, `health`, `ready` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `identity`, `admin`, `document_summary`, `QueryRequest`, `FeedbackRequest`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
