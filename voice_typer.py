#!/usr/bin/env python3
"""
Sesli Yazı — Gerçek zamanlı Türkçe ses-metin uygulaması
"""

import sys
import os
import threading
import queue
import ctypes
import time

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from pynput.keyboard import Controller, Key, GlobalHotKeys
import tkinter as tk
from tkinter import ttk

# ─── Ayarlar ──────────────────────────────────────────────────────────────────
SAMPLE_RATE       = 16000
CHUNK_SECONDS     = 0.5
SILENCE_THRESHOLD = 0.012
SILENCE_SECONDS   = 0.7
MIN_AUDIO_SECONDS = 0.3
MODEL_SIZE        = "large-v3-turbo"
MODEL_CACHE       = os.path.join(os.path.expanduser("~"), ".cache", "sesli_yazi")
# ──────────────────────────────────────────────────────────────────────────────

_own_hwnd:    int = 0
_paste_hwnd:  int = 0   # Başlat'a basılınca kaydedilen hedef pencere

# 64-bit Windows'ta HWND pointer-sized (8 byte) — varsayılan 32-bit int truncate eder
def _fix_user32_restypes():
    u32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32
    for fn in (u32.GetForegroundWindow, u32.GetAncestor, u32.GetFocus,
               u32.GetParent, u32.FindWindowW):
        fn.restype = ctypes.c_void_p
    u32.GetWindowThreadProcessId.restype = ctypes.c_ulong
    k32.GetCurrentThreadId.restype       = ctypes.c_ulong

_fix_user32_restypes()


def get_input_devices():
    """Sistemdeki mikrofon cihazlarını döndürür: [(index, isim), ...]"""
    devs = []
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            devs.append((i, d["name"]))
    return devs


def win32_clipboard_set(text: str) -> None:
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE  = 0x0002
    encoded = (text + "\0").encode("utf-16-le")
    k32 = ctypes.windll.kernel32
    u32 = ctypes.windll.user32
    # 64-bit Windows'ta pointer'lar 64-bit — restype mutlaka belirtilmeli
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalLock.restype  = ctypes.c_void_p
    h = k32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
    if not h:
        return
    p = k32.GlobalLock(h)
    if not p:
        k32.GlobalFree(h)
        return
    ctypes.memmove(p, encoded, len(encoded))
    k32.GlobalUnlock(h)
    u32.OpenClipboard(0)
    u32.EmptyClipboard()
    u32.SetClipboardData(CF_UNICODETEXT, h)
    u32.CloseClipboard()


def paste_to_window(target_hwnd: int, text: str, kb: Controller) -> None:
    """AttachThreadInput ile hedef pencereyi öne getir, sonra Ctrl+V gönder."""
    win32_clipboard_set(text + " ")
    time.sleep(0.05)

    if not target_hwnd:
        kb.press(Key.ctrl); kb.press("v"); kb.release("v"); kb.release(Key.ctrl)
        return

    u32 = ctypes.windll.user32
    k32 = ctypes.windll.kernel32
    target_tid = u32.GetWindowThreadProcessId(target_hwnd, None)
    current_tid = k32.GetCurrentThreadId()

    # Kendi thread'imizi hedef pencerenin input kuyruğuna bağla
    u32.AttachThreadInput(current_tid, target_tid, True)
    try:
        u32.ShowWindow(target_hwnd, 9)       # SW_RESTORE
        u32.BringWindowToTop(target_hwnd)
        u32.SetForegroundWindow(target_hwnd)
        time.sleep(0.12)
    finally:
        u32.AttachThreadInput(current_tid, target_tid, False)

    time.sleep(0.05)
    kb.press(Key.ctrl); kb.press("v"); kb.release("v"); kb.release(Key.ctrl)



