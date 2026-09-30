"""Search for open-access books referenced in course materials."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class BookMatch:
    title: str
    author: str
    source: str
    url: str
    score: float
    local_path: Optional[Path] = None


class BookFinder:
    """Locate open-access versions of textbooks referenced in a course."""

    def __init__(self, *, session: Optional[requests.Session] = None, output_dir: Path, config: Dict[str, any]) -> None:
        self.session = session or requests.Session()
        self.output_dir = output_dir
        self.config = config

    def search_and_download(self, reading_list: Iterable[Dict[str, str]]) -> List[BookMatch]:
        matches: List[BookMatch] = []
        not_found: List[str] = []
        for entry in reading_list:
            title = entry.get("title", "").strip()
            author = entry.get("author", "").strip()
            if not title:
                continue
            match = self._query_providers(title=title, author=author)
            if match:
                matches.append(match)
                try:
                    match.local_path = self._download(match)
                except Exception as exc:
                    logger.warning("Failed to download %s: %s", match.url, exc)
                    not_found.append(f"{title} — download failed")
                else:
                    if not match.local_path:
                        not_found.append(f"{title} — skipped (size limit)")
            else:
                not_found.append(f"{title} — {author}")

        if not_found:
            (self.output_dir / "_Books_Not_Found.txt").write_text("\n".join(not_found), encoding="utf-8")
        return matches

    # ------------------------------------------------------------------
    def _query_providers(self, *, title: str, author: str) -> Optional[BookMatch]:
        providers = self.config.get("providers", ["open_library", "internet_archive", "gutenberg"])
        for provider in providers:
            if provider == "open_library":
                match = self._query_open_library(title=title, author=author)
            elif provider == "internet_archive":
                match = self._query_internet_archive(title=title, author=author)
            elif provider == "gutenberg":
                match = self._query_gutenberg(title=title, author=author)
            else:  # pragma: no cover
                logger.warning("Unknown book provider %s", provider)
                continue
            if match:
                return match
        return None

    # ------------------------------------------------------------------
    def _query_open_library(self, *, title: str, author: str) -> Optional[BookMatch]:
        params = {"title": title, "author": author, "limit": 1}
        response = self.session.get("https://openlibrary.org/search.json", params=params, timeout=self.config.get("timeout", 20))
        response.raise_for_status()
        data = response.json()
        docs = data.get("docs", [])
        if not docs:
            return None
        doc = docs[0]
        olid = doc.get("key")
        if not olid:
            return None
        url = f"https://openlibrary.org{olid}"
        score = doc.get("score", 0)
        return BookMatch(title=doc.get("title", title), author=", ".join(doc.get("author_name", [])[:2]), source="open_library", url=url, score=score)

    # ------------------------------------------------------------------
    def _query_internet_archive(self, *, title: str, author: str) -> Optional[BookMatch]:
        params = {"q": f'title:("{title}") AND creator:("{author}")', "output": "json", "rows": 1}
        response = self.session.get("https://archive.org/advancedsearch.php", params=params, timeout=self.config.get("timeout", 20))
        response.raise_for_status()
        data = response.json()
        docs = data.get("response", {}).get("docs", [])
        if not docs:
            return None
        doc = docs[0]
        identifier = doc.get("identifier")
        if not identifier:
            return None
        url = f"https://archive.org/details/{identifier}"
        return BookMatch(title=doc.get("title", title), author=doc.get("creator", ""), source="internet_archive", url=url, score=float(doc.get("score", 0)))

    # ------------------------------------------------------------------
    def _query_gutenberg(self, *, title: str, author: str) -> Optional[BookMatch]:
        params = {"search": title, "format": "json"}
        response = self.session.get("https://gutendex.com/books", params=params, timeout=self.config.get("timeout", 20))
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None
        book = results[0]
        formats = book.get("formats", {})
        pdf_url = formats.get("application/pdf") or next((url for mime, url in formats.items() if mime.endswith("pdf")), None)
        if not pdf_url:
            return None
        authors = ", ".join(person.get("name", "") for person in book.get("authors", []) if person.get("name"))
        return BookMatch(title=book.get("title", title), author=authors, source="gutenberg", url=pdf_url, score=float(book.get("download_count", 0)))

    # ------------------------------------------------------------------
    def _download(self, match: BookMatch) -> Optional[Path]:
        filename = f"{match.title.replace(' ', '_')}.pdf"
        target = self.output_dir / "books" / filename
        target.parent.mkdir(parents=True, exist_ok=True)

        response = self.session.get(match.url, timeout=self.config.get("timeout", 20), stream=True)
        response.raise_for_status()

        max_download_mb = self.config.get("max_download_size_mb")
        max_bytes: Optional[int] = None
        if isinstance(max_download_mb, (int, float)) and max_download_mb > 0:
            max_bytes = int(max_download_mb * 1024 * 1024)
        if max_bytes:
            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > max_bytes:
                        logger.warning(
                            "Skipping book download %s (%s MB exceeds %.2f MB limit)",
                            match.title,
                            int(content_length) / (1024 * 1024),
                            max_download_mb,
                        )
                        return None
                except ValueError:
                    pass

        with target.open("wb") as handle:
            written = 0
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)
                    written += len(chunk)
                    if max_bytes and written > max_bytes:
                        logger.warning(
                            "Aborting book download %s (size exceeded %.2f MB limit)",
                            match.title,
                            max_download_mb,
                        )
                        handle.close()
                        target.unlink(missing_ok=True)
                        return None
        logger.info("Downloaded book %s -> %s", match.title, target)
        return target
