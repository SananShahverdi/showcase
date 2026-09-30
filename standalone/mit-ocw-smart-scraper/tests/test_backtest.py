from pathlib import Path

import requests

from ocw_smart_scraper.backtest import BacktestRunner
from ocw_smart_scraper.config import load_config


class DummyPipeline:
    def __init__(self, *_, **__):
        self.processed = []

    def _process_course(self, metadata):  # pylint: disable=protected-access
        self.processed.append(metadata.course_id)
        return object()


def test_backtest_runner(monkeypatch, tmp_path: Path) -> None:
    config = load_config(config_path=None, overrides=[f"output.base_directory={tmp_path}"])
    backtest_file = tmp_path / "backtest_courses.txt"
    backtest_file.write_text(
        "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/\n",
        encoding="utf-8",
    )

    pipeline_instance = DummyPipeline()

    def pipeline_factory(*args, **kwargs):  # pragma: no cover - simple factory
        return pipeline_instance

    monkeypatch.setattr("ocw_smart_scraper.backtest.ScraperPipeline", pipeline_factory)

    runner = BacktestRunner(config=config, session=requests.Session(), backtest_file=backtest_file)
    assert runner.run() is True
    assert pipeline_instance.processed == ["6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016"]
