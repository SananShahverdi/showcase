import io
from bs4 import BeautifulSoup
import markdown

def parse_pdf(file_bytes: bytes) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        return "\n".join([page.extract_text() for page in reader.pages])
    except ImportError as exc:
        # Never index an error message as if it were document text.
        raise ValueError("PDF parsing requires the pypdf package") from exc

def parse_docx(file_bytes: bytes) -> str:
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    except ImportError as exc:
        raise ValueError("DOCX parsing requires the python-docx package") from exc

def parse_html(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    return soup.get_text(separator="\n", strip=True)

def parse_markdown(md_str: str) -> str:
    html = markdown.markdown(md_str)
    return parse_html(html)

def extract_text(file_bytes: bytes, file_type: str) -> str:
    if file_type == "application/pdf":
        return parse_pdf(file_bytes)
    elif file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/msword"]:
        return parse_docx(file_bytes)
    elif file_type == "text/html":
        return parse_html(file_bytes.decode('utf-8', errors='ignore'))
    elif file_type == "text/markdown":
        return parse_markdown(file_bytes.decode('utf-8', errors='ignore'))
    else:
        return file_bytes.decode('utf-8', errors='ignore')
