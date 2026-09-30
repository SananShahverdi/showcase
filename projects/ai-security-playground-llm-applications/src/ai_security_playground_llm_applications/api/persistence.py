"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from ai_security_playground_llm_applications.adapters.database import Binding, StatePersistence
from ai_security_playground_llm_applications.api import routes
from ai_security_playground_llm_applications.domain.models import Approval, ExecutionResult, SecurityReport


NAMESPACE = "ai_security_playground_llm_applications"


def bindings() -> list:
    return [
        Binding("runs", lambda: routes.service.runs, ExecutionResult),
        Binding("reports", lambda: routes.service.reports, SecurityReport, UUID),
        Binding("approvals", lambda: routes.service.approvals, Approval, UUID),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
