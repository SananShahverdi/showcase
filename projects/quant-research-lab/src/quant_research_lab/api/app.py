"""FastAPI application for the research console."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles

from quant_research_lab.algorithms.data import DataError
from quant_research_lab.domain.models import DatasetSummary, DatasetUpload, ForecastRequest, StrategyRequest
from quant_research_lab.services.lab_service import LabService, NotFound

FRONTEND = Path(__file__).resolve().parents[3] / "frontend"


def create_app(service: LabService | None = None) -> FastAPI:
    app = FastAPI(title="Quant Research Lab", version="1.0.0")
    lab = service or LabService()

    def guard(action):
        try:
            return action()
        except NotFound as exc:
            raise HTTPException(404, str(exc)) from exc
        except (DataError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @app.get("/health")
    def health():
        return {"status": "ok", "datasets": len(lab.datasets())}

    @app.get("/api/datasets", response_model=list[DatasetSummary])
    def datasets():
        return lab.datasets()

    @app.post("/api/datasets", response_model=DatasetSummary, status_code=201)
    def upload(payload: DatasetUpload):
        return guard(lambda: lab.upload(payload.name, payload.csv))

    @app.post("/api/forecast")
    def forecast(payload: ForecastRequest):
        return guard(lambda: lab.forecast(payload))

    @app.post("/api/strategy")
    def backtest(payload: StrategyRequest):
        return guard(lambda: lab.strategy(payload))

    @app.get("/api/risk/{dataset_id}")
    def risk(dataset_id: str):
        return guard(lambda: lab.risk(dataset_id))

    @app.get("/api/report/{dataset_id}", response_class=PlainTextResponse)
    def report(dataset_id: str, format: str = Query(default="markdown", pattern="^markdown$")):
        return PlainTextResponse(guard(lambda: lab.report(dataset_id)), media_type="text/markdown")

    if FRONTEND.exists():
        app.mount("/", StaticFiles(directory=FRONTEND, html=True), name="frontend")
    return app


app = create_app()
