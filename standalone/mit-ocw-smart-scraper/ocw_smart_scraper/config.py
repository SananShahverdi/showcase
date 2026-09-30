"""Configuration loading and validation for the OCW Smart Scraper."""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

logger = logging.getLogger(__name__)


DEFAULT_CONFIG: Dict[str, Any] = {
    "output": {
        "base_directory": "MIT_OCW_Courses",
    },
    "scraping": {
        "timeout": 30,
        "asset_timeout": 180,
        "calls_per_second": 1.5,
        "max_workers": 3,
        "scroll_pause": 1.2,
        "max_scroll_iterations": 60,
        "stable_iterations": 4,
        "max_retries": 3,
        "retry_backoff_seconds": 2.0,
        "max_asset_size_mb": 75,
        "allowed_asset_hosts": [
            "ocw.mit.edu",
            "open-learning-course-data-production.s3.amazonaws.com",
            "open-learning-course-data-rc.s3.amazonaws.com",
            "open-learning-course-data.s3.amazonaws.com",
            "openlearninglibrary.mit.edu",
            "archive.org",
        ],
    },
    "processing": {
        "enable_audio_transcription": True,
        "enable_book_search": True,
        "max_workers": 3,
        "keep_section_files": True,
        "max_master_pdf_mb": 200,
    },
    "whisper": {
        "model": "base",
        "device": "cpu",
    },
    "book_search": {
        "providers": ["open_library", "internet_archive", "gutenberg"],
        "timeout": 20,
        "max_download_size_mb": 120,
    },
}


@dataclass
class RuntimeConfig:
    """Wrapper around the merged configuration dictionary."""

    data: Dict[str, Any] = field(default_factory=lambda: copy.deepcopy(DEFAULT_CONFIG))

    @property
    def output_dir(self) -> Path:
        base = Path(self.data["output"]["base_directory"]).expanduser().resolve()
        base.mkdir(parents=True, exist_ok=True)
        return base

    def dump(self) -> str:
        return json.dumps(self.data, indent=2, sort_keys=True)


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(*, config_path: Optional[Path], overrides: Iterable[str]) -> RuntimeConfig:
    """Load configuration from disk and apply CLI overrides."""

    config_data = copy.deepcopy(DEFAULT_CONFIG)

    if config_path:
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        cfg = _load_yaml(config_path)
        config_data = _merge_dict(config_data, cfg)
        logger.debug("Loaded config from %s -> %s", config_path, cfg)
    else:
        candidate = Path("config.yaml")
        if candidate.exists():
            cfg = _load_yaml(candidate)
            config_data = _merge_dict(config_data, cfg)
            logger.debug("Loaded config from %s", candidate)

    for override in overrides:
        # Overrides use key=value dot notation, e.g. processing.max_workers=5
        try:
            key, value = override.split("=", 1)
        except ValueError:
            raise ValueError(f"Invalid override format '{override}'. Expected key=value.")
        keys = key.split(".")
        node: Dict[str, Any] = config_data
        for piece in keys[:-1]:
            node = node.setdefault(piece, {})
        typed_value: Any
        if value.lower() in {"true", "false"}:
            typed_value = value.lower() == "true"
        else:
            try:
                typed_value = int(value)
            except ValueError:
                try:
                    typed_value = float(value)
                except ValueError:
                    typed_value = value
        node[keys[-1]] = typed_value
        logger.debug("Applied override %s=%s", key, typed_value)

    return RuntimeConfig(data=config_data)
