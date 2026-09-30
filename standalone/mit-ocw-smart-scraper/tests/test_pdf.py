from pathlib import Path

from ocw_smart_scraper.pdf import merge_pdfs, write_text_pdf


def test_write_text_pdf(tmp_path: Path) -> None:
    target = tmp_path / "sample.pdf"
    write_text_pdf(target, ["Hello", "World"])
    assert target.exists()
    assert target.stat().st_size > 0


def test_merge_pdfs(tmp_path: Path) -> None:
    doc1 = write_text_pdf(tmp_path / "a.pdf", ["Doc A"])
    doc2 = write_text_pdf(tmp_path / "b.pdf", ["Doc B"])
    merged = merge_pdfs([doc1, doc2], output_path=tmp_path / "merged.pdf")
    assert merged.exists()
    assert merged.stat().st_size >= doc1.stat().st_size


def test_merge_pdfs_with_attachments(tmp_path: Path) -> None:
    doc = write_text_pdf(tmp_path / "a.pdf", ["Doc A"])
    attachment = tmp_path / "data.bin"
    attachment.write_bytes(b"hello world")
    merged = merge_pdfs(
        [doc],
        output_path=tmp_path / "merged.pdf",
        attachments=[("data.bin", attachment)],
    )
    from pypdf import PdfReader

    reader = PdfReader(str(merged))
    assert "data.bin" in reader.attachments
