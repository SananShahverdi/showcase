# Source layout

The application lives in the `network_digital_twin_rl_routing_optimizer` package. Run it from the project root with `PYTHONPATH=src`.

## `domain/`

Pydantic domain models, enums, and request/response contracts.

| Module | Contents |
|---|---|
| `models.py` | Defines `RoutingAlgorithm`, `Node`, `Link`, `Packet`, `TopologyType`, … |

## `algorithms/`

Pure, framework-free logic. Most unit tests target this layer.

| Module | Contents |
|---|---|
| `baselines.py` | Defines `RoutingLogic` |
| `q_learning.py` | Defines `QLearningRouter` |
| `simulator.py` | Defines `NetworkSimulator` |

## `services/`

Workflow orchestration: validation, state transitions, audit evidence.

| Module | Contents |
|---|---|
| `inference_service.py` | Defines `InferenceService` |
| `training_service.py` | Defines `TrainingService` |

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
| `routes.py` | Defines `BuildTopologyRequest`, `LinkRequest`, `EvaluateRequest`, `TrainRequest`, `CompareRequest`, … |

## Configuration and persistence

`config.py` reads settings from environment variables with the project prefix; no credential has a default. When `<PREFIX>DATABASE_URL` is set (SQLite or PostgreSQL), `api/persistence.py` binds the repository collections to `adapters/database.py`, which restores them at startup and saves changed documents after each successful write request in one transaction. Without it, state stays in memory.
