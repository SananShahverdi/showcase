import logging

import pytest

from ocw_smart_scraper.config import RuntimeConfig
from ocw_smart_scraper.self_test import CheckResult, SelfTestRunner


@pytest.fixture
def runner(monkeypatch):
    config = RuntimeConfig()
    instance = SelfTestRunner(config=config)
    # Avoid reconfiguring global logging during tests
    monkeypatch.setattr("ocw_smart_scraper.self_test.configure_logging", lambda *args, **kwargs: None)
    return instance


def test_self_test_runner_success_with_optional_warnings(monkeypatch, runner, caplog):
    results = [
        CheckResult("Python runtime", True, "OK"),
        CheckResult("Output directory", True, "OK"),
        CheckResult("Network connectivity", True, "OK"),
        CheckResult("Whisper", False, "Not installed", optional=True),
    ]
    monkeypatch.setattr(runner, "_collect_checks", lambda: results)

    with caplog.at_level(logging.INFO):
        assert runner.run(verbose=False) is True


def test_self_test_runner_failure_on_required_check(monkeypatch, runner, caplog):
    results = [
        CheckResult("Python runtime", True, "OK"),
        CheckResult("Network connectivity", False, "Blocked"),
    ]
    monkeypatch.setattr(runner, "_collect_checks", lambda: results)

    with caplog.at_level(logging.INFO):
        assert runner.run(verbose=False) is False
