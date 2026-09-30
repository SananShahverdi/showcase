# MIT OCW Smart Scraper Evidence

Date verified: 2026-09-29

## Current Status

The project is a runnable and tested Python course archival system for MIT OpenCourseWare content.

## Verified Command

```bash
python3 -m pytest -q
```

Result:

```text
20 passed in 3.99s
```

## Live Run (2026-09-29)

`python smart_scraper.py --self-test`: 10 required checks passed, 5 optional components available (Selenium, webdriver-manager, Torch, Torchaudio, Whisper).

Live search discovery (`https://ocw.mit.edu/search/?d=Physics --limit 1`): static parsing found 0 courses because the search page is JavaScript-rendered; the Selenium fallback discovered the course.

Live archive of 6.0001 (Introduction to CS and Programming in Python, Fall 2016), transcription and book search disabled, 5 MB asset cap:

- 119 sections (syllabus, readings, lecture notes, assignments, video lectures) and 615 files.
- 114 lecture caption files (`.vtt`) plus transcript PDFs.
- A 1,110-page master PDF with a generated table of contents, merged from 251 source PDFs.

## CV-Supported Evidence

- Modular package under `ocw_smart_scraper/`.
- CLI entry point through `smart_scraper.py` and package CLI.
- Selenium fallback for dynamic course discovery.
- Rate limiting and bounded concurrency.
- YAML configuration with CLI overrides.
- Course section extraction with HTML, PDF, and Markdown derivatives.
- Offline OCW zip ingestion.
- Optional transcription workflow.
- Open-access book discovery.
- Manifest generation and tests.

## Recent Refinement

- Section discovery now follows `/video_galleries/` pages, so lecture resource pages, captions, and transcripts are archived (previously skipped).
- Hardened course-content pruning against malformed/nonstandard BeautifulSoup nodes.
- Updated course scraper tests to reflect the current HTML/PDF/Markdown derivative output.
