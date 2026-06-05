"""Frameless always-on-top subtitle overlay window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from infrastructure.config import SubtitleConfig
from ui.view_models.subtitle_view_model import SubtitleViewModel


class SubtitleOverlay(QWidget):
    def __init__(
        self,
        view_model: SubtitleViewModel,
        config: SubtitleConfig,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._view_model = view_model
        self._config = config

        self.setWindowTitle("字幕")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._label = QLabel("", self)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setWordWrap(True)
        self._label.setFont(QFont("Microsoft YaHei UI", config.font_size))
        self._label.setStyleSheet(
            "color: white;"
            "background-color: rgba(0, 0, 0, 180);"
            "padding: 16px 24px;"
            "border-radius: 8px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 0, 40, 60)
        layout.addStretch()
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.setWindowOpacity(config.opacity)

        self._view_model.visible_lines_changed.connect(self._refresh_text)
        self._refresh_text()
        self._resize_to_screen()

    def _refresh_text(self) -> None:
        text = self._view_model.get_display_text()
        self._label.setText(text)
        self._label.setVisible(bool(text))

    def _resize_to_screen(self) -> None:
        screen = self.screen().availableGeometry()
        width = int(screen.width() * 0.8)
        height = int(screen.height() * 0.25)
        x = screen.x() + (screen.width() - width) // 2
        y = screen.y() + screen.height() - height - 40
        self.setGeometry(x, y, width, height)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._resize_to_screen()
