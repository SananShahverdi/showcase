from fastapi import FastAPI
from local_ai_inference_gateway_llmops_console.api.routes import openai_router, router

app = FastAPI(title="Local AI Inference Gateway", version="1.0.0")
app.include_router(router, prefix="/api")
app.include_router(openai_router, prefix="/v1")

@app.get("/health")
def health_check():
    return {"status": "ok"}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from local_ai_inference_gateway_llmops_console.adapters.database import install  # noqa: E402
from local_ai_inference_gateway_llmops_console.api.persistence import build_persistence  # noqa: E402
from local_ai_inference_gateway_llmops_console.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
