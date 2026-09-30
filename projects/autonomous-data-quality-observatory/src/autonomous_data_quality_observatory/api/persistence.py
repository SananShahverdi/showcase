"""State collections persisted when a database URL is configured."""

from typing import Dict, List  # noqa: F401
from uuid import UUID  # noqa: F401

from autonomous_data_quality_observatory.adapters.database import Binding, StatePersistence
from autonomous_data_quality_observatory.api import routes
from autonomous_data_quality_observatory.domain.models import DataSource, DatasetProfile, Issue, ObservationReport, Rule


NAMESPACE = "autonomous_data_quality_observatory"


def bindings() -> list:
    return [
        Binding("sources", lambda: routes.repo.sources, DataSource, str),
        Binding("profiles", lambda: routes.repo.profiles, List[DatasetProfile], str),
        Binding("rules", lambda: routes.repo.rules, Dict[str, Rule], str),
        Binding("issues", lambda: routes.repo.issues, Issue, UUID),
        Binding("reports", lambda: routes.repo.reports, List[ObservationReport], str),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
