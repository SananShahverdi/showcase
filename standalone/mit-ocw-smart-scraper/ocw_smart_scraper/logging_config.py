"""Logging helpers for the OCW Smart Scraper."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional


LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging(output_dir: Path, *, verbose: bool = False) -> Path:
    """Configure application and file logging."""

    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "scraper.log"

    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(log_path, encoding="utf-8"),
    ]

    for handler in handlers:
        handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        handlers=handlers,
    )

    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    return log_path
