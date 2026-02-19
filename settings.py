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
