from fastapi import FastAPI
from agentic_ba_automation_platform.api.routes import router

app = FastAPI(title="Agentic BA Automation Platform API", version="1.0.0")
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from agentic_ba_automation_platform.adapters.database import install  # noqa: E402
from agentic_ba_automation_platform.api.persistence import build_persistence  # noqa: E402
from agentic_ba_automation_platform.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
