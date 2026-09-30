from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from self_healing_public_data_intelligence_pipeline.adapters.repositories import InMemoryRepository
from self_healing_public_data_intelligence_pipeline.domain.models import (
    CrawlRun,
    ExtractionRecipe,
    RepairProposal,
    Source,
    ValidationFailure,
)
from self_healing_public_data_intelligence_pipeline.services.pipeline_service import PipelineService
from self_healing_public_data_intelligence_pipeline.services.repair_agent import RepairAgentService

router = APIRouter()
repo = InMemoryRepository()
pipeline_service = PipelineService(repo)
repair_service = RepairAgentService(repo)


class RegisterSourceRequest(BaseModel):
    url: str
    name: str = Field(min_length=1, max_length=200)
    selectors: Dict[str, str]
    expected_schema: Dict[str, str] = Field(default_factory=lambda: {"title": "str", "price": "float"})
    rate_limit_ms: int = Field(default=1000, ge=100, le=60_000)


class CrawlRequest(BaseModel):
    source_id: UUID
    html_content: str = Field(min_length=1, max_length=2_000_000)
    extracted_data: Optional[List[Dict[str, Any]]] = None


class ReplayProposalRequest(BaseModel):
    test_html: str = Field(min_length=1, max_length=2_000_000)


class ActivateProposalRequest(BaseModel):
    approved: bool


@router.post("/sources", response_model=Source)
def register_source(request: RegisterSourceRequest):
    try:
        return pipeline_service.register_source(
            request.url,
            request.name,
            request.selectors,
            request.expected_schema,
            request.rate_limit_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/sources", response_model=List[Source])
def list_sources():
    return list(repo.sources.values())


@router.post("/crawl", response_model=CrawlRun)
def trigger_crawl(request: CrawlRequest):
    try:
        return pipeline_service.process_crawl(
            source_id=str(request.source_id),
            html_content=request.html_content,
            raw_extracted_data=request.extracted_data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/runs", response_model=List[CrawlRun])
def list_runs(source_id: Optional[UUID] = None):
    runs = list(repo.runs.values())
    return [run for run in runs if source_id is None or run.source_id == source_id]


@router.get("/records/valid")
def get_valid_records():
    return repo.get_valid_records()


@router.get("/failures", response_model=List[ValidationFailure])
def get_failures():
    return list(repo.failures.values())


@router.get("/recipes", response_model=List[ExtractionRecipe])
def get_recipes(source_id: Optional[UUID] = None):
    return [recipe for recipe in repo.recipes.values() if source_id is None or recipe.source_id == source_id]


@router.get("/repair/proposals", response_model=List[RepairProposal])
def get_proposals():
    return list(repo.proposals.values())


@router.post("/repair/propose/{failure_id}", response_model=RepairProposal)
def propose_repair(failure_id: UUID):
    try:
        return repair_service.propose_repair(failure_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/repair/replay/{proposal_id}", response_model=RepairProposal)
def replay_proposal(proposal_id: UUID, request: ReplayProposalRequest):
    try:
        return repair_service.replay_proposal(proposal_id, request.test_html)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/repair/activate/{proposal_id}", response_model=ExtractionRecipe)
def activate_proposal(proposal_id: UUID, request: ActivateProposalRequest):
    try:
        return repair_service.activate_proposal(proposal_id, request.approved)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/repair/test/{proposal_id}", response_model=ExtractionRecipe, deprecated=True)
def test_and_activate_proposal(proposal_id: UUID, request: ReplayProposalRequest):
    """Compatibility alias; new clients should replay and activate separately."""
    try:
        return repair_service.test_and_activate_proposal(proposal_id, request.test_html)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/dashboard")
def get_dashboard_analytics():
    total_records = len(repo.records)
    valid_records = len(repo.get_valid_records())
    quarantined = len([record for record in repo.records.values() if record.quarantined])
    drifted_runs = len([run for run in repo.runs.values() if run.schema_drift])
    return {
        "source_health": {
            "total_tracked": len(repo.sources),
            "active": len([source for source in repo.sources.values() if source.status.value == "active"]),
            "degraded": len([recipe for recipe in repo.recipes.values() if recipe.is_active and recipe.success_rate < 1]),
        },
        "extraction_trends": {
            "total_extracted": total_records,
            "valid_records": valid_records,
            "quarantined_records": quarantined,
            "success_rate": valid_records / total_records if total_records else 1.0,
            "drifted_runs": drifted_runs,
        },
        "repair_queue": {
            "open_failures": len(repo.failures),
            "pending_proposals": len([proposal for proposal in repo.proposals.values() if not proposal.approved]),
        },
    }


@router.post("/demo/seed")
def seed_demo():
    return pipeline_service.seed_demo()
