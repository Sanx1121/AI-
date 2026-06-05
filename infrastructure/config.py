"""Application configuration loaded from TOML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib


@dataclass(frozen=True, slots=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_sec: float = 2.0


@dataclass(frozen=True, slots=True)
class AsrConfig:
    model_size: str = "base"
    device: str = "auto"
    compute_type: str = "default"


@dataclass(frozen=True, slots=True)
class TranslationConfig:
    ollama_base_url: str = "http://localhost:11434"
    model_name: str = "qwen2.5:7b"


@dataclass(frozen=True, slots=True)
class SubtitleConfig:
    max_visible_lines: int = 3
    font_size: int = 28
    opacity: float = 0.85
    position: str = "bottom"


@dataclass(frozen=True, slots=True)
class AppConfig:
    audio: AudioConfig = field(default_factory=AudioConfig)
    asr: AsrConfig = field(default_factory=AsrConfig)
    translation: TranslationConfig = field(default_factory=TranslationConfig)
    subtitle: SubtitleConfig = field(default_factory=SubtitleConfig)
    log_level: str = "INFO"


def _section(data: dict, key: str) -> dict:
    value = data.get(key, {})
    return value if isinstance(value, dict) else {}


def load_config(path: Path | None = None) -> AppConfig:
    if path is None:
        path = Path(__file__).resolve().parent.parent / "resources" / "default_config.toml"

    if not path.exists():
        return AppConfig()

    with path.open("rb") as file:
        data = tomllib.load(file)

    audio = _section(data, "audio")
    asr = _section(data, "asr")
    translation = _section(data, "translation")
    subtitle = _section(data, "subtitle")

    return AppConfig(
        audio=AudioConfig(
            sample_rate=int(audio.get("sample_rate", 16000)),
            channels=int(audio.get("channels", 1)),
            chunk_duration_sec=float(audio.get("chunk_duration_sec", 2.0)),
        ),
        asr=AsrConfig(
            model_size=str(asr.get("model_size", "base")),
            device=str(asr.get("device", "auto")),
            compute_type=str(asr.get("compute_type", "default")),
        ),
        translation=TranslationConfig(
            ollama_base_url=str(
                translation.get("ollama_base_url", "http://localhost:11434")
            ),
            model_name=str(translation.get("model_name", "qwen2.5:7b")),
        ),
        subtitle=SubtitleConfig(
            max_visible_lines=int(subtitle.get("max_visible_lines", 3)),
            font_size=int(subtitle.get("font_size", 28)),
            opacity=float(subtitle.get("opacity", 0.85)),
            position=str(subtitle.get("position", "bottom")),
        ),
        log_level=str(data.get("log_level", "INFO")),
    )
