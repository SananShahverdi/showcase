import csv
from io import StringIO
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from real_time_fraud_risk_stream_analytics.adapters.repositories import AlertRepository
from real_time_fraud_risk_stream_analytics.domain.models import (
    Alert,
    AnalystFeedback,
    Event,
    FeedbackRequest,
    MetricsDashboard,
    ProcessingResult,
)
from real_time_fraud_risk_stream_analytics.services.analytics_service import AnalyticsService

router = APIRouter()
repo = AlertRepository()
service = AnalyticsService(repo)


@router.post("/events", response_model=ProcessingResult)
async def ingest_event(event: Event):
    return service.process_event(event)


@router.post("/events/batch", response_model=List[ProcessingResult])
async def ingest_batch(events: List[Event]):
    if not 1 <= len(events) <= 500:
        raise HTTPException(status_code=422, detail="Batch must contain between 1 and 500 events")
    return service.process_batch(events)


@router.post("/demo/seed", response_model=List[ProcessingResult])
async def seed_demo():
    return service.seed_demo()


@router.get("/alerts", response_model=List[Alert])
async def list_alerts(status: AnalystFeedback | None = Query(default=None)):
    return service.list_alerts(status)


@router.get("/alerts/{alert_id}", response_model=Alert)
async def get_alert(alert_id: UUID):
    try:
        return service.get_alert(alert_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/alerts/{alert_id}/feedback", response_model=Alert)
async def submit_feedback(alert_id: UUID, request: FeedbackRequest):
    try:
        return service.submit_feedback(alert_id, request)
    except ValueError as error:
        status = 404 if "not found" in str(error).lower() else 409
        raise HTTPException(status_code=status, detail=str(error)) from error


@router.get("/entities/{user_id}/timeline", response_model=List[Event])
async def entity_timeline(user_id: str):
    return repo.timeline(user_id)


@router.get("/metrics", response_model=MetricsDashboard)
async def get_metrics():
    return service.get_metrics()


@router.get("/feedback/export")
async def export_feedback():
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["alert_id", "event_id", "decision", "reviewed_by", "review_note", "risk_score", "model_version", "policy_version"])
    for alert in repo.get_all():
        if alert.status != AnalystFeedback.PENDING:
            writer.writerow([
                alert.id, alert.event.id, alert.status.value, alert.reviewed_by or "", alert.review_note or "",
                alert.score.total_risk_score, alert.score.model_version, alert.score.policy_version,
            ])
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="analyst-feedback.csv"'},
    )
