import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from ocw_smart_scraper.course import CourseScraper
from ocw_smart_scraper.discovery import CourseMetadata
from ocw_smart_scraper.utils import RateLimiter


class DummyResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class DummySession(requests.Session):
    def __init__(self, html_map: dict[str, str]) -> None:
        super().__init__()
        self.html_map = html_map

    def get(self, url: str, *args: Any, **kwargs: Any) -> DummyResponse:
        return DummyResponse(self.html_map.get(url, "<html></html>"))


def test_course_scraper_filters_nav(tmp_path: Path) -> None:
    course_url = "https://ocw.mit.edu/courses/8-06-quantum-physics-iii-spring-2018/"
    section_url = f"{course_url}pages/syllabus/"

    course_page = """
    <html>
      <body>
        <nav>
          <a href="/pages/privacy-and-terms-of-use/">Privacy</a>
        </nav>
        <div>
          <a href="/courses/8-06-quantum-physics-iii-spring-2018/pages/syllabus/">Syllabus</a>
        </div>
      </body>
    </html>
    """

    section_page = """
    <html>
      <body>
        <main id="course-content-section">
          <h1>Syllabus</h1>
          <p>Course goals and readings.</p>
        </main>
      </body>
    </html>
    """

    session = DummySession(
        {
            course_url: course_page,
            section_url: section_page,
        }
    )

    scraper = CourseScraper(
        session=session,
        config={"timeout": 10},
        rate_limiter=RateLimiter(100),
    )
    archive = scraper.scrape(
        CourseMetadata(title="Q III", url=course_url, course_id="8-06-quantum-physics-iii-spring-2018", description=""),
        tmp_path,
    )

    assert len(archive.sections) == 1
    section = archive.sections[0]
    assert section.name == "Syllabus"
    assert {path.suffix for path in section.materials} == {".html", ".pdf", ".md"}
    html = next(path for path in section.materials if path.suffix == ".html")
    assert "Course goals" in html.read_text(encoding="utf-8")


def test_course_scraper_collects_media_and_transcripts(tmp_path: Path, monkeypatch) -> None:
    course_url = "https://ocw.mit.edu/courses/test-course/"
    section_url = f"{course_url}pages/lecture-1/"

    course_page = """
    <html>
      <body>
        <a href="/courses/test-course/pages/lecture-1/">Lecture 1</a>
      </body>
    </html>
    """

    section_page = """
    <html>
      <body>
        <main id="course-content-section">
          <h1>Lecture 1</h1>
          <p>Welcome to the course.</p>
          <a href="/courses/test-course/resources/lecture1_notes.pdf">Lecture Notes</a>
          <div class="video-tab-download-popup hidden">
            <a href="https://archive.org/download/TestCourse/video01.mp4">Download video</a>
          </div>
          <audio controls data-downloadlink="https://open-learning-course-data-production.s3.amazonaws.com/test/audio01.mp3">
            <source src="/courses/test-course/resources/audio01.m4a" type="audio/mp4">
          </audio>
          <track kind="captions" src="/courses/test-course/resources/caption_en.vtt" srclang="en" />
        </main>
      </body>
    </html>
    """

    session = DummySession(
        {
            course_url: course_page,
            section_url: section_page,
        }
    )

    downloaded: list[str] = []

    def fake_download(self, url: str, section_dir: Path) -> Path:
        downloaded.append(url)
        parsed = urlparse(url)
        filename = os.path.basename(parsed.path) or "asset.bin"
        target = section_dir / filename
        target.write_text("dummy", encoding="utf-8")
        return target

    monkeypatch.setattr(CourseScraper, "_download_asset", fake_download)

    scraper = CourseScraper(
        session=session,
        config={
            "timeout": 10,
            "allowed_asset_hosts": [
                "archive.org",
                "open-learning-course-data-production.s3.amazonaws.com",
            ],
        },
        rate_limiter=RateLimiter(100),
    )

    archive = scraper.scrape(
        CourseMetadata(title="Test Course", url=course_url, course_id="test-course", description=""),
        tmp_path,
    )

    assert set(downloaded) == {
        "https://ocw.mit.edu/courses/test-course/resources/lecture1_notes.pdf",
        "https://archive.org/download/TestCourse/video01.mp4",
        "https://open-learning-course-data-production.s3.amazonaws.com/test/audio01.mp3",
        "https://ocw.mit.edu/courses/test-course/resources/audio01.m4a",
        "https://ocw.mit.edu/courses/test-course/resources/caption_en.vtt",
    }

    section = archive.sections[0]
    suffixes = {material.suffix for material in section.materials}
    assert ".mp4" in suffixes
    assert ".mp3" in suffixes
    assert ".m4a" in suffixes
    assert ".vtt" in suffixes


