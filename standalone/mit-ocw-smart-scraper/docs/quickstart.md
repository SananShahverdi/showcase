# MIT OCW Smart Scraper – Quickstart

The v2.0 toolchain discovers MIT OCW courses from a filtered search URL and
packages course materials into a single master PDF optimised for NotebookLM.
This guide helps you run your first scrape in minutes.

## 1. Set up a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\Activate.ps1
pip install -U pip
pip install -r requirements.txt
```

Optional: install Whisper/Torch, Selenium, and PyMuPDF for richer features.

## 2. Validate the environment

Run diagnostics before the first scrape:

```bash
python smart_scraper.py --self-test
```

The self-test writes its summary to ``MIT_OCW_Courses/scraper.log`` and exits
non-zero when a required dependency fails (environment, imports, ffmpeg, or
network reachability). Optional integrations such as Selenium, Torch, and
Whisper appear as ``[OK]`` entries so you can confirm they are installed
without failing the run.

## 3. Choose a search URL

1. Visit <https://ocw.mit.edu/search>
2. Apply filters (department, topics, term, etc.)
3. Copy the resulting URL – this is the argument for the scraper

Example: ``https://ocw.mit.edu/search/?d=Physics``

## 4. Run discovery (optional)

```bash
python smart_scraper.py "https://ocw.mit.edu/search/?d=Mathematics" --discover-only
```

The command scrolls the dynamic results page until it matches the reported
count. It writes ``discovered_courses.json`` and ``_discovered_diff.txt`` when a
discrepancy remains after a retry.

## 5. Convert a downloaded course bundle

```bash
python smart_scraper.py --from-zip /path/to/ocw-course.zip
```

The scraper unpacks the official OCW download archive, converts every page to
PDF, and embeds the raw media/code assets as PDF attachments so downstream
tools can access them without hitting the network.

## 6. Process courses

```bash
python smart_scraper.py "https://ocw.mit.edu/search/?d=Physics" --limit 3
```

Key flags:

* ``--skip-audio`` – disable Whisper transcription
* ``--skip-books`` – bypass textbook discovery
* ``--skip-code-pdf`` – leave code files in their original format
* ``--max-workers`` – bound download concurrency
* ``--courses-file`` – process a curated list instead of running discovery

Outputs land in ``MIT_OCW_Courses/<course-id>/``. Each course receives a master
PDF with bookmarks plus auxiliary logs (``_merge_skipped.txt``,
``_Books_Not_Found.txt``) when applicable. Offline bundles include code/media
files as embedded attachments inside the master PDF.

## 7. Run the backtest harness (optional)

```bash
python smart_scraper.py --backtest
```

The harness runs four scenarios (baseline, merge, books, transcription) against
``backtest_courses.txt`` and produces ``backtest_report.md`` summarising
timings and pass/fail status.

## 8. Troubleshooting

Refer to ``docs/troubleshooting.md`` for guidance on Selenium discovery,
manifest fallbacks, redirect loops, and transcription edge cases.

Happy archiving! 🎓
