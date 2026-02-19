"""
Storage — save / load / list / delete patterns as JSON files.
"""

import os
import json
import re
from typing import List, Optional
from datetime import datetime

from models import Pattern


def _get_default_dir() -> str:
    """
    Return the default patterns directory.
    Uses ~/Library/Application Support/Mac Auto/patterns so it works
    both when running as a .app bundle (py2app zips source files)
    and during development.
    """
    support = os.path.join(
        os.path.expanduser("~"),
        "Library", "Application Support", "Mac Auto", "patterns",
    )
    return support


_DEFAULT_DIR = _get_default_dir()


def _ensure_dir(directory: str):
    os.makedirs(directory, exist_ok=True)


def _safe_filename(name: str) -> str:
    """Sanitise pattern name for use as a filename."""
    return re.sub(r'[^\w\-가-힣 ]', '_', name).strip()


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def save_pattern(name: str, events: list, directory: str = _DEFAULT_DIR) -> str:
    """Save events under the given name. Returns the file path."""
    _ensure_dir(directory)
    pattern = Pattern(
        name=name,
        events=events,
        created_at=datetime.now().isoformat(),
    )
    path = os.path.join(directory, f"{_safe_filename(name)}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(pattern.to_json())
    return path


def load_pattern(name: str, directory: str = _DEFAULT_DIR) -> Optional[Pattern]:
    path = os.path.join(directory, f"{_safe_filename(name)}.json")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return Pattern.from_json(f.read())


def list_patterns(directory: str = _DEFAULT_DIR) -> List[str]:
    """Return a sorted list of pattern names."""
    _ensure_dir(directory)
    names = []
    for fn in sorted(os.listdir(directory)):
        if fn.endswith(".json"):
            try:
                with open(os.path.join(directory, fn), encoding="utf-8") as f:
                    data = json.loads(f.read())
                    names.append(data.get("name", fn[:-5]))
            except Exception:
                names.append(fn[:-5])
    return names


def delete_pattern(name: str, directory: str = _DEFAULT_DIR) -> bool:
    path = os.path.join(directory, f"{_safe_filename(name)}.json")
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def rename_pattern(old_name: str, new_name: str, directory: str = _DEFAULT_DIR) -> bool:
    old_path = os.path.join(directory, f"{_safe_filename(old_name)}.json")
    if not os.path.isfile(old_path):
        return False
    with open(old_path, "r", encoding="utf-8") as f:
        p = Pattern.from_json(f.read())
    p.name = new_name
    new_path = os.path.join(directory, f"{_safe_filename(new_name)}.json")
    with open(new_path, "w", encoding="utf-8") as f:
        f.write(p.to_json())
    if old_path != new_path:
        os.remove(old_path)
    return True
