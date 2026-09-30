from typing import Dict, List, Optional
from uuid import UUID

from process_mining_workflow_automation_analyzer.algorithms.ai_assistant import EvidenceAssistant
from process_mining_workflow_automation_analyzer.algorithms.engine import ProcessEngine
from process_mining_workflow_automation_analyzer.domain.models import AnalysisConfig, AnalysisReport, DataQuality, Event


class AnalyzerService:
    def __init__(self):
        self.reports: Dict[UUID, AnalysisReport] = {}

    def analyze_events(
        self, events: List[Event], config: AnalysisConfig | None = None, *, rejected_issues: Optional[List[str]] = None,
    ) -> AnalysisReport:
        if not events:
            raise ValueError("At least one valid event is required")
        if len(events) > 100_000:
            raise ValueError("Analysis is limited to 100,000 events")
        unique_events: List[Event] = []
        seen = set()
        duplicate_count = 0
        for event in events:
            identity = event.event_id or (event.case_id, event.activity, event.timestamp.isoformat(), event.resource, event.lifecycle)
            if identity in seen:
                duplicate_count += 1
                continue
            seen.add(identity)
            unique_events.append(event)
        if not unique_events:
            raise ValueError("All submitted events were duplicates")
        config = config or AnalysisConfig()
        analysis = ProcessEngine.analyze(unique_events, config)
        report = AnalysisReport(
            total_cases=len({event.case_id for event in unique_events}), total_events=len(unique_events), config=config,
            data_quality=DataQuality(
                accepted_events=len(unique_events), rejected_rows=len(rejected_issues or []), duplicate_events=duplicate_count,
                single_event_cases=sum(metric.event_count == 1 for metric in analysis["case_metrics"]),
                issues=(rejected_issues or [])[:100],
            ),
            variants=analysis["variants"], transitions=analysis["transitions"], bottlenecks=analysis["bottlenecks"],
            rework_loops=analysis["rework_loops"], case_metrics=analysis["case_metrics"],
            sla_breaches=analysis["sla_breaches"], resources=analysis["resources"], ai_summary="", recommendations=[],
        )
        report = EvidenceAssistant.generate_recommendations(report)
        self.reports[report.id] = report
        return report

    def list_reports(self) -> List[AnalysisReport]:
        return sorted(self.reports.values(), key=lambda report: report.created_at, reverse=True)

    def get_report(self, report_id: str | UUID) -> Optional[AnalysisReport]:
        return next((report for key, report in self.reports.items() if str(key) == str(report_id)), None)

    def export_report_markdown(self, report_id: str) -> Optional[str]:
        report = self.get_report(report_id)
        if report is None:
            return None
        lines = [
            "# Process Mining Report", "", f"- **Report ID**: `{report.id}`", f"- **Cases**: {report.total_cases}",
            f"- **Events**: {report.total_events}", f"- **Variants**: {len(report.variants)}",
            f"- **SLA breaches**: {len(report.sla_breaches)}", "", "## Computed evidence", "", report.ai_summary, "",
            "| Transition | Frequency | Mean seconds | Median seconds | P95 seconds | Coverage |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for transition in report.transitions:
            lines.append(
                f"| {transition.source} → {transition.target} | {transition.frequency} | {transition.avg_duration_seconds:.1f} | "
                f"{transition.median_duration_seconds:.1f} | {transition.p95_duration_seconds:.1f} | {transition.case_coverage:.1%} |"
            )
        lines.extend(["", "## Automation recommendations", ""])
        for recommendation in report.recommendations:
            lines.extend([
                f"### P{recommendation.priority} — {recommendation.title}", "", recommendation.description, "",
                "Evidence: " + "; ".join(recommendation.evidence), "", f"Validation: {recommendation.validation_step}",
                f"Rollback: {recommendation.rollback_guardrail}", "",
            ])
        lines.extend(["## Data quality", "", f"- Rejected rows: {report.data_quality.rejected_rows}",
                      f"- Duplicates removed: {report.data_quality.duplicate_events}"])
        return "\n".join(lines) + "\n"

    def export_issues(self, report_id: str) -> Optional[List[dict]]:
        report = self.get_report(report_id)
        if report is None:
            return None
        return [{
            "title": f"[Process automation P{recommendation.priority}] {recommendation.title}",
            "body": f"{recommendation.description}\n\nEvidence\n- " + "\n- ".join(recommendation.evidence)
                    + f"\n\nValidation: {recommendation.validation_step}\nRollback: {recommendation.rollback_guardrail}",
            "labels": ["process-mining", "automation-candidate", f"priority-{recommendation.priority}"],
        } for recommendation in report.recommendations]
