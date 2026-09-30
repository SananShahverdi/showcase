from collections import Counter
from typing import List

from post_quantum_crypto_migration_scanner.adapters.repositories import InventoryStore
from post_quantum_crypto_migration_scanner.algorithms.scanners import RepoScanner, TLSScanner
from post_quantum_crypto_migration_scanner.domain.models import (
    MigrationItem, ScanError, ScanReport, ServiceInventory, ServiceScanInput, Severity,
)


class ScannerService:
    def __init__(self, store: InventoryStore):
        self.store = store

    def run_scan(self, services_data: List[ServiceScanInput]) -> ScanReport:
        if not services_data:
            raise ValueError("At least one service is required")
        if len(services_data) > 50:
            raise ValueError("A local scan may contain at most 50 services")
        inventories: List[ServiceInventory] = []
        errors: List[ScanError] = []
        migration_plan: List[MigrationItem] = []

        for raw_service in services_data:
            service = raw_service if isinstance(raw_service, ServiceScanInput) else ServiceScanInput.model_validate(raw_service)
            try:
                source_findings = RepoScanner.scan(
                    service.files,
                    retention_years=service.retention_years,
                    internet_exposed=service.internet_exposed,
                )
            except ValueError as exc:
                source_findings = []
                errors.append(ScanError(service_name=service.name, source="repository", code="scan_limit", message=str(exc)))
            tls_findings, tls_errors = TLSScanner.analyze(
                service.endpoints,
                service.name,
                retention_years=service.retention_years,
                internet_exposed=service.internet_exposed,
            )
            errors.extend(tls_errors)
            findings = sorted(
                source_findings + tls_findings,
                key=lambda item: (-item.migration_priority, item.source, item.line or 0, item.algorithm),
            )
            has_pqc = any(f.rule_id == "PQC-STANDARD-CANDIDATE" for f in findings)
            blocking = any(f.quantum_vulnerable or f.severity in (Severity.HIGH, Severity.CRITICAL) for f in findings)
            service_errors = any(error.service_name == service.name for error in errors)
            is_quantum_safe = bool(findings) and has_pqc and not blocking and not service_errors
            if is_quantum_safe:
                posture = "migration_candidate_verified"
            elif findings:
                posture = "action_required"
            else:
                posture = "unknown"
            counts = dict(sorted(Counter(f.algorithm for f in findings).items()))
            inventories.append(ServiceInventory(
                service_name=service.name,
                findings=findings,
                is_quantum_safe=is_quantum_safe,
                posture=posture,
                retention_years=service.retention_years,
                internet_exposed=service.internet_exposed,
                algorithm_counts=counts,
            ))
            actionable = [f for f in findings if f.severity in (Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL)]
            if actionable:
                priority = max(f.migration_priority for f in actionable)
                migration_plan.append(MigrationItem(
                    service_name=service.name,
                    priority=priority,
                    finding_ids=[f.id for f in actionable],
                    target_state="Crypto-agile abstraction with approved TLS and standardized hybrid PQC where required",
                    rationale=(
                        f"{len(actionable)} actionable finding(s); retention={service.retention_years}y; "
                        f"internet_exposed={str(service.internet_exposed).lower()}."
                    ),
                ))

        all_findings = [finding for inventory in inventories for finding in inventory.findings]
        report = ScanReport(
            services=inventories,
            migration_plan=sorted(migration_plan, key=lambda item: (-item.priority, item.service_name)),
            errors=errors,
            total_findings=len(all_findings),
            critical_findings=sum(f.severity == Severity.CRITICAL for f in all_findings),
            high_findings=sum(f.severity == Severity.HIGH for f in all_findings),
        )
        self.store.save(report)
        return report

    def get_dashboard(self) -> ScanReport:
        report = self.store.get_latest()
        if report is None:
            raise KeyError("No scans have been completed")
        return report

    @staticmethod
    def export_markdown(report: ScanReport) -> str:
        lines = [
            "# Post-Quantum Cryptography Migration Report", "",
            f"- Scan ID: `{report.id}`", f"- Rule version: `{report.rule_version}`",
            f"- Services: {len(report.services)}", f"- Findings: {report.total_findings}",
            f"- Critical / high: {report.critical_findings} / {report.high_findings}", "",
            "## Migration order", "",
        ]
        if not report.migration_plan:
            lines.append("No actionable migration item was detected; verify inventory coverage before concluding readiness.")
        for item in report.migration_plan:
            lines.extend([f"### {item.service_name} — priority {item.priority}", "", item.rationale, "", f"Target: {item.target_state}", ""])
        lines.extend(["## Evidence", "", "| Service | Severity | Algorithm | Source | Line | Rule |", "|---|---|---|---|---:|---|"])
        for inventory in report.services:
            for finding in inventory.findings:
                lines.append(
                    f"| {inventory.service_name} | {finding.severity.value} | {finding.algorithm} | "
                    f"{finding.source} | {finding.line or ''} | {finding.rule_id} |"
                )
        if report.errors:
            lines.extend(["", "## Coverage errors", ""])
            lines.extend(f"- `{error.service_name}/{error.source}` [{error.code}]: {error.message}" for error in report.errors)
        return "\n".join(lines) + "\n"
