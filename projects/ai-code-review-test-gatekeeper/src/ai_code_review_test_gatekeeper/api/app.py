from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ai_code_review_test_gatekeeper.api.routes import router

app = FastAPI(title="AI Code Review and Test Gatekeeper", version="1.0.0")
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
from ai_code_review_test_gatekeeper.adapters.database import install  # noqa: E402
from ai_code_review_test_gatekeeper.api.persistence import build_persistence  # noqa: E402
from ai_code_review_test_gatekeeper.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
