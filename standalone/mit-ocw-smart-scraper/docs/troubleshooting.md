# Troubleshooting Guide

This document summarises the common failure modes fixed in v2.0 and provides
actionable steps to recover quickly.

## Discovery mismatches

*Symptom:* the OCW search page reports more results than the scraper captures.

1. Run discovery only:

   ```bash
   python smart_scraper.py "<search-url>" --discover-only
   ```

2. Inspect ``discovered_courses.json`` for the canonical list.
3. If the counts still differ, check ``_discovered_diff.txt``. It lists the
   attempt number, reported total, and the discovered URLs. Use this to spot
   new lazy-load behaviours or filters that hide courses mid-scroll.
4. Increase ``scraping.scroll_pause`` or ``scraping.max_scroll_iterations`` in
   ``config.yaml`` when the page loads slowly.

## Merge produced a manifest

*Symptom:* the master PDF contains a single page with ``FALLBACK MANIFEST —
MERGE FAILED``.

1. Verify PyMuPDF or pypdf is installed (`pip install pymupdf pypdf`).
2. Review ``_merge_skipped.txt`` in the course folder – corrupt source PDFs are
   listed there.
3. Delete the bad files and rerun the merge; the scraper validates each input
   by counting its pages before attempting to join.

## Book finder stuck in redirect loops

*Symptom:* log contains ``Redirect loop`` or ``Exceeded redirect limit`` and
``_Books_Not_Found.txt`` references the course.

* Fix the offending source by visiting the logged URL in a browser; if it
  redirects through login walls, manual retrieval is required.
* Adjust ``books.max_redirects`` in ``config.yaml`` for providers that use long
  redirect chains, but keep the value ≤ 10 to avoid infinite loops.

## Whisper transcription failures

*Symptom:* errors such as ``cannot reshape tensor`` or ``ffmpeg ... timescale
not set``.

1. Ensure ffmpeg is installed and accessible (`ffmpeg -version`).
2. Check the generated ``*.wav`` in the course folder; if its duration is below
   1 second, the scraper writes a stub transcript explaining that the media was
   too short.
3. For legacy MP4s, the scraper already retries with ``-fflags +genpts``. When
   issues persist, run ffmpeg manually and inspect the warnings.
4. If Torch/Whisper is not installed the scraper skips transcription and writes
   a stub. Install with ``pip install openai-whisper torch`` for full support.

## Self-test failures

Run ``python smart_scraper.py --self-test`` and read the final log lines in
``MIT_OCW_Courses/scraper.log``:

* *Network check failed* – verify outbound HTTPS access to ``ocw.mit.edu``.
* *Filesystem check failed* – ensure you have write permissions to the working
  directory or change ``output.base_directory``.
* *ffmpeg not found* – install from your package manager and add it to ``PATH``.

The command exits with code 1 when a required dependency fails so CI systems
can catch regressions. Optional integrations (Selenium, Torch, Whisper) show up
as ``[OK]`` or ``[WARN]`` entries but do not change the exit status.

## Backtest harness notes

* ``backtest_courses.txt`` contains stable URLs used for regression testing.
* The harness writes ``backtest_report.md`` under ``MIT_OCW_Courses`` with the
  status for scenarios A–D. Scenario C and D rely on mockable APIs/transcription
  and may skip optional steps when dependencies are missing.

## Getting support

Include the following when opening an issue:

* Command executed and relevant flags
* ``scraper.log`` excerpt
* ``_discovered_diff.txt`` or ``_merge_skipped.txt`` if present
* Platform information (OS, Python version, optional dependency versions)
