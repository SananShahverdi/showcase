"""End-to-end pipeline for the OCW Smart Scraper."""

from __future__ import annotations

import json
import logging
import shutil
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from urllib.parse import urlparse

import requests

from .book_finder import BookFinder
from .config import RuntimeConfig
from .course import CourseArchive, CourseScraper, CourseSection
from .discovery import CourseDiscoverer, CourseMetadata
from .logging_config import configure_logging
from .pdf import merge_pdfs, write_front_matter_pdf, write_text_pdf
from .transcription import Transcriber
from .utils import RateLimiter

logger = logging.getLogger(__name__)


def course_metadata_from_url(url: str) -> CourseMetadata:
    """Build metadata for a course page such as https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/."""
    parsed = urlparse(url.strip())
    parts = [part for part in parsed.path.split("/") if part]
    if parsed.scheme not in {"http", "https"} or len(parts) < 2 or parts[0] != "courses":
        raise ValueError(f"Not an OCW course URL: {url!r}. Expected https://ocw.mit.edu/courses/<course-id>/")
    course_id = parts[1]
    canonical = f"{parsed.scheme}://{parsed.netloc}/courses/{course_id}/"
    return CourseMetadata(title=course_id.replace("-", " "), url=canonical, course_id=course_id, description="")


@dataclass
class PipelineResult:
    success: bool
    processed_courses: List[CourseArchive]


