# MIT OCW Smart Scraper v2.0

"Your Personal Course Archivist" – a research assistant that discovers MIT OpenCourseWare courses, ingests their materials, enriches them with books and transcripts, and packages everything into NotebookLM-ready bundles.

---

## ✨ Highlights

- **Automated discovery** – crawl filtered search URLs with Selenium fallback when pages lazy-load.
- **Structured archives** – every course is normalised into a predictable directory tree with sections, transcripts, and a master PDF.
- **Offline bundle parity** – ingest official OCW zip downloads and reproduce the same human-readable, NotebookLM-friendly PDFs without hitting the live site.
- **Config-driven workflow** – override any default through `config.yaml` or CLI key=value overrides.
- **Optional intelligence** – Whisper-backed transcription and an open-access book finder integrate seamlessly when dependencies are present.
- **Polite scraping** – rate limiting, bounded concurrency, and detailed logging keep runs stable.

---

## 📦 Output Layout

For each processed course the scraper writes:

```
MIT_OCW_Courses/<course-id>/
├── course.json                  # metadata & section index
├── <course-id>_Complete.pdf     # merged master document
├── lecture_notes/section_1.pdf  # PDFs per section (categorised)
├── assignments/
├── transcripts/
├── media/
└── books/                       # downloaded open-access titles
```

The bundle is optimised for NotebookLM ingestion while remaining human-readable.

---

## 🔧 Requirements

- Python 3.9+ (tested on 3.11)
- `pip` with virtual environment support (`python -m venv`)
- Google Chrome/Chromium (for Selenium discovery)
- Optional: FFmpeg, Torch, and Whisper for audio/video transcription

Install dependencies with:

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Add Whisper GPU acceleration via:

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## 🚀 Quick Start

```bash
source venv/bin/activate
python smart_scraper.py "https://ocw.mit.edu/search/?d=Physics" --limit 3
```

Key flags:

- `--course URL` – archive one or more specific course pages directly (repeatable), e.g. `--course https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/`
- `--no-selenium` – force static discovery (useful for CI)
- `--limit N` – process only the first *N* discovered courses
- `--override key=value` – override config keys (e.g. `processing.max_workers=5`)
- `--backtest` – run the curated sample in `backtest_courses.txt`
- `--from-zip` – convert one or more downloaded OCW bundles into the same layout and master PDFs produced by the live scraper

All options: `python smart_scraper.py --help`

---

## ⚙️ Configuration

The loader merges defaults, `config.yaml` (if present), and CLI overrides. Example:

```yaml
output:
  base_directory: MIT_OCW_Courses

scraping:
  timeout: 45
  asset_timeout: 180
  calls_per_second: 1.5
  max_workers: 4

processing:
  enable_audio_transcription: true
  enable_book_search: true
  max_workers: 4
  keep_section_files: true  # set false to keep only the merged master PDF

whisper:
  model: base
  device: cpu

book_search:
  providers: [open_library, internet_archive, gutenberg]
  timeout: 20
```

Override any field at runtime:

```bash
python smart_scraper.py "https://ocw.mit.edu/search/?d=Physics" \
  --override processing.enable_audio_transcription=false \
  --override scraping.max_workers=2
```

---

## 🧠 Architecture

| Module | Responsibility |
| ------ | -------------- |
| `ocw_smart_scraper.config` | Load and merge configuration sources |
| `ocw_smart_scraper.discovery` | Discover course metadata (static + Selenium) |
| `ocw_smart_scraper.course` | Scrape, categorise, and normalise course sections (including offline pages) |
| `ocw_smart_scraper.book_finder` | Query open-access providers for reported readings |
| `ocw_smart_scraper.transcription` | Whisper-backed audio/video transcription |
| `ocw_smart_scraper.pdf` | Text rendering and PDF merging |
| `ocw_smart_scraper.pipeline` | End-to-end orchestration & packaging (live scrape + offline zip ingestion) |

This modular layout keeps each concern testable and allows future expansion (e.g. alternate storage backends or new book providers).

---

## 🧪 Testing

```bash
source venv/bin/activate
pytest -v
```

The suite covers configuration loading, rate limiting, discovery parsing, and PDF composition. Extend with integration tests by seeding deterministic HTML fixtures or by recording HTTP interactions.

---

## 🛠️ Development Tips

- Set `--log-cli-level=DEBUG` when running pytest to inspect configuration merges.
- Use `--no-selenium` in CI to avoid browser dependencies.
- When iterating on book search, stub provider responses with `pytest-mock` to keep tests fast and deterministic.

---

## ⚠️ Known Limitations

- Courses that primarily link to external wikis (for example, some MIT "RES" resources) may expose few first-party pages; the scraper records metadata but skips master PDF creation when no course PDFs are generated.
- Static discovery occasionally returns zero courses on highly dynamic search pages; rerun with Selenium enabled (default) or supply curated course URLs in a future enhancement.
- Whisper transcription depends on local FFmpeg support; set `processing.enable_audio_transcription=false` to bypass media-heavy runs on constrained machines.

---

## 📄 License

This project ships without an explicit license. Contact the original author(s) before redistribution or commercial use.
