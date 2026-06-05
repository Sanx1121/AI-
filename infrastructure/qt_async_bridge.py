"""Bridge between asyncio coroutines and the Qt main thread."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from PySide6.QtCore import QObject, QTimer, Signal

T = TypeVar("T")


class QtAsyncBridge(QObject):
    """Schedules coroutines on the shared qasync loop and dispatches callbacks to Qt."""

    callback_ready = Signal(object)

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._loop = loop
        self.callback_ready.connect(self._dispatch_callback)

    def run_coroutine(
        self,
        coro: Coroutine[Any, Any, T],
        *,
        on_success: Callable[[T], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> asyncio.Task[T]:
        task = self._loop.create_task(coro)

        def _done_callback(future: asyncio.Task[T]) -> None:
            try:
                result = future.result()
            except asyncio.CancelledError:
                return
            except Exception as exc:
                if on_error is not None:
                    self.emit_to_main_thread(on_error, exc)
                return
            if on_success is not None:
                self.emit_to_main_thread(on_success, result)

        task.add_done_callback(_done_callback)
        return task

    def emit_to_main_thread(self, callback: Callable[..., None], *args: Any) -> None:
        """Thread-safe: queue a callable to run on the Qt main thread."""
        self.callback_ready.emit((callback, args))

    def call_soon_threadsafe(self, callback: Callable[..., None], *args: Any) -> None:
        self._loop.call_soon_threadsafe(self.emit_to_main_thread, callback, *args)

    @staticmethod
    def _dispatch_callback(payload: object) -> None:
        callback, args = payload  # type: ignore[misc]
        callback(*args)

    def call_later(self, delay_sec: float, callback: Callable[[], None]) -> QTimer:
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.start(int(delay_sec * 1000))
        return timer
