from __future__ import annotations

import io

from bs4 import BeautifulSoup
import markdown


class DocumentParseError(ValueError):
    pass


def parse_pdf(file_bytes: bytes) -> str:
    import pypdf

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        if reader.is_encrypted:
            raise DocumentParseError("Encrypted PDFs are not supported")
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
    except DocumentParseError:
        raise
    except Exception as exc:
        raise DocumentParseError(f"PDF parsing failed: {type(exc).__name__}") from exc
    return text


def parse_docx(file_bytes: bytes) -> str:
    import docx

    try:
        document = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    except Exception as exc:
        raise DocumentParseError(f"DOCX parsing failed: {type(exc).__name__}") from exc


def parse_html(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    for unsafe in soup(["script", "style", "noscript"]):
        unsafe.decompose()
    # A space preserves inline emphasis/link boundaries without concatenating words.
    return soup.get_text(separator=" ", strip=True)


def parse_markdown(md_str: str) -> str:
    return parse_html(markdown.markdown(md_str))


def extract_text(file_bytes: bytes, file_type: str, filename: str = "") -> str:
    normalized_type = (file_type or "").split(";", 1)[0].strip().lower()
    lower_filename = filename.lower()
    if normalized_type == "application/pdf" or lower_filename.endswith(".pdf"):
        text = parse_pdf(file_bytes)
    elif normalized_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or lower_filename.endswith(".docx"):
        text = parse_docx(file_bytes)
    elif normalized_type == "text/html" or lower_filename.endswith((".html", ".htm")):
        text = parse_html(file_bytes.decode("utf-8", errors="strict"))
    elif normalized_type in {"text/markdown", "text/x-markdown"} or lower_filename.endswith((".md", ".markdown")):
        text = parse_markdown(file_bytes.decode("utf-8", errors="strict"))
    elif normalized_type in {"text/plain", "application/octet-stream", ""} or lower_filename.endswith(".txt"):
        try:
            text = file_bytes.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            raise DocumentParseError("Text files must be UTF-8 encoded") from exc
    else:
        raise DocumentParseError(f"Unsupported document type: {normalized_type or 'unknown'}")
    cleaned = "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()
    if not cleaned:
        raise DocumentParseError("Document contained no extractable text")
    return cleaned


def parser_name(file_type: str, filename: str = "") -> str:
    lower = filename.lower()
    if file_type == "application/pdf" or lower.endswith(".pdf"):
        return "pypdf"
    if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or lower.endswith(".docx"):
        return "python-docx"
    if file_type == "text/html" or lower.endswith((".html", ".htm")):
        return "beautifulsoup-html"
    if file_type in {"text/markdown", "text/x-markdown"} or lower.endswith((".md", ".markdown")):
        return "markdown-beautifulsoup"
    return "utf8-plain-text"
