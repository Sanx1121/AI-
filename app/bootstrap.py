"""Application bootstrap: DI wiring, Qt + asyncio unified event loop."""

from __future__ import annotations

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor

import qasync
from PySide6.QtWidgets import QApplication

from app.controller import AppController
from core.pipeline.orchestrator import PipelineOrchestrator
from core.pipeline.streaming_orchestrator import StreamingPipelineOrchestrator
from core.pipeline.vad_utterance_processor import VadUtteranceProcessor
from core.subtitle.subtitle_manager import SubtitleManager
from infrastructure.config import AppConfig, load_config
from infrastructure.logging import setup_logging
from infrastructure.qt_async_bridge import QtAsyncBridge
from services.asr.utterance_transcriber import UtteranceTranscriber
from services.asr.whisper_service import WhisperASRService
from services.audio.system_capture import SystemAudioCapture
from services.vad.factory import create_vad
from ui.main_window import MainWindow
from ui.subtitle_overlay import SubtitleOverlay
from ui.view_models.subtitle_view_model import SubtitleViewModel


def create_orchestrator(config: AppConfig, on_event):
    if config.app.demo_mode:
        return PipelineOrchestrator(on_event=on_event, demo_mode=True)

    executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="asr")
    whisper = WhisperASRService(config.asr, executor=executor)
    transcriber = UtteranceTranscriber(
        whisper,
        config.asr,
        config.utterance,
        sample_rate=config.audio.sample_rate,
        executor=executor,
    )
    vad = create_vad(config.utterance, sample_rate=config.audio.sample_rate)
    vad_processor = VadUtteranceProcessor(
        config.utterance,
        sample_rate=config.audio.sample_rate,
        vad=vad,
    )
    audio_source = SystemAudioCapture(config.audio)
    return StreamingPipelineOrchestrator(
        on_event=on_event,
        config=config,
        audio_source=audio_source,
        vad_processor=vad_processor,
        utterance_transcriber=transcriber,
        subtitle_manager=SubtitleManager(),
    )


def run() -> None:
    config = load_config()
    setup_logging(config.log_level)

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("AI 同声传译助手")
    qt_app.setOrganizationName("AI-Translator")

    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    view_model = SubtitleViewModel(
        max_visible_lines=config.subtitle.max_visible_lines,
        history_max_lines=config.subtitle.history_max_lines,
        final_color=config.subtitle.final_color,
        partial_color=config.subtitle.partial_color,
    )
    bridge = QtAsyncBridge(loop)
    controller = AppController(bridge, view_model, config=config)

    subtitle_overlay = SubtitleOverlay(view_model, config.subtitle)
    main_window = MainWindow(view_model, controller, subtitle_overlay)

    subtitle_overlay.show()
    main_window.show()

    with loop:
        loop.run_forever()
