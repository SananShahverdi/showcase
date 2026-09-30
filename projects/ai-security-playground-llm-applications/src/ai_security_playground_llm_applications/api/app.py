from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai_security_playground_llm_applications.api.routes import router

app = FastAPI(title="AI Security Playground", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok", "mode": "offline", "synthetic_tools": True}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from ai_security_playground_llm_applications.adapters.database import install  # noqa: E402
from ai_security_playground_llm_applications.api.persistence import build_persistence  # noqa: E402
from ai_security_playground_llm_applications.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
