"""State collections persisted when a database URL is configured."""

from datetime import datetime  # noqa: F401
from typing import Optional  # noqa: F401
from uuid import UUID  # noqa: F401

from real_time_fraud_risk_stream_analytics.adapters.database import Binding, StatePersistence
from real_time_fraud_risk_stream_analytics.api import routes
from real_time_fraud_risk_stream_analytics.domain.models import Alert, Event, Score


NAMESPACE = "real_time_fraud_risk_stream_analytics"


def bindings() -> list:
    return [
        Binding("alerts", lambda: routes.repo.alerts, Alert, UUID),
        Binding("events", lambda: routes.repo.events, Event, UUID),
        Binding("scores", lambda: routes.repo.scores, Score, UUID),
        Binding("stream_history", lambda: routes.service.processor.history, Event),
        Binding("stream_watermark", lambda: routes.service.processor.watermark, Optional[datetime], setter=lambda value: setattr(routes.service.processor, "watermark", value)),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
