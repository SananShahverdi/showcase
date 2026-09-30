"""Deterministic, evidence-grounded incident analysis.

The local analyzer is intentionally credential-free.  A hosted model can later be
added behind the same interface, but it must not replace policy evaluation.
"""

from aiops_incident_assistant_human_approval.domain.models import (
    EvidenceReference,
    Incident,
    IncidentType,
    RemediationAction,
    RemediationPlan,
)


RUNBOOKS = {
    IncidentType.LATENCY_SPIKE: "runbooks/database-pool-saturation.md",
    IncidentType.DEPENDENCY_FAILURE: "runbooks/dependency-failure.md",
    IncidentType.HIGH_ERROR_RATE: "runbooks/release-rollback.md",
    IncidentType.QUEUE_BACKLOG: "runbooks/queue-backlog.md",
}


class AIOpsAgent:
    @staticmethod
    def analyze_incident(incident: Incident, revision: int = 1) -> RemediationPlan:
        metrics = incident.telemetry.metrics
        first_log = incident.telemetry.logs[0] if incident.telemetry.logs else "No log sample available"
        first_trace = incident.telemetry.traces[0] if incident.telemetry.traces else {}
        runbook = RUNBOOKS[incident.type]

        evidence = [
            EvidenceReference(kind="metric", source=f"metrics/{incident.service_name}", observation=str(metrics)),
            EvidenceReference(kind="log", source=f"logs/{incident.service_name}", observation=first_log),
            EvidenceReference(kind="trace", source=str(first_trace.get("trace_id", "unavailable")), observation=str(first_trace)),
            EvidenceReference(kind="runbook", source=runbook, observation="Matched by incident type and service symptoms"),
        ]

        if incident.type == IncidentType.LATENCY_SPIKE:
            hypothesis = "Database connection-pool saturation is increasing request wait time."
            confidence = 0.91 if metrics.get("db_pool_waiters", 0) > 10 else 0.72
            actions = [RemediationAction(
                description="Increase the API deployment capacity while the connection pool recovers.",
                command=f"kubectl scale deployment {incident.service_name} --replicas=3",
                risk_level="medium",
                rollback_command=f"kubectl scale deployment {incident.service_name} --replicas=1",
            )]
        elif incident.type == IncidentType.DEPENDENCY_FAILURE:
            hypothesis = "The payment dependency is unavailable and causing upstream timeouts."
            confidence = 0.88
            actions = [RemediationAction(
                description="Restart the affected service to renew stale dependency connections.",
                command=f"kubectl rollout restart deployment/{incident.service_name}",
                risk_level="medium",
                rollback_command=f"kubectl rollout undo deployment/{incident.service_name}",
            )]
        elif incident.type == IncidentType.HIGH_ERROR_RATE:
            hypothesis = "A recent release regression is producing elevated HTTP 500 responses."
            confidence = 0.94 if metrics.get("error_rate", 0) >= 0.1 else 0.75
            actions = [RemediationAction(
                description="Roll back the affected deployment to its previous revision.",
                command=f"kubectl rollout undo deployment/{incident.service_name}",
                risk_level="high",
                rollback_command=f"kubectl rollout undo deployment/{incident.service_name}",
            )]
        else:
            hypothesis = "Worker throughput is below arrival rate, allowing the queue to grow."
            confidence = 0.90 if metrics.get("queue_depth", 0) > 500 else 0.70
            actions = [
                RemediationAction(
                    description="Restart worker pods to recover stalled consumers.",
                    command=f"kubectl rollout restart deployment/{incident.service_name}",
                    risk_level="low",
                    rollback_command=f"kubectl rollout undo deployment/{incident.service_name}",
                ),
                RemediationAction(
                    description="Unsafe cleanup suggested by an untrusted source; retained as policy evidence.",
                    command="rm -rf /var/log/*",
                    risk_level="high",
                    rollback_command="kubectl rollout undo deployment/worker",
                ),
            ]

        return RemediationPlan(
            incident_id=incident.id,
            hypothesis=hypothesis,
            confidence=confidence,
            runbook=runbook,
            evidence=evidence,
            actions=actions,
            revision=revision,
        )