# ─── Transkripsiyon motoru ─────────────────────────────────────────────────────
class AudioTranscriber:
    def __init__(self, on_text, on_status, on_volume):
        self.on_text    = on_text
        self.on_status  = on_status
        self.on_volume  = on_volume
        self.model      = None
        self.kb         = Controller()
        self.q          = queue.Queue()
        self.is_running = False
        self.buf        = []
        self.sil_count  = 0
        self.max_sil    = int(SILENCE_SECONDS / CHUNK_SECONDS)

    def load_model(self) -> bool:
        self.on_status("⏳ Model yükleniyor…")
        try:
            import huggingface_hub.file_download as _fd
            _orig = _fd.http_get

            def _prog(url, tmp, *a, **kw):
                name = url.split("/")[-1].split("?")[0][:28]
                self.on_status(f"⬇ İndiriliyor: {name}")
                return _orig(url, tmp, *a, **kw)

            _fd.http_get = _prog
            self.model = WhisperModel(
                MODEL_SIZE, device="cpu", compute_type="int8",
                download_root=MODEL_CACHE,
            )
            _fd.http_get = _orig
            self.on_status("✅ Hazır — mikrofon seçin ve Başlat'a basın")
            return True
        except Exception as e:
            self.on_status(f"❌ Model hatası: {e}")
            return False

    def _audio_cb(self, indata, frames, t, status):
        if self.is_running:
            self.q.put(indata.copy())

    def _loop(self):
        while self.is_running:
            try:
                chunk = self.q.get(timeout=0.1)
            except queue.Empty:
                continue
            data = chunk.flatten().astype(np.float32)
            rms  = float(np.sqrt(np.mean(data ** 2)))
            self.on_volume(min(rms / 0.07, 1.0))
            if rms > SILENCE_THRESHOLD:
                self.buf.extend(data)
                self.sil_count = 0
            elif self.buf:
                self.buf.extend(data)
                self.sil_count += 1
                if self.sil_count >= self.max_sil:
                    self._flush()
        if self.buf:
            self._flush()
        self.on_volume(0)

    def _flush(self):
        audio = np.array(self.buf, dtype=np.float32)
        self.buf       = []
        self.sil_count = 0
        if len(audio) < SAMPLE_RATE * MIN_AUDIO_SECONDS:
            if self.is_running:
                self.on_status("🎙 Dinleniyor…")
            return
        self.on_status("⚙ Çevriliyor…")
        try:
            segs, _ = self.model.transcribe(
                audio,
                language="tr",
                beam_size=1,
                initial_prompt="Türkçe konuşma. Doğal, akıcı cümleler.",
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 300},
                condition_on_previous_text=False,
            )
            text = " ".join(s.text.strip() for s in segs).strip()
            if text:
                self.on_text(text)
        except Exception as e:
            self.on_status(f"❌ Hata: {e}")
        finally:
            if self.is_running:
                self.on_status("🎙 Dinleniyor…")

    def start(self, device_idx=None) -> bool:
        if not self.model:
            return False
        self.is_running = True
        self.buf        = []
        self.sil_count  = 0
        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype=np.float32,
                blocksize=int(SAMPLE_RATE * CHUNK_SECONDS),
                callback=self._audio_cb,
                device=device_idx,
            )
            self.stream.start()
        except Exception as e:
            self.is_running = False
            self.on_status(f"❌ Mikrofon hatası: {e}")
            return False
        threading.Thread(target=self._loop, daemon=True).start()
        return True

    def stop(self):
        self.is_running = False
        if hasattr(self, "stream"):
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass


