"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from local_ai_inference_gateway_llmops_console.adapters.database import Binding, StatePersistence
from local_ai_inference_gateway_llmops_console.api import routes
from local_ai_inference_gateway_llmops_console.domain.models import GatewayApiKey, GatewayMetrics, PromptTemplate, ProviderConfig, RequestLog


NAMESPACE = "local_ai_inference_gateway_llmops_console"


def bindings() -> list:
    return [
        Binding("providers", lambda: routes.repo.providers, ProviderConfig, UUID),
        Binding("prompts", lambda: routes.repo.prompts, PromptTemplate, UUID),
        Binding("logs", lambda: routes.repo.logs, RequestLog, UUID),
        Binding("api_keys", lambda: routes.repo.api_keys, GatewayApiKey, UUID),
        Binding("metrics", lambda: routes.repo.metrics, GatewayMetrics, setter=lambda value: setattr(routes.repo, "metrics", value)),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
