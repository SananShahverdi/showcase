from typing import List

from fastapi import APIRouter, HTTPException, Query

from process_mining_workflow_automation_analyzer.algorithms.importers import parse_csv_events, parse_xes_events
from process_mining_workflow_automation_analyzer.demo import DEMO_CONFIG, DEMO_CSV
from process_mining_workflow_automation_analyzer.domain.models import AnalysisConfig, AnalysisReport, Event, ImportPayload
from process_mining_workflow_automation_analyzer.services.analyzer_service import AnalyzerService

router = APIRouter()
service = AnalyzerService()


@router.post("/analyze", response_model=AnalysisReport)
def analyze_events(
    events: List[Event], sla_seconds: float = Query(default=86_400, gt=0),
    bottleneck_seconds: float = Query(default=86_400, ge=0), bottleneck_min_frequency: int = Query(default=1, ge=1),
) -> AnalysisReport:
    try:
        return service.analyze_events(events, AnalysisConfig(
            sla_seconds=sla_seconds, bottleneck_seconds=bottleneck_seconds,
            bottleneck_min_frequency=bottleneck_min_frequency,
        ))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import/csv", response_model=AnalysisReport)
def import_csv(payload: ImportPayload) -> AnalysisReport:
    try:
        events, issues = parse_csv_events(payload.content, payload.mapping)
        return service.analyze_events(events, payload.config, rejected_issues=issues)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import/xes", response_model=AnalysisReport)
def import_xes(payload: ImportPayload) -> AnalysisReport:
    try:
        events, issues = parse_xes_events(payload.content)
        return service.analyze_events(events, payload.config, rejected_issues=issues)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/demo/seed", response_model=AnalysisReport)
def seed_demo() -> AnalysisReport:
    """Analyze the synthetic demo event log through the same CSV import path."""
    events, issues = parse_csv_events(DEMO_CSV)
    return service.analyze_events(events, DEMO_CONFIG.model_copy(), rejected_issues=issues)


@router.get("/reports", response_model=List[AnalysisReport])
def list_reports() -> List[AnalysisReport]:
    return service.list_reports()


@router.get("/reports/{report_id}", response_model=AnalysisReport)
def get_report(report_id: str) -> AnalysisReport:
    report = service.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/export/{report_id}")
def export_report(report_id: str, format: str = Query(default="markdown", pattern="^(markdown|issues)$")):
    if format == "issues":
        issues = service.export_issues(report_id)
        if issues is None:
            raise HTTPException(status_code=404, detail="Report not found")
        return {"issues": issues}
    markdown = service.export_report_markdown(report_id)
    if markdown is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"markdown": markdown}
