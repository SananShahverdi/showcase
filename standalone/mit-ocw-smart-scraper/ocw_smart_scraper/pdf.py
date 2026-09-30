"""PDF helpers for the OCW Smart Scraper."""

from __future__ import annotations

import io
import logging
import textwrap
from pathlib import Path
from typing import Sequence

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


def write_text_pdf(output_path: Path, sections: Sequence[str]) -> Path:
    """Render textual sections into a simple multi-page PDF."""

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    _, height = letter
    left_margin = 40
    top_margin = 60
    bottom_margin = 60
    line_height = 14

    def start_page() -> tuple[float, float]:
        pdf.setFont("Helvetica", 11)
        return left_margin, height - top_margin

    x, y = start_page()

    def new_page() -> tuple[float, float]:
        pdf.showPage()
        return start_page()

    def ensure_space(lines: int = 1) -> None:
        nonlocal x, y
        required = lines * line_height
        if y - required < bottom_margin:
            x, y = new_page()

    for section in sections:
        lines = section.splitlines() or [""]
        for raw_line in lines:
            wrapped = textwrap.wrap(raw_line, width=95) or [""]
            for idx, line in enumerate(wrapped):
                ensure_space()
                pdf.drawString(x, y, line)
                y -= line_height
            # Blank line between wrapped paragraphs if the original had none
            if raw_line.strip():
                continue
            ensure_space()
            y -= line_height
        # Extra whitespace between top-level sections
        ensure_space(lines=2)
        y -= 2 * line_height

    pdf.save()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buffer.getvalue())
    return output_path


