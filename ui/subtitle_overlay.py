"""Frameless always-on-top subtitle overlay window."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextDocument
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from infrastructure.config import SubtitleConfig
from ui.view_models.subtitle_view_model import SubtitleViewModel


class SubtitleOverlay(QWidget):
    """Subtitle overlay that grows vertically with wrapped content."""

    _WIDTH_RATIO = 0.8
    _MAX_HEIGHT_RATIO = 0.55
    _HORIZONTAL_MARGIN = 80
    _BOTTOM_MARGIN = 60
    _BOTTOM_OFFSET = 40
    _LABEL_VERTICAL_PADDING = 32

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
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setFont(QFont("Microsoft YaHei UI", config.font_size))
        self._label.setStyleSheet(
            "background-color: rgba(0, 0, 0, 180);"
            "padding: 16px 24px;"
            "border-radius: 8px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 0, 40, self._BOTTOM_MARGIN)
        layout.setSpacing(0)
        layout.addStretch()
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.setWindowOpacity(config.opacity)

        self._view_model.visible_lines_changed.connect(self._refresh_text)
        self._refresh_text()

    def _refresh_text(self) -> None:
        html_text = self._view_model.get_display_html()
        self._label.setText(html_text)
        self._label.setVisible(bool(html_text))
        self._adjust_overlay_size()

    def _content_width(self) -> int:
        screen = self.screen().availableGeometry()
        return max(320, int(screen.width() * self._WIDTH_RATIO) - self._HORIZONTAL_MARGIN)

    def _measure_html_height(self, html_text: str, content_width: int) -> int:
        document = QTextDocument()
        document.setDefaultFont(self._label.font())
        document.setHtml(html_text)
        document.setTextWidth(float(content_width))
        return int(document.size().height()) + self._LABEL_VERTICAL_PADDING

    def _adjust_overlay_size(self) -> None:
        screen = self.screen().availableGeometry()
        content_width = self._content_width()
        window_width = content_width + self._HORIZONTAL_MARGIN

        html_text = self._view_model.get_display_html()
        if not html_text:
            height = 0
        else:
            label_height = self._measure_html_height(html_text, content_width)
            max_label_height = max(
                80,
                int(screen.height() * self._MAX_HEIGHT_RATIO) - self._BOTTOM_OFFSET,
            )
            label_height = min(label_height, max_label_height)
            self._label.setFixedWidth(content_width)
            self._label.setFixedHeight(label_height)
            height = label_height + self._BOTTOM_MARGIN

        if height <= 0:
            self.hide()
            return

        self.show()
        x = screen.x() + (screen.width() - window_width) // 2
        y = screen.y() + screen.height() - height - self._BOTTOM_OFFSET
        self.setGeometry(x, y, window_width, height)

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._adjust_overlay_size()
