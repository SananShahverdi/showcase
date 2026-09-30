from typing import Dict, List, Optional
from uuid import UUID

from ai_security_playground_llm_applications.adapters.repositories import ScenarioRepository
from ai_security_playground_llm_applications.algorithms.apps import HardenedApp, VulnerableApp
from ai_security_playground_llm_applications.domain.models import (
    AppMode, Approval, ApprovalDecision, ApprovalStatus, ExecutionResult, MetricsSummary,
    ScenarioType, SecurityReport, UserRole, utc_now,
)


APPROVAL_ACTIONS = {
    ScenarioType.EXCESSIVE_AGENCY: "synthetic database mutation",
    ScenarioType.WEAK_TOOL_PERMISSIONS: "synthetic ticket creation",
}


class SecurityService:
    def __init__(self, repo: ScenarioRepository):
        self.repo = repo
        self.runs: List[ExecutionResult] = []
        self.reports: Dict[UUID, SecurityReport] = {}
        self.approvals: Dict[UUID, Approval] = {}

    def _create_approval(self, scenario_id: str, result: ExecutionResult) -> UUID:
        approval = Approval(
            execution_id=result.id,
            scenario_id=scenario_id,
            requested_action=APPROVAL_ACTIONS.get(result.scenario_type, "synthetic side effect"),
            requested_by=result.role,
        )
        self.approvals[approval.id] = approval
        return approval.id

    def run_scenario(
        self,
        scenario_id: str,
        mode: AppMode,
        payload: Optional[str] = None,
        role: UserRole = UserRole.LEARNER,
    ) -> ExecutionResult:
        scenario = self.repo.get(scenario_id)
        query = payload if payload is not None else scenario.attack_payload
        allowed_tools = scenario.allowed_tools_by_role.get(role, [])
        if mode == AppMode.VULNERABLE:
            result = VulnerableApp.execute(scenario.type, query, role, allowed_tools=allowed_tools)
        else:
            result = HardenedApp.execute(
                scenario.type,
                query,
                role,
                create_approval=lambda execution: self._create_approval(scenario_id, execution),
                allowed_tools=allowed_tools,
            )
        self.runs.append(result)
        return result

    def list_runs(self, limit: int = 100) -> List[ExecutionResult]:
        return list(reversed(self.runs[-max(1, min(limit, 500)):]))

    def list_approvals(self) -> List[Approval]:
        return sorted(self.approvals.values(), key=lambda item: item.created_at, reverse=True)

    def resolve_approval(self, approval_id: UUID, decision: ApprovalDecision) -> Approval:
        approval = self.approvals.get(approval_id)
        if approval is None:
            raise KeyError(str(approval_id))
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError("Approval has already been resolved")
        approval.status = ApprovalStatus.APPROVED if decision.approve else ApprovalStatus.DENIED
        approval.resolved_by = decision.actor
        approval.reason = decision.reason
        approval.resolved_at = utc_now()
        return approval

    def consume_approval(self, approval_id: UUID) -> Approval:
        approval = self.approvals.get(approval_id)
        if approval is None:
            raise KeyError(str(approval_id))
        if approval.status == ApprovalStatus.CONSUMED:
            raise ValueError("Approval is one-time and has already been consumed")
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError("Approval must be approved before execution")
        approval.status = ApprovalStatus.CONSUMED
        approval.consumed_at = utc_now()
        return approval

    def run_assessment(self) -> SecurityReport:
        results: List[ExecutionResult] = []
        for scenario in self.repo.get_all():
            results.append(self.run_scenario(scenario.id, AppMode.VULNERABLE))
            results.append(self.run_scenario(scenario.id, AppMode.HARDENED))
        vulnerable = [r for r in results if r.mode == AppMode.VULNERABLE]
        hardened = [r for r in results if r.mode == AppMode.HARDENED]
        vulnerabilities = sum(r.was_successful_attack for r in vulnerable)
        mitigations = sum(r.mitigation_triggered and not r.was_successful_attack for r in hardened)
        report = SecurityReport(
            scenarios_tested=len(vulnerable),
            vulnerabilities_found=vulnerabilities,
            mitigations_verified=mitigations,
            mitigation_rate=round(mitigations / len(hardened), 4) if hardened else 0.0,
            results=results,
        )
        self.reports[report.id] = report
        return report

    def list_reports(self, limit: int = 20) -> List[SecurityReport]:
        """Stored assessments, newest first."""
        ordered = sorted(self.reports.values(), key=lambda report: report.created_at, reverse=True)
        return ordered[:max(1, min(limit, 100))]

    def get_report(self, report_id: UUID) -> SecurityReport:
        report = self.reports.get(report_id)
        if report is None:
            raise KeyError(str(report_id))
        return report

    @staticmethod
    def report_markdown(report: SecurityReport) -> str:
        lines = [
            "# AI Security Playground Assessment",
            "",
            f"- Report ID: `{report.id}`",
            f"- Policy version: `{report.policy_version}`",
            f"- Scenarios tested: {report.scenarios_tested}",
            f"- Vulnerable exposures demonstrated: {report.vulnerabilities_found}",
            f"- Hardened mitigations verified: {report.mitigations_verified}",
            f"- Mitigation rate: {report.mitigation_rate:.0%}",
            "",
            "## Evidence",
            "",
            "| Scenario | Mode | Attack succeeded | Controls | Outcome |",
            "|---|---|---:|---|---|",
        ]
        for result in report.results:
            controls = ", ".join(result.controls_triggered) or "none"
            outcome = "expected" if result.expected_outcome_met else "unexpected"
            lines.append(
                f"| {result.scenario_type.value} | {result.mode.value} | "
                f"{'yes' if result.was_successful_attack else 'no'} | {controls} | {outcome} |"
            )
        lines.extend(["", "> All vulnerable side effects use synthetic fixtures; no host resource was changed."])
        return "\n".join(lines) + "\n"

    def metrics(self) -> MetricsSummary:
        total = len(self.runs)
        return MetricsSummary(
            total_runs=total,
            blocked_runs=sum(r.mitigation_triggered for r in self.runs),
            successful_attacks=sum(r.was_successful_attack for r in self.runs),
            pending_approvals=sum(a.status == ApprovalStatus.PENDING for a in self.approvals.values()),
            average_duration_ms=round(sum(r.duration_ms for r in self.runs) / total, 3) if total else 0.0,
        )
