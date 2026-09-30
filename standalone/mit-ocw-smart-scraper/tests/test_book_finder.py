from pathlib import Path
from typing import Any, Dict, Optional

import requests

from ocw_smart_scraper.book_finder import BookFinder


class DummyResponse:
    def __init__(self, json_data: Optional[Dict[str, Any]] = None, content: bytes = b"") -> None:
        self._json = json_data
        self._content = content

    def json(self) -> Dict[str, Any]:
        if self._json is None:
            raise ValueError("No JSON payload")
        return self._json

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 65536):
        yield self._content


class DummySession(requests.Session):
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: Any = None, stream: bool = False):
        if "gutendex.com" in url:
            search = (params or {}).get("search", "")
            if search == "Sample Book":
                return DummyResponse(
                    json_data={
                        "results": [
                            {
                                "title": "Sample Book",
                                "formats": {"application/pdf": "https://example.com/sample.pdf"},
                                "authors": [{"name": "Sample Author"}],
                            }
                        ]
                    }
                )
            return DummyResponse(json_data={"results": []})
        if "example.com/sample.pdf" in url:
            return DummyResponse(content=b"%PDF-1.4 sample")
        return DummyResponse(json_data={"results": []})


def test_book_finder_downloads_and_logs(tmp_path: Path) -> None:
    session = DummySession()
    finder = BookFinder(
        session=session,
        output_dir=tmp_path,
        config={"providers": ["gutenberg"], "timeout": 5},
    )

    matches = finder.search_and_download([{"title": "Sample Book", "author": "Sample Author"}])
    assert matches
    book_dir = tmp_path / "books"
    assert any(path.suffix == ".pdf" for path in book_dir.glob("*.pdf"))

    finder.search_and_download([{"title": "Unknown Book", "author": ""}])
    not_found = tmp_path / "_Books_Not_Found.txt"
    assert not_found.exists()
    assert "Unknown Book" in not_found.read_text(encoding="utf-8")
