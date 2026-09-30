from fastapi import FastAPI
from self_healing_public_data_intelligence_pipeline.api.routes import router

app = FastAPI(title="Self-Healing Pipeline API", version="1.0.0")
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from self_healing_public_data_intelligence_pipeline.adapters.database import install  # noqa: E402
from self_healing_public_data_intelligence_pipeline.api.persistence import build_persistence  # noqa: E402
from self_healing_public_data_intelligence_pipeline.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
