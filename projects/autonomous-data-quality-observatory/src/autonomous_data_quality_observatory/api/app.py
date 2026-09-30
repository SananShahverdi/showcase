import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from autonomous_data_quality_observatory.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("data-quality-observatory")

app = FastAPI(
    title="Autonomous Data Quality Observatory",
    version="1.0.0",
    description="Source profiling, rules, drift evidence, health history, and incident operations.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)
app.include_router(router, prefix="/api")


@app.middleware("http")
async def add_request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id, request.method, request.url.path, response.status_code,
        (time.perf_counter() - started) * 1000,
    )
    return response


@app.get("/health", tags=["operations"])
def health_check():
    return {"status": "ok", "service": "autonomous-data-quality-observatory", "version": app.version}


@app.get("/ready", tags=["operations"])
def readiness_check():
    return {"status": "ready"}


# Optional durable state: set the project's DATABASE_URL setting to enable it.
from autonomous_data_quality_observatory.adapters.database import install  # noqa: E402
from autonomous_data_quality_observatory.api.persistence import build_persistence  # noqa: E402
from autonomous_data_quality_observatory.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
