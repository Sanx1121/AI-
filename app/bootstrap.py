"""Application bootstrap: DI wiring, Qt + asyncio unified event loop."""

from __future__ import annotations

import asyncio
import sys

import qasync
from PySide6.QtWidgets import QApplication

from app.controller import AppController
from infrastructure.config import load_config
from infrastructure.logging import setup_logging
from infrastructure.qt_async_bridge import QtAsyncBridge
from ui.main_window import MainWindow
from ui.subtitle_overlay import SubtitleOverlay
from ui.view_models.subtitle_view_model import SubtitleViewModel


def run() -> None:
    config = load_config()
    setup_logging(config.log_level)

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("AI 同声传译助手")
    qt_app.setOrganizationName("AI-Translator")

    loop = qasync.QEventLoop(qt_app)
    asyncio.set_event_loop(loop)

    view_model = SubtitleViewModel(max_visible_lines=config.subtitle.max_visible_lines)
    bridge = QtAsyncBridge(loop)
    controller = AppController(bridge, view_model, demo_mode=True)

    subtitle_overlay = SubtitleOverlay(view_model, config.subtitle)
    main_window = MainWindow(view_model, controller, subtitle_overlay)

    subtitle_overlay.show()
    main_window.show()

    with loop:
        loop.run_forever()
