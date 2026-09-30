# Project Alignment & Expansion Guide

## Alignment with the "Personal Course Archivist" vision

| Vision pillar | Repository implementation | Evidence |
| --- | --- | --- |
| Automated discovery of MIT OCW courses | `CourseDiscovery` walks filtered search pages or consumes curated course lists via the CLI. | [`smart_scraper.py`](../smart_scraper.py) implements `CourseDiscovery` with paging, rate limiting, and Selenium fallbacks for dynamic pages.【F:smart_scraper.py†L40-L159】 |
| Material packaging for NotebookLM | The `ContentProcessor` converts text, code, audio, and transcripts into PDFs before merging them into a master `{course-id}_Complete.pdf`. | PDF helpers in [`pdf_utils.py`](../pdf_utils.py) and merge orchestration in [`smart_scraper.py`](../smart_scraper.py).【F:pdf_utils.py†L1-L220】【F:smart_scraper.py†L160-L419】 |
| Reading list extraction and book search | The configuration enables reading extraction, book search, and `_Books_Not_Found.txt` logging for unresolved titles. | Default configuration in [`smart_scraper.py`](../smart_scraper.py) enables book search, reading scraping, and graceful logging.【F:smart_scraper.py†L66-L155】 |
| Audio/video transcription | Optional Whisper integration transcribes supported media types into searchable text. | Media configuration and transcription hooks reside in [`smart_scraper.py`](../smart_scraper.py).【F:smart_scraper.py†L66-L155】 |
| Config-driven, fault-tolerant workflow | `config.yaml` overrides fine-tune scraping, processing, and rate limiting without code changes. | The README and `config.example.yaml` document the available switches.【F:README.md†L1-L120】【F:config.example.yaml†L1-L185】 |

The existing codebase already satisfies the pillars of the original product idea: it discovers courses, captures courseware, expands the corpus with open-access books, and produces NotebookLM-ready master documents while logging any gaps for follow-up.

## Expansion opportunities

To deepen the "research assistant" experience, the following initiatives are planned:

1. **Contextual metadata capture** – capture instructor bios, term information, and prerequisite tags so NotebookLM sessions can provide course context without manual research.
2. **Semantic transcript indexing** – build lightweight embeddings for transcripts to enable question answering across the merged PDF bundle.
3. **Enhanced book intelligence** – integrate structured matching (Open Library work IDs, ISBN crosswalks) and optional paywall-aware searches so that `_Books_Not_Found.txt` becomes progressively shorter.
4. **Interactive progress dashboard** – expose the run state via a local web UI or TUI with resumable job queues for large course batches.
5. **Pluggable storage backends** – add writers for S3, Google Drive, and local NAS targets so that processed courses can be archived off-device automatically.

Each item can be developed incrementally without disrupting the existing CLI: new modules can hook into the `ContentProcessor` lifecycle and reuse the configuration system to enable/disable features.

## Recommended next steps

- Draft design notes for metadata capture and transcript indexing in `docs/architecture/`.
- Extend the pytest suite with integration tests that validate `_Books_Not_Found.txt` logging and multi-course packaging.
- Provide sample NotebookLM notebooks built from generated master PDFs to showcase end-to-end value.

These actions will keep the implementation tightly aligned with the product pitch while growing the assistant into a comprehensive researcher for MIT OCW materials.