def write_front_matter_pdf(manifest: dict, output_path: Path) -> Path:
    """Create a structured front matter PDF (cover + table of contents)."""

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    left_margin = 50
    top_margin = 70
    bottom_margin = 60
    line_height = 16

    def start_page() -> tuple[float, float]:
        pdf.setFont("Helvetica", 11)
        return left_margin, height - top_margin

    x, y = start_page()

    def new_page() -> tuple[float, float]:
        pdf.showPage()
        return start_page()

    def ensure_space(lines: int = 1) -> None:
        nonlocal x, y
        required = lines * line_height
        if y - required < bottom_margin:
            x, y = new_page()

    def write_wrapped(text: str, *, prefix: str = "", width_chars: int = 92, indent: int = 0) -> None:
        nonlocal y
        if not text:
            return
        lines = textwrap.wrap(text, width=width_chars) or [text]
        for idx, line in enumerate(lines):
            ensure_space()
            draw_x = x + indent
            pdf.drawString(draw_x, y, f"{prefix if idx == 0 else ''}{line}")
            y -= line_height

    def heading(text: str, font_size: int = 14, spacing: int = 2) -> None:
        nonlocal y
        ensure_space(spacing)
        pdf.setFont("Helvetica-Bold", font_size)
        pdf.drawString(x, y, text)
        y -= line_height
        pdf.setFont("Helvetica", 11)

    # Cover
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(x, y, manifest.get("title", "MIT OpenCourseWare Course"))
    y -= line_height * 2
    pdf.setFont("Helvetica", 12)
    pdf.drawString(x, y, f"Course ID: {manifest.get('course_id', 'n/a')}")
    y -= line_height
    pdf.drawString(x, y, f"URL: {manifest.get('url', 'n/a')}")
    y -= line_height * 2

    description = manifest.get("description") or ""
    if description:
        heading("Overview", font_size=14, spacing=1)
        write_wrapped(description, width_chars=92)

    # Table of Contents
    sections = manifest.get("sections", [])
    heading("Table of Contents", font_size=14, spacing=2)
    if not sections:
        write_wrapped("No sections discovered.")
    else:
        for index, section in enumerate(sections, start=1):
            label = f"{index}. {section.get('name') or section.get('section_key', 'Section')}"
            details = []
            pdf_count = section.get("pdf_count")
            material_count = section.get("material_count")
            if pdf_count:
                details.append(f"{pdf_count} PDF{'s' if pdf_count != 1 else ''}")
            if material_count and material_count != pdf_count:
                details.append(f"{material_count} files")
            if details:
                label += f" ({', '.join(details)})"
            write_wrapped(label, width_chars=92)

    # Media / transcripts summary
    transcripts = manifest.get("transcripts", [])
    heading("Transcripts & Media", font_size=14, spacing=2)
    if transcripts:
        write_wrapped(f"Total transcripts: {len(transcripts)}")
        for entry in transcripts[:20]:
            media_name = entry.get("media", "media")
            transcript_path = entry.get("transcript_path", "")
            pdf_path = entry.get("transcript_pdf")
            snippet = f"- {media_name}"
            if pdf_path:
                snippet += f" (PDF: {pdf_path})"
            elif transcript_path:
                snippet += f" (Text: {transcript_path})"
            write_wrapped(snippet, indent=12, width_chars=86)
        if len(transcripts) > 20:
            write_wrapped(f"...and {len(transcripts) - 20} more transcripts.", indent=12)
    else:
        write_wrapped("No transcripts available.", indent=0)

    # Books summary
    books = manifest.get("books", [])
    heading("Supplemental Books", font_size=14, spacing=2)
    if books:
        write_wrapped(f"Books located: {len(books)}")
        for entry in books[:20]:
            title = entry.get("title", "Book")
            author = entry.get("author")
            path = entry.get("local_path")
            desc = f"- {title}"
            if author:
                desc += f" — {author}"
            if path:
                desc += f" (PDF: {path})"
            write_wrapped(desc, indent=12, width_chars=86)
        if len(books) > 20:
            write_wrapped(f"...and {len(books) - 20} more titles.", indent=12)
    else:
        write_wrapped("No supplemental books were downloaded.", indent=0)

    # Media assets summary
    media_assets = manifest.get("media_assets", [])
    heading("Media Assets", font_size=14, spacing=2)
    if media_assets:
        write_wrapped(f"Detected media files: {len(media_assets)}")
        for entry in media_assets[:20]:
            write_wrapped(f"- {entry.get('name')} ({entry.get('path')})", indent=12, width_chars=86)
        if len(media_assets) > 20:
            write_wrapped(f"...and {len(media_assets) - 20} more media assets.", indent=12)
    else:
        write_wrapped("No audio or video assets detected.", indent=0)

    attachments = manifest.get("attachments", [])
    heading("Embedded Attachments", font_size=14, spacing=2)
    if attachments:
        write_wrapped(f"Total attachments: {len(attachments)}")
        for entry in attachments[:20]:
            name = entry.get("name") or entry.get("path")
            kind = entry.get("kind", "")
            size_bytes = entry.get("size_bytes")
            detail = f"- {name}"
            if kind:
                detail += f" [{kind}]"
            if size_bytes:
                detail += f" ({size_bytes / (1024 * 1024):.2f} MB)"
            write_wrapped(detail, indent=12, width_chars=86)
        if len(attachments) > 20:
            write_wrapped(f"...and {len(attachments) - 20} more attachments.", indent=12)
    else:
        write_wrapped("No additional attachments embedded.", indent=0)

    pdf.save()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(buffer.getvalue())
    return output_path


def merge_pdfs(
    documents: Sequence[Path],
    *,
    output_path: Path,
    attachments: Sequence[tuple[str, Path]] | None = None,
) -> Path:
    """Merge multiple PDFs into a single master document with optional attachments."""
    try:
        from pypdf import PdfReader, PdfWriter
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pypdf not installed; cannot merge PDFs") from exc

    writer = PdfWriter()  # type: ignore[call-arg]
    for document in documents:
        reader = PdfReader(str(document))  # type: ignore[arg-type]
        for page in reader.pages:
            writer.add_page(page)
    if attachments:
        for name, path in attachments:
            attachment_path = Path(path)
            if not attachment_path.exists():
                logger.debug("Skipping missing attachment %s", attachment_path)
                continue
            try:
                writer.add_attachment(name, attachment_path.read_bytes())
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to embed attachment %s: %s", name, exc)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        writer.write(handle)
    return output_path
