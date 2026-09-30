"""State collections persisted when a database URL is configured."""

from typing import Dict, List  # noqa: F401

from smart_network_capacity_planner.adapters.database import Binding, StatePersistence
from smart_network_capacity_planner.api import routes
from smart_network_capacity_planner.domain.models import TelemetryData, WhatIfScenario


NAMESPACE = "smart_network_capacity_planner"


def bindings() -> list:
    return [
        Binding("telemetry", lambda: routes.repo._data, Dict[str, TelemetryData], str),
        Binding("scenarios", lambda: routes.repo._scenarios, List[WhatIfScenario], str),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
