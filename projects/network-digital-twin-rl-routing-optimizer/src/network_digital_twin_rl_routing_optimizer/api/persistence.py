"""State collections persisted when a database URL is configured."""

from typing import Any, Dict  # noqa: F401

from network_digital_twin_rl_routing_optimizer.adapters.database import Binding, StatePersistence
from network_digital_twin_rl_routing_optimizer.api import routes


NAMESPACE = "network_digital_twin_rl_routing_optimizer"


def bindings() -> list:
    return [
        Binding("experiments", lambda: routes.training_service.experiments, Dict[str, Any]),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
