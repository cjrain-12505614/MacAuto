#!/usr/bin/env python3
"""
Mac Auto — macOS 매크로 녹화 & 재생 자동화 도구
"""

import sys
import os
import tkinter as tk


def request_accessibility():
    """
    Use AXIsProcessTrustedWithOptions to trigger the macOS system
    accessibility permission prompt.  Returns True if already trusted.
    """
    if sys.platform != "darwin":
        return True
    try:
        import HIServices
        options = {HIServices.kAXTrustedCheckOptionPrompt: True}
        return HIServices.AXIsProcessTrustedWithOptions(options)
    except Exception:
        # Fallback: try via ApplicationServices
        try:
            from ApplicationServices import (
                AXIsProcessTrustedWithOptions,
                kAXTrustedCheckOptionPrompt,
            )
            options = {kAXTrustedCheckOptionPrompt: True}
            return AXIsProcessTrustedWithOptions(options)
        except Exception:
            return False


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
