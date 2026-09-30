from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, Field

from aiops_incident_assistant_human_approval.adapters.repositories import InMemoryRepository
from aiops_incident_assistant_human_approval.domain.models import (
    AuditEvent,
    Incident,
    IncidentStatus,
    IncidentType,
    PostIncidentReport,
    RemediationPlan,
)
from aiops_incident_assistant_human_approval.services.incident_service import IncidentService

router = APIRouter()
repo = InMemoryRepository()
service = IncidentService(repo)


class GenerateIncidentRequest(BaseModel):
    type: IncidentType
    service_name: str = Field(min_length=2, max_length=80, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9-]*$")


class ActionDecisionRequest(BaseModel):
    action_index: int = Field(ge=0)
    actor: str = Field(default="local-operator", min_length=2, max_length=80)
    reason: str = Field(default="Reviewed evidence and approved safe execution", min_length=3, max_length=500)


def _not_found_or_conflict(error: ValueError) -> HTTPException:
    message = str(error)
    lowered = message.lower()
    status = 404 if "not found" in lowered else 422 if lowered.startswith("invalid") else 409
    return HTTPException(status_code=status, detail=message)


@router.post("/incidents/generate", response_model=Incident)
async def generate_incident(request: GenerateIncidentRequest):
    return service.generate_incident(request.type, request.service_name)


@router.get("/incidents", response_model=List[Incident])
async def list_incidents(status: IncidentStatus | None = Query(default=None)):
    return service.list_incidents(status)


@router.get("/incidents/{incident_id}", response_model=Incident)
async def get_incident(incident_id: UUID):
    try:
        return service.get_incident(incident_id)
    except ValueError as error:
        raise _not_found_or_conflict(error) from error


@router.get("/incidents/{incident_id}/plans", response_model=List[RemediationPlan])
async def list_incident_plans(incident_id: UUID):
    """Every plan revision for an incident, oldest first, so a console can reopen the latest."""
    try:
        service.get_incident(incident_id)
    except ValueError as error:
        raise _not_found_or_conflict(error) from error
    return repo.get_plans_for_incident(incident_id)


@router.post("/incidents/{incident_id}/analyze", response_model=RemediationPlan)
async def analyze_incident(incident_id: UUID, actor: str = Query(default="local-operator")):
    try:
        return service.analyze(incident_id, actor)
    except ValueError as error:
        raise _not_found_or_conflict(error) from error


@router.get("/plans/{plan_id}", response_model=RemediationPlan)
async def get_plan(plan_id: UUID):
    try:
        return service.get_plan(plan_id)
    except ValueError as error:
        raise _not_found_or_conflict(error) from error


@router.post("/plans/{plan_id}/approve", response_model=RemediationPlan)
async def approve_action(plan_id: UUID, request: ActionDecisionRequest):
    try:
        return service.approve_and_execute_action(plan_id, request.action_index, request.actor, request.reason)
    except ValueError as error:
        raise _not_found_or_conflict(error) from error


@router.post("/plans/{plan_id}/reject", response_model=RemediationPlan)
async def reject_action(plan_id: UUID, request: ActionDecisionRequest):
    try:
        return service.reject_action(plan_id, request.action_index, request.actor, request.reason)
    except ValueError as error:
        raise _not_found_or_conflict(error) from error


@router.get("/audit", response_model=List[AuditEvent])
async def get_audit_events(incident_id: UUID | None = Query(default=None)):
    return repo.get_audit_events(incident_id)


@router.get("/reports", response_model=List[PostIncidentReport])
async def get_reports(incident_id: UUID | None = Query(default=None)):
    reports = repo.get_reports()
    return [report for report in reports if incident_id is None or report.incident_id == incident_id]


@router.get("/reports/{report_id}/export")
async def export_report(report_id: UUID):
    try:
        content = service.report_markdown(report_id)
    except ValueError as error:
        raise _not_found_or_conflict(error) from error
    return Response(
        content=content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="incident-{report_id}.md"'},
    )
