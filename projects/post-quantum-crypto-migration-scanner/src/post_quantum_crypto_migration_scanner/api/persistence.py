"""State collections persisted when a database URL is configured."""

from uuid import UUID  # noqa: F401

from post_quantum_crypto_migration_scanner.adapters.database import Binding, StatePersistence
from post_quantum_crypto_migration_scanner.api import routes
from post_quantum_crypto_migration_scanner.domain.models import ScanReport


NAMESPACE = "post_quantum_crypto_migration_scanner"


def bindings() -> list:
    return [
        Binding("reports", lambda: routes.store.reports, ScanReport, UUID),
    ]


def build_persistence(url):
    """None keeps the documented in-memory mode."""
    return StatePersistence(url, NAMESPACE, bindings()) if url else None
