from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from post_quantum_crypto_migration_scanner.api.routes import router

app = FastAPI(title="Post-Quantum Crypto Migration Scanner", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok", "offline_scanner": True, "live_probe_requires_authorization": True}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from post_quantum_crypto_migration_scanner.adapters.database import install  # noqa: E402
from post_quantum_crypto_migration_scanner.api.persistence import build_persistence  # noqa: E402
from post_quantum_crypto_migration_scanner.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
