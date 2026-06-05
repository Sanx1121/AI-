"""Main control window — start/stop and status display."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.controller import AppController
from core.events import PipelineState
from ui.subtitle_overlay import SubtitleOverlay
from ui.view_models.subtitle_view_model import SubtitleViewModel


class MainWindow(QMainWindow):
    def __init__(
        self,
        view_model: SubtitleViewModel,
        controller: AppController,
        subtitle_overlay: SubtitleOverlay,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._view_model = view_model
        self._controller = controller
        self._subtitle_overlay = subtitle_overlay

        self.setWindowTitle("AI 同声传译助手")
        self.setMinimumSize(420, 220)

        central = QWidget(self)
        self.setCentralWidget(central)

        title = QLabel("AI 同声传译助手")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold;")

        self._status_label = QLabel("就绪")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #666;")

        self._start_button = QPushButton("开始")
        self._stop_button = QPushButton("停止")
        self._stop_button.setEnabled(False)

        self._start_button.clicked.connect(self._on_start_clicked)
        self._stop_button.clicked.connect(self._on_stop_clicked)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(self._start_button)
        button_row.addWidget(self._stop_button)
        button_row.addStretch()

        hint = QLabel("Phase 1：点击「开始」播放演示字幕，验证 UI 与异步流水线。")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #888; font-size: 12px;")

        layout = QVBoxLayout(central)
        layout.addStretch()
        layout.addWidget(title)
        layout.addSpacing(8)
        layout.addWidget(self._status_label)
        layout.addSpacing(16)
        layout.addLayout(button_row)
        layout.addSpacing(12)
        layout.addWidget(hint)
        layout.addStretch()

        self._view_model.pipeline_state_changed.connect(self._update_controls)
        self._view_model.status_message_changed.connect(self._update_status)
        self._update_controls()

    def _on_start_clicked(self) -> None:
        self._subtitle_overlay.show()
        self._controller.start_pipeline()

    def _on_stop_clicked(self) -> None:
        self._controller.stop_pipeline()

    def _update_status(self) -> None:
        self._status_label.setText(self._view_model.status_message)

    def _update_controls(self) -> None:
        state = self._view_model.pipeline_state
        running = state in (PipelineState.RUNNING.value, PipelineState.STARTING.value)
        self._start_button.setEnabled(not running)
        self._stop_button.setEnabled(running)
        self._update_status()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self._controller.is_running:
            self._controller.stop_pipeline()
        super().closeEvent(event)
