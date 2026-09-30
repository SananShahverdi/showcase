"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from aiops_incident_assistant_human_approval.adapters.database import Binding, StatePersistence
from aiops_incident_assistant_human_approval.api import routes
from aiops_incident_assistant_human_approval.domain.models import AuditEvent, Incident, PostIncidentReport, RemediationPlan


NAMESPACE = "aiops_incident_assistant_human_approval"


def bindings() -> list:
    return [
        Binding("incidents", lambda: routes.repo.incidents, Incident, UUID),
        Binding("plans", lambda: routes.repo.plans, RemediationPlan, UUID),
        Binding("reports", lambda: routes.repo.reports, PostIncidentReport, UUID),
        Binding("audit_events", lambda: routes.repo.audit_events, AuditEvent, UUID),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
