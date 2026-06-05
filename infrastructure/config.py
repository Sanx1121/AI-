"""Application configuration loaded from TOML."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python < 3.11
    import tomli as tomllib


@dataclass(frozen=True, slots=True)
class AppSettings:
    demo_mode: bool = False
    profile: str = "balanced"


@dataclass(frozen=True, slots=True)
class AudioConfig:
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_sec: float = 2.0
    feed_chunk_sec: float = 0.1
    loopback_device: str = ""
    silence_rms_threshold: float = 0.002


@dataclass(frozen=True, slots=True)
class AsrConfig:
    engine: str = "whisper"
    model_size: str = "small"
    device: str = "auto"
    compute_type: str = "default"
    language: str = "en"
    vad_filter: bool = True
    normalize_audio: bool = True
    whisper_vad_threshold: float = 0.35
    whisper_vad_min_silence_ms: int = 500
    whisper_vad_speech_pad_ms: int = 200


@dataclass(frozen=True, slots=True)
class UtteranceConfig:
    vad_frame_ms: int = 30
    speech_pad_ms: int = 200
    utterance_end_silence_ms: int = 600
    max_utterance_sec: float = 15.0
    max_phrase_sec: float = 0.0
    ring_buffer_sec: float = 30.0
    vad_threshold: float = 0.45
    use_silero_vad: bool = True
    energy_threshold: float = 0.015
    partial_interval_ms: int = 300
    partial_tail_sec: float = 1.0
    partial_window_sec: float = 3.0
    min_partial_sec: float = 0.25
    ring_drop_sec: float = 1.0


@dataclass(frozen=True, slots=True)
class TranslationConfig:
    ollama_base_url: str = "http://localhost:11434"
    model_name: str = "qwen2.5:7b"


@dataclass(frozen=True, slots=True)
class SubtitleConfig:
    max_visible_lines: int = 3
    history_max_lines: int = 2
    font_size: int = 28
    opacity: float = 0.85
    position: str = "bottom"
    final_color: str = "#FFFFFF"
    partial_color: str = "#9EACB4"


@dataclass(frozen=True, slots=True)
class AppConfig:
    app: AppSettings = field(default_factory=AppSettings)
    audio: AudioConfig = field(default_factory=AudioConfig)
    asr: AsrConfig = field(default_factory=AsrConfig)
    utterance: UtteranceConfig = field(default_factory=UtteranceConfig)
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

    app = _section(data, "app")
    audio = _section(data, "audio")
    asr = _section(data, "asr")
    utterance = _section(data, "utterance")
    translation = _section(data, "translation")
    subtitle = _section(data, "subtitle")

    return AppConfig(
        app=AppSettings(
            demo_mode=bool(app.get("demo_mode", False)),
            profile=str(app.get("profile", "balanced")),
        ),
        audio=AudioConfig(
            sample_rate=int(audio.get("sample_rate", 16000)),
            channels=int(audio.get("channels", 1)),
            chunk_duration_sec=float(audio.get("chunk_duration_sec", 2.0)),
            feed_chunk_sec=float(audio.get("feed_chunk_sec", 0.1)),
            loopback_device=str(audio.get("loopback_device", "")),
            silence_rms_threshold=float(audio.get("silence_rms_threshold", 0.002)),
        ),
        asr=AsrConfig(
            engine=str(asr.get("engine", "whisper")),
            model_size=str(asr.get("model_size", "small")),
            device=str(asr.get("device", "auto")),
            compute_type=str(asr.get("compute_type", "default")),
            language=str(asr.get("language", "en")),
            vad_filter=bool(asr.get("vad_filter", True)),
            normalize_audio=bool(asr.get("normalize_audio", True)),
            whisper_vad_threshold=float(asr.get("whisper_vad_threshold", 0.35)),
            whisper_vad_min_silence_ms=int(asr.get("whisper_vad_min_silence_ms", 500)),
            whisper_vad_speech_pad_ms=int(asr.get("whisper_vad_speech_pad_ms", 200)),
        ),
        utterance=UtteranceConfig(
            vad_frame_ms=int(utterance.get("vad_frame_ms", 30)),
            speech_pad_ms=int(utterance.get("speech_pad_ms", 200)),
            utterance_end_silence_ms=int(
                utterance.get("utterance_end_silence_ms", 600)
            ),
            max_utterance_sec=float(utterance.get("max_utterance_sec", 15.0)),
            max_phrase_sec=float(utterance.get("max_phrase_sec", 0.0)),
            ring_buffer_sec=float(utterance.get("ring_buffer_sec", 30.0)),
            vad_threshold=float(utterance.get("vad_threshold", 0.45)),
            use_silero_vad=bool(utterance.get("use_silero_vad", True)),
            energy_threshold=float(utterance.get("energy_threshold", 0.015)),
            partial_interval_ms=int(utterance.get("partial_interval_ms", 300)),
            partial_tail_sec=float(utterance.get("partial_tail_sec", 1.0)),
            partial_window_sec=float(utterance.get("partial_window_sec", 3.0)),
            min_partial_sec=float(utterance.get("min_partial_sec", 0.25)),
            ring_drop_sec=float(utterance.get("ring_drop_sec", 1.0)),
        ),
        translation=TranslationConfig(
            ollama_base_url=str(
                translation.get("ollama_base_url", "http://localhost:11434")
            ),
            model_name=str(translation.get("model_name", "qwen2.5:7b")),
        ),
        subtitle=SubtitleConfig(
            max_visible_lines=int(subtitle.get("max_visible_lines", 3)),
            history_max_lines=int(subtitle.get("history_max_lines", 2)),
            font_size=int(subtitle.get("font_size", 28)),
            opacity=float(subtitle.get("opacity", 0.85)),
            position=str(subtitle.get("position", "bottom")),
            final_color=str(subtitle.get("final_color", "#FFFFFF")),
            partial_color=str(subtitle.get("partial_color", "#9EACB4")),
        ),
        log_level=str(data.get("log_level", "INFO")),
    )
