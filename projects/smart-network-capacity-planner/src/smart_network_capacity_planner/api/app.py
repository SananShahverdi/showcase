from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from smart_network_capacity_planner.api.routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("capacity-planner")

app = FastAPI(
    title="Smart Network Capacity Planner",
    version="1.0.0",
    description="Explainable link forecasting, risk, scenarios, and weekly planning reports.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
)
app.include_router(router, prefix="/api")


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
    started = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - started) * 1000
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health", tags=["operations"])
def health_check():
    return {"status": "ok", "service": "smart-network-capacity-planner", "version": app.version}


@app.get("/ready", tags=["operations"])
def readiness_check():
    return {"status": "ready"}



# Optional durable state: set the project's DATABASE_URL setting to enable it.
from smart_network_capacity_planner.adapters.database import install  # noqa: E402
from smart_network_capacity_planner.api.persistence import build_persistence  # noqa: E402
from smart_network_capacity_planner.config import settings  # noqa: E402

install(app, build_persistence(settings.database_url))
