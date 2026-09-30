from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from autonomous_data_quality_observatory.adapters.repositories import MetadataRepository
from autonomous_data_quality_observatory.algorithms.engines import ConnectorError
from autonomous_data_quality_observatory.domain.models import (
    ConnectorPreview,
    DataSource,
    DatasetOverview,
    DatasetProfile,
    DeliveryResult,
    Issue,
    IssueUpdate,
    ObservationReport,
    Rule,
)
from autonomous_data_quality_observatory.services.observatory_service import ObservatoryService

router = APIRouter()
repo = MetadataRepository()
service = ObservatoryService(repo)


def not_found_or_bad_request(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc))


@router.post("/sources", response_model=DataSource, status_code=201)
def add_source(source: DataSource) -> DataSource:
    return service.add_source(source).safe_view()


@router.put("/sources/{source_id}", response_model=DataSource)
def update_source(source_id: str, source: DataSource) -> DataSource:
    if source_id != source.id:
        raise HTTPException(status_code=400, detail="Path and body source IDs must match")
    return service.add_source(source).safe_view()


@router.get("/sources", response_model=List[DataSource])
def list_sources() -> List[DataSource]:
    return service.list_sources()


@router.post("/sources/{source_id}/preview", response_model=ConnectorPreview)
def preview_source(source_id: str, limit: int = Query(default=5, ge=1, le=25)) -> ConnectorPreview:
    try:
        return service.preview(source_id, limit)
    except ValueError as exc:
        raise not_found_or_bad_request(exc) from exc


@router.post("/rules", response_model=Rule, status_code=201)
def add_rule(rule: Rule) -> Rule:
    try:
        return service.add_rule(rule)
    except ValueError as exc:
        raise not_found_or_bad_request(exc) from exc


@router.get("/sources/{source_id}/rules", response_model=List[Rule])
def list_rules(source_id: str) -> List[Rule]:
    if not repo.get_source(source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return repo.get_rules(source_id)


@router.post("/observe/{source_id}", response_model=ObservationReport)
def run_observation(source_id: str) -> ObservationReport:
    try:
        return service.observe(source_id)
    except (ValueError, ConnectorError) as exc:
        raise not_found_or_bad_request(exc) from exc


@router.get("/datasets", response_model=List[DatasetOverview])
def list_datasets() -> List[DatasetOverview]:
    return service.overviews()


@router.get("/sources/{source_id}/profiles", response_model=List[DatasetProfile])
def list_profiles(source_id: str) -> List[DatasetProfile]:
    if not repo.get_source(source_id):
        raise HTTPException(status_code=404, detail="Source not found")
    return repo.list_profiles(source_id)


@router.put("/sources/{source_id}/baseline/{profile_id}", response_model=DatasetProfile)
def set_baseline(source_id: str, profile_id: UUID) -> DatasetProfile:
    try:
        return repo.set_baseline(source_id, profile_id)
    except ValueError as exc:
        raise not_found_or_bad_request(exc) from exc


@router.get("/issues", response_model=List[Issue])
def list_issues(source_id: Optional[str] = None, active_only: bool = False) -> List[Issue]:
    return repo.list_issues(source_id, active_only)


@router.patch("/issues/{issue_id}", response_model=Issue)
def update_issue(issue_id: UUID, update: IssueUpdate) -> Issue:
    try:
        return service.update_issue(issue_id, update)
    except ValueError as exc:
        raise not_found_or_bad_request(exc) from exc


@router.post("/issues/{issue_id}/export", response_model=DeliveryResult)
def export_issue(issue_id: UUID, destination: str = "jira-json") -> DeliveryResult:
    try:
        return service.export_issue(issue_id, destination)
    except ValueError as exc:
        raise not_found_or_bad_request(exc) from exc


@router.post("/demo/seed", response_model=List[DatasetOverview])
def seed_demo(reset: bool = Query(default=False)) -> List[DatasetOverview]:
    return service.seed_demo(reset)


@router.post("/demo/drift", response_model=DataSource)
def introduce_demo_drift() -> DataSource:
    try:
        return service.introduce_demo_drift().safe_view()
    except ValueError as exc:
        raise not_found_or_bad_request(exc) from exc


@router.delete("/demo/reset", status_code=204)
def reset_demo() -> Response:
    repo.clear()
    return Response(status_code=204)
