# Source layout

The application lives in the `local_ai_inference_gateway_llmops_console` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `ProviderType`, `ProviderConfig`, `PromptVersion`, `PromptTemplate`, `RequestLog`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `prompt_registry.py` | Defines `extract_variables`, `compile_prompt` |
| `routing_policy.py` | Defines `select_provider` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `gateway_service.py` | Defines `ModelNotFoundError`, `GatewayService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `database.py` | Optional SQL persistence for the in-process repositories |
| `orm.py` | SQLAlchemy table for durable repository state |
| `provider_adapters.py` | Defines `ProviderAdapters` |
| `repositories.py` | Defines `InMemoryRepository` |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `health_check` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `ChatMessage`, `ChatCompletionRequest`, `EmbeddingRequest`, `ApiKeyCreate`, `PromptVersionCreate`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
