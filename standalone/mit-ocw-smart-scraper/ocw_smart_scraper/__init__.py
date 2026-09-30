"""
High-level package for the MIT OCW Smart Scraper v2.

The package exposes a single entry point, :func:`ocw_smart_scraper.cli.main`,
which wires together discovery, processing, transcription, book search and
packaging into NotebookLM-friendly course archives.
"""

from __future__ import annotations

from .pipeline import ScraperPipeline

__all__ = ["ScraperPipeline"]
