"""Tests for subtitle overlay height measurement."""

import sys

from PySide6.QtGui import QFont, QTextDocument
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication(sys.argv)


def measure_html_height(
    html_text: str,
    *,
    content_width: int,
    font_size: int = 28,
    vertical_padding: int = 32,
) -> int:
    document = QTextDocument()
    document.setDefaultFont(QFont("Microsoft YaHei UI", font_size))
    document.setHtml(html_text)
    document.setTextWidth(float(content_width))
    return int(document.size().height()) + vertical_padding


def test_longer_html_measures_taller():
    short = '<span style="color:#FFFFFF;">Hello</span>'
    long_html = '<span style="color:#FFFFFF;">' + ("word " * 40) + "</span>"
    width = 600
    assert measure_html_height(long_html, content_width=width) > measure_html_height(
        short, content_width=width
    )


def test_multiline_html_measures_taller_than_single_line():
    single = '<span style="color:#FFFFFF;">One line</span>'
    multi = (
        '<span style="color:#FFFFFF;">First sentence.</span><br/>'
        '<span style="color:#9EACB4;">Second live line.</span>'
    )
    width = 600
    assert measure_html_height(multi, content_width=width) > measure_html_height(
        single, content_width=width
    )
