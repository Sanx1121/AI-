"""Tests for configuration loading."""

from pathlib import Path

from infrastructure.config import AppConfig, load_config


def test_load_default_config():
    config = load_config()
    assert isinstance(config, AppConfig)
    assert config.app.demo_mode is False
    assert config.app.profile == "balanced"
    assert config.audio.sample_rate == 16000
    assert config.asr.engine == "whisper"
    assert config.asr.model_size == "tiny"
    assert config.asr.vad_filter is False
    assert config.utterance.partial_interval_ms == 200
    assert config.utterance.partial_tail_sec == 0.8
    assert config.utterance.utterance_end_silence_ms == 400
    assert config.subtitle.max_visible_lines == 4
    assert config.subtitle.font_size == 24
    assert config.subtitle.final_color == "#FFFFFF"
    assert config.subtitle.partial_color == "#9EACB4"
    assert config.translation.enabled is True
    assert config.translation.provider == "dashscope_mt"
    assert config.translation.mode == "final_only"
    assert config.translation.dashscope_model == "qwen-mt-lite"


def test_load_from_resources_file():
    path = Path(__file__).resolve().parents[2] / "resources" / "default_config.toml"
    config = load_config(path)
    assert config.subtitle.font_size == 24
    assert config.log_level == "INFO"


def test_missing_config_returns_defaults(tmp_path: Path):
    config = load_config(tmp_path / "nonexistent.toml")
    assert config.asr.model_size == "small"