# ─── GUI ──────────────────────────────────────────────────────────────────────
class SesliYazi:
    # ── Dark Cyberpunk Palette ────────────────────────────────────────────────
    BG        = "#0b0b14"   # deep void black
    CARD      = "#12121e"   # slightly lighter card
    BORDER    = "#1e1e35"   # subtle border
    VIOLET    = "#8b5cf6"   # primary accent
    VIOLET2   = "#6d28d9"   # darker violet
    CYAN      = "#22d3ee"   # secondary accent
    RED       = "#f43f5e"   # stop red
    RED2      = "#be123c"   # darker red
    GREEN     = "#10b981"   # success
    TEXT      = "#e2e8f0"   # main text
    TEXT_DIM  = "#4b5563"   # muted text
    BLUE      = "#8b5cf6"   # alias for toggle compat

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Sesli Yazı")
        self.root.resizable(False, True)
        self.root.configure(bg=self.BG)
        self.root.attributes("-topmost", True)
        sw = self.root.winfo_screenwidth()
        self.root.geometry(f"380x560+{sw - 395}+10")
        self._set_icon()
        self._build_ui()

        self.root.update()
        self._apply_noactivate()
        self._apply_rounded_corners()

        self.tr = AudioTranscriber(
            on_text   = self._got_text,
            on_status = self._set_status,
            on_volume = self._set_volume,
        )
        threading.Thread(target=self.tr.load_model, daemon=True).start()

        self.hk = GlobalHotKeys({"<f9>": self._toggle})
        self.hk.start()

    def _apply_rounded_corners(self):
        """Windows 11: rounded window corners via DWM API."""
        try:
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWMWCP_ROUND = 2
            raw = ctypes.windll.user32.GetAncestor(self.root.winfo_id(), 2)
            if raw:
                hwnd = ctypes.c_void_p(int(raw))
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_WINDOW_CORNER_PREFERENCE,
                    ctypes.byref(ctypes.c_int(DWMWCP_ROUND)),
                    ctypes.sizeof(ctypes.c_int),
                )
        except Exception:
            pass

    def _apply_noactivate(self):
        GWL_EXSTYLE      = -20
        WS_EX_NOACTIVATE = 0x08000000
        try:
            u32  = ctypes.windll.user32
            raw  = u32.GetAncestor(self.root.winfo_id(), 2)  # c_void_p → int or None
            if raw:
                hwnd = ctypes.c_void_p(int(raw))
                global _own_hwnd
                _own_hwnd = hwnd
                style = u32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                u32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_NOACTIVATE)
        except Exception:
            pass

    def _set_icon(self):
        path = self._res("icon.ico")
        if os.path.exists(path):
            try:
                self.root.iconbitmap(path)
            except Exception:
                pass

    @staticmethod
    def _res(name):
        base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, name)

    def _build_ui(self):
        # ── Title bar ────────────────────────────────────────────────────
        title_frame = tk.Frame(self.root, bg=self.BG)
        title_frame.pack(fill=tk.X, pady=(14, 0))
        tk.Label(title_frame, text="⬡", font=("Segoe UI", 18),
                 fg=self.VIOLET, bg=self.BG).pack(side=tk.LEFT, padx=(14, 6))
        tk.Label(title_frame, text="SESLI YAZI",
                 font=("Consolas", 14, "bold"), fg=self.TEXT, bg=self.BG
                 ).pack(side=tk.LEFT)
        tk.Label(title_frame, text="v2",
                 font=("Consolas", 8), fg=self.TEXT_DIM, bg=self.BG
                 ).pack(side=tk.LEFT, padx=(4, 0))

        # ── Divider ──────────────────────────────────────────────────────
        div = tk.Frame(self.root, bg=self.VIOLET, height=1)
        div.pack(fill=tk.X, padx=14, pady=(6, 10))

        # ── Mic selector card ────────────────────────────────────────────
        mic_card = tk.Frame(self.root, bg=self.CARD,
                            highlightbackground=self.BORDER, highlightthickness=1)
        mic_card.pack(fill=tk.X, padx=14, pady=(0, 8))

        tk.Label(mic_card, text="  MIC", font=("Consolas", 7, "bold"),
                 fg=self.CYAN, bg=self.CARD).pack(anchor=tk.W, pady=(6, 0))

        mic_inner = tk.Frame(mic_card, bg=self.CARD)
        mic_inner.pack(fill=tk.X, padx=8, pady=(2, 8))

        self.devices   = get_input_devices()
        self.mic_names = [d[1][:40] for d in self.devices]
        self.mic_var   = tk.StringVar()

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Dark.TCombobox",
                         fieldbackground=self.BG,
                         background=self.CARD,
                         foreground=self.TEXT,
                         selectbackground=self.VIOLET,
                         selectforeground=self.TEXT,
                         bordercolor=self.VIOLET,
                         arrowcolor=self.VIOLET,
                         font=("Consolas", 8))
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", self.BG)],
                  foreground=[("readonly", self.TEXT)])

        self.mic_combo = ttk.Combobox(
            mic_inner, textvariable=self.mic_var,
            values=self.mic_names, state="readonly",
            style="Dark.TCombobox", width=28, font=("Consolas", 8),
        )
        self.mic_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)

        refresh_btn = tk.Label(mic_inner, text="⟳", font=("Segoe UI", 12),
                               fg=self.VIOLET, bg=self.CARD, cursor="hand2")
        refresh_btn.pack(side=tk.LEFT, padx=(8, 0))
        refresh_btn.bind("<Button-1>", lambda e: self._refresh_mics())

        sel = self._preferred_mic_idx()
        if self.mic_names:
            self.mic_combo.current(sel)

        # ── Volume visualizer (7 bars) ───────────────────────────────────
        self.vol_canvas = tk.Canvas(self.root, width=356, height=28,
                                    bg=self.BG, highlightthickness=0)
        self.vol_canvas.pack(padx=14, pady=(0, 4))
        self._vol_bars = []
        bar_w, gap, total = 16, 6, 7
        start_x = (356 - total * (bar_w + gap) + gap) // 2
        for i in range(total):
            x0 = start_x + i * (bar_w + gap)
            bid = self.vol_canvas.create_rectangle(
                x0, 14, x0 + bar_w, 14,
                fill=self.TEXT_DIM, outline="", width=0)
            self._vol_bars.append((bid, x0, bar_w))
        self._vol_level = 0.0

        # ── Status label ─────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="⏳  Initializing…")
        self.status_lbl = tk.Label(
            self.root, textvariable=self.status_var,
            font=("Consolas", 9), fg=self.TEXT_DIM, bg=self.BG,
        )
        self.status_lbl.pack(pady=(0, 10))

        # ── Round main button (Canvas) ────────────────────────────────────
        self._btn_running = False
        btn_size = 110
        self.btn_canvas = tk.Canvas(self.root, width=btn_size, height=btn_size,
                                     bg=self.BG, highlightthickness=0)
        self.btn_canvas.pack(pady=(0, 10))

        r = btn_size // 2
        # Outer glow ring
        self._btn_ring = self.btn_canvas.create_oval(
            4, 4, btn_size - 4, btn_size - 4,
            outline=self.VIOLET, width=2)
        # Fill circle
        self._btn_fill = self.btn_canvas.create_oval(
            12, 12, btn_size - 12, btn_size - 12,
            fill=self.VIOLET2, outline="")
        # Icon text
        self._btn_icon = self.btn_canvas.create_text(
            r, r - 6, text="▶", font=("Segoe UI", 20, "bold"),
            fill=self.TEXT)
        # Label text
        self._btn_label = self.btn_canvas.create_text(
            r, r + 18, text="START", font=("Consolas", 8, "bold"),
            fill=self.TEXT)

        self.btn_canvas.bind("<Button-1>", self._on_btn_click)
        self.btn_canvas.bind("<Enter>", self._on_btn_enter)
        self.btn_canvas.bind("<Leave>", self._on_btn_leave)
        self.btn_canvas.config(cursor="hand2")
        self._btn_enabled = False  # disabled until model loads

        # Start pulse animation
        self._pulse_dir = 1
        self._pulse_val = 0
        self._animate_pulse()

        # ── Transcript card ───────────────────────────────────────────────
        tx_card = tk.Frame(self.root, bg=self.CARD,
                           highlightbackground=self.BORDER, highlightthickness=1)
        tx_card.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))

        tx_header = tk.Frame(tx_card, bg=self.CARD)
        tx_header.pack(fill=tk.X, padx=8, pady=(6, 2))
        tk.Label(tx_header, text="TRANSCRIPT",
                 font=("Consolas", 7, "bold"), fg=self.CYAN, bg=self.CARD
                 ).pack(side=tk.LEFT)

        # Copy / Clear as label-buttons
        clear_lbl = tk.Label(tx_header, text="✕ clear",
                             font=("Consolas", 7), fg=self.TEXT_DIM, bg=self.CARD,
                             cursor="hand2")
        clear_lbl.pack(side=tk.RIGHT)
        clear_lbl.bind("<Button-1>", lambda e: self._clear_text())
        clear_lbl.bind("<Enter>", lambda e: clear_lbl.config(fg=self.RED))
        clear_lbl.bind("<Leave>", lambda e: clear_lbl.config(fg=self.TEXT_DIM))

        copy_lbl = tk.Label(tx_header, text="⎘ copy",
                            font=("Consolas", 7), fg=self.TEXT_DIM, bg=self.CARD,
                            cursor="hand2")
        copy_lbl.pack(side=tk.RIGHT, padx=(0, 10))
        copy_lbl.bind("<Button-1>", lambda e: self._copy_all())
        copy_lbl.bind("<Enter>", lambda e: copy_lbl.config(fg=self.CYAN))
        copy_lbl.bind("<Leave>", lambda e: copy_lbl.config(fg=self.TEXT_DIM))

        sb = tk.Scrollbar(tx_card, bg=self.CARD)
        sb.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 2))

        self.txt_box = tk.Text(
            tx_card, font=("Consolas", 10),
            fg=self.TEXT, bg=self.CARD,
            insertbackground=self.VIOLET,
            selectbackground=self.VIOLET2,
            relief=tk.FLAT, bd=0,
            wrap=tk.WORD, state=tk.DISABLED,
            yscrollcommand=sb.set, height=7,
            padx=8, pady=4,
        )
        self.txt_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.config(command=self.txt_box.yview)

        # ── Footer ────────────────────────────────────────────────────────
        tk.Label(self.root,
                 text="F9  start/stop  •  speech auto-pastes to active window",
                 font=("Consolas", 7), fg=self.TEXT_DIM, bg=self.BG,
                 ).pack(side=tk.BOTTOM, pady=(2, 6))

    # ── Button animation helpers ──────────────────────────────────────────────
    def _animate_pulse(self):
        if not self._btn_running and self._btn_enabled:
            self._pulse_val += self._pulse_dir * 3
            if self._pulse_val >= 60:
                self._pulse_dir = -1
            elif self._pulse_val <= 0:
                self._pulse_dir = 1
            alpha = self._pulse_val
            # modulate ring brightness
            r = min(255, 139 + alpha)
            color = f"#{r:02x}5c{min(255,246):02x}"
            self.btn_canvas.itemconfig(self._btn_ring, outline=color)
        self.root.after(40, self._animate_pulse)

    def _on_btn_click(self, _event=None):
        if self._btn_enabled:
            self._toggle()

    def _on_btn_enter(self, _event=None):
        if self._btn_enabled:
            self.btn_canvas.itemconfig(self._btn_fill,
                fill=self.RED2 if self._btn_running else self.VIOLET)

    def _on_btn_leave(self, _event=None):
        self.btn_canvas.itemconfig(self._btn_fill,
            fill=self.RED2 if self._btn_running else self.VIOLET2)

    def _set_btn_state(self, running: bool):
        self._btn_running = running
        if running:
            self.btn_canvas.itemconfig(self._btn_fill, fill=self.RED2)
            self.btn_canvas.itemconfig(self._btn_ring, outline=self.RED)
            self.btn_canvas.itemconfig(self._btn_icon, text="■")
            self.btn_canvas.itemconfig(self._btn_label, text="STOP")
        else:
            self.btn_canvas.itemconfig(self._btn_fill, fill=self.VIOLET2)
            self.btn_canvas.itemconfig(self._btn_ring, outline=self.VIOLET)
            self.btn_canvas.itemconfig(self._btn_icon, text="▶")
            self.btn_canvas.itemconfig(self._btn_label, text="START")

    # ── Volume bars ───────────────────────────────────────────────────────────
    def _draw_vol_bars(self, level: float):
        max_h, base_y, canvas_h = 22, 26, 28
        colors = [self.TEXT_DIM, self.VIOLET, self.VIOLET,
                  self.CYAN, self.VIOLET, self.VIOLET, self.TEXT_DIM]
        for i, (bid, x0, bar_w) in enumerate(self._vol_bars):
            # each bar has a slightly different threshold
            threshold = (i + 1) / (len(self._vol_bars) + 1)
            if level >= threshold:
                h = int(max_h * level)
                fill = colors[i]
            else:
                h = 3
                fill = self.TEXT_DIM
            self.vol_canvas.coords(bid, x0, base_y - h, x0 + bar_w, base_y)
            self.vol_canvas.itemconfig(bid, fill=fill)



    PREFERRED_MIC = "Brio 100"   # bu isim adda geçerse öncelikli seç

    def _preferred_mic_idx(self) -> int:
        """Listede PREFERRED_MIC geçen ilk cihazı döndürür, yoksa sistem varsayılanı."""
        for i, (_, name) in enumerate(self.devices):
            if self.PREFERRED_MIC.lower() in name.lower():
                return i
        # Sistem varsayılanına düş
        try:
            default_idx = sd.default.device[0] if isinstance(sd.default.device, (list, tuple)) else sd.default.device
            for i, (idx, _) in enumerate(self.devices):
                if idx == default_idx:
                    return i
        except Exception:
            pass
        return 0

    def _refresh_mics(self):
        try:
            sd._initialize()
        except Exception:
            pass
        self.devices   = get_input_devices()
        self.mic_names = [d[1][:42] for d in self.devices]
        self.mic_combo["values"] = self.mic_names
        if self.mic_names:
            self.mic_combo.current(self._preferred_mic_idx())

    def _selected_device_idx(self):
        sel = self.mic_combo.current()
        if 0 <= sel < len(self.devices):
            return self.devices[sel][0]
        return None

    def _set_status(self, text: str):
        self.root.after(0, self.status_var.set, text)
        if "✅" in text:
            self.root.after(0, lambda: self.status_lbl.config(fg=self.GREEN))
            self.root.after(0, lambda: setattr(self, "_btn_enabled", True))
        elif "❌" in text:
            self.root.after(0, lambda: self.status_lbl.config(fg=self.RED))
        elif "⬇" in text or "⏳" in text:
            self.root.after(0, lambda: self.status_lbl.config(fg="#f59e0b"))
        elif "⚙" in text:
            self.root.after(0, lambda: self.status_lbl.config(fg=self.VIOLET))
        else:
            self.root.after(0, lambda: self.status_lbl.config(fg=self.CYAN))

    def _set_volume(self, val: float):
        self._vol_level = val
        self.root.after(0, lambda: self._draw_vol_bars(val))

    def _got_text(self, text: str):
        def _update():
            self.txt_box.config(state=tk.NORMAL)
            content = self.txt_box.get("1.0", tk.END).strip()
            if content:
                self.txt_box.insert(tk.END, "\n" + text)
            else:
                self.txt_box.insert(tk.END, text)
            self.txt_box.see(tk.END)
            self.txt_box.config(state=tk.DISABLED)
        self.root.after(0, _update)
        # Paste'i UI thread'inde yap (50ms sonra, UI güncellemesi bittikten sonra)
        hwnd_snapshot = _paste_hwnd
        self.root.after(50, lambda: self._do_paste(hwnd_snapshot, text))

    def _do_paste(self, target_hwnd, text: str) -> None:
        """UI thread'de çalışır. Clipboard'a yaz, Ctrl+V gönder."""
        try:
            # tkinter clipboard — ctypes overflow riski yok
            self.root.clipboard_clear()
            self.root.clipboard_append(text + " ")
            self.root.update()   # clipboard flush
            # WS_EX_NOACTIVATE sayesinde focus hâlâ hedef pencerede
            kb = self.tr.kb
            kb.press(Key.ctrl)
            kb.press("v")
            kb.release("v")
            kb.release(Key.ctrl)
        except Exception as e:
            self._set_status(f"❌ Paste hatası: {e}")

    def _copy_all(self):
        content = self.txt_box.get("1.0", tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)

    def _clear_text(self):
        self.txt_box.config(state=tk.NORMAL)
        self.txt_box.delete("1.0", tk.END)
        self.txt_box.config(state=tk.DISABLED)

    def _toggle(self):
        if self.tr.is_running:
            self.tr.stop()
            self.root.after(0, lambda: self._set_btn_state(False))
            self._set_status("◼  Stopped")
        else:
            global _paste_hwnd
            raw = ctypes.windll.user32.GetForegroundWindow()
            own_val = _own_hwnd.value if isinstance(_own_hwnd, ctypes.c_void_p) else _own_hwnd
            if raw and int(raw) != (own_val or 0):
                _paste_hwnd = ctypes.c_void_p(int(raw))
            try:
                buf = ctypes.create_unicode_buffer(128)
                ctypes.windll.user32.GetWindowTextW(_paste_hwnd, buf, 128)
                win_title = buf.value[:26] or "?"
            except Exception:
                win_title = "?"
            dev = self._selected_device_idx()
            if self.tr.start(device_idx=dev):
                self.root.after(0, lambda: self._set_btn_state(True))
                self._set_status(f"🎙  Listening → '{win_title}'")

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.mainloop()

    def _close(self):
        if self.tr.is_running:
            self.tr.stop()
        self.hk.stop()
        self.root.destroy()


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    SesliYazi().run()
