"""
GUI — tkinter-based interface for mac_auto.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Optional, Dict, Any
import subprocess, sys

from keyboard_monitor import KeyboardMonitor, KEYCODE_ESC
from recorder import Recorder
from player import Player
import storage
import settings as app_settings


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Colour palette & style constants
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BG           = "#1e1e2e"
BG_SECONDARY = "#282840"
BG_CARD      = "#313152"
FG           = "#cdd6f4"
FG_DIM       = "#6c7086"
ACCENT       = "#89b4fa"
ACCENT_HOVER = "#74c7ec"
RED          = "#f38ba8"
RED_HOVER    = "#eba0ac"
GREEN        = "#a6e3a1"
GREEN_HOVER  = "#94e2d5"
YELLOW       = "#f9e2af"
ORANGE       = "#fab387"
BORDER       = "#45475a"
FONT         = ("SF Pro Text", 13)
FONT_SM      = ("SF Pro Text", 11)
FONT_LG      = ("SF Pro Text", 15, "bold")
FONT_TITLE   = ("SF Pro Display", 20, "bold")
FONT_MONO    = ("SF Mono", 12)

# Action labels
ACTION_LABELS = {
    "toggle_record": "녹화 시작/중지",
    "start_playback": "재생 시작",
    "stop": "중지 (재생/녹화)",
}


class AutomationApp:
    def __init__(self, root: tk.Tk, kb_monitor: KeyboardMonitor,
                 accessibility_ok: bool = True):
        self.root = root
        self.kb_monitor = kb_monitor
        self.recorder = Recorder(kb_monitor)
        self.player = Player()

        # State
        self._selected_pattern: Optional[str] = None
        self._settings = app_settings.load_settings()
        self._accessibility_ok = accessibility_ok

        # Configure root
        self.root.title("Mac Auto — 매크로 자동화")
        self.root.geometry("720x680")
        self.root.minsize(640, 600)
        self.root.configure(bg=BG)
        self.root.option_add("*TCombobox*Listbox.background", BG_CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", FG)

        # Callbacks
        self.recorder.set_status_callback(self._on_record_status)
        self.player.set_status_callback(self._on_play_status)
        self.player.set_progress_callback(self._on_progress)

        self._setup_styles()
        self._build_ui()
        self._refresh_pattern_list()
        self._register_hotkeys()

        # Check tap status after a brief delay
        self.root.after(500, self._check_tap_status)

    # ──────────────────────────────────────────────────────────────
    # Styles
    # ──────────────────────────────────────────────────────────────

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=BG_CARD)
        style.configure("TLabel", background=BG, foreground=FG, font=FONT)
        style.configure("Card.TLabel", background=BG_CARD, foreground=FG, font=FONT)
        style.configure("Title.TLabel", background=BG, foreground=FG, font=FONT_TITLE)
        style.configure("Dim.TLabel", background=BG, foreground=FG_DIM, font=FONT_SM)
        style.configure("CardDim.TLabel", background=BG_CARD, foreground=FG_DIM, font=FONT_SM)
        style.configure("Status.TLabel", background=BG, foreground=YELLOW, font=FONT_MONO)
        style.configure("WarnBanner.TLabel", background="#45200a",
                         foreground=ORANGE, font=FONT_SM)
        style.configure("OkBanner.TLabel", background="#1a3a1a",
                         foreground=GREEN, font=FONT_SM)

        # Accent button
        style.configure(
            "Accent.TButton",
            background=ACCENT, foreground=BG, font=FONT,
            padding=(16, 8), borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])

        # Red button
        style.configure(
            "Red.TButton",
            background=RED, foreground=BG, font=FONT,
            padding=(16, 8), borderwidth=0,
        )
        style.map("Red.TButton", background=[("active", RED_HOVER)])

        # Green button
        style.configure(
            "Green.TButton",
            background=GREEN, foreground=BG, font=FONT,
            padding=(16, 8), borderwidth=0,
        )
        style.map("Green.TButton", background=[("active", GREEN_HOVER)])

        # Default button
        style.configure(
            "TButton",
            background=BG_SECONDARY, foreground=FG, font=FONT,
            padding=(12, 6), borderwidth=0,
        )
        style.map("TButton", background=[("active", BORDER)])

        # Scale / slider
        style.configure(
            "TScale",
            background=BG, troughcolor=BG_SECONDARY,
        )

        # Spinbox
        style.configure("TSpinbox", fieldbackground=BG_CARD, foreground=FG, font=FONT)

    # ──────────────────────────────────────────────────────────────
    # Hotkey helpers
    # ──────────────────────────────────────────────────────────────

    def _hk_display(self, action: str) -> str:
        """Return human-readable label for a hotkey action."""
        hk = self._settings["hotkeys"].get(action, {})
        return app_settings.hotkey_display(
            hk.get("keycode", 0), hk.get("modifiers", 0)
        )

    def _register_hotkeys(self):
        """Register all hotkeys from current settings onto the KeyboardMonitor."""
        self.kb_monitor.clear_hotkeys()
        hotkeys = self._settings["hotkeys"]

        # Toggle record
        rec = hotkeys["toggle_record"]
        self.kb_monitor.add_hotkey(
            rec["keycode"],
            lambda: self.root.after(0, self._toggle_record),
            modifiers=rec.get("modifiers", 0),
        )

        # Start playback
        play = hotkeys["start_playback"]
        self.kb_monitor.add_hotkey(
            play["keycode"],
            lambda: self.root.after(0, self._start_playback),
            modifiers=play.get("modifiers", 0),
        )

        # Stop
        stop = hotkeys["stop"]
        self.kb_monitor.add_hotkey(
            stop["keycode"],
            lambda: self.root.after(0, self._on_esc),
            modifiers=stop.get("modifiers", 0),
        )

    def _check_tap_status(self):
        """Update accessibility banner based on actual tap status."""
        tap_ok = self.kb_monitor.tap_created
        if tap_ok:
            self.lbl_banner.configure(
                text="✅ 글로벌 단축키 활성화됨",
                style="OkBanner.TLabel",
            )
        else:
            self.lbl_banner.configure(
                text="⚠️ 접근성 권한 필요 — 시스템 설정 > 접근성에서 Mac Auto에 권한을 허용하세요",
                style="WarnBanner.TLabel",
            )

    # ──────────────────────────────────────────────────────────────
    # UI construction
    # ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Main container
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill=tk.BOTH, expand=True)

        # Title row
        title_frame = ttk.Frame(container)
        title_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(title_frame, text="⌨️ Mac Auto", style="Title.TLabel").pack(side=tk.LEFT)
        ttk.Label(title_frame, text="매크로 녹화 & 재생", style="Dim.TLabel").pack(
            side=tk.LEFT, padx=(12, 0), pady=(6, 0)
        )

        # Settings button
        ttk.Button(
            title_frame, text="⚙️ 단축키 설정",
            command=self._open_settings,
        ).pack(side=tk.RIGHT)

        # ── Accessibility / tap status banner ──
        self.lbl_banner = ttk.Label(
            container, text="⏳ 글로벌 단축키 확인 중...",
            style="OkBanner.TLabel", padding=(8, 4),
        )
        self.lbl_banner.pack(fill=tk.X, pady=(0, 8))

        # ── Recording card ──
        rec_card = ttk.Frame(container, style="Card.TFrame", padding=16)
        rec_card.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(rec_card, text="🔴 녹화", style="Card.TLabel", font=FONT_LG).pack(anchor=tk.W)
        self.lbl_rec_hint = ttk.Label(
            rec_card,
            text=f"{self._hk_display('toggle_record')} 키를 눌러 녹화 시작/중지",
            style="CardDim.TLabel",
        )
        self.lbl_rec_hint.pack(anchor=tk.W, pady=(2, 8))

        rec_btn_frame = ttk.Frame(rec_card, style="Card.TFrame")
        rec_btn_frame.pack(fill=tk.X)

        self.btn_record = ttk.Button(
            rec_btn_frame,
            text=f"● 녹화 시작  ({self._hk_display('toggle_record')})",
            style="Red.TButton",
            command=self._toggle_record,
        )
        self.btn_record.pack(side=tk.LEFT)

        self.lbl_rec_status = ttk.Label(
            rec_btn_frame, text="대기 중", style="Card.TLabel",
        )
        self.lbl_rec_status.pack(side=tk.LEFT, padx=(16, 0))

        # ── Pattern list card ──
        list_card = ttk.Frame(container, style="Card.TFrame", padding=16)
        list_card.pack(fill=tk.BOTH, expand=True, pady=(0, 12))

        list_header = ttk.Frame(list_card, style="Card.TFrame")
        list_header.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(list_header, text="📁 저장된 패턴", style="Card.TLabel", font=FONT_LG).pack(
            side=tk.LEFT
        )

        btn_del = ttk.Button(
            list_header, text="🗑 삭제", command=self._delete_selected,
        )
        btn_del.pack(side=tk.RIGHT, padx=(8, 0))

        btn_rename = ttk.Button(
            list_header, text="✏️ 이름 변경", command=self._rename_selected,
        )
        btn_rename.pack(side=tk.RIGHT)

        # Listbox
        list_inner = ttk.Frame(list_card, style="Card.TFrame")
        list_inner.pack(fill=tk.BOTH, expand=True)

        self.pattern_list = tk.Listbox(
            list_inner,
            bg=BG_SECONDARY, fg=FG, selectbackground=ACCENT, selectforeground=BG,
            font=FONT, borderwidth=0, highlightthickness=0, activestyle="none",
        )
        self.pattern_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pattern_list.bind("<<ListboxSelect>>", self._on_select_pattern)

        scrollbar = ttk.Scrollbar(list_inner, orient=tk.VERTICAL, command=self.pattern_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pattern_list.config(yscrollcommand=scrollbar.set)

        # ── Playback card ──
        play_card = ttk.Frame(container, style="Card.TFrame", padding=16)
        play_card.pack(fill=tk.X, pady=(0, 12))

        ttk.Label(play_card, text="▶️ 재생 설정", style="Card.TLabel", font=FONT_LG).pack(
            anchor=tk.W, pady=(0, 8)
        )

        settings_frame = ttk.Frame(play_card, style="Card.TFrame")
        settings_frame.pack(fill=tk.X, pady=(0, 8))

        # Repeat count
        ttk.Label(settings_frame, text="반복 횟수", style="Card.TLabel").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 8)
        )
        self.var_repeat = tk.IntVar(value=1)
        spin_repeat = tk.Spinbox(
            settings_frame, from_=0, to=9999, textvariable=self.var_repeat,
            width=6, bg=BG_SECONDARY, fg=FG, font=FONT, borderwidth=0,
            buttonbackground=BG_CARD, insertbackground=FG,
        )
        spin_repeat.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(settings_frame, text="(0 = 무한)", style="CardDim.TLabel").grid(
            row=0, column=2, sticky=tk.W, padx=(6, 24)
        )

        # Speed multiplier
        ttk.Label(settings_frame, text="속도 배수", style="Card.TLabel").grid(
            row=0, column=3, sticky=tk.W, padx=(0, 8)
        )
        self.var_speed = tk.DoubleVar(value=1.0)
        self.speed_scale = tk.Scale(
            settings_frame, variable=self.var_speed, from_=0.1, to=10.0,
            resolution=0.1, orient=tk.HORIZONTAL, length=160,
            bg=BG_CARD, fg=FG, troughcolor=BG_SECONDARY, highlightthickness=0,
            borderwidth=0, activebackground=ACCENT, font=FONT_SM,
        )
        self.speed_scale.grid(row=0, column=4, sticky=tk.W)

        self.lbl_speed = ttk.Label(
            settings_frame, text="1.0x", style="Card.TLabel",
        )
        self.lbl_speed.grid(row=0, column=5, padx=(6, 0))
        self.var_speed.trace_add("write", lambda *_: self.lbl_speed.configure(
            text=f"{self.var_speed.get():.1f}x"
        ))

        # Play / stop buttons
        play_btn_frame = ttk.Frame(play_card, style="Card.TFrame")
        play_btn_frame.pack(fill=tk.X)

        self.btn_play = ttk.Button(
            play_btn_frame,
            text=f"▶ 재생 시작  ({self._hk_display('start_playback')})",
            style="Green.TButton",
            command=self._start_playback,
        )
        self.btn_play.pack(side=tk.LEFT)

        self.btn_stop = ttk.Button(
            play_btn_frame,
            text=f"⏹ 중지  ({self._hk_display('stop')})",
            style="Red.TButton",
            command=self._stop_playback,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=(8, 0))

        self.lbl_play_status = ttk.Label(
            play_btn_frame, text="", style="Card.TLabel",
        )
        self.lbl_play_status.pack(side=tk.LEFT, padx=(16, 0))

        # ── Status bar ──
        self.lbl_status = ttk.Label(container, text="준비됨", style="Status.TLabel")
        self.lbl_status.pack(fill=tk.X)

    # ──────────────────────────────────────────────────────────────
    # Hotkeys
    # ──────────────────────────────────────────────────────────────

    def _on_esc(self):
        if self.player.is_playing:
            self._stop_playback()
        elif self.recorder.is_recording:
            self.recorder.stop()

    # ──────────────────────────────────────────────────────────────
    # Settings dialog
    # ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        SettingsDialog(self.root, self.kb_monitor, self._settings, self._on_settings_saved)

    def _on_settings_saved(self, new_settings: Dict[str, Any]):
        """Called when the settings dialog saves new hotkeys."""
        self._settings = new_settings
        app_settings.save_settings(new_settings)
        self._register_hotkeys()
        self._update_button_labels()
        self._set_status("단축키 설정이 저장되었습니다.")

    def _update_button_labels(self):
        """Refresh all button texts and hints with current hotkey labels."""
        rec_label = self._hk_display("toggle_record")
        play_label = self._hk_display("start_playback")
        stop_label = self._hk_display("stop")

        self.btn_record.configure(text=f"● 녹화 시작  ({rec_label})")
        self.lbl_rec_hint.configure(text=f"{rec_label} 키를 눌러 녹화 시작/중지")
        self.btn_play.configure(text=f"▶ 재생 시작  ({play_label})")
        self.btn_stop.configure(text=f"⏹ 중지  ({stop_label})")

    # ──────────────────────────────────────────────────────────────
    # Recording
    # ──────────────────────────────────────────────────────────────

    def _toggle_record(self):
        if self.recorder.is_recording:
            self.recorder.stop()
        else:
            if self.player.is_playing:
                self._stop_playback()
            self.recorder.start()

    def _on_record_status(self, is_recording: bool):
        rec_label = self._hk_display("toggle_record")

        def _update():
            if is_recording:
                self.btn_record.configure(text=f"⏹ 녹화 중지  ({rec_label})")
                self.lbl_rec_status.configure(text="🔴 녹화 중...", foreground=RED)
                self._set_status(f"녹화 중입니다. {rec_label}을 눌러 중지하세요.")
            else:
                self.btn_record.configure(text=f"● 녹화 시작  ({rec_label})")
                events = self.recorder.events
                count = len(events)
                self.lbl_rec_status.configure(
                    text=f"✅ {count}개 이벤트 녹화 완료", foreground=GREEN,
                )
                self._set_status(f"녹화 완료: {count}개 이벤트")
                if count > 0:
                    self.root.after(100, self._ask_save)
        self.root.after(0, _update)

    def _ask_save(self):
        name = simpledialog.askstring(
            "패턴 저장",
            "패턴 이름을 입력하세요:",
            parent=self.root,
        )
        if name and name.strip():
            storage.save_pattern(name.strip(), self.recorder.events)
            self._refresh_pattern_list()
            self._set_status(f"패턴 '{name.strip()}'이(가) 저장되었습니다.")
        else:
            self._set_status("저장 취소됨")

    # ──────────────────────────────────────────────────────────────
    # Pattern list
    # ──────────────────────────────────────────────────────────────

    def _refresh_pattern_list(self):
        self.pattern_list.delete(0, tk.END)
        for name in storage.list_patterns():
            self.pattern_list.insert(tk.END, f"  {name}")
        self._selected_pattern = None

    def _on_select_pattern(self, _event):
        sel = self.pattern_list.curselection()
        if sel:
            self._selected_pattern = self.pattern_list.get(sel[0]).strip()
        else:
            self._selected_pattern = None

    def _delete_selected(self):
        if not self._selected_pattern:
            messagebox.showwarning("경고", "삭제할 패턴을 선택하세요.")
            return
        if messagebox.askyesno("삭제 확인", f"'{self._selected_pattern}'을(를) 삭제할까요?"):
            storage.delete_pattern(self._selected_pattern)
            self._refresh_pattern_list()
            self._set_status("패턴이 삭제되었습니다.")

    def _rename_selected(self):
        if not self._selected_pattern:
            messagebox.showwarning("경고", "이름을 변경할 패턴을 선택하세요.")
            return
        new_name = simpledialog.askstring(
            "이름 변경", f"'{self._selected_pattern}'의 새 이름:", parent=self.root
        )
        if new_name and new_name.strip():
            storage.rename_pattern(self._selected_pattern, new_name.strip())
            self._refresh_pattern_list()
            self._set_status(f"이름이 '{new_name.strip()}'(으)로 변경되었습니다.")

    # ──────────────────────────────────────────────────────────────
    # Playback
    # ──────────────────────────────────────────────────────────────

    def _start_playback(self):
        if self.player.is_playing:
            return
        if self.recorder.is_recording:
            self.recorder.stop()

        if not self._selected_pattern:
            messagebox.showwarning("경고", "재생할 패턴을 선택하세요.")
            return

        pattern = storage.load_pattern(self._selected_pattern)
        if pattern is None or not pattern.events:
            messagebox.showerror("오류", "패턴을 불러올 수 없거나 이벤트가 없습니다.")
            return

        repeat = self.var_repeat.get()
        speed = self.var_speed.get()

        self._set_status(
            f"재생 중: '{self._selected_pattern}' | 반복: {'무한' if repeat == 0 else repeat} | 속도: {speed:.1f}x"
        )
        self.player.play(pattern.events, repeat=repeat, speed=speed)

    def _stop_playback(self):
        self.player.stop()

    def _on_play_status(self, is_playing: bool):
        def _update():
            if is_playing:
                self.lbl_play_status.configure(text="▶ 재생 중...", foreground=GREEN)
            else:
                self.lbl_play_status.configure(text="⏹ 중지됨", foreground=FG_DIM)
                self._set_status("준비됨")
        self.root.after(0, _update)

    def _on_progress(self, cur_repeat: int, total_repeat: int, cur_ev: int, total_ev: int):
        def _update():
            if total_repeat < 0:
                rpt = f"∞ (현재: {cur_repeat}회)"
            else:
                rpt = f"{cur_repeat}/{total_repeat}"
            self.lbl_play_status.configure(
                text=f"반복 {rpt}  |  이벤트 {cur_ev}/{total_ev}",
                foreground=GREEN,
            )
        self.root.after(0, _update)

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def _set_status(self, text: str):
        self.lbl_status.configure(text=text)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Settings Dialog
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SettingsDialog:
    """Modal dialog for customising global hotkeys."""

    def __init__(self, parent: tk.Tk, kb_monitor: KeyboardMonitor,
                 current_settings: Dict[str, Any],
                 on_save: callable):
        self._kb_monitor = kb_monitor
        self._settings = current_settings
        self._on_save = on_save
        self._pending: Dict[str, Dict] = {}  # action → {keycode, modifiers}
        self._capturing_action: Optional[str] = None

        # Copy current hotkeys as pending edits
        for action, hk in self._settings["hotkeys"].items():
            self._pending[action] = dict(hk)

        # Create top-level window
        self.win = tk.Toplevel(parent)
        self.win.title("⚙️ 단축키 설정")
        self.win.geometry("480x340")
        self.win.resizable(False, False)
        self.win.configure(bg=BG)
        self.win.transient(parent)
        self.win.grab_set()

        self._build()

    def _build(self):
        frame = tk.Frame(self.win, bg=BG, padx=20, pady=16)
        frame.pack(fill=tk.BOTH, expand=True)

        # Title
        tk.Label(
            frame, text="글로벌 단축키 설정", font=FONT_LG,
            bg=BG, fg=FG,
        ).pack(anchor=tk.W, pady=(0, 4))

        tk.Label(
            frame, text="버튼을 클릭한 후 원하는 키 조합을 누르세요.", font=FONT_SM,
            bg=BG, fg=FG_DIM,
        ).pack(anchor=tk.W, pady=(0, 12))

        # Hotkey rows
        self._buttons: Dict[str, tk.Button] = {}

        for action in ["toggle_record", "start_playback", "stop"]:
            row = tk.Frame(frame, bg=BG_CARD, padx=12, pady=8)
            row.pack(fill=tk.X, pady=(0, 6))

            tk.Label(
                row, text=ACTION_LABELS[action], font=FONT,
                bg=BG_CARD, fg=FG, width=16, anchor=tk.W,
            ).pack(side=tk.LEFT)

            btn = tk.Button(
                row,
                text=self._display(action),
                font=FONT_MONO, width=16,
                bg=BG_SECONDARY, fg=ACCENT,
                activebackground=BORDER, activeforeground=ACCENT,
                borderwidth=0, highlightthickness=1,
                highlightbackground=BORDER,
                command=lambda a=action: self._start_capture(a),
            )
            btn.pack(side=tk.RIGHT)
            self._buttons[action] = btn

        # Status label for capture
        self.lbl_capture = tk.Label(
            frame, text="", font=FONT_SM, bg=BG, fg=YELLOW,
        )
        self.lbl_capture.pack(anchor=tk.W, pady=(8, 0))

        # Bottom buttons
        btn_frame = tk.Frame(frame, bg=BG)
        btn_frame.pack(fill=tk.X, pady=(16, 0))

        tk.Button(
            btn_frame, text="기본값 복원", font=FONT_SM,
            bg=BG_SECONDARY, fg=FG, borderwidth=0,
            activebackground=BORDER, activeforeground=FG,
            command=self._reset_defaults,
        ).pack(side=tk.LEFT)

        tk.Button(
            btn_frame, text="저장", font=FONT,
            bg=GREEN, fg=BG, borderwidth=0,
            activebackground=GREEN_HOVER, activeforeground=BG,
            padx=24, pady=4,
            command=self._save,
        ).pack(side=tk.RIGHT)

        tk.Button(
            btn_frame, text="취소", font=FONT,
            bg=BG_SECONDARY, fg=FG, borderwidth=0,
            activebackground=BORDER, activeforeground=FG,
            padx=16, pady=4,
            command=self.win.destroy,
        ).pack(side=tk.RIGHT, padx=(0, 8))

    def _display(self, action: str) -> str:
        hk = self._pending[action]
        return app_settings.hotkey_display(hk["keycode"], hk.get("modifiers", 0))

    def _start_capture(self, action: str):
        """Enter key-capture mode for the given action."""
        self._capturing_action = action
        self._buttons[action].configure(
            text="⌨️  키를 누르세요...",
            fg=YELLOW,
        )
        self.lbl_capture.configure(text="아무 키 조합을 누르세요. ESC를 누르면 취소됩니다.")

        # Bind tkinter KeyPress on the dialog — works without accessibility
        self.win.bind("<KeyPress>", self._on_tk_keypress)
        self.win.focus_force()

    def _on_tk_keypress(self, event):
        """Handle tkinter KeyPress event for key capture."""
        keycode = event.keycode

        # Skip modifier-only keys (Cmd, Shift, etc.)
        if keycode in app_settings.MODIFIER_KEYCODES:
            return

        # Convert tkinter state bits → Quartz modifier mask
        modifiers = app_settings.tk_state_to_quartz_mods(event.state)

        # Unbind
        self.win.unbind("<KeyPress>")

        action = self._capturing_action
        if action is None:
            return
        self._capturing_action = None

        # ESC without modifiers = cancel capture
        if keycode == KEYCODE_ESC and modifiers == 0:
            self._buttons[action].configure(
                text=self._display(action), fg=ACCENT,
            )
            self.lbl_capture.configure(text="캡처 취소됨.")
            return

        # Save the captured key
        self._pending[action] = {"keycode": keycode, "modifiers": modifiers}
        display = app_settings.hotkey_display(keycode, modifiers)
        self._buttons[action].configure(text=display, fg=ACCENT)
        self.lbl_capture.configure(text=f"✅ {ACTION_LABELS[action]} → {display}")

    def _reset_defaults(self):
        """Reset all hotkeys to defaults."""
        self._pending = app_settings.get_default_hotkeys()
        for action, btn in self._buttons.items():
            btn.configure(text=self._display(action), fg=ACCENT)
        self.lbl_capture.configure(text="기본값으로 복원되었습니다.")

    def _save(self):
        """Save pending hotkeys and close."""
        self._settings["hotkeys"] = self._pending
        self._on_save(self._settings)
        self.win.destroy()
