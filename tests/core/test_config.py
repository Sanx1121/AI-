"""Tests for configuration loading."""

from pathlib import Path

from infrastructure.config import AppConfig, load_config


def test_load_default_config():
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.audio.sample_rate == 16000
    assert config.subtitle.max_visible_lines == 3
    assert config.translation.model_name == "qwen2.5:7b"


def test_load_from_resources_file():
    path = Path(__file__).resolve().parents[2] / "resources" / "default_config.toml"
    config = load_config(path)
    assert config.subtitle.font_size == 28
    assert config.log_level == "INFO"


def test_missing_config_returns_defaults(tmp_path: Path):
    config = load_config(tmp_path / "nonexistent.toml")
    assert config.asr.model_size == "base"
