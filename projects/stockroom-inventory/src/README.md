# Source layout

The application lives in the `stockroom_inventory` package. Run it from the project root with `PYTHONPATH=src`.

| Module | Contents |
|---|---|
| `api/app.py` | `create_app(db_path)` factory, SQLite schema with `CHECK` constraints, Pydantic contracts (`ItemCreate`, `ItemEdit`, `MovementCreate`), routes, and static frontend mounting |

The service is intentionally a single module: storage, validation, and routes are small enough that splitting them would add indirection without adding clarity. Each request opens its own SQLite connection, and every stock change runs inside one `BEGIN IMMEDIATE` transaction.
