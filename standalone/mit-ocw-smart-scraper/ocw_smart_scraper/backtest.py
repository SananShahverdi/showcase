"""Backtest runner for the OCW Smart Scraper."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional

import requests

from .config import RuntimeConfig
from .discovery import CourseMetadata
from .pipeline import ScraperPipeline

logger = logging.getLogger(__name__)


class BacktestRunner:
    """Run a repeatable scrape over a curated course list."""

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        session: Optional[requests.Session] = None,
        backtest_file: Optional[Path] = None,
    ) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.backtest_file = backtest_file or Path("backtest_courses.txt")

    def _load_courses(self) -> List[str]:
        if not self.backtest_file.exists():
            raise FileNotFoundError(f"Backtest file not found: {self.backtest_file}")
        urls: List[str] = []
        for line in self.backtest_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            urls.append(stripped)
        if not urls:
            raise ValueError(f"No course URLs found in {self.backtest_file}")
        return urls

    def run(self) -> bool:
        urls = self._load_courses()
        pipeline = ScraperPipeline(config=self.config, session=self.session, verbose=False)
        successes = 0
        for url in urls:
            course_id = self._course_id_from_url(url)
            metadata = CourseMetadata(
                title=course_id.replace("-", " ").title(),
                url=url,
                course_id=course_id,
                description="",
            )
            result = pipeline._process_course(metadata)  # pylint: disable=protected-access
            if result:
                successes += 1
        logger.info("Backtest processed %s/%s courses", successes, len(urls))
        return successes == len(urls)

    @staticmethod
    def _course_id_from_url(url: str) -> str:
        parts = [segment for segment in url.rstrip("/").split("/") if segment]
        return parts[-1] if parts else "course"
