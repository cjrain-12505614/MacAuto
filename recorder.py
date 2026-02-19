"""
Recorder — captures mouse and keyboard events.

Mouse events are captured via pynput's mouse listener.
Keyboard events are captured via KeyboardMonitor (Quartz CGEventTap),
which avoids the macOS TSMGetInputSourceProperty crash.
"""

import time
import threading
from typing import List, Callable, Optional

from pynput import mouse

from models import (
    MouseMoveEvent,
    MouseClickEvent,
    MouseScrollEvent,
    KeyEvent,
    Event,
    event_to_dict,
)
from keyboard_monitor import (
    KeyboardMonitor, KEYCODE_F9, KEYCODE_F10, KEYCODE_ESC,
    KEYCODE_R, KEYCODE_P,
)

# Minimum interval between mouse-move events (seconds) to avoid flooding
_MIN_MOVE_INTERVAL = 0.01  # 10 ms

# Keycodes to skip during recording (hotkeys should not be recorded)
_SKIP_KEYCODES = {KEYCODE_F9, KEYCODE_F10, KEYCODE_ESC}
# Modifier keycodes: cmd(55/54), shift(56/60)
_MODIFIER_KEYCODES = {54, 55, 56, 60}


class Recorder:
    def __init__(self, kb_monitor: KeyboardMonitor):
        self._events: List[dict] = []
        self._recording = False
        self._start_time: float = 0.0
        self._last_move_time: float = 0.0
        self._mouse_listener: Optional[mouse.Listener] = None
        self._kb_monitor = kb_monitor
        self._lock = threading.Lock()
        self._on_status_change: Optional[Callable[[bool], None]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def events(self) -> List[dict]:
        return list(self._events)

    def set_status_callback(self, cb: Callable[[bool], None]):
        """Called with True when recording starts, False when it stops."""
        self._on_status_change = cb

    def start(self):
        if self._recording:
            return
        self._events.clear()
        self._start_time = time.perf_counter()
        self._last_move_time = 0.0
        self._recording = True

        # Mouse listener (pynput — safe on macOS)
        self._mouse_listener = mouse.Listener(
            on_move=self._on_move,
            on_click=self._on_click,
            on_scroll=self._on_scroll,
        )
        self._mouse_listener.start()

        # Keyboard events via shared Quartz-based monitor
        self._kb_monitor.add_event_callback(self._on_key_event)

        if self._on_status_change:
            self._on_status_change(True)

    def stop(self):
        if not self._recording:
            return
        self._recording = False

        if self._mouse_listener:
            self._mouse_listener.stop()

        self._kb_monitor.remove_event_callback(self._on_key_event)

        if self._on_status_change:
            self._on_status_change(False)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ts(self) -> float:
        return time.perf_counter() - self._start_time

    def _append(self, ev: Event):
        with self._lock:
            self._events.append(event_to_dict(ev))

    # ------------------------------------------------------------------
    # Mouse callbacks (pynput)
    # ------------------------------------------------------------------

    def _on_move(self, x: int, y: int):
        if not self._recording:
            return
        now = self._ts()
        if now - self._last_move_time < _MIN_MOVE_INTERVAL:
            return
        self._last_move_time = now
        self._append(MouseMoveEvent(x=int(x), y=int(y), timestamp=now))

    def _on_click(self, x: int, y: int, button, pressed: bool):
        if not self._recording:
            return
        self._append(
            MouseClickEvent(
                x=int(x), y=int(y), button=button.name, pressed=pressed,
                timestamp=self._ts(),
            )
        )

    def _on_scroll(self, x: int, y: int, dx: int, dy: int):
        if not self._recording:
            return
        self._append(
            MouseScrollEvent(
                x=int(x), y=int(y), dx=dx, dy=dy, timestamp=self._ts(),
            )
        )

    # ------------------------------------------------------------------
    # Keyboard callback (KeyboardMonitor / Quartz)
    # ------------------------------------------------------------------

    def _on_key_event(self, keycode: int, key_name: str, is_down: bool):
        if not self._recording:
            return
        # Don't record hotkey presses
        if keycode in _SKIP_KEYCODES:
            return
        self._append(
            KeyEvent(
                key=key_name,
                keycode=keycode,
                pressed=is_down,
                timestamp=self._ts(),
            )
        )
