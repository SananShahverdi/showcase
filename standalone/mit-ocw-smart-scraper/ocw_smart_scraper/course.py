"""Course domain models and parsing helpers."""

from __future__ import annotations

import logging
import os
import re
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

from .pdf import write_text_pdf

logger = logging.getLogger(__name__)


SECTION_MAP = {
    "lecture": "lecture_notes",
    "notes": "lecture_notes",
    "assignment": "assignments",
    "exam": "exams",
    "project": "projects",
    "reading": "readings",
    "video": "media",
    "audio": "media",
    "transcript": "transcripts",
}


# Course paths that hold crawlable content. Video galleries list lecture
# resource pages, which carry the video, transcript, and caption links.
SECTION_PATH_MARKERS = ("/pages/", "/sections/", "/resources/", "/video_galleries/")


def classify_section(title: str) -> str:
    lower_title = title.lower()
    for keyword, section in SECTION_MAP.items():
        if keyword in lower_title:
            return section
    return "misc"


@dataclass
class CourseSection:
    name: str
    url: str
    section_key: str
    materials: List[Path] = field(default_factory=list)


@dataclass
class RenderedPageArtifacts:
    pdf: Optional[Path] = None
    markdown: Optional[Path] = None


@dataclass
class CourseArchive:
    """Represents the output bundle for a single course."""

    title: str
    course_id: str
    url: str
    description: str
    base_dir: Path
    sections: List[CourseSection] = field(default_factory=list)
    readings: List[Dict[str, str]] = field(default_factory=list)
    transcripts: List[Dict[str, str]] = field(default_factory=list)
    books: List[Dict[str, str]] = field(default_factory=list)
    master_files: List[Path] = field(default_factory=list)
    attachments: List[Path] = field(default_factory=list)
    manifest: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "course_id": self.course_id,
            "url": self.url,
            "description": self.description,
            "sections": [section.name for section in self.sections],
            "readings": self.readings,
            "transcripts": self.transcripts,
            "books": self.books,
            "master_files": [str(path) for path in self.master_files],
            "attachments": [str(path) for path in self.attachments],
        }

    # ------------------------------------------------------------------
    def relative_path(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.base_dir))
        except ValueError:
            return str(path)

    # ------------------------------------------------------------------
    def _summarize_material(self, path: Path) -> Dict[str, Any]:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            kind = "pdf"
        elif suffix in {".html", ".htm"}:
            kind = "html"
        elif suffix in {".mp3", ".mp4", ".m4a", ".wav", ".m4v", ".mov", ".ogg", ".webm", ".flv"}:
            kind = "media"
        elif suffix in {".txt", ".srt", ".vtt", ".md"}:
            kind = "text"
        else:
            kind = "asset"

        exists = path.exists()
        size = path.stat().st_size if exists else None
        record = {
            "name": path.name,
            "path": self.relative_path(path),
            "kind": kind,
            "suffix": suffix.lstrip("."),
            "exists": exists,
            "size_bytes": size,
        }
        return record

    # ------------------------------------------------------------------
    def _normalize_transcripts(self) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for entry in self.transcripts:
            updated = dict(entry)
            transcript_rel = updated.get("transcript_path")
            if transcript_rel:
                transcript_path = Path(transcript_rel)
                if not transcript_path.is_absolute():
                    transcript_path = self.base_dir / transcript_path
                if transcript_path.exists():
                    updated["transcript_path"] = self.relative_path(transcript_path)
            pdf_path = updated.get("transcript_pdf")
            if pdf_path:
                pdf_full = Path(pdf_path)
                if not pdf_full.is_absolute():
                    pdf_full = self.base_dir / pdf_full
                if pdf_full.exists():
                    updated["transcript_pdf"] = self.relative_path(pdf_full)
            normalized.append(updated)
        return normalized

    # ------------------------------------------------------------------
    def _normalize_books(self) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for book in self.books:
            updated = dict(book)
            local_path = updated.get("local_path")
            if local_path:
                book_path = Path(local_path)
                if not book_path.is_absolute():
                    book_path = (self.base_dir / local_path).resolve()
                if book_path.exists():
                    try:
                        updated["local_path"] = self.relative_path(book_path)
                    except ValueError:
                        updated["local_path"] = str(book_path)
                else:
                    updated["local_path"] = str(book_path)
            normalized.append(updated)
        return normalized

    # ------------------------------------------------------------------
    def generate_manifest(self) -> Dict[str, Any]:
        sections_data: List[Dict[str, Any]] = []
        media_entries: List[Dict[str, Any]] = []
        for section in self.sections:
            materials: List[Dict[str, Any]] = []
            pdf_rel_paths: List[str] = []
            for material in section.materials:
                summary = self._summarize_material(material)
                materials.append(summary)
                if summary["kind"] == "pdf" and summary["exists"]:
                    pdf_rel_paths.append(summary["path"])
                if summary["kind"] == "media":
                    media_entries.append(summary)
            sections_data.append(
                {
                    "name": section.name,
                    "section_key": section.section_key,
                    "materials": materials,
                    "pdfs": pdf_rel_paths,
                    "material_count": len(materials),
                    "pdf_count": len(pdf_rel_paths),
                }
            )

        manifest = {
            "title": self.title,
            "course_id": self.course_id,
            "url": self.url,
            "description": self.description,
            "sections": sections_data,
            "transcripts": self._normalize_transcripts(),
            "books": self._normalize_books(),
            "media_assets": media_entries,
            "attachments": [
                self._summarize_material(path) for path in self.attachments if path.exists()
            ],
        }
        self.manifest = manifest
        return manifest


