from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from process_mining_workflow_automation_analyzer.api.routes import router

app = FastAPI(title="Process Mining and Workflow Automation Analyzer", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok", "analysis": "deterministic", "external_ai_required": False}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from process_mining_workflow_automation_analyzer.adapters.database import install  # noqa: E402
from process_mining_workflow_automation_analyzer.api.persistence import build_persistence  # noqa: E402
from process_mining_workflow_automation_analyzer.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
