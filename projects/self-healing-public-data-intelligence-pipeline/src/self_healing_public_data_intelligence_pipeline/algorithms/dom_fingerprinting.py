import hashlib
import re

def compute_dom_fingerprint(html_content: str) -> str:
    """Computes a structural hash of the DOM (ignoring text/classes for layout changes)."""
    # The ordered tag sequence is deterministic and ignores volatile text values.
    tags = re.findall(r'<\s*([a-zA-Z0-9]+)[^>]*>', html_content)
    tag_string = "".join(tags).lower()
    return hashlib.sha256(tag_string.encode()).hexdigest()

def detect_drift(old_html: str, new_html: str) -> bool:
    """Detects layout changes by comparing structural DOM hashes."""
    return compute_dom_fingerprint(old_html) != compute_dom_fingerprint(new_html)
