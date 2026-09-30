"""Course discovery from MIT OCW search pages."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class CourseMetadata:
    title: str
    url: str
    course_id: str
    description: str


class CourseDiscoverer:
    """Discover MIT OCW courses via static parsing or Selenium fallback."""

    COURSE_LINK_RE = re.compile(r"^/courses/[\w\-.\/]+/?$")

    def __init__(
        self,
        *,
        session: Optional[requests.Session] = None,
        output_dir: Optional[Path] = None,
        config: Optional[dict] = None,
    ) -> None:
        self.session = session or requests.Session()
        self.output_dir = Path(output_dir or "MIT_OCW_Courses")
        self.config = config or {}
        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def discover(self, search_url: str, *, limit: Optional[int] = None, use_selenium: bool = True) -> List[CourseMetadata]:
        if use_selenium:
            try:
                return self._discover_with_selenium(search_url, limit=limit)
            except Exception as exc:
                logger.warning("Selenium discovery failed, falling back to static parsing: %s", exc)

        return self._discover_static(search_url, limit=limit)

    # ------------------------------------------------------------------
    def _discover_static(self, search_url: str, *, limit: Optional[int]) -> List[CourseMetadata]:
        response = self.session.get(search_url, timeout=self.config.get("timeout", 30))
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        courses = self._extract_courses(soup, base_url=search_url)
        if limit:
            courses = courses[:limit]

        self._write_discovery_json(search_url, courses)
        logger.info("Discovered %s courses via static parser", len(courses))
        return courses

    # ------------------------------------------------------------------
    def _discover_with_selenium(self, search_url: str, *, limit: Optional[int]) -> List[CourseMetadata]:
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service as ChromeService
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Selenium dependencies missing") from exc

        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")

        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        try:
            driver.get(search_url)
            wait = WebDriverWait(driver, 15)
            scroll_pause = self.config.get("scroll_pause", 1.0)
            max_iters = self.config.get("max_scroll_iterations", 50)
            stable_iters_required = self.config.get("stable_iterations", 3)

            stable_iters = 0
            last_count = 0

            for _ in range(max_iters):
                wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[href^='/courses/']")))
                elements = driver.find_elements(By.CSS_SELECTOR, "a[href^='/courses/']")
                if len(elements) == last_count:
                    stable_iters += 1
                else:
                    stable_iters = 0
                last_count = len(elements)

                if stable_iters >= stable_iters_required:
                    break

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause)

            soup = BeautifulSoup(driver.page_source, "html.parser")
        finally:
            driver.quit()

        courses = self._extract_courses(soup, base_url=search_url)
        if limit:
            courses = courses[:limit]

        self._write_discovery_json(search_url, courses)
        logger.info("Discovered %s courses via Selenium parser", len(courses))
        return courses

    # ------------------------------------------------------------------
    def _extract_courses(self, soup: BeautifulSoup, *, base_url: str) -> List[CourseMetadata]:
        origin = urlparse(base_url)
        courses: List[CourseMetadata] = []
        seen: set[str] = set()
        for anchor in soup.select("a[href^='/courses/']"):
            href = anchor.get("href")
            if not href:
                continue
            parsed_path = urlparse(href).path
            match = self.COURSE_LINK_RE.match(parsed_path)
            if not match:
                continue
            parts = [segment for segment in parsed_path.split("/") if segment]
            if len(parts) != 2:
                continue
            url = urljoin(f"{origin.scheme}://{origin.netloc}", href)
            if url in seen:
                continue
            seen.add(url)
            course_id = url.rstrip("/").split("/")[-1]
            title = anchor.get_text(strip=True) or course_id.replace("-", " ").title()
            description = anchor.find_next("p").get_text(strip=True) if anchor.find_next("p") else ""
            courses.append(CourseMetadata(title=title, url=url, course_id=course_id, description=description))
        courses.sort(key=lambda item: item.title.lower())
        return courses

    # ------------------------------------------------------------------
    def _write_discovery_json(self, search_url: str, courses: Sequence[CourseMetadata]) -> None:
        payload = {
            "search_url": search_url,
            "discovered": [
                {"title": c.title, "url": c.url, "course_id": c.course_id, "description": c.description}
                for c in courses
            ],
        }
        output_path = self.output_dir / "discovered_courses.json"
        output_path.write_text(repr(payload), encoding="utf-8")
        logger.debug("Wrote discovery payload to %s", output_path)
