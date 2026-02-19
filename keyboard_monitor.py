"""
Quartz-based keyboard event monitor for macOS.

Uses a CGEventTap (listen-only) to capture keyboard events without calling
TSMGetInputSourceProperty — which crashes on background threads on macOS 15+.

This module replaces pynput's keyboard.Listener to avoid the crash.
"""

import threading
from typing import Callable, Dict, List, Optional, Tuple

import Quartz

import os
import logging

# Setup debug logging
DEBUG_LOG = os.path.join(os.path.expanduser("~"), "mac_auto_debug.log")
logging.basicConfig(
    filename=DEBUG_LOG,
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# macOS virtual key-code → human-readable name
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

KEYCODE_MAP: Dict[int, str] = {
    0: "a", 1: "s", 2: "d", 3: "f", 4: "h", 5: "g", 6: "z", 7: "x",
    8: "c", 9: "v", 10: "section", 11: "b", 12: "q", 13: "w", 14: "e",
    15: "r", 16: "y", 17: "t", 18: "1", 19: "2", 20: "3", 21: "4",
    22: "6", 23: "5", 24: "=", 25: "9", 26: "7", 27: "-", 28: "8",
    29: "0", 30: "]", 31: "o", 32: "u", 33: "[", 34: "i", 35: "p",
    36: "return", 37: "l", 38: "j", 39: "'", 40: "k", 41: ";",
    42: "\\", 43: ",", 44: "/", 45: "n", 46: "m", 47: ".",
    48: "tab", 49: "space", 50: "`", 51: "backspace",
    53: "escape",
    54: "cmd_right", 55: "cmd", 56: "shift", 57: "caps_lock",
    58: "option", 59: "control", 60: "shift_right",
    61: "option_right", 62: "control_right", 63: "fn",
    64: "f17", 65: "keypad_.", 67: "keypad_*", 69: "keypad_+",
    71: "keypad_clear", 75: "keypad_/", 76: "keypad_enter",
    78: "keypad_-",
    82: "keypad_0", 83: "keypad_1", 84: "keypad_2", 85: "keypad_3",
    86: "keypad_4", 87: "keypad_5", 88: "keypad_6", 89: "keypad_7",
    91: "keypad_8", 92: "keypad_9",
    96: "f5", 97: "f6", 98: "f7", 99: "f3", 100: "f8",
    101: "f9", 103: "f11", 105: "f13", 107: "f14",
    109: "f10", 111: "f12", 113: "f15", 114: "help",
    115: "home", 116: "page_up", 117: "delete_forward", 118: "f4",
    119: "end", 120: "f2", 121: "page_down", 122: "f1",
    123: "left", 124: "right", 125: "down", 126: "up",
}

# Well-known keycodes
KEYCODE_F9 = 101
KEYCODE_F10 = 109
KEYCODE_ESC = 53
KEYCODE_R = 15
KEYCODE_P = 35

# Modifier masks for hotkey combos
MOD_CMD = Quartz.kCGEventFlagMaskCommand
MOD_SHIFT = Quartz.kCGEventFlagMaskShift
MOD_CMD_SHIFT = MOD_CMD | MOD_SHIFT

# Modifier keycode → corresponding CGEvent flag mask
_MODIFIER_KEY_FLAGS: Dict[int, int] = {
    54: Quartz.kCGEventFlagMaskCommand,
    55: Quartz.kCGEventFlagMaskCommand,
    56: Quartz.kCGEventFlagMaskShift,
    57: Quartz.kCGEventFlagMaskAlphaShift,
    58: Quartz.kCGEventFlagMaskAlternate,
    59: Quartz.kCGEventFlagMaskControl,
    60: Quartz.kCGEventFlagMaskShift,
    61: Quartz.kCGEventFlagMaskAlternate,
    62: Quartz.kCGEventFlagMaskControl,
    63: getattr(Quartz, "kCGEventFlagMaskSecondaryFn", 0x00800000),
}

# CGEvent tap-disabled sentinel (re-enable when system times out the tap)
_TAP_DISABLED_BY_TIMEOUT = getattr(
    Quartz, "kCGEventTapDisabledByTimeout", 0xFFFFFFFE
)

# Mask to isolate only the modifier flags we care about (ignore caps lock etc.)
_INTERESTING_MODIFIERS = (
    Quartz.kCGEventFlagMaskCommand
    | Quartz.kCGEventFlagMaskShift
    | Quartz.kCGEventFlagMaskAlternate
    | Quartz.kCGEventFlagMaskControl
)

# Callback signature: (keycode: int, key_name: str, is_down: bool)
KeyCallback = Callable[[int, str, bool], None]

# Hotkey: (keycode, required_modifier_mask)  →  0 = any modifiers OK
HotkeyKey = Tuple[int, int]


class KeyboardMonitor:
    """
    Global keyboard monitor using a Quartz CGEventTap (listen-only).
    • Dispatches registered hotkey callbacks on key-down.
    • Dispatches general key-event callbacks for recording.
    """

    def __init__(self):
        self._hotkeys: Dict[HotkeyKey, Callable] = {}
        self._callbacks: List[KeyCallback] = []
        self._capture_cb: Optional[Callable[[int, int], None]] = None
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._run_loop_ref = None
        self._tap_port = None
        self._running = False
        self._ready_event = threading.Event()
        self.tap_created = False  # public flag for status checking

    # ── public API ───────────────────────────────────────────────

    def add_hotkey(self, keycode: int, callback: Callable,
                   modifiers: int = 0):
        """
        Register a global hotkey callback (key-down only).

        modifiers=0        → fire on this key regardless of modifiers
        modifiers=MOD_CMD  → fire only when Cmd is held
        modifiers=MOD_CMD_SHIFT → fire only when Cmd+Shift are held
        """
        with self._lock:
            self._hotkeys[(keycode, modifiers)] = callback

    def add_event_callback(self, cb: KeyCallback):
        with self._lock:
            self._callbacks.append(cb)

    def remove_event_callback(self, cb: KeyCallback):
        with self._lock:
            if cb in self._callbacks:
                self._callbacks.remove(cb)

    def clear_hotkeys(self):
        """Remove all registered hotkeys (used before re-registering)."""
        with self._lock:
            self._hotkeys.clear()

    def set_capture_callback(self, cb: Optional[Callable[[int, int], None]]):
        """
        Enable one-shot key capture mode for the settings dialog.
        cb(keycode, modifiers) is called on the next key-down, then cleared.
        Pass None to cancel capture mode.
        """
        with self._lock:
            self._capture_cb = cb

    def wait_for_ready(self, timeout: float = 2.0) -> bool:
        """Block until the event tap is created (or timeout). Returns tap_created."""
        self._ready_event.wait(timeout)
        return self.tap_created

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._run_loop_ref is not None:
            Quartz.CFRunLoopStop(self._run_loop_ref)

    # ── internals ────────────────────────────────────────────────

    def _tap_callback(self, proxy, event_type, event, refcon):
        """Called by Quartz for every keyboard event."""
        # Re-enable tap if system disabled it
        if event_type == _TAP_DISABLED_BY_TIMEOUT:
            if self._tap_port is not None:
                Quartz.CGEventTapEnable(self._tap_port, True)
            return event

        if event_type not in (
            Quartz.kCGEventKeyDown,
            Quartz.kCGEventKeyUp,
            Quartz.kCGEventFlagsChanged,
        ):
            return event

        keycode = Quartz.CGEventGetIntegerValueField(
            event, Quartz.kCGKeyboardEventKeycode
        )
        key_name = KEYCODE_MAP.get(keycode, f"key_{keycode}")
        flags = Quartz.CGEventGetFlags(event)
        active_mods = flags & _INTERESTING_MODIFIERS

        # Determine press vs release
        logging.debug(f"Event: type={event_type}, keycode={keycode}, flags={flags}")


        if event_type == Quartz.kCGEventFlagsChanged:
            flag_mask = _MODIFIER_KEY_FLAGS.get(keycode)
            if flag_mask is not None:
                is_down = bool(flags & flag_mask)
            else:
                is_down = True
        else:
            is_down = (event_type == Quartz.kCGEventKeyDown)

        # Dispatch hotkeys (key-down only)
        if is_down and event_type == Quartz.kCGEventKeyDown:
            # One-shot capture mode (for settings dialog)
            with self._lock:
                capture = self._capture_cb
                if capture is not None:
                    self._capture_cb = None
            if capture is not None:
                try:
                    capture(keycode, active_mods)
                except Exception:
                    pass
                return event  # don't fire normal hotkeys during capture

            with self._lock:
                hotkeys_snapshot = dict(self._hotkeys)
            for (hk_keycode, hk_mods), hk_cb in hotkeys_snapshot.items():
                if keycode != hk_keycode:
                    continue
                # modifiers=0 means "match regardless of modifiers"
                if hk_mods == 0 or (active_mods & hk_mods) == hk_mods:
                    try:
                        hk_cb()
                    except Exception:
                        pass

        # Dispatch general callbacks
        with self._lock:
            cbs = list(self._callbacks)
        for cb in cbs:
            try:
                cb(keycode, key_name, is_down)
            except Exception:
                pass

        return event

    def _run(self):
        event_mask = (
            (1 << Quartz.kCGEventKeyDown)
            | (1 << Quartz.kCGEventKeyUp)
            | (1 << Quartz.kCGEventFlagsChanged)
        )

        self._tap_port = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionListenOnly,
            event_mask,
            self._tap_callback,
            None,
        )

        if self._tap_port is None:
            logging.error("CGEventTapCreate failed (requires Accessibility permissions).")
            print(
                "⚠️  키보드 이벤트 탭 생성 실패.\n"
                "   시스템 설정 > 개인정보 보호 및 보안 > 접근성 권한을 확인하세요."
            )
            self._running = False
            self.tap_created = False
            self._ready_event.set()
            return

        logging.info("CGEventTap created successfully.")
        self.tap_created = True
        self._ready_event.set()

        source = Quartz.CFMachPortCreateRunLoopSource(None, self._tap_port, 0)
        self._run_loop_ref = Quartz.CFRunLoopGetCurrent()
        Quartz.CFRunLoopAddSource(
            self._run_loop_ref, source, Quartz.kCFRunLoopDefaultMode
        )
        Quartz.CGEventTapEnable(self._tap_port, True)

        # This blocks until CFRunLoopStop is called
        Quartz.CFRunLoopRun()
        self._running = False
