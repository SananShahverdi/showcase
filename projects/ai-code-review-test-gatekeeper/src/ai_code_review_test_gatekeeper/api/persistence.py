"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from ai_code_review_test_gatekeeper.adapters.database import Binding, StatePersistence
from ai_code_review_test_gatekeeper.api import routes
from ai_code_review_test_gatekeeper.domain.models import ReviewReport


NAMESPACE = "ai_code_review_test_gatekeeper"


def bindings() -> list:
    return [
        Binding("reports", lambda: routes.repo.reports, ReviewReport, UUID),
        Binding("idempotency", lambda: routes.repo.idempotency, UUID, str),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
