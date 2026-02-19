"""
Settings — persistent app configuration stored in
~/Library/Application Support/Mac Auto/settings.json.
"""

import os
import json
from typing import Dict, Any

_SUPPORT_DIR = os.path.join(
    os.path.expanduser("~"),
    "Library", "Application Support", "Mac Auto",
)
_SETTINGS_FILE = os.path.join(_SUPPORT_DIR, "settings.json")


# ── Modifier display helpers ─────────────────────────────────────
# Quartz modifier flag values (these are stable across macOS versions)
_MOD_CMD   = 0x00100000   # kCGEventFlagMaskCommand
_MOD_SHIFT = 0x00020000   # kCGEventFlagMaskShift
_MOD_OPT   = 0x00080000   # kCGEventFlagMaskAlternate
_MOD_CTRL  = 0x00040000   # kCGEventFlagMaskControl

# order: ctrl → opt → shift → cmd (macOS convention)
_MOD_SYMBOLS = [
    (_MOD_CTRL,  "⌃"),
    (_MOD_OPT,   "⌥"),
    (_MOD_SHIFT, "⇧"),
    (_MOD_CMD,   "⌘"),
]

# keycode → uppercase display name
KEYCODE_DISPLAY: Dict[int, str] = {
    0: "A", 1: "S", 2: "D", 3: "F", 4: "H", 5: "G", 6: "Z", 7: "X",
    8: "C", 9: "V", 11: "B", 12: "Q", 13: "W", 14: "E",
    15: "R", 16: "Y", 17: "T", 18: "1", 19: "2", 20: "3", 21: "4",
    22: "6", 23: "5", 24: "=", 25: "9", 26: "7", 27: "-", 28: "8",
    29: "0", 30: "]", 31: "O", 32: "U", 33: "[", 34: "I", 35: "P",
    36: "↩", 37: "L", 38: "J", 40: "K",
    43: ",", 44: "/", 45: "N", 46: "M", 47: ".",
    48: "⇥", 49: "Space", 50: "`", 51: "⌫",
    53: "ESC",
    96: "F5", 97: "F6", 98: "F7", 99: "F3", 100: "F8",
    101: "F9", 103: "F11", 109: "F10", 111: "F12",
    118: "F4", 120: "F2", 122: "F1",
    123: "←", 124: "→", 125: "↓", 126: "↑",
}


def modifier_display(mod_mask: int) -> str:
    """Convert a modifier bitmask to a symbol string like '⌘⇧'."""
    parts = []
    for flag, sym in _MOD_SYMBOLS:
        if mod_mask & flag:
            parts.append(sym)
    return "".join(parts)


def hotkey_display(keycode: int, modifiers: int) -> str:
    """Human-readable hotkey label, e.g. '⌘⇧R'."""
    mod_str = modifier_display(modifiers)
    key_str = KEYCODE_DISPLAY.get(keycode, f"Key{keycode}")
    return f"{mod_str}{key_str}"


# ── Default hotkey configuration ─────────────────────────────────

def get_default_hotkeys() -> Dict[str, Dict[str, Any]]:
    return {
        "toggle_record": {
            "keycode": 101,            # F9
            "modifiers": 0,
        },
        "start_playback": {
            "keycode": 109,            # F10
            "modifiers": 0,
        },
        "stop": {
            "keycode": 53,             # ESC
            "modifiers": 0,
        },
    }


# macOS modifier virtual keycodes (these are NOT regular keys)
MODIFIER_KEYCODES = {54, 55, 56, 57, 58, 59, 60, 61, 62, 63}

# tkinter modifier keysym names (skip these during key capture)
MODIFIER_KEYSYMS = {
    "Shift_L", "Shift_R", "Control_L", "Control_R",
    "Meta_L", "Meta_R", "Alt_L", "Alt_R",
    "Super_L", "Super_R", "Caps_Lock",
}

# tkinter event.keysym → Quartz virtual keycode
KEYSYM_TO_QUARTZ: Dict[str, int] = {
    # Letters
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5,
    "z": 6, "x": 7, "c": 8, "v": 9, "b": 11,
    "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17,
    "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38,
    "k": 40, "n": 45, "m": 46,
    # Numbers
    "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22,
    "7": 26, "8": 28, "9": 25, "0": 29,
    # Symbols
    "minus": 27, "equal": 24, "bracketleft": 33, "bracketright": 30,
    "semicolon": 41, "quoteright": 39, "quoteleft": 50,
    "apostrophe": 39, "grave": 50,
    "backslash": 42, "comma": 43, "period": 47, "slash": 44,
    # Special keys
    "Return": 36, "Tab": 48, "space": 49, "BackSpace": 51,
    "Escape": 53, "Delete": 117,
    # Arrow keys
    "Left": 123, "Right": 124, "Down": 125, "Up": 126,
    # Navigation
    "Home": 115, "End": 119, "Prior": 116, "Next": 121,  # PgUp/PgDn
    # Function keys
    "F1": 122, "F2": 120, "F3": 99, "F4": 118, "F5": 96,
    "F6": 97, "F7": 98, "F8": 100, "F9": 101, "F10": 109,
    "F11": 103, "F12": 111, "F13": 105, "F14": 107, "F15": 113,
}


def tk_keysym_to_quartz(keysym: str) -> int:
    """
    Convert a tkinter event.keysym string to a Quartz virtual keycode.
    Returns -1 if the keysym is unknown.
    """
    # Try exact match first
    code = KEYSYM_TO_QUARTZ.get(keysym)
    if code is not None:
        return code
    # Try lowercase (tkinter sends uppercase for letters when Shift is held)
    code = KEYSYM_TO_QUARTZ.get(keysym.lower())
    if code is not None:
        return code
    return -1


def tk_state_to_quartz_mods(tk_state: int) -> int:
    """
    Convert tkinter event.state modifier bits (macOS Aqua Tk)
    into Quartz CGEvent flag mask.
    """
    mods = 0
    if tk_state & 0x0001:  # Shift
        mods |= _MOD_SHIFT
    if tk_state & 0x0004:  # Control
        mods |= _MOD_CTRL
    if tk_state & 0x0008:  # Command / Meta
        mods |= _MOD_CMD
    if tk_state & 0x0010:  # Option / Alt
        mods |= _MOD_OPT
    return mods


# ── Load / Save ──────────────────────────────────────────────────

def load_settings() -> Dict[str, Any]:
    """Load settings from disk, returning defaults where missing."""
    defaults = {"hotkeys": get_default_hotkeys()}
    if not os.path.isfile(_SETTINGS_FILE):
        return defaults
    try:
        with open(_SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge: ensure all keys exist
        hotkeys = defaults["hotkeys"]
        saved = data.get("hotkeys", {})
        for action in hotkeys:
            if action in saved and "keycode" in saved[action]:
                hotkeys[action] = saved[action]
        data["hotkeys"] = hotkeys
        return data
    except Exception:
        return defaults


def save_settings(settings: Dict[str, Any]):
    """Persist settings to disk."""
    os.makedirs(_SUPPORT_DIR, exist_ok=True)
    with open(_SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
