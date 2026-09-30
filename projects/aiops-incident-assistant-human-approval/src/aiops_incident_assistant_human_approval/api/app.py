from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiops_incident_assistant_human_approval.api.routes import router

app = FastAPI(title="AIOps Incident Assistant", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "ok"}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from aiops_incident_assistant_human_approval.adapters.database import install  # noqa: E402
from aiops_incident_assistant_human_approval.api.persistence import build_persistence  # noqa: E402
from aiops_incident_assistant_human_approval.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
