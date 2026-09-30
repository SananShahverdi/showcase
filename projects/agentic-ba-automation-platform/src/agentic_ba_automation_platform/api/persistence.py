"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from agentic_ba_automation_platform.adapters.database import Binding, StatePersistence
from agentic_ba_automation_platform.api import routes
from agentic_ba_automation_platform.domain.models import Document, Chunk, Artifact, AuditLog


NAMESPACE = "agentic_ba_automation_platform"


def bindings() -> list:
    return [
        Binding("documents", lambda: routes.repo.documents, Document, UUID),
        Binding("chunks", lambda: routes.repo.chunks, Chunk, UUID),
        Binding("artifacts", lambda: routes.repo.artifacts, Artifact, UUID),
        Binding("audit_logs", lambda: routes.repo.audit_logs, AuditLog, UUID),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
