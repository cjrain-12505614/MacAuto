#!/usr/bin/env python3
"""
Mac Auto — macOS 매크로 녹화 & 재생 자동화 도구
"""

import sys
import os
import tkinter as tk


_PROMPT_MARKER = os.path.join(
    os.path.expanduser("~"),
    "Library", "Application Support", "Mac Auto", ".accessibility_prompted",
)


def _check_trusted(prompt: bool = False) -> bool:
    """Check accessibility trust, optionally triggering the system prompt."""
    try:
        import HIServices
        opts = {HIServices.kAXTrustedCheckOptionPrompt: prompt}
        return HIServices.AXIsProcessTrustedWithOptions(opts)
    except Exception:
        try:
            from ApplicationServices import (
                AXIsProcessTrustedWithOptions,
                kAXTrustedCheckOptionPrompt,
            )
            opts = {kAXTrustedCheckOptionPrompt: prompt}
            return AXIsProcessTrustedWithOptions(opts)
        except Exception:
            return False


def request_accessibility() -> bool:
    """
    Check macOS accessibility permission.
    - If already trusted → return True (no dialog).
    - If not trusted and first time → show system prompt once.
    - If not trusted but already prompted → skip dialog, return False.
    """
    if sys.platform != "darwin":
        return True

    # Silent check first — no dialog
    if _check_trusted(prompt=False):
        return True

    # Not trusted: always try to prompt
    # (macOS will handle the frequency of the actual system dialog)
    return _check_trusted(prompt=True)


def main():
    trusted = request_accessibility()

    from keyboard_monitor import KeyboardMonitor
    from gui import AutomationApp

    # Start the shared Quartz keyboard monitor
    kb_monitor = KeyboardMonitor()
    kb_monitor.start()

    # Wait briefly for the event tap to initialise
    kb_monitor.wait_for_ready(timeout=2.0)

    root = tk.Tk()
    app = AutomationApp(root, kb_monitor, accessibility_ok=trusted)

    # Handle clean shutdown
    def on_close():
        if app.recorder.is_recording:
            app.recorder.stop()
        if app.player.is_playing:
            app.player.stop()
        kb_monitor.stop()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
