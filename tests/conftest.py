"""Keep direct `pytest tests` runs away from configured workspace databases."""
import tempfile
from pathlib import Path

import pytest


def pytest_configure(config):
    directory = tempfile.TemporaryDirectory(prefix="portfolio-api-tests-")
    state = Path(directory.name)
    environment = pytest.MonkeyPatch()
    for key, value in {
        "PORTFOLIO_STATE_DIR": state,
        "RAG_STATE_DIR": state / "rag",
        "DATA_QUALITY_STATE_FILE": state / "orbit.json",
        "CAPACITY_STATE_FILE": state / "capacity.json",
        "DELIVERY_DESK_DB": state / "delivery.sqlite3",
        "STOCKROOM_INVENTORY_DB": state / "stockroom.sqlite3",
        "AGENTIC_BA_ALLOW_REMOTE_EXPORT": "false",
    }.items():
        environment.setenv(key, str(value))
    environment.delenv("MLFLOW_TRACKING_URI", raising=False)
    config._portfolio_test_environment = environment
    config._portfolio_test_directory = directory


def pytest_unconfigure(config):
    if hasattr(config, "_portfolio_test_environment"):
        config._portfolio_test_environment.undo()
        config._portfolio_test_directory.cleanup()
