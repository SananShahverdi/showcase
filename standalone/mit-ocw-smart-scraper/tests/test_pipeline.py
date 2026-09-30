import json
import zipfile
from pathlib import Path

from ocw_smart_scraper.config import load_config
from ocw_smart_scraper.course import CourseArchive, CourseSection
from ocw_smart_scraper.pipeline import ScraperPipeline


def test_cleanup_keeps_only_master(tmp_path: Path) -> None:
    overrides = [
        f"output.base_directory={tmp_path}",
        "processing.keep_section_files=false",
    ]
    config = load_config(config_path=None, overrides=overrides)
    pipeline = ScraperPipeline(config=config, verbose=False)

    course_dir = config.output_dir / "test-course"
    course_dir.mkdir(parents=True, exist_ok=True)
    section_dir = course_dir / "misc"
    section_dir.mkdir()
    html_file = section_dir / "section_1.html"
    pdf_file = section_dir / "section_1.pdf"
    html_file.write_text("<p>Content</p>", encoding="utf-8")
    pdf_file.write_text("PDF", encoding="utf-8")

    master_pdf = course_dir / "test-course_Complete.pdf"
    master_pdf.write_text("MASTER", encoding="utf-8")
    metadata = course_dir / "course.json"
    metadata.write_text("{}", encoding="utf-8")

    archive = CourseArchive(
        title="Test",
        course_id="test-course",
        url="https://example.com",
        description="",
        base_dir=course_dir,
    )
    section = CourseSection(name="Test Section", url="https://example.com", section_key="misc")
    section.materials = [html_file, pdf_file]
    archive.sections.append(section)

    pipeline._cleanup_course(archive)

    remaining = {p.name for p in course_dir.iterdir()}
    assert remaining == {master_pdf.name}


def test_process_course_zip_embeds_attachments(tmp_path: Path) -> None:
    bundle_root = tmp_path / "bundle"
    (bundle_root / "pages/lecture-1").mkdir(parents=True)
    (bundle_root / "static_resources").mkdir()
    (bundle_root / "static_shared/js").mkdir(parents=True)

    (bundle_root / "index.html").write_text(
        """
        <html>
          <head>
            <link rel="canonical" href="https://ocw.mit.edu/courses/sample-course/">
            <title>Sample Course</title>
          </head>
          <body>Offline bundle</body>
        </html>
        """,
        encoding="utf-8",
    )

    (bundle_root / "data.json").write_text(
        json.dumps({"course_title": "Sample Course", "course_description": "Offline test"}, indent=2),
        encoding="utf-8",
    )

    (bundle_root / "pages/lecture-1/index.html").write_text(
        """
        <html>
          <body class="has-nav">
            <header>
              <nav class="course-navigation">Navigation should disappear</nav>
            </header>
            <main id="course-content-section">
              <h1>Lecture 1</h1>
              <p>Hello from offline content.</p>
              <ul>
                <li>Topic A</li>
                <li>Topic B</li>
              </ul>
              <table>
                <thead>
                  <tr><th>Col1</th><th>Col2</th></tr>
                </thead>
                <tbody>
                  <tr><td>A</td><td>B</td></tr>
                </tbody>
              </table>
            </main>
          </body>
        </html>
        """,
        encoding="utf-8",
    )

    (bundle_root / "static_resources/audio.mp3").write_bytes(b"FAKEAUDIO")
    (bundle_root / "static_resources/example.py").write_text("print('hello')", encoding="utf-8")
    (bundle_root / "static_shared/js/app.js").write_text("console.log('skip');", encoding="utf-8")

    zip_path = tmp_path / "sample-course.zip"
    with zipfile.ZipFile(zip_path, "w") as bundle:
        for file_path in bundle_root.rglob("*"):
            bundle.write(file_path, file_path.relative_to(bundle_root))

    overrides = [
        f"output.base_directory={tmp_path / 'output'}",
    ]
    config = load_config(config_path=None, overrides=overrides)
    pipeline = ScraperPipeline(config=config, verbose=False)

    archive = pipeline.process_course_zip(zip_path)
    assert archive is not None
    master_files = list(archive.base_dir.glob(f"{archive.course_id}_Complete*.pdf"))
    assert master_files, "Master PDF was not generated"

    lecture_section = None
    for section in archive.sections:
        for material in section.materials:
            if material.name == "index.html" and material.parent.name == "lecture-1":
                lecture_section = section
                break
        if lecture_section:
            break
    assert lecture_section is not None
    markdown_materials = [path for path in lecture_section.materials if path.suffix == ".md"]
    assert markdown_materials, "Markdown derivative was not generated"
    markdown_text = markdown_materials[0].read_text(encoding="utf-8")
    assert "Navigation should disappear" not in markdown_text
    assert "Hello from offline content." in markdown_text
    assert "Topic A" in markdown_text

    from pypdf import PdfReader

    reader = PdfReader(str(master_files[0]))
    attachment_names = list(reader.attachments.keys())
    assert "static_resources/audio.mp3" in attachment_names
    assert "static_resources/example.py" in attachment_names
    assert "static_shared/js/app.js" not in attachment_names


def test_course_metadata_from_url_normalizes_course_pages():
    import pytest

    from ocw_smart_scraper.pipeline import course_metadata_from_url

    meta = course_metadata_from_url("https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/pages/syllabus/")
    assert meta.course_id == "18-06-linear-algebra-spring-2010"
    assert meta.url == "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/"
    for bad in ("https://ocw.mit.edu/search/?d=Physics", "ftp://ocw.mit.edu/courses/x/", "not a url"):
        with pytest.raises(ValueError):
            course_metadata_from_url(bad)


def test_cli_rejects_non_course_urls(capsys):
    import pytest

    from ocw_smart_scraper.cli import main

    with pytest.raises(SystemExit) as exit_info:
        main(["--course", "https://ocw.mit.edu/search/?d=Physics"])
    assert exit_info.value.code == 2
    assert "Not an OCW course URL" in capsys.readouterr().err
