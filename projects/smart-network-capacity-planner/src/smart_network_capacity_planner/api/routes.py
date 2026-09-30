from __future__ import annotations

from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Response

from smart_network_capacity_planner.adapters.repositories import TelemetryConflictError, TelemetryRepository
from smart_network_capacity_planner.domain.models import (
    ForecastResult,
    IngestionSummary,
    LinkSummary,
    PortfolioOverview,
    TelemetryData,
    WhatIfScenario,
)
from smart_network_capacity_planner.services.capacity_service import CapacityService

router = APIRouter()
repo = TelemetryRepository()
service = CapacityService(repo)


@router.post("/telemetry", response_model=IngestionSummary)
def ingest_telemetry(data: List[TelemetryData]) -> IngestionSummary:
    try:
        return service.ingest_telemetry(data)
    except TelemetryConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/demo/seed", response_model=IngestionSummary)
def seed_demo(reset: bool = Query(default=False)) -> IngestionSummary:
    return service.seed_demo(reset=reset)


@router.delete("/demo/reset", status_code=204)
def reset_demo() -> Response:
    repo.clear()
    return Response(status_code=204)


@router.get("/links", response_model=List[LinkSummary])
def list_links() -> List[LinkSummary]:
    return service.list_links()


@router.get("/overview", response_model=PortfolioOverview)
def get_overview() -> PortfolioOverview:
    return service.get_overview()


@router.get("/forecast/{link_id}", response_model=ForecastResult)
def get_forecast(
    link_id: str,
    days: int = Query(default=90, ge=7, le=90),
    budget_usd: Optional[float] = Query(default=None, ge=0),
) -> ForecastResult:
    try:
        return service.generate_forecast(link_id, days=days, budget_usd=budget_usd)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "No data" in str(exc) else 400, detail=str(exc)) from exc


@router.post("/what-if/{link_id}", response_model=WhatIfScenario, status_code=201)
def run_what_if(link_id: str, scenario: WhatIfScenario) -> WhatIfScenario:
    try:
        return service.run_what_if(link_id, scenario)
    except ValueError as exc:
        raise HTTPException(status_code=404 if "No data" in str(exc) else 400, detail=str(exc)) from exc


@router.get("/what-if/{link_id}", response_model=List[WhatIfScenario])
def list_what_if(link_id: str) -> List[WhatIfScenario]:
    if not repo.get_by_link(link_id):
        raise HTTPException(status_code=404, detail="No data found for link")
    return repo.list_scenarios(link_id)


@router.get("/reports/weekly")
def weekly_report(format: Literal["json", "markdown"] = Query(default="json")):
    report = service.weekly_report()
    if format == "markdown":
        return Response(
            content=service.report_as_markdown(report),
            media_type="text/markdown",
            headers={"Content-Disposition": "attachment; filename=weekly-capacity-report.md"},
        )
    return report