class CourseScraper:
    """Scrape course sections and transform them into course archives."""

    def __init__(self, *, session: Optional[requests.Session] = None, config: Dict[str, Any], rate_limiter=None) -> None:
        self.session = session or requests.Session()
        self.config = config
        self.rate_limiter = rate_limiter

    def scrape(self, metadata, output_dir: Path) -> CourseArchive:
        base_dir = output_dir / metadata.course_id
        base_dir.mkdir(parents=True, exist_ok=True)

        timeout = self.config.get("timeout", 30)
        try:
            landing_response = self.session.get(metadata.url, timeout=timeout)
            landing_response.raise_for_status()
        except requests.RequestException as exc:
            logger.error("Failed to load course landing page %s: %s", metadata.url, exc)
            raise

        final_url = getattr(landing_response, "url", metadata.url)
        archive = CourseArchive(
            title=metadata.title,
            course_id=metadata.course_id,
            url=final_url,
            description=metadata.description,
            base_dir=base_dir,
        )

        if "dspace.mit.edu" in urlparse(final_url).netloc:
            self._scrape_dspace(archive, landing_response, final_url)
        else:
            self._scrape_ocw(archive, final_url)

        archive.readings = self._extract_readings(archive.base_dir / "readings")
        return archive

    # ------------------------------------------------------------------
    def _scrape_ocw(self, archive: CourseArchive, start_url: str) -> None:
        queue = deque(self._enumerate_sections(start_url))
        visited: Set[str] = set()
        section_counter = 0
        downloaded_assets: Set[Path] = set()

        while queue:
            section = queue.popleft()
            if section.url in visited:
                continue
            visited.add(section.url)
            section_counter += 1

            section_dir = archive.base_dir / section.section_key
            section_dir.mkdir(parents=True, exist_ok=True)
            html_content, subpages, assets = self._fetch_section(section.url)
            if html_content:
                html_path = section_dir / f"section_{section_counter}.html"
                html_path.write_text(html_content, encoding="utf-8")
                section.materials.append(html_path)
                artifacts = self._render_html_derivatives(html_path, section_dir)
                if artifacts.pdf and artifacts.pdf not in section.materials:
                    section.materials.append(artifacts.pdf)
                if artifacts.markdown and artifacts.markdown not in section.materials:
                    section.materials.append(artifacts.markdown)
            for asset_url in assets:
                asset_path = self._download_asset(asset_url, section_dir)
                if asset_path and asset_path not in downloaded_assets:
                    section.materials.append(asset_path)
                    downloaded_assets.add(asset_path)
            for sub_url, sub_title in subpages:
                if sub_url in visited:
                    continue
                sub_section_key = classify_section(sub_title or sub_url.split("/")[-1])
                queue.append(CourseSection(name=sub_title or sub_section_key.title(), url=sub_url, section_key=sub_section_key))
            archive.sections.append(section)

    # ------------------------------------------------------------------
    def _scrape_dspace(self, archive: CourseArchive, landing_response: requests.Response, final_url: str) -> None:
        logger.info("Routing %s to DSpace scraper via %s", archive.course_id, final_url)
        section_dir = archive.base_dir / "dspace"
        section_dir.mkdir(parents=True, exist_ok=True)

        html_path = section_dir / "record.html"
        html_path.write_text(landing_response.text, encoding="utf-8")
        dspace_section = CourseSection(name="DSpace Record", url=final_url, section_key="dspace")
        dspace_section.materials.append(html_path)
        artifacts = self._render_html_derivatives(html_path, section_dir)
        if artifacts.pdf:
            dspace_section.materials.append(artifacts.pdf)
        if artifacts.markdown:
            dspace_section.materials.append(artifacts.markdown)
        archive.sections.append(dspace_section)

        soup = BeautifulSoup(landing_response.text, "html.parser")
        api_assets, description = self._extract_dspace_assets_api(final_url)
        if description and not archive.description:
            archive.description = description
        html_assets = self._extract_dspace_assets_html(soup, final_url)

        ordered_urls: Dict[str, None] = {}
        for url in api_assets + html_assets:
            ordered_urls.setdefault(url, None)
        if not ordered_urls:
            logger.warning("No downloadable content detected for %s (DSpace)", archive.course_id)
            return

        sections_by_key: Dict[str, CourseSection] = {}
        for asset_url in ordered_urls.keys():
            asset_path = self._download_asset(asset_url, section_dir)
            if not asset_path:
                continue
            section_key = self._classify_asset(asset_path)
            section = sections_by_key.get(section_key)
            if section is None:
                section = CourseSection(
                    name=section_key.replace("_", " ").title(),
                    url=final_url,
                    section_key=section_key,
                )
                sections_by_key[section_key] = section
                archive.sections.append(section)
            section.materials.append(asset_path)

    # ------------------------------------------------------------------
    def _extract_dspace_assets_api(self, handle_url: str) -> Tuple[List[str], Optional[str]]:
        parsed = urlparse(handle_url)
        path = parsed.path.strip("/")
        if not path.startswith("handle/"):
            return [], None
        handle = path.split("/", 1)[1] if "/" in path else ""
        if not handle:
            return [], None
        api_url = f"{parsed.scheme}://{parsed.netloc}/rest/handle/{handle}?expand=all"
        try:
            response = self.session.get(api_url, timeout=self.config.get("timeout", 30))
            response.raise_for_status()
        except requests.RequestException as exc:
            logger.debug("DSpace API lookup failed for %s: %s", handle, exc)
            return [], None

        try:
            payload = response.json()
        except ValueError as exc:
            logger.debug("DSpace API returned invalid JSON for %s: %s", handle, exc)
            return [], None

        bitstreams: List[Dict[str, Any]] = []
        if isinstance(payload, dict):
            if "bitstreams" in payload:
                bitstreams.extend(payload.get("bitstreams") or [])
            for bundle in payload.get("bundles", []) or []:
                bitstreams.extend(bundle.get("bitstreams") or [])
        asset_urls: List[str] = []
        for entry in bitstreams:
            link = entry.get("retrieveLink") or entry.get("link")
            if not link:
                continue
            absolute = urljoin(f"{parsed.scheme}://{parsed.netloc}", link)
            asset_urls.append(absolute)

        description: Optional[str] = None
        metadata_entries = []
        if isinstance(payload, dict):
            metadata_entries = payload.get("metadata", []) or []
        for item in metadata_entries:
            key = (item.get("key") or "").lower()
            if "description" in key:
                description = item.get("value")
                break

        return asset_urls, description

    # ------------------------------------------------------------------
    @staticmethod
    def _extract_dspace_assets_html(soup: BeautifulSoup, base_url: str) -> List[str]:
        asset_urls: List[str] = []
        for anchor in soup.select("a[href]"):
            href = anchor.get("href")
            if not href:
                continue
            if "bitstream" in href or "download" in href.lower():
                asset_urls.append(urljoin(base_url, href))
        return asset_urls

    # ------------------------------------------------------------------
    @staticmethod
    def _classify_asset(path: Path) -> str:
        ext = path.suffix.lower()
        if ext in {".pdf"}:
            return "readings"
        if ext in {".mp3", ".mp4", ".m4a", ".wav", ".m4v", ".mov", ".ogg", ".webm", ".flv"}:
            return "media"
        if ext in {".txt", ".srt", ".vtt"}:
            return "transcripts"
        if ext in {".zip", ".tar", ".tgz", ".gz"}:
            return "resources"
        if ext in {".ppt", ".pptx"}:
            return "lecture_notes"
        return "misc"

    # ------------------------------------------------------------------
    def _enumerate_sections(self, course_url: str) -> List[CourseSection]:
        response = self.session.get(course_url, timeout=self.config.get("timeout", 30))
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        sections: List[CourseSection] = []
        course_origin = urlparse(course_url)
        course_path_prefix = course_origin.path.rstrip("/") + "/"

        for anchor in soup.select("a[href]"):
            href = anchor.get("href")
            if not href or href.startswith("#"):
                continue
            absolute = urljoin(course_url, href)
            path = urlparse(absolute).path
            if not path.startswith(course_path_prefix):
                continue
            if not any(marker in path for marker in SECTION_PATH_MARKERS):
                continue
            title = anchor.get_text(strip=True)
            section_key = classify_section(title or path.split("/")[-1])
            sections.append(CourseSection(name=title or section_key.title(), url=absolute, section_key=section_key))
        seen = set()
        deduped: List[CourseSection] = []
        for section in sections:
            key = (section.section_key, section.url)
            if key not in seen:
                seen.add(key)
                deduped.append(section)
        return deduped

    # ------------------------------------------------------------------
    def _fetch_section(self, url: str) -> Tuple[Optional[str], List[Tuple[str, str]], List[str]]:
        if self.rate_limiter:
            self.rate_limiter.wait()
        response = self.session.get(url, timeout=self.config.get("timeout", 30))
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        main = soup.select_one("main#course-content-section") or soup.select_one("main") or soup.select_one("article")
        if not main:
            main = soup.body or soup
        html = main.prettify()

        origin = urlparse(url)
        course_root = "/".join(origin.path.rstrip("/").split("/")[:3]) + "/"
        subpage_links: List[Tuple[str, str]] = []
        asset_links: Set[str] = set()
        asset_extensions = {
            ".pdf",
            ".zip",
            ".doc",
            ".docx",
            ".ppt",
            ".pptx",
            ".ps",
            ".tex",
            ".mp3",
            ".mp4",
            ".m4a",
            ".m4v",
            ".mov",
            ".wav",
            ".ogg",
            ".webm",
            ".flv",
            ".srt",
            ".vtt",
        }

        allowed_hosts_config = self.config.get("allowed_asset_hosts", [])
        allowed_hosts: Set[str] = {origin.netloc}
        for host in allowed_hosts_config:
            if isinstance(host, str) and host:
                allowed_hosts.add(host.lower())

        def host_allowed(netloc: str) -> bool:
            if not netloc or netloc == origin.netloc:
                return True
            netloc = netloc.lower()
            if netloc in allowed_hosts:
                return True
            for host in allowed_hosts:
                if host.startswith(".") and netloc.endswith(host):
                    return True
                if host and netloc.endswith(f".{host}"):
                    return True
            return False

        def is_asset_path(parsed: Any) -> bool:
            path = parsed.path.lower()
            if any(path.endswith(ext) for ext in asset_extensions):
                return True
            query_values = []
            if parsed.query:
                query = parse_qs(parsed.query)
                for values in query.values():
                    query_values.extend(values)
            for value in query_values:
                lower_value = value.lower()
                if any(lower_value.endswith(ext) for ext in asset_extensions):
                    return True
            return False

        def consider_asset(href: Optional[str]) -> None:
            if not href:
                return
            absolute = urljoin(url, href)
            parsed = urlparse(absolute)
            if parsed.scheme not in {"http", "https"}:
                return
            if parsed.netloc and not host_allowed(parsed.netloc):
                return
            if is_asset_path(parsed):
                asset_links.add(absolute)

        for anchor in main.select("a[href]"):
            href = anchor.get("href")
            if not href or href.startswith("#"):
                continue
            absolute = urljoin(url, href)
            parsed = urlparse(absolute)
            if is_asset_path(parsed) and host_allowed(parsed.netloc):
                asset_links.add(absolute)
                continue
            if parsed.netloc and parsed.netloc != origin.netloc:
                continue
            path = parsed.path
            if not path.startswith(course_root):
                continue
            if any(marker in path for marker in SECTION_PATH_MARKERS):
                subpage_links.append((absolute, anchor.get_text(strip=True)))

        for tag in main.select("[src]"):
            consider_asset(tag.get("src"))

        for tag in main.find_all():
            for attr_name, attr_value in tag.attrs.items():
                if not isinstance(attr_value, str):
                    continue
                lowered = attr_name.lower()
                if "download" in lowered or "transcript" in lowered or lowered.endswith("url"):
                    consider_asset(attr_value)

        return html, subpage_links, sorted(asset_links)

    # ------------------------------------------------------------------
    def _html_to_pdf(self, html_path: Path, section_dir: Path) -> Optional[Path]:
        artifacts = self._render_html_derivatives(html_path, section_dir)
        return artifacts.pdf

    # ------------------------------------------------------------------
    def _render_html_derivatives(self, html_path: Path, section_dir: Path) -> RenderedPageArtifacts:
        markdown, sections = self._extract_markdown_and_sections(html_path)
        if not sections:
            return RenderedPageArtifacts()

        pdf_path = section_dir / f"{html_path.stem}.pdf"
        write_text_pdf(pdf_path, sections)

        markdown_path: Optional[Path] = None
        if markdown:
            markdown_path = section_dir / f"{html_path.stem}.md"
            markdown_output = markdown if markdown.endswith("\n") else f"{markdown}\n"
            markdown_path.write_text(markdown_output, encoding="utf-8")

        return RenderedPageArtifacts(pdf=pdf_path, markdown=markdown_path)

    # ------------------------------------------------------------------
    def _extract_markdown_and_sections(self, html_path: Path) -> Tuple[Optional[str], List[str]]:
        try:
            text = html_path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.debug("Failed to read %s: %s", html_path, exc)
            return None, []

        soup = BeautifulSoup(text, "html.parser")
        content_root = self._select_content_root(soup)
        if content_root is None:
            return None, []
        self._prune_noncontent_nodes(content_root)

        inner_html = content_root.decode_contents().strip()
        markdown: Optional[str] = None
        sections: List[str] = []

        if inner_html:
            markdown = self._to_markdown(inner_html)
            if markdown:
                sections = self._markdown_to_text_sections(markdown)

        if not sections:
            fallback_text = content_root.get_text("\n")
            sections = self._text_blocks_from_plaintext(fallback_text)

        return markdown, sections

    # ------------------------------------------------------------------
    @staticmethod
    def _select_content_root(soup: BeautifulSoup) -> Optional[Any]:
        selectors = [
            "main#course-content-section",
            "main[role=main]",
            "main.course-main",
            "article#course-content",
            "article",
            "[role=main]",
        ]
        for selector in selectors:
            node = soup.select_one(selector)
            if node:
                return node
        if soup.body:
            return soup.body
        return soup

    # ------------------------------------------------------------------
    @staticmethod
    def _prune_noncontent_nodes(root: Any) -> None:
        discard_tags = ["nav", "header", "footer", "aside", "script", "style", "noscript", "form"]
        for tag in root.find_all(discard_tags):
            tag.decompose()

        class_keywords = ("breadcrumb", "nav", "sidebar", "footer", "toolbar", "menu", "related", "banner")
        for element in list(root.find_all(True)):
            if not isinstance(element, Tag) or not isinstance(getattr(element, "attrs", None), dict):
                continue
            classes = element.get("class")
            if not classes:
                continue
            normalized = " ".join(classes).lower()
            if any(keyword in normalized for keyword in class_keywords):
                element.decompose()

    # ------------------------------------------------------------------
    @staticmethod
    def _to_markdown(inner_html: str) -> Optional[str]:
        markdown: Optional[str] = None
        try:
            from markdownify import markdownify as to_markdown
        except Exception:
            markdown = CourseScraper._fallback_markdown(inner_html)
        else:
            markdown = to_markdown(inner_html, heading_style="ATX")

        if not markdown:
            return None

        normalized = CourseScraper._normalize_markdown(markdown)
        return normalized if normalized.strip() else None

    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_markdown(markdown: str) -> str:
        lines = markdown.replace("\r\n", "\n").split("\n")
        normalized: List[str] = []
        previous_blank = True
        for line in lines:
            stripped = line.rstrip()
            if stripped:
                normalized.append(stripped)
                previous_blank = False
            else:
                if not previous_blank:
                    normalized.append("")
                previous_blank = True
        while normalized and not normalized[-1]:
            normalized.pop()
        return "\n".join(normalized)

    # ------------------------------------------------------------------
    @staticmethod
    def _fallback_markdown(inner_html: str) -> Optional[str]:
        soup = BeautifulSoup(inner_html, "html.parser")
        text = soup.get_text("\n")
        lines = [line.strip() for line in text.splitlines()]
        paragraphs: List[str] = []
        current: List[str] = []
        for line in lines:
            if not line:
                if current:
                    paragraphs.append(" ".join(current))
                    current = []
                continue
            current.append(line)
        if current:
            paragraphs.append(" ".join(current))
        if not paragraphs:
            return None
        return "\n\n".join(paragraphs)

    # ------------------------------------------------------------------
    @staticmethod
    def _markdown_to_text_sections(markdown: str) -> List[str]:
        lines = markdown.split("\n")
        sections: List[str] = []
        current: List[str] = []
        table_block: List[str] = []

        def flush_current() -> None:
            nonlocal current
            if not current:
                return
            if any(line.startswith("• ") for line in current):
                sections.append("\n".join(current))
            else:
                sections.append(" ".join(current))
            current = []

        def flush_table() -> None:
            nonlocal table_block
            if table_block:
                sections.append("\n".join(table_block))
                table_block = []

        for raw_line in lines:
            stripped = raw_line.strip()
            if not stripped:
                flush_current()
                flush_table()
                continue

            if stripped.startswith("|"):
                flush_current()
                table_block.append(stripped)
                continue

            flush_table()
            normalized = CourseScraper._normalize_markdown_line(stripped)
            if not normalized:
                continue
            current.append(normalized)

        flush_current()
        flush_table()
        return [section for section in sections if section.strip()]

    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_markdown_line(line: str) -> str:
        if line.startswith("#"):
            line = line.lstrip("#").strip()
        bullet_match = re.match(r"^(\*|\-|\+)\s+(.*)", line)
        if bullet_match:
            content = bullet_match.group(2).strip()
            return f"• {content}" if content else ""
        ordered_match = re.match(r"^(\d+)[.)]\s+(.*)", line)
        if ordered_match:
            content = ordered_match.group(2).strip()
            return f"• {content}" if content else ""

        line = re.sub(r"\[(.*?)\]\((.*?)\)", lambda m: f"{m.group(1)} ({m.group(2)})", line)
        line = line.replace("`", "")
        line = line.replace("**", "")
        line = line.replace("__", "")
        return line.strip()

    # ------------------------------------------------------------------
    @staticmethod
    def _text_blocks_from_plaintext(text: str) -> List[str]:
        lines = [line.strip() for line in text.splitlines()]
        sections: List[str] = []
        current: List[str] = []
        for line in lines:
            if not line:
                if current:
                    sections.append(" ".join(current))
                    current = []
                continue
            current.append(line)
        if current:
            sections.append(" ".join(current))
        return [section for section in sections if section.strip()]

    # ------------------------------------------------------------------
    def _download_asset(self, url: str, section_dir: Path) -> Optional[Path]:
        if self.rate_limiter:
            self.rate_limiter.wait()
        timeout = self.config.get("asset_timeout", self.config.get("timeout", 30))
        retries = int(self.config.get("max_retries", 3))
        base_backoff = float(self.config.get("retry_backoff_seconds", 2.0))

        response: Optional[requests.Response] = None
        for attempt in range(retries + 1):
            try:
                response = self.session.get(url, timeout=(10, timeout), stream=True)
            except requests.RequestException as exc:
                if attempt == retries:
                    logger.warning("Failed to download asset %s: %s", url, exc)
                    return None
                wait = base_backoff * (2 ** attempt)
                logger.debug("Retrying asset %s after error (%s); sleeping %.1fs", url, exc, wait)
                time.sleep(wait)
                continue

            if response.status_code == 429 or 500 <= response.status_code < 600:
                response.close()
                if attempt == retries:
                    logger.warning("Asset %s returned %s; giving up after %d attempts", url, response.status_code, retries + 1)
                    return None
                wait = base_backoff * (2 ** attempt)
                logger.info("Asset %s returned %s; retrying in %.1fs", url, response.status_code, wait)
                time.sleep(wait)
                continue

            try:
                response.raise_for_status()
            except requests.RequestException as exc:
                response.close()
                if attempt == retries:
                    logger.warning("Failed to download asset %s: %s", url, exc)
                    return None
                wait = base_backoff * (2 ** attempt)
                logger.debug("Retrying asset %s after HTTP error (%s); sleeping %.1fs", url, exc, wait)
                time.sleep(wait)
                continue
            break
        else:
            return None

        if response is None:
            return None

        filename = os.path.basename(urlparse(url).path)
        if not filename:
            response.close()
            return None
        target = section_dir / filename
        max_asset_mb = self.config.get("max_asset_size_mb")
        max_bytes: Optional[int] = None
        if isinstance(max_asset_mb, (int, float)) and max_asset_mb > 0:
            max_bytes = int(max_asset_mb * 1024 * 1024)
        if max_bytes:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > max_bytes:
                        logger.warning(
                            "Skipping asset %s (%.2f MB exceeds %.2f MB limit)",
                            url,
                            int(content_length) / (1024 * 1024),
                            max_asset_mb,
                        )
                        response.close()
                        return None
                except ValueError:
                    pass
        with open(target, "wb") as handle:
            written = 0
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)
                    written += len(chunk)
                    if max_bytes and written > max_bytes:
                        logger.warning(
                            "Aborting asset %s (download exceeded %.2f MB limit)",
                            url,
                            max_asset_mb,
                        )
                        handle.close()
                        target.unlink(missing_ok=True)
                        response.close()
                        return None
        response.close()
        return target

    # ------------------------------------------------------------------
    def _extract_readings(self, readings_dir: Path) -> List[Dict[str, str]]:
        readings: List[Dict[str, str]] = []
        if not readings_dir.exists():
            return readings
        for text_file in readings_dir.glob("*.txt"):
            for line in text_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                readings.append({"title": line, "author": ""})
        return readings
