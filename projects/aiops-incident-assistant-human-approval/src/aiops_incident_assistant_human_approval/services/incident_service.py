from datetime import datetime
from typing import List
from uuid import UUID

from aiops_incident_assistant_human_approval.adapters.executor import LocalSafeExecutor
from aiops_incident_assistant_human_approval.adapters.repositories import InMemoryRepository
from aiops_incident_assistant_human_approval.algorithms.ai_agent import AIOpsAgent
from aiops_incident_assistant_human_approval.algorithms.policy_engine import PolicyEngine
from aiops_incident_assistant_human_approval.domain.models import (
    ActionStatus,
    AuditEvent,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
    PostIncidentReport,
    RemediationPlan,
    TelemetryData,
)


SCENARIO_TELEMETRY = {
    IncidentType.LATENCY_SPIKE: TelemetryData(
        logs=["request timeout while waiting for database connection", "pool checkout exceeded 2000ms"],
        metrics={"p95_latency_ms": 2410.0, "db_pool_waiters": 34.0, "error_rate": 0.04},
        traces=[{"trace_id": "trace-latency-001", "duration_ms": 2518, "slow_span": "postgres.checkout"}],
    ),
    IncidentType.DEPENDENCY_FAILURE: TelemetryData(
        logs=["payment dependency returned connection refused", "circuit breaker opened"],
        metrics={"dependency_success_rate": 0.12, "error_rate": 0.22, "p95_latency_ms": 4100.0},
        traces=[{"trace_id": "trace-dependency-001", "duration_ms": 4200, "error_span": "payment.authorize"}],
    ),
    IncidentType.HIGH_ERROR_RATE: TelemetryData(
        logs=["release rev-42 raised AttributeError in checkout handler", "HTTP 500 POST /checkout"],
        metrics={"error_rate": 0.27, "deploy_revision": 42.0, "requests_per_second": 188.0},
        traces=[{"trace_id": "trace-errors-001", "duration_ms": 92, "error_span": "checkout.create"}],
    ),
    IncidentType.QUEUE_BACKLOG: TelemetryData(
        logs=["consumer heartbeat missed; partition revoked", "job processing rate below arrival rate"],
        metrics={"queue_depth": 1840.0, "oldest_message_seconds": 610.0, "worker_throughput": 2.0},
        traces=[{"trace_id": "trace-queue-001", "duration_ms": 31000, "slow_span": "jobs.consume"}],
    ),
}