def test_course_scraper_with_real_ocw_fixture(tmp_path: Path, monkeypatch) -> None:
    course_url = "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/"
    section_path = "pages/lecture-1-what-is-computation/"
    section_url = f"{course_url}{section_path}"

    course_root_html = f"""
    <html>
      <body>
        <a href="/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/{section_path}">Lecture 1</a>
      </body>
    </html>
    """

    fixture_path = Path("tests/fixtures/ocw/6-0001_lecture-1.main.html")
    section_html = fixture_path.read_text(encoding="utf-8")

    session = DummySession(
        {
            course_url: course_root_html,
            section_url: section_html,
        }
    )

    downloaded: list[str] = []

    def fake_download(self, url: str, section_dir: Path) -> Path:
        downloaded.append(url)
        filename = Path(urlparse(url).path).name or "asset.bin"
        target = section_dir / filename
        target.write_text("fixture", encoding="utf-8")
        return target

    monkeypatch.setattr(CourseScraper, "_download_asset", fake_download)

    scraper = CourseScraper(
        session=session,
        config={
            "timeout": 10,
            "allowed_asset_hosts": [
                "archive.org",
                "ocw.mit.edu",
            ],
        },
        rate_limiter=RateLimiter(100),
    )

    archive = scraper.scrape(
        CourseMetadata(
            title="6.0001 Intro to CS",
            url=course_url,
            course_id="6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016",
            description="",
        ),
        tmp_path,
    )

    expected_assets = {
        "https://archive.org/download/MIT6.0001F16/MIT6_0001F16_Lecture_01_300k.mp4",
        "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/a746f6bc380f5e6d807ffff5f56cd877_nykOeWgQcHM.vtt",
        "https://ocw.mit.edu/courses/6-0001-introduction-to-computer-science-and-programming-in-python-fall-2016/904de062253d2fad3064ab5ca917883d_nykOeWgQcHM.pdf",
    }

    assert expected_assets.issubset(set(downloaded))
    section = archive.sections[0]
    suffixes = {material.suffix for material in section.materials}
    assert ".mp4" in suffixes
    assert ".vtt" in suffixes
    assert ".pdf" in suffixes


def test_course_scraper_follows_video_galleries_to_lecture_pages(tmp_path: Path) -> None:
    course_url = "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/"
    gallery_url = f"{course_url}video_galleries/video-lectures/"
    lecture_url = f"{course_url}resources/lecture-1-the-geometry-of-linear-equations/"

    session = DummySession(
        {
            course_url: '<html><body><a href="/courses/18-06-linear-algebra-spring-2010/video_galleries/video-lectures/">Video Lectures</a></body></html>',
            gallery_url: '<html><body><main><h1>Video Lectures</h1><a href="/courses/18-06-linear-algebra-spring-2010/resources/lecture-1-the-geometry-of-linear-equations/">Lecture 1</a></main></body></html>',
            lecture_url: "<html><body><main><h1>Lecture 1</h1><p>The geometry of linear equations.</p></main></body></html>",
        }
    )
    scraper = CourseScraper(session=session, config={"timeout": 10}, rate_limiter=RateLimiter(100))
    archive = scraper.scrape(
        CourseMetadata(title="Linear Algebra", url=course_url, course_id="18-06-linear-algebra-spring-2010", description=""),
        tmp_path,
    )

    assert [section.url for section in archive.sections] == [gallery_url, lecture_url]
    lecture_html = next(path for path in archive.sections[1].materials if path.suffix == ".html")
    assert "geometry of linear equations" in lecture_html.read_text(encoding="utf-8")
