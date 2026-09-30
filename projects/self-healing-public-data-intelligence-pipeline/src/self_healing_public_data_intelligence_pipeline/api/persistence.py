"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from self_healing_public_data_intelligence_pipeline.adapters.database import Binding, StatePersistence
from self_healing_public_data_intelligence_pipeline.api import routes
from self_healing_public_data_intelligence_pipeline.domain.models import CrawlRun, ExtractionRecipe, Record, RepairProposal, Source, ValidationFailure


NAMESPACE = "self_healing_public_data_intelligence_pipeline"


def bindings() -> list:
    return [
        Binding("sources", lambda: routes.repo.sources, Source, UUID),
        Binding("recipes", lambda: routes.repo.recipes, ExtractionRecipe, UUID),
        Binding("runs", lambda: routes.repo.runs, CrawlRun, UUID),
        Binding("records", lambda: routes.repo.records, Record, UUID),
        Binding("failures", lambda: routes.repo.failures, ValidationFailure, UUID),
        Binding("proposals", lambda: routes.repo.proposals, RepairProposal, UUID),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
