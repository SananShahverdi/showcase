from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from ai_code_review_test_gatekeeper.domain.models import DashboardSummary, PullRequest, ReviewReport, ReviewStatus, Severity
from ai_code_review_test_gatekeeper.services.review_service import ReviewRepository, ReviewService

router = APIRouter()
repo = ReviewRepository()
service = ReviewService(repo)


def _review(pr: PullRequest) -> ReviewReport:
    if len(pr.diff_content.encode()) > 500_000:
        raise HTTPException(status_code=413, detail="Diff exceeds the 500 KB local review limit")
    if not pr.diff_content.strip():
        raise HTTPException(status_code=422, detail="Diff content cannot be empty")
    return service.analyze_pr(pr)


@router.post("/reviews/local", response_model=ReviewReport)
async def review_local_diff(pr: PullRequest):
    return _review(pr)


@router.post("/webhook/pr", response_model=ReviewReport)
async def review_pr(pr: PullRequest):
    # The route remains for adapter compatibility. Deployments must place SCM
    # signature verification in front of it; local mode does not claim GitHub publication.
    return _review(pr)


@router.get("/dashboard/reports", response_model=List[ReviewReport])
async def get_dashboard(
    repo_name: str | None = Query(default=None, alias="repo"),
    status: ReviewStatus | None = Query(default=None),
    severity: Severity | None = Query(default=None),
):
    return service.get_dashboard_data(repo_name, status, severity)


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(repo_name: str | None = Query(default=None, alias="repo")):
    return service.get_summary(repo_name)


@router.get("/reports/{report_id}", response_model=ReviewReport)
async def get_report(report_id: UUID):
    try:
        return service.get_report(report_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
