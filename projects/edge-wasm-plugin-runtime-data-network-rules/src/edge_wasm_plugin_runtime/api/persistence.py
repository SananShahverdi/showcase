"""State collections persisted when a database URL is configured."""


from edge_wasm_plugin_runtime.adapters.database import Binding, StatePersistence
from edge_wasm_plugin_runtime.api import routes
from edge_wasm_plugin_runtime.domain.models import ExecutionResult, Plugin


NAMESPACE = "edge_wasm_plugin_runtime"


def bindings() -> list:
    return [
        Binding("plugins", lambda: routes.repo.plugins, Plugin, str),
        Binding("executions", lambda: routes.service.executions, ExecutionResult),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
