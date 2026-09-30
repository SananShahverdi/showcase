from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from autonomous_data_quality_observatory.adapters.repositories import MetadataRepository
from autonomous_data_quality_observatory.algorithms.engines import Connectors, DriftDetector, Profiler, RulesEngine
from autonomous_data_quality_observatory.domain.models import (
    ConnectorPreview,
    DataSource,
    DatasetOverview,
    DeliveryResult,
    Issue,
    IssueEvent,
    IssueStatus,
    IssueUpdate,
    ObservationReport,
    Rule,
    Severity,
    SourceType,
    utc_now,
)


class ObservatoryService:
    def __init__(self, repo: MetadataRepository):
        self.repo = repo

    def add_source(self, source: DataSource) -> DataSource:
        return self.repo.save_source(source)

    def list_sources(self) -> List[DataSource]:
        return [source.safe_view() for source in self.repo.list_sources()]

    def add_rule(self, rule: Rule) -> Rule:
        if not self.repo.get_source(rule.source_id):
            raise ValueError("Source not found")
        return self.repo.save_rule(rule)

    def preview(self, source_id: str, limit: int = 5) -> ConnectorPreview:
        source = self._source(source_id)
        records = Connectors.fetch_data(source)
        columns = sorted({key for row in records for key in row})
        return ConnectorPreview(
            source_id=source_id,
            row_count=len(records),
            columns=columns,
            rows=records[:limit],
            truncated=len(records) > limit,
        )

    @staticmethod
    def _freshness(source: DataSource, records: List[Dict[str, Any]]) -> Optional[datetime]:
        field = source.config.get("freshness_field")
        if not field:
            return source.updated_at
        timestamps: List[datetime] = []
        for record in records:
            raw = record.get(str(field))
            if raw is None:
                continue
            try:
                parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                timestamps.append(parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc))
            except ValueError:
                continue
        return max(timestamps) if timestamps else None

    @staticmethod
    def _health(rule_results, drift_result) -> tuple[float, str]:
        weights = {Severity.LOW: 5, Severity.MEDIUM: 12, Severity.HIGH: 22, Severity.CRITICAL: 35}
        penalty = sum(weights[result.severity] for result in rule_results if not result.passed)
        penalty += min(35, len(drift_result.signals) * 12)
        score = max(0.0, 100.0 - penalty)
        status = "healthy" if score >= 90 else "warning" if score >= 70 else "critical"
        return score, status

    def observe(self, source_id: str) -> ObservationReport:
        source = self._source(source_id)
        records = Connectors.fetch_data(source)
        baseline = self.repo.get_baseline_profile(source_id)
        profile = Profiler.profile(source_id, records, self._freshness(source, records))
        if baseline is None:
            profile.is_baseline = True
        rules = self.repo.get_rules(source_id)
        results = RulesEngine.evaluate(profile, rules, records)
        drift = DriftDetector.detect(profile, baseline)
        health_score, health_status = self._health(results, drift)
        created: List[Issue] = []
        updated: List[Issue] = []

        for result in (item for item in results if not item.passed):
            issue = Issue(
                fingerprint=f"{source_id}:rule:{result.rule_id}",
                source_id=source_id,
                title=f"Rule failure: {result.rule_id}",
                description=result.details,
                severity=result.severity,
                owner=source.owner,
                suggested_remediation="Inspect the failing evidence, validate the upstream contract, and rerun the observation after remediation.",
                evidence={"rule_id": result.rule_id, "observed": result.observed, "expected": result.expected},
            )
            stored, was_created = self.repo.upsert_issue(issue)
            (created if was_created else updated).append(stored)

        for signal in drift.signals:
            severity = Severity.CRITICAL if signal.drift_type in {"schema", "type"} else Severity.HIGH
            issue = Issue(
                fingerprint=f"{source_id}:drift:{signal.drift_type}:{signal.column or 'dataset'}",
                source_id=source_id,
                title=f"{signal.drift_type.replace('_', ' ').title()} drift detected",
                description=signal.details,
                severity=severity,
                owner=source.owner,
                suggested_remediation="Confirm whether the change is expected; update the producer or explicitly promote a reviewed profile as the new baseline.",
                evidence=signal.model_dump(mode="json"),
            )
            stored, was_created = self.repo.upsert_issue(issue)
            (created if was_created else updated).append(stored)

        self.repo.save_profile(profile)
        report = ObservationReport(
            profile=profile,
            rule_results=results,
            drift_result=drift,
            health_score=health_score,
            health_status=health_status,
            issues_created=created,
            issues_updated=updated,
        )
        return self.repo.save_report(report)

    def overviews(self) -> List[DatasetOverview]:
        results: List[DatasetOverview] = []
        for source in self.repo.list_sources():
            reports = self.repo.list_reports(source.id)
            latest_report = reports[0] if reports else None
            results.append(
                DatasetOverview(
                    source=source.safe_view(),
                    latest_profile=self.repo.get_latest_profile(source.id),
                    health_score=latest_report.health_score if latest_report else None,
                    health_status=latest_report.health_status if latest_report else "not_observed",
                    active_issue_count=len(self.repo.list_issues(source.id, active_only=True)),
                    rule_count=len(self.repo.get_rules(source.id)),
                )
            )
        return results

    def update_issue(self, issue_id: UUID, update: IssueUpdate) -> Issue:
        issue = self.repo.get_issue(issue_id)
        if issue is None:
            raise ValueError("Issue not found")
        if update.owner is not None:
            issue.owner = update.owner or None
            issue.timeline.append(IssueEvent(actor=update.actor, action="assigned", note=update.owner))
        if update.status is not None and update.status != issue.status:
            issue.status = update.status
            issue.resolved_at = utc_now() if update.status == IssueStatus.RESOLVED else None
            issue.timeline.append(IssueEvent(actor=update.actor, action=f"status:{update.status.value}"))
        if update.comment:
            issue.timeline.append(IssueEvent(actor=update.actor, action="commented", note=update.comment))
        issue.updated_at = utc_now()
        return self.repo.save_issue(issue)

    def export_issue(self, issue_id: UUID, destination: str = "jira-json") -> DeliveryResult:
        issue = self.repo.get_issue(issue_id)
        if issue is None:
            raise ValueError("Issue not found")
        payload = {
            "summary": issue.title,
            "description": issue.description,
            "labels": ["data-quality", issue.severity.value, issue.source_id],
            "assignee": issue.owner,
            "custom_fields": {"evidence": issue.evidence, "remediation": issue.suggested_remediation},
        }
        return DeliveryResult(
            issue_id=issue.id,
            destination=destination,
            delivered=False,
            payload=payload,
            message="Export payload generated. Configure an approved webhook adapter to deliver it; no external success was fabricated.",
        )

    def seed_demo(self, reset: bool = False) -> List[DatasetOverview]:
        if reset:
            self.repo.clear()
        now = utc_now()
        orders = [
            {"order_id": f"ORD-{index:03d}", "amount": 100 + index * 12, "status": "paid", "event_at": (now - timedelta(hours=index)).isoformat()}
            for index in range(1, 13)
        ]
        customers = [
            {"customer_id": f"C-{index:03d}", "email": f"user{index}@example.com", "country": "AZ" if index < 6 else "GE"}
            for index in range(1, 9)
        ]
        self.add_source(DataSource(id="orders_daily", name="Daily orders", type=SourceType.INLINE, owner="commerce-data", config={"records": orders, "freshness_field": "event_at"}))
        self.add_source(DataSource(id="customer_accounts", name="Customer accounts", type=SourceType.JSON, owner="customer-data", config={"records": customers}))
        for rule in [
            Rule(id="orders-schema", source_id="orders_daily", rule_type="schema", severity=Severity.CRITICAL, parameters={"columns": ["order_id", "amount", "status", "event_at"], "types": {"amount": "number"}}),
            Rule(id="orders-volume", source_id="orders_daily", rule_type="volume", parameters={"min_rows": 10, "max_rows": 5000}),
            Rule(id="orders-amount", source_id="orders_daily", rule_type="range", parameters={"column": "amount", "min": 0, "max": 10000}),
            Rule(id="orders-freshness", source_id="orders_daily", rule_type="freshness", parameters={"max_age_hours": 24}),
            Rule(id="customer-email", source_id="customer_accounts", rule_type="null_ratio", parameters={"column": "email", "max_ratio": 0}),
            Rule(id="customer-id-unique", source_id="customer_accounts", rule_type="uniqueness", parameters={"column": "customer_id", "min_ratio": 1}),
        ]:
            self.add_rule(rule)
        self.observe("orders_daily")
        self.observe("customer_accounts")
        return self.overviews()

    def introduce_demo_drift(self) -> DataSource:
        source = self._source("orders_daily")
        source.config["records"] = [
            {"order_id": f"ORD-{index:03d}", "amount_usd": 5000 + index * 800, "status": None, "event_at": (utc_now() - timedelta(days=3)).isoformat()}
            for index in range(1, 6)
        ]
        source.updated_at = utc_now()
        return self.repo.save_source(source)

    def _source(self, source_id: str) -> DataSource:
        source = self.repo.get_source(source_id)
        if source is None:
            raise ValueError("Source not found")
        return source
