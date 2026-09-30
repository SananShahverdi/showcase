from pathlib import Path

import pytest

from ocw_smart_scraper.config import DEFAULT_CONFIG, RuntimeConfig, load_config


def test_load_config_defaults(tmp_path: Path) -> None:
    config = load_config(config_path=None, overrides=[])
    assert config.data["output"]["base_directory"] == DEFAULT_CONFIG["output"]["base_directory"]


def test_load_config_from_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("output:\n  base_directory: custom_dir\n", encoding="utf-8")
    config = load_config(config_path=config_path, overrides=[])
    assert config.data["output"]["base_directory"] == "custom_dir"


def test_overrides_apply() -> None:
    config = load_config(config_path=None, overrides=["processing.max_workers=5", "whisper.device=cuda", "processing.enable_book_search=false"])
    assert config.data["processing"]["max_workers"] == 5
    assert config.data["whisper"]["device"] == "cuda"
    assert config.data["processing"]["enable_book_search"] is False


def test_output_dir_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = RuntimeConfig(data={"output": {"base_directory": str(tmp_path / "courses")}})
    output = cfg.output_dir
    assert output.exists()
