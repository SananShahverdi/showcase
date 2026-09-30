"""State collections persisted when a database URL is configured."""


from internal_developer_portal_golden_paths.adapters.database import Binding, StatePersistence
from internal_developer_portal_golden_paths.api import routes
from internal_developer_portal_golden_paths.domain.models import ArtifactManifest, ServiceMetadata, TemplateDefinition


NAMESPACE = "internal_developer_portal_golden_paths"


def bindings() -> list:
    return [
        Binding("services", lambda: routes.catalog.services, ServiceMetadata, str),
        Binding("templates", lambda: routes.catalog.templates, TemplateDefinition, str),
        Binding("manifests", lambda: routes.artifacts.manifests, ArtifactManifest, str),
        Binding("archives", lambda: routes.artifacts.archives, bytes, str),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
