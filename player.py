"""
Player — replays recorded events with speed multiplier and repeat count.

Mouse replay uses pynput controllers.
Keyboard replay uses Quartz CGEventCreateKeyboardEvent for reliability
(exact keycode matching, no name-to-key translation issues).
"""

import time
import threading
from typing import List, Callable, Optional

from pynput.mouse import Button, Controller as MouseCtrl
import Quartz

from models import (
    dict_to_event,
    MouseMoveEvent,
    MouseClickEvent,
    MouseScrollEvent,
    KeyEvent,
)


class Player:
    def __init__(self):
        self._mouse = MouseCtrl()
        self._playing = False
        self._thread: Optional[threading.Thread] = None
        self._on_status_change: Optional[Callable[[bool], None]] = None
        self._on_progress: Optional[Callable[[int, int, int, int], None]] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_playing(self) -> bool:
        return self._playing

    def set_status_callback(self, cb: Callable[[bool], None]):
        self._on_status_change = cb

    def set_progress_callback(self, cb: Callable[[int, int, int, int], None]):
        """cb(current_repeat, total_repeats, current_event, total_events)"""
        self._on_progress = cb

    def play(self, events: List[dict], repeat: int = 1, speed: float = 1.0):
        """
        Start playback in a background thread.
        repeat=0  → infinite loop (until stop() is called)
        speed     → multiplier (2.0 = twice as fast)
        """
        if self._playing:
            return
        self._playing = True
        self._thread = threading.Thread(
            target=self._run, args=(events, repeat, speed), daemon=True
        )
        self._thread.start()
        if self._on_status_change:
            self._on_status_change(True)

    def stop(self):
        self._playing = False
        if self._on_status_change:
            self._on_status_change(False)

    # ------------------------------------------------------------------
    # Internal playback loop
    # ------------------------------------------------------------------

    def _run(self, events: List[dict], repeat: int, speed: float):
        if not events:
            self._playing = False
            if self._on_status_change:
                self._on_status_change(False)
            return

        infinite = repeat == 0
        total_repeats = repeat if not infinite else -1
        current_repeat = 0

        try:
            while self._playing and (infinite or current_repeat < repeat):
                current_repeat += 1
                total_events = len(events)

                for idx, ev_dict in enumerate(events):
                    if not self._playing:
                        return

                    if self._on_progress:
                        self._on_progress(
                            current_repeat, total_repeats, idx + 1, total_events
                        )

                    ev = dict_to_event(ev_dict)

                    # Wait for correct timing
                    if idx == 0:
                        prev_ts = 0.0
                    else:
                        prev_ts = events[idx - 1].get("timestamp", 0.0)
                    delay = (ev.timestamp - prev_ts) / speed
                    if delay > 0:
                        # Sleep in small increments so we can respond to stop()
                        end = time.perf_counter() + delay
                        while time.perf_counter() < end and self._playing:
                            time.sleep(min(0.01, max(0, end - time.perf_counter())))

                    if not self._playing:
                        return

                    self._dispatch(ev)

        finally:
            self._playing = False
            if self._on_status_change:
                self._on_status_change(False)

    def _dispatch(self, ev):
        if isinstance(ev, MouseMoveEvent):
            self._mouse.position = (ev.x, ev.y)

        elif isinstance(ev, MouseClickEvent):
            btn = getattr(Button, ev.button, Button.left)
            self._mouse.position = (ev.x, ev.y)
            if ev.pressed:
                self._mouse.press(btn)
            else:
                self._mouse.release(btn)

        elif isinstance(ev, MouseScrollEvent):
            self._mouse.position = (ev.x, ev.y)
            self._mouse.scroll(ev.dx, ev.dy)

        elif isinstance(ev, KeyEvent):
            self._dispatch_key(ev)

    @staticmethod
    def _dispatch_key(ev: KeyEvent):
        """Replay a keyboard event using Quartz (exact keycode match)."""
        cg_event = Quartz.CGEventCreateKeyboardEvent(None, ev.keycode, ev.pressed)
        if cg_event is not None:
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, cg_event)