class IncidentService:
    def __init__(self, repo: InMemoryRepository, executor: LocalSafeExecutor | None = None):
        self.repo = repo
        self.executor = executor or LocalSafeExecutor()

    def _audit(self, incident_id: UUID, event_type: str, actor: str, detail: str, plan_id: UUID | None = None, action_id: UUID | None = None) -> None:
        self.repo.save_audit_event(AuditEvent(
            incident_id=incident_id,
            plan_id=plan_id,
            action_id=action_id,
            event_type=event_type,
            actor=actor,
            detail=detail,
        ))

    def generate_incident(self, type: IncidentType, service_name: str) -> Incident:
        severity = IncidentSeverity.SEV1 if type in {IncidentType.HIGH_ERROR_RATE, IncidentType.DEPENDENCY_FAILURE} else IncidentSeverity.SEV2
        incident = Incident(type=type, service_name=service_name, severity=severity, telemetry=SCENARIO_TELEMETRY[type].model_copy(deep=True))
        self.repo.save_incident(incident)
        self._audit(incident.id, "incident.created", "scenario-generator", f"Created {type.value} for {service_name}")
        return incident

    def list_incidents(self, status: IncidentStatus | None = None) -> List[Incident]:
        incidents = self.repo.get_incidents()
        return [incident for incident in incidents if status is None or incident.status == status]

    def get_incident(self, incident_id: UUID) -> Incident:
        incident = self.repo.get_incident(incident_id)
        if incident is None:
            raise ValueError("Incident not found")
        return incident

    def analyze(self, incident_id: UUID, actor: str = "local-operator") -> RemediationPlan:
        incident = self.get_incident(incident_id)
        if incident.status == IncidentStatus.RESOLVED:
            raise ValueError("Resolved incidents cannot be analyzed")

        incident.status = IncidentStatus.INVESTIGATING
        incident.updated_at = datetime.utcnow()
        self.repo.save_incident(incident)

        revision = len(self.repo.get_plans_for_incident(incident.id)) + 1
        plan = AIOpsAgent.analyze_incident(incident, revision=revision)
        for action in plan.actions:
            allowed, reason = PolicyEngine.evaluate(action.command)
            action.policy_reason = reason
            if not allowed:
                action.status = ActionStatus.BLOCKED

        self.repo.save_plan(plan)
        self._audit(incident.id, "plan.created", actor, f"Created evidence-grounded plan revision {revision}", plan.id)
        return plan

    def get_plan(self, plan_id: UUID) -> RemediationPlan:
        plan = self.repo.get_plan(plan_id)
        if plan is None:
            raise ValueError("Plan not found")
        return plan

    def decide_action(self, plan_id: UUID, action_index: int, approve: bool, actor: str, reason: str) -> RemediationPlan:
        plan = self.get_plan(plan_id)
        if action_index < 0 or action_index >= len(plan.actions):
            raise ValueError("Invalid action index")
        if not actor.strip() or not reason.strip():
            raise ValueError("Actor and decision reason are required")

        action = plan.actions[action_index]
        if action.status == ActionStatus.BLOCKED:
            raise ValueError("Cannot approve or reject a policy-blocked action")
        if action.status != ActionStatus.PENDING:
            raise ValueError(f"Action is already {action.status.value}")

        action.decided_by = actor.strip()
        action.decision_reason = reason.strip()
        action.decided_at = datetime.utcnow()
        action.status = ActionStatus.APPROVED if approve else ActionStatus.REJECTED
        self.repo.save_plan(plan)
        self._audit(plan.incident_id, "action.approved" if approve else "action.rejected", actor, reason, plan.id, action.id)

        if approve:
            self._execute_approved_action(plan, action_index)
        else:
            self._finish_if_terminal(plan)
        return plan

    def approve_and_execute_action(self, plan_id: UUID, action_index: int, actor: str = "local-operator", reason: str = "Approved after reviewing evidence") -> RemediationPlan:
        return self.decide_action(plan_id, action_index, True, actor, reason)

    def reject_action(self, plan_id: UUID, action_index: int, actor: str, reason: str) -> RemediationPlan:
        return self.decide_action(plan_id, action_index, False, actor, reason)

    def _execute_approved_action(self, plan: RemediationPlan, action_index: int) -> None:
        action = plan.actions[action_index]
        if action.status != ActionStatus.APPROVED:
            raise ValueError("Execution requires an approved action")
        result = self.executor.execute(action.command)
        action.executed_at = datetime.utcnow()
        action.execution_output = result.output[:2000]
        action.status = ActionStatus.COMPLETED if result.succeeded else ActionStatus.FAILED
        self.repo.save_plan(plan)
        self._audit(
            plan.incident_id,
            "action.completed" if result.succeeded else "action.failed",
            action.decided_by or "unknown",
            result.output,
            plan.id,
            action.id,
        )
        self._finish_if_terminal(plan)

    def _finish_if_terminal(self, plan: RemediationPlan) -> None:
        terminal = {ActionStatus.COMPLETED, ActionStatus.BLOCKED, ActionStatus.REJECTED}
        if not all(action.status in terminal for action in plan.actions):
            return
        incident = self.get_incident(plan.incident_id)
        incident.status = IncidentStatus.RESOLVED
        incident.updated_at = datetime.utcnow()
        self.repo.save_incident(incident)
        resolution_time = (datetime.utcnow() - incident.created_at).total_seconds() / 60.0
        report = PostIncidentReport(
            incident_id=incident.id,
            summary=f"Resolved {incident.type.value.replace('_', ' ')} for {incident.service_name}",
            root_cause=plan.hypothesis,
            actions_taken=[action.command for action in plan.actions if action.status == ActionStatus.COMPLETED],
            time_to_resolution_minutes=resolution_time,
            evidence=plan.evidence,
        )
        self.repo.save_report(report)
        self._audit(incident.id, "incident.resolved", "workflow", f"Generated report {report.id}", plan.id)

    def report_markdown(self, report_id: UUID) -> str:
        report = self.repo.get_report(report_id)
        if report is None:
            raise ValueError("Report not found")
        evidence = "\n".join(f"- **{item.kind}** `{item.source}`: {item.observation}" for item in report.evidence)
        actions = "\n".join(f"- `{command}`" for command in report.actions_taken) or "- No command executed"
        return (
            f"# Post-incident report\n\n{report.summary}\n\n"
            f"## Root cause\n\n{report.root_cause}\n\n"
            f"## Evidence\n\n{evidence}\n\n"
            f"## Actions taken\n\n{actions}\n\n"
            f"Time to resolution: {report.time_to_resolution_minutes:.2f} minutes.\n"
        )
