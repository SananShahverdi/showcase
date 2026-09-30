from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from ai_security_playground_llm_applications.adapters.repositories import ScenarioRepository
from ai_security_playground_llm_applications.domain.models import (
    AppMode, Approval, ApprovalDecision, ExecuteRequest, ExecutionResult, MetricsSummary,
    Scenario, SecurityReport, UserRole,
)
from ai_security_playground_llm_applications.services.security_service import SecurityService

router = APIRouter()
repo = ScenarioRepository()
service = SecurityService(repo)


@router.get("/scenarios", response_model=List[Scenario])
def get_scenarios() -> List[Scenario]:
    return repo.get_all()


@router.get("/scenarios/{scenario_id}", response_model=Scenario)
def get_scenario(scenario_id: str) -> Scenario:
    try:
        return repo.get(scenario_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scenario not found") from exc


@router.post("/execute/{scenario_id}", response_model=ExecutionResult)
def execute_scenario(
    scenario_id: str,
    request: Optional[ExecuteRequest] = None,
    mode: Optional[AppMode] = Query(default=None),
    role: UserRole = Query(default=UserRole.LEARNER),
) -> ExecutionResult:
    selected_mode = request.mode if request else mode
    if selected_mode is None:
        raise HTTPException(status_code=422, detail="mode is required in the query or request body")
    try:
        return service.run_scenario(
            scenario_id,
            selected_mode,
            payload=request.payload if request else None,
            role=request.role if request else role,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Scenario not found") from exc


@router.get("/runs", response_model=List[ExecutionResult])
def list_runs(limit: int = Query(default=100, ge=1, le=500)) -> List[ExecutionResult]:
    return service.list_runs(limit)


@router.get("/approvals", response_model=List[Approval])
def list_approvals() -> List[Approval]:
    return service.list_approvals()


@router.post("/approvals/{approval_id}/resolve", response_model=Approval)
def resolve_approval(approval_id: UUID, decision: ApprovalDecision) -> Approval:
    try:
        return service.resolve_approval(approval_id, decision)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/execute", response_model=Approval)
def consume_approval(approval_id: UUID) -> Approval:
    try:
        return service.consume_approval(approval_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Approval not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/assessment", response_model=SecurityReport)
def run_assessment() -> SecurityReport:
    return service.run_assessment()


@router.get("/assessments", response_model=List[SecurityReport])
def list_assessments(limit: int = Query(default=20, ge=1, le=100)) -> List[SecurityReport]:
    return service.list_reports(limit)


@router.get("/assessment/{report_id}", response_model=SecurityReport)
def get_assessment(report_id: UUID) -> SecurityReport:
    try:
        return service.get_report(report_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Assessment not found") from exc


@router.get("/assessment/{report_id}/export")
def export_assessment(report_id: UUID, format: str = Query(default="markdown", pattern="^(markdown|json)$")):
    try:
        report = service.get_report(report_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Assessment not found") from exc
    if format == "json":
        return report
    return Response(service.report_markdown(report), media_type="text/markdown")


@router.get("/metrics", response_model=MetricsSummary)
def metrics() -> MetricsSummary:
    return service.metrics()
