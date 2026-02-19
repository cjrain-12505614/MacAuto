"""
Event data models for mac_auto.
All events store a relative timestamp (seconds from recording start).
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import json


# ---------------------------------------------------------------------------
# Event types
# ---------------------------------------------------------------------------

@dataclass
class MouseMoveEvent:
    event_type: str = field(default="mouse_move", init=False)
    x: int = 0
    y: int = 0
    timestamp: float = 0.0


@dataclass
class MouseClickEvent:
    event_type: str = field(default="mouse_click", init=False)
    x: int = 0
    y: int = 0
    button: str = "left"
    pressed: bool = True
    timestamp: float = 0.0


@dataclass
class MouseScrollEvent:
    event_type: str = field(default="mouse_scroll", init=False)
    x: int = 0
    y: int = 0
    dx: int = 0
    dy: int = 0
    timestamp: float = 0.0


@dataclass
class KeyEvent:
    event_type: str = field(default="key", init=False)
    key: str = ""          # human-readable name (for display)
    keycode: int = 0       # macOS virtual key code (for replay)
    pressed: bool = True
    timestamp: float = 0.0


# Union type alias
Event = MouseMoveEvent | MouseClickEvent | MouseScrollEvent | KeyEvent


# ---------------------------------------------------------------------------
# Pattern — a named sequence of events
# ---------------------------------------------------------------------------

@dataclass
class Pattern:
    name: str = ""
    events: List[dict] = field(default_factory=list)
    created_at: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "Pattern":
        data = json.loads(raw)
        return cls(**data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def event_to_dict(ev: Event) -> dict:
    return asdict(ev)


def dict_to_event(d: dict) -> Event:
    d = dict(d)  # copy so we don't mutate the original
    t = d.pop("event_type")

    # Handle legacy 'vk' field from older saved patterns
    if t == "key":
        vk = d.pop("vk", None)
        if "keycode" not in d:
            d["keycode"] = vk if vk is not None else 0

    mapping = {
        "mouse_move": MouseMoveEvent,
        "mouse_click": MouseClickEvent,
        "mouse_scroll": MouseScrollEvent,
        "key": KeyEvent,
    }
    cls = mapping.get(t)
    if cls is None:
        raise ValueError(f"Unknown event type: {t}")
    return cls(**d)
