from pathlib import Path
from textwrap import dedent

import requests
from ocw_smart_scraper.discovery import CourseDiscoverer


class DummyResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class DummySession(requests.Session):
    def __init__(self, text: str) -> None:
        super().__init__()
        self._text = text

    def get(self, *_, **__):
        return DummyResponse(self._text)


def test_static_discovery(tmp_path: Path) -> None:
    html = dedent(
        """
        <html>
          <body>
            <a href="/courses/physics-101-spring-2020/">Physics 101</a>
            <p>Introductory physics</p>
            <a href="/courses/physics-101-spring-2020/pages/syllabus/">Syllabus</a>
          </body>
        </html>
        """
    )
    session = DummySession(html)
    discoverer = CourseDiscoverer(session=session, output_dir=tmp_path)
    courses = discoverer.discover("https://ocw.mit.edu/search/?d=Physics", limit=None, use_selenium=False)
    assert len(courses) == 1
    assert courses[0].course_id == "physics-101-spring-2020"
