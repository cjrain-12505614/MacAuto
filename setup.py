"""
py2app build configuration for Mac Auto.

Usage:
    python3 setup.py py2app        # standalone build
    python3 setup.py py2app -A     # alias (dev) build
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = []
OPTIONS = {
    "argv_emulation": False,
    "iconfile": "icon.icns",
    "plist": {
        "CFBundleName": "Mac Auto",
        "CFBundleDisplayName": "Mac Auto",
        "CFBundleIdentifier": "com.macauto.app",
        "CFBundleVersion": "1.0.0",
        "CFBundleShortVersionString": "1.0.0",
        "NSAccessibilityUsageDescription": (
            "매크로 녹화 및 재생을 위해 접근성 권한이 필요합니다."
        ),
        "NSHumanReadableCopyright": "Mac Auto © 2026",
        "LSMinimumSystemVersion": "12.0",
    },
    "includes": [
        "pynput",
        "pynput.mouse",
        "pynput.mouse._darwin",
        "pynput.keyboard",
        "pynput.keyboard._darwin",
        "Quartz",
        "CoreFoundation",
        "Foundation",
        "AppKit",
        "objc",
        "HIServices",
        "settings",
        "tkinter",
        "_tkinter",
    ],
    "packages": [
        "pynput",
        "objc",
    ],
    "frameworks": [],
    "resources": [],
}

setup(
    name="Mac Auto",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
