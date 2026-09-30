"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from process_mining_workflow_automation_analyzer.adapters.database import Binding, StatePersistence
from process_mining_workflow_automation_analyzer.api import routes
from process_mining_workflow_automation_analyzer.domain.models import AnalysisReport


NAMESPACE = "process_mining_workflow_automation_analyzer"


def bindings() -> list:
    return [
        Binding("reports", lambda: routes.service.reports, AnalysisReport, UUID),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
