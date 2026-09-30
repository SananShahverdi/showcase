# Source layout

The application lives in the `edge_wasm_plugin_runtime` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `utc_now`, `PluginStatus`, `VersionStatus`, `RuntimeKind`, `ExecutionStatus`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `runtime_host.py` | Defines `WasmValidator`, `RuntimeHost` |
| `wasm_examples.py` | Inspectable, self-contained WebAssembly examples for the local workbench |
| `wasmtime_executor.py` | Bounded edge-json-v1 execution without host imports or WASI capabilities |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `plugin_service.py` | Defines `percentile`, `PluginService` |

## `adapters/`

Repositories and external boundaries.

| Module | Contents |
|---|---|
| `database.py` | Optional SQL persistence for the in-process repositories |
| `orm.py` | SQLAlchemy table for durable repository state |
| `repositories.py` | Defines `PluginRepository` |

## `api/`

FastAPI application factory and HTTP routes.

| Module | Contents |
|---|---|
| `app.py` | Defines `health_check` |
| `persistence.py` | State collections persisted when a database URL is configured |
| `routes.py` | Defines `CanaryPayload`, `BenchmarkPayload`, `not_found_or_conflict`, `list_plugins`, `get_plugin`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