class ScraperPipeline:
    """Coordinate discovery, scraping, transcription, book finding, and packaging."""

    def __init__(self, *, config: RuntimeConfig, session: Optional[requests.Session] = None, verbose: bool = False) -> None:
        self.config = config
        self.session = session or requests.Session()
        self.verbose = verbose
        configure_logging(config.output_dir, verbose=verbose)

        self.rate_limiter = RateLimiter(self.config.data["scraping"]["calls_per_second"])
        self.course_scraper = CourseScraper(session=self.session, config=self.config.data["scraping"], rate_limiter=self.rate_limiter)
        self.transcriber = Transcriber(config=self.config.data.get("whisper", {}))

    # ------------------------------------------------------------------
    def run(self, search_url: str, *, limit: Optional[int], use_selenium: bool) -> PipelineResult:
        discoverer = CourseDiscoverer(session=self.session, output_dir=self.config.output_dir, config=self.config.data["scraping"])
        courses = discoverer.discover(search_url, limit=limit, use_selenium=use_selenium)

        processed: List[CourseArchive] = []
        with ThreadPoolExecutor(max_workers=self.config.data["processing"]["max_workers"]) as executor:
            futures = {
                executor.submit(self._process_course, course): course
                for course in courses
            }
            for future in as_completed(futures):
                course_meta = futures[future]
                try:
                    archive = future.result()
                except Exception as exc:
                    logger.error("Failed to process %s: %s", course_meta.course_id, exc)
                    continue
                if archive:
                    processed.append(archive)
        return PipelineResult(success=bool(processed), processed_courses=processed)

    def run_courses(self, course_urls: List[str]) -> PipelineResult:
        """Archive specific course pages directly, without a search-page discovery step."""
        processed: List[CourseArchive] = []
        for url in course_urls:
            metadata = course_metadata_from_url(url)
            try:
                archive = self._process_course(metadata)
            except Exception as exc:
                logger.error("Failed to process %s: %s", metadata.course_id, exc)
                continue
            if archive:
                processed.append(archive)
        return PipelineResult(success=bool(processed), processed_courses=processed)

    # ------------------------------------------------------------------
    def _process_course(self, metadata: CourseMetadata) -> Optional[CourseArchive]:
        logger.info("Processing course %s", metadata.course_id)
        archive = self.course_scraper.scrape(metadata, self.config.output_dir)

        if self.config.data["processing"].get("enable_book_search"):
            book_finder = BookFinder(session=self.session, output_dir=archive.base_dir, config=self.config.data["book_search"])
            matches = book_finder.search_and_download(archive.readings)
            logger.info("Book finder located %d matches for %s", len(matches), metadata.course_id)
            if matches:
                books_section = next(
                    (section for section in archive.sections if section.section_key == "books"),
                    None,
                )
                if books_section is None:
                    books_section = CourseSection(
                        name="Supplemental Books",
                        url=metadata.url,
                        section_key="books",
                    )
                    archive.sections.append(books_section)
                for match in matches:
                    archive.books.append(
                        {
                            "title": match.title,
                            "author": match.author,
                            "source": match.source,
                            "url": match.url,
                            "local_path": str(match.local_path) if match.local_path else "",
                        }
                    )
                    if match.local_path and match.local_path.suffix.lower() == ".pdf":
                        if match.local_path not in books_section.materials:
                            books_section.materials.append(match.local_path)

        self._transcribe_media(archive)
        self._create_master_pdf(archive)
        self._write_metadata(archive)
        self._cleanup_course(archive)
        return archive

    # ------------------------------------------------------------------
    def process_course_zip(self, zip_path: Path) -> Optional[CourseArchive]:
        """Build a course archive directly from an OCW download bundle."""

        bundle_path = Path(zip_path)
        if not bundle_path.exists():
            logger.error("Zip bundle not found: %s", zip_path)
            return None

        with tempfile.TemporaryDirectory() as tmp_dir:
            scratch = Path(tmp_dir)
            try:
                with zipfile.ZipFile(bundle_path) as bundle:
                    bundle.extractall(scratch)
            except Exception as exc:
                logger.error("Failed to extract %s: %s", zip_path, exc)
                return None

            metadata = self._load_zip_metadata(scratch, bundle_path)
            if not metadata:
                return None

            destination = self.config.output_dir / metadata["course_id"]
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)
            shutil.copytree(scratch, destination, dirs_exist_ok=True)

            archive = CourseArchive(
                title=metadata["title"],
                course_id=metadata["course_id"],
                url=metadata["url"],
                description=metadata["description"],
                base_dir=destination,
            )

            sections: dict[str, CourseSection] = {}
            generated_pdfs: List[Path] = []

            def _ensure_section(parts: List[str], prefix: str) -> CourseSection:
                key = "/".join(parts) if parts else prefix
                section = sections.get(key)
                if section is None:
                    section = CourseSection(
                        name=" / ".join(part.replace("-", " ").title() for part in parts) or prefix.replace("-", " ").title(),
                        url=archive.url,
                        section_key=key.replace("/", "_") if key else prefix,
                    )
                    sections[key] = section
                    archive.sections.append(section)
                return section

            for html_path in sorted(destination.glob("pages/**/*.html")):
                if html_path.name.lower() != "index.html":
                    continue
                relatives = list(html_path.relative_to(destination).parts[1:-1])
                section = _ensure_section(relatives or ["pages"], "pages")
                section.materials.append(html_path)
                artifacts = self.course_scraper._render_html_derivatives(html_path, html_path.parent)
                if artifacts.pdf:
                    section.materials.append(artifacts.pdf)
                    generated_pdfs.append(artifacts.pdf)
                if artifacts.markdown:
                    section.materials.append(artifacts.markdown)

            for resource_html in sorted(destination.glob("resources/**/*.html")):
                if resource_html.name.lower() != "index.html":
                    continue
                relatives = ["resources"] + list(resource_html.relative_to(destination).parts[1:-1])
                section = _ensure_section(relatives or ["resources"], "resources")
                section.materials.append(resource_html)
                artifacts = self.course_scraper._render_html_derivatives(resource_html, resource_html.parent)
                if artifacts.pdf:
                    section.materials.append(artifacts.pdf)
                    generated_pdfs.append(artifacts.pdf)
                if artifacts.markdown:
                    section.materials.append(artifacts.markdown)

            generated_pdf_set = {path.resolve() for path in generated_pdfs}

            for file_path in destination.rglob("*"):
                if not file_path.is_file():
                    continue
                suffix = file_path.suffix.lower()
                if suffix in {".html", ".htm", ".json", ".xml", ".yaml", ".yml"}:
                    continue
                if suffix == ".pdf" and file_path.resolve() in generated_pdf_set:
                    continue
                archive.attachments.append(file_path)

            archive.readings = self.course_scraper._extract_readings(archive.base_dir / "readings")
            archive.manifest = archive.generate_manifest()
            self._create_master_pdf(archive)
            archive.manifest = archive.generate_manifest()
            self._write_metadata(archive)
            self._cleanup_course(archive)
            logger.info("Processed offline bundle %s -> %s", zip_path, archive.course_id)
            return archive

    # ------------------------------------------------------------------
    def _load_zip_metadata(self, extracted_root: Path, zip_path: Path) -> Optional[dict]:
        index_html = extracted_root / "index.html"
        if not index_html.exists():
            logger.error("Zip bundle %s missing index.html", zip_path)
            return None
        try:
            from bs4 import BeautifulSoup
        except Exception as exc:  # pragma: no cover
            logger.error("BeautifulSoup is required for offline bundle processing: %s", exc)
            return None

        soup = BeautifulSoup(index_html.read_text(encoding="utf-8"), "html.parser")
        canonical_tag = soup.find("link", rel="canonical")
        canonical_url = canonical_tag["href"].strip() if canonical_tag and canonical_tag.get("href") else ""
        if canonical_url:
            course_id = canonical_url.rstrip("/").split("/")[-1]
        else:
            course_id = zip_path.stem.replace(" ", "-")
        data_json = extracted_root / "data.json"
        title = course_id.replace("-", " ").title()
        description = ""
        if data_json.exists():
            try:
                payload = json.loads(data_json.read_text(encoding="utf-8"))
                title = payload.get("course_title") or title
                description = payload.get("course_description") or ""
            except json.JSONDecodeError:
                logger.debug("Failed to parse data.json for %s", zip_path)
        return {
            "title": title,
            "description": description,
            "url": canonical_url or f"https://ocw.mit.edu/courses/{course_id}/",
            "course_id": course_id,
        }

    # ------------------------------------------------------------------
    def _transcribe_media(self, archive: CourseArchive) -> None:
        if not self.config.data["processing"].get("enable_audio_transcription"):
            return
        media_dir = archive.base_dir / "media"
        if not media_dir.exists():
            return
        transcripts_section: Optional[CourseSection] = next(
            (section for section in archive.sections if section.section_key == "transcripts"), None
        )
        supported_media = {".mp3", ".mp4", ".m4a", ".wav"}
        for media_file in sorted(media_dir.glob("*")):
            if media_file.suffix.lower() not in supported_media:
                continue
            try:
                transcript = self.transcriber.transcribe(media_file, output_dir=archive.base_dir)
                if not transcript:
                    continue
                logger.info("Transcribed %s -> %s", media_file.name, transcript.name)
                text = transcript.read_text(encoding="utf-8").strip()
                transcript_entry = {"media": media_file.name, "transcript_path": transcript.name, "chars": len(text)}
                if text:
                    transcript_pdf = transcript.with_suffix(".pdf")
                    try:
                        write_text_pdf(
                            transcript_pdf,
                            [f"Transcript for {media_file.name}", "", text],
                        )
                    except Exception as exc:  # pragma: no cover - report but continue
                        logger.warning("Failed to render transcript PDF for %s: %s", media_file.name, exc)
                    else:
                        transcript_entry["transcript_pdf"] = transcript_pdf.name
                        if transcripts_section is None:
                            transcripts_section = CourseSection(
                                name="Transcripts",
                                url=archive.url,
                                section_key="transcripts",
                            )
                            archive.sections.append(transcripts_section)
                        if transcript_pdf not in transcripts_section.materials:
                            transcripts_section.materials.append(transcript_pdf)
                archive.transcripts.append(transcript_entry)
            except Exception as exc:
                logger.warning("Failed to transcribe %s: %s", media_file.name, exc)

    # ------------------------------------------------------------------
    def _create_master_pdf(self, archive: CourseArchive) -> None:
        manifest = archive.generate_manifest()
        front_matter_path = write_front_matter_pdf(
            manifest,
            archive.base_dir / f"{archive.course_id}_FrontMatter.pdf",
        )
        manifest["front_matter"] = archive.relative_path(front_matter_path)

        ordered_documents: List[Path] = [front_matter_path]
        for section in manifest["sections"]:
            for rel_path in section.get("pdfs", []):
                candidate = Path(rel_path)
                if not candidate.is_absolute():
                    candidate = archive.base_dir / rel_path
                ordered_documents.append(candidate)

        for book in manifest.get("books", []):
            local_path = book.get("local_path")
            if not local_path:
                continue
            candidate = Path(local_path)
            if not candidate.is_absolute():
                candidate = archive.base_dir / local_path
            ordered_documents.append(candidate)

        for transcript in manifest.get("transcripts", []):
            pdf_path = transcript.get("transcript_pdf")
            if not pdf_path:
                continue
            candidate = Path(pdf_path)
            if not candidate.is_absolute():
                candidate = archive.base_dir / pdf_path
            ordered_documents.append(candidate)

        if len(ordered_documents) == 1:
            logger.warning("No PDFs available for %s; skipping master merge", archive.course_id)
            return
        try:
            from pypdf import PdfReader
        except Exception as exc:  # pragma: no cover - configuration issue
            logger.error("pypdf not available; cannot merge PDFs for %s: %s", archive.course_id, exc)
            return

        unique_documents: List[Path] = []
        seen: set[Path] = set()
        for document in ordered_documents:
            resolved = document.resolve()
            if not resolved.exists():
                logger.debug("Skipping missing PDF %s", resolved)
                continue
            if resolved in seen:
                continue
            try:
                PdfReader(str(resolved))  # type: ignore[arg-type]
            except Exception as exc:
                logger.warning("Skipping unreadable PDF %s: %s", resolved.name, exc)
                continue
            unique_documents.append(resolved)
            seen.add(resolved)
        if not unique_documents:
            logger.warning("All PDFs for %s were invalid; skipping master merge", archive.course_id)
            return

        excluded_attachment_exts = {".html", ".htm", ".json", ".xml", ".yaml", ".yml"}
        generated_pdf_set = set(unique_documents)
        attachment_paths: List[Path] = []
        seen_attachment_paths: set[Path] = set()

        for section in archive.sections:
            for material in section.materials:
                resolved = material.resolve()
                if not resolved.exists():
                    continue
                suffix = resolved.suffix.lower()
                if suffix in excluded_attachment_exts:
                    continue
                if suffix == ".pdf" and resolved in generated_pdf_set:
                    continue
                if resolved in seen_attachment_paths:
                    continue
                seen_attachment_paths.add(resolved)
                attachment_paths.append(resolved)

        for extra in archive.attachments:
            resolved = extra.resolve()
            if not resolved.exists():
                continue
            suffix = resolved.suffix.lower()
            if suffix in excluded_attachment_exts:
                continue
            if suffix == ".pdf" and resolved in generated_pdf_set:
                continue
            if resolved in seen_attachment_paths:
                continue
            seen_attachment_paths.add(resolved)
            attachment_paths.append(resolved)

        excluded_exact = {".keep", "favicon.ico", "robots.txt"}
        excluded_prefixes = ("static_shared/",)
        excluded_suffixes = {".ico", ".js", ".css", ".map"}

        attachment_payload: List[tuple[str, Path]] = []
        for attachment in attachment_paths:
            attachment_name = archive.relative_path(attachment)
            lower_name = attachment_name.lower()
            if lower_name in excluded_exact:
                continue
            if any(lower_name.startswith(prefix) for prefix in excluded_prefixes):
                continue
            if any(lower_name.endswith(suffix) for suffix in excluded_suffixes):
                continue
            attachment_payload.append((attachment_name, attachment))

        max_master_mb = self.config.data["processing"].get("max_master_pdf_mb")
        limit_bytes: Optional[int] = None
        if isinstance(max_master_mb, (int, float)) and max_master_mb > 0:
            limit_bytes = int(max_master_mb * 1024 * 1024)

        chunks: List[List[Path]] = []
        current_chunk: List[Path] = []
        current_size = 0
        for document in unique_documents:
            doc_size = document.stat().st_size if document.exists() else 0
            if limit_bytes and current_chunk and current_size + doc_size > limit_bytes:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            current_chunk.append(document)
            current_size += doc_size
            if limit_bytes and doc_size > limit_bytes:
                logger.warning(
                    "Single PDF %s (%.2f MB) exceeds master limit %.2f MB",
                    document.name,
                    doc_size / (1024 * 1024),
                    max_master_mb,
                )
        if current_chunk:
            chunks.append(current_chunk)
        if not chunks:
            logger.warning("No PDF chunks prepared for %s", archive.course_id)
            return

        archive.master_files = []
        for index, chunk in enumerate(chunks, start=1):
            if not chunk:
                continue
            output_name = (
                f"{archive.course_id}_Complete.pdf"
                if len(chunks) == 1
                else f"{archive.course_id}_Complete_part{index:02d}.pdf"
            )
            master_path = archive.base_dir / output_name
            try:
                merge_pdfs(
                    chunk,
                    output_path=master_path,
                    attachments=attachment_payload if index == 1 else None,
                )
            except Exception as exc:
                logger.error("Master PDF merge failed for %s (%s): %s", archive.course_id, output_name, exc)
                if master_path.exists():
                    master_path.unlink(missing_ok=True)
                continue
            archive.master_files.append(master_path)
            if limit_bytes:
                size_mb = master_path.stat().st_size / (1024 * 1024)
                if size_mb > max_master_mb:
                    logger.warning(
                        "Master PDF %s is %.2f MB, exceeding %.2f MB limit",
                        master_path.name,
                        size_mb,
                        max_master_mb,
                    )
            logger.info(
                "Created master PDF %s (%d source PDFs)",
                master_path.name,
                len(chunk),
            )

    # ------------------------------------------------------------------
    def _write_metadata(self, archive: CourseArchive) -> None:
        if not self.config.data["processing"].get("keep_section_files", True):
            return
        manifest = archive.manifest or archive.generate_manifest()
        metadata = {
            "course": archive.to_dict(),
            "manifest": manifest,
        }
        metadata_path = archive.base_dir / "course.json"
        metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

    # ------------------------------------------------------------------
    def _cleanup_course(self, archive: CourseArchive) -> None:
        keep_files = self.config.data["processing"].get("keep_section_files", True)
        if keep_files:
            return
        master_candidates = archive.master_files or list(archive.base_dir.glob(f"{archive.course_id}_Complete*.pdf"))
        if not master_candidates:
            logger.debug("No master PDF for %s; retaining section files", archive.course_id)
            return

        master_paths = {path.resolve() for path in master_candidates if path.exists()}
        for entry in archive.base_dir.iterdir():
            if entry.resolve() in master_paths:
                continue
            if entry.is_dir():
                shutil.rmtree(entry, ignore_errors=True)
            else:
                entry.unlink(missing_ok=True)
