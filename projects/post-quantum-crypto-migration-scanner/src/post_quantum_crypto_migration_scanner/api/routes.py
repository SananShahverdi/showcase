from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response

from post_quantum_crypto_migration_scanner.adapters.repositories import InventoryStore
from post_quantum_crypto_migration_scanner.algorithms.scanners import TLSScanner
from post_quantum_crypto_migration_scanner.demo import demo_estate
from post_quantum_crypto_migration_scanner.domain.models import (
    LiveProbeRequest, ScanReport, ScanSummary, ServiceScanInput, TLSObservation,
)
from post_quantum_crypto_migration_scanner.services.scanner_service import ScannerService

router = APIRouter()
store = InventoryStore()
service = ScannerService(store)


@router.post("/scan", response_model=ScanReport)
def trigger_scan(services: List[ServiceScanInput]) -> ScanReport:
    try:
        return service.run_scan(services)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dashboard", response_model=ScanReport)
def get_dashboard() -> ScanReport:
    try:
        return service.get_dashboard()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="No completed scan") from exc


@router.get("/scans", response_model=List[ScanSummary])
def list_scans() -> List[ScanSummary]:
    """Stored scans, newest first. An empty list means nothing has been scanned yet."""
    reports = sorted(store.reports.values(), key=lambda report: report.scanned_at, reverse=True)
    return [ScanSummary(
        id=report.id, rule_version=report.rule_version, scanned_at=report.scanned_at,
        service_count=len(report.services), total_findings=report.total_findings,
        critical_findings=report.critical_findings, high_findings=report.high_findings,
        error_count=len(report.errors),
    ) for report in reports]


@router.post("/demo/seed", response_model=ScanReport)
def seed_demo() -> ScanReport:
    """Scan the synthetic demo estate; earlier scans are kept as history."""
    return service.run_scan(demo_estate())


@router.get("/scans/{report_id}", response_model=ScanReport)
def get_scan(report_id: UUID) -> ScanReport:
    report = store.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return report


@router.get("/scans/{report_id}/export")
def export_scan(report_id: UUID, format: str = Query(default="markdown", pattern="^(markdown|json)$")):
    report = store.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if format == "json":
        return report
    return Response(service.export_markdown(report), media_type="text/markdown")


@router.post("/tls/probe", response_model=TLSObservation)
def probe_tls(request: LiveProbeRequest) -> TLSObservation:
    try:
        return TLSScanner.probe(
            request.endpoint,
            authorized=request.authorized,
            timeout_seconds=request.timeout_seconds,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (OSError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail=f"TLS probe failed: {type(exc).__name__}") from exc
