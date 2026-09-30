from process_mining_workflow_automation_analyzer.domain.models import AnalysisReport, Recommendation


def describe_duration(seconds: float) -> str:
    """Readable threshold label: 86400 -> "24-hour", 5400 -> "90-minute", 45 -> "45-second"."""
    if seconds >= 3600 and seconds % 3600 == 0:
        return f"{seconds / 3600:.0f}-hour"
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}-hour"
    if seconds >= 60 and seconds % 60 == 0:
        return f"{seconds / 60:.0f}-minute"
    return f"{seconds:g}-second"


class EvidenceAssistant:
    """Deterministic narrative layer: it may only restate metrics already in the report."""

    @staticmethod
    def generate_recommendations(report: AnalysisReport) -> AnalysisReport:
        recommendations = []
        for bottleneck in report.bottlenecks:
            hours = bottleneck.avg_duration_seconds / 3600
            recommendations.append(Recommendation(
                title=f"Reduce delay: {bottleneck.source} → {bottleneck.target}",
                description=(
                    f"The transition affects {bottleneck.frequency} observed occurrence(s) and averages "
                    f"{hours:.1f} hours. Pilot queue routing, an API handoff, or decision support at this boundary."
                ),
                expected_impact=f"Target a reduction in the measured {hours:.1f}-hour average delay.",
                evidence=[
                    f"transition={bottleneck.source}->{bottleneck.target}",
                    f"frequency={bottleneck.frequency}",
                    f"average_seconds={bottleneck.avg_duration_seconds:.1f}",
                    f"p95_seconds={bottleneck.p95_duration_seconds:.1f}",
                ],
                priority=min(100, int(60 + min(hours, 40))),
            ))
        if report.rework_loops:
            affected_cases = sum(metric.rework_count > 0 for metric in report.case_metrics)
            recommendations.append(Recommendation(
                title="Prevent repeated activities",
                description=(
                    f"Repeated activities ({', '.join(report.rework_loops)}) occur in {affected_cases} case(s). "
                    "Add entry validation and a reason code before automating the repeated step."
                ),
                expected_impact="Reduce rework events and avoidable handoffs.",
                evidence=[f"activities={','.join(report.rework_loops)}", f"affected_cases={affected_cases}"],
                priority=min(95, 55 + affected_cases * 5),
            ))
        if report.sla_breaches:
            recommendations.append(Recommendation(
                title="Triage SLA-risk cases",
                description=f"{len(report.sla_breaches)} of {report.total_cases} cases exceeded the configured SLA.",
                expected_impact="Route at-risk cases before their remaining SLA budget is exhausted.",
                evidence=[f"sla_seconds={report.config.sla_seconds}", f"breached_cases={len(report.sla_breaches)}"],
                priority=min(100, 50 + round(50 * len(report.sla_breaches) / report.total_cases)),
            ))
        if not recommendations:
            recommendations.append(Recommendation(
                title="Validate the stable baseline",
                description="No transition crossed the configured bottleneck threshold and no rework or SLA breach was observed.",
                expected_impact="Preserve current performance while collecting a larger representative sample.",
                evidence=[f"cases={report.total_cases}", f"bottleneck_seconds={report.config.bottleneck_seconds}"],
                priority=20,
            ))
        recommendations.sort(key=lambda item: (-item.priority, item.title))
        report.ai_summary = (
            f"Computed {len(report.variants)} variant(s) across {report.total_cases} case(s) and "
            f"{report.total_events} event(s). {len(report.bottlenecks)} transition(s) exceeded the "
            f"{describe_duration(report.config.bottleneck_seconds)} bottleneck threshold; "
            f"{len(report.sla_breaches)} case(s) breached the {describe_duration(report.config.sla_seconds)} SLA."
        )
        report.recommendations = recommendations
        return report


# Compatibility name for existing imports; this implementation is deterministic and evidence-bound.
AIAssistant = EvidenceAssistant
