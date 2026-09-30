from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from edge_wasm_plugin_runtime.api.routes import router

app = FastAPI(title="Edge Wasm Plugin Runtime", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    from edge_wasm_plugin_runtime.algorithms.runtime_host import RuntimeHost
    return {"status": "ok", "local_adapters_ready": True, "wasmtime_available": RuntimeHost.runtime_available()}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from edge_wasm_plugin_runtime.adapters.database import install  # noqa: E402
from edge_wasm_plugin_runtime.api.persistence import build_persistence  # noqa: E402
from edge_wasm_plugin_runtime.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
