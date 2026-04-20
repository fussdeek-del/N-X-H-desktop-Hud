"""
HUD Monitor , 
Tray icon + minimal UI + metric selector + serial sender to Pico TFT
"""

import ctypes
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

# optional tray (pystray + Pillow) 
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_TRAY = True
except ImportError:
    HAS_TRAY = False

 
#  serial
try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None


#  psutil 
import psutil


# CONFIG

UPDATE_MS          = 1000
SERIAL_BAUD        = 115200
SERIAL_RETRY_S     = 3
SERIAL_PORT        = None          # None = auto-detect Pico
MAX_TFT_METRICS    = 4
SETTINGS_FILE      = os.path.join(os.path.dirname(__file__), "hud_settings.json")
SINGLE_INSTANCE    = "HUDMonitorSingleInstanceMutex"

ALL_METRICS = ["CPU", "RAM", "DISK", "TIME", "FPS"]


#  colours 

BG          = "#0b0f14"
CARD        = "#111720"
BORDER      = "#1e2a38"
ACCENT      = "#00c6ff"
ACCENT2     = "#0072ff"
TEXT        = "#e4ecf7"
MUTED       = "#5a6a80"
GREEN       = "#00e676"
RED         = "#ff1744"
WARN        = "#ffc400"



# HELPERS

class DEVMODEW(ctypes.Structure):
    _fields_ = [
        ("dmDeviceName",        ctypes.c_wchar * 32),
        ("dmSpecVersion",       ctypes.c_ushort),
        ("dmDriverVersion",     ctypes.c_ushort),
        ("dmSize",              ctypes.c_ushort),
        ("dmDriverExtra",       ctypes.c_ushort),
        ("dmFields",            ctypes.c_ulong),
        ("dmPositionX",         ctypes.c_long),
        ("dmPositionY",         ctypes.c_long),
        ("dmDisplayOrientation",ctypes.c_ulong),
        ("dmDisplayFixedOutput",ctypes.c_ulong),
        ("dmColor",             ctypes.c_short),
        ("dmDuplex",            ctypes.c_short),
        ("dmYResolution",       ctypes.c_short),
        ("dmTTOption",          ctypes.c_short),
        ("dmCollate",           ctypes.c_short),
        ("dmFormName",          ctypes.c_wchar * 32),
        ("dmLogPixels",         ctypes.c_ushort),
        ("dmBitsPerPel",        ctypes.c_ulong),
        ("dmPelsWidth",         ctypes.c_ulong),
        ("dmPelsHeight",        ctypes.c_ulong),
        ("dmDisplayFlags",      ctypes.c_ulong),
        ("dmDisplayFrequency",  ctypes.c_ulong),
        ("dmICMMethod",         ctypes.c_ulong),
        ("dmICMIntent",         ctypes.c_ulong),
        ("dmMediaType",         ctypes.c_ulong),
        ("dmDitherType",        ctypes.c_ulong),
        ("dmReserved1",         ctypes.c_ulong),
        ("dmReserved2",         ctypes.c_ulong),
        ("dmPanningWidth",      ctypes.c_ulong),
        ("dmPanningHeight",     ctypes.c_ulong),
    ]


def get_refresh_rate():
    try:
        dm = DEVMODEW()
        dm.dmSize = ctypes.sizeof(DEVMODEW)
        if ctypes.windll.user32.EnumDisplaySettingsW(None, -1, ctypes.byref(dm)):
            return int(dm.dmDisplayFrequency or 60)
    except Exception:
        pass
    return 60


def get_main_drive():
    drive = os.path.splitdrive(os.getcwd())[0]
    return f"{drive}\\" if drive else "C:\\"


def collect_metrics():
    from datetime import datetime
    return {
        "CPU":  f"{int(round(psutil.cpu_percent(interval=None)))}%",
        "RAM":  f"{int(round(psutil.virtual_memory().percent))}%",
        "DISK": f"{int(round(psutil.disk_usage(get_main_drive()).percent))}%",
        "TIME": datetime.now().strftime("%H:%M:%S"),
        "FPS":  str(get_refresh_rate()),
    }


# prime cpu
psutil.cpu_percent(interval=None)



# SETTINGS  (persist selected metrics)

def load_settings():
    try:
        with open(SETTINGS_FILE) as f:
            data = json.load(f)
            sel = [m for m in data.get("selected", ALL_METRICS) if m in ALL_METRICS]
            return sel[:MAX_TFT_METRICS] if sel else ALL_METRICS[:MAX_TFT_METRICS]
    except Exception:
        return ALL_METRICS[:MAX_TFT_METRICS]


def save_settings(selected):
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump({"selected": selected}, f)
    except Exception:
        pass


# SERIAL SENDER
# 

class SerialSender:
    def __init__(self):
        self.conn = None
        self.last_try = 0.0

    def send(self, line):
        if not self._write(line):
            pass  # silent — no cmd spam

    def close(self):
        if self.conn:
            try: self.conn.close()
            except Exception: pass
            self.conn = None

    def connected(self):
        return self.conn is not None

    def _write(self, line):
        if serial is None: return False
        if not self.conn and not self._connect(): return False
        try:
            self.conn.write(line.encode("ascii"))
            return True
        except Exception:
            self.close()
            return False

    def _connect(self):
        now = time.monotonic()
        if now - self.last_try < SERIAL_RETRY_S: return False
        self.last_try = now
        for port in self._ports():
            try:
                self.conn = serial.Serial(port=port, baudrate=SERIAL_BAUD, timeout=0, write_timeout=0)
                return True
            except Exception:
                self.conn = None
        return False

    def _ports(self):
        if SERIAL_PORT: return [SERIAL_PORT]
        if list_ports is None: return []
        pref, fall = [], []
        for p in list_ports.comports():
            txt = " ".join(x for x in (p.device, p.description, p.manufacturer) if x).lower()
            if any(t in txt for t in ("rp2040", "pico", "tinyusb", "cdc", "usb serial")):
                pref.append(p.device)
            else:
                fall.append(p.device)
        return pref + fall



# FORMAT payload → serial line  (only sends selected metrics)

def format_for_tft(metrics, selected):
    KEY_MAP = {"CPU": "CPU", "RAM": "RAM", "DISK": "DISK", "TIME": "TIME", "FPS": "FPS"}
    parts = []
    for key in selected:
        val = metrics.get(key, "--").replace("%", "")
        parts.append(f"{KEY_MAP[key]}:{val}")
    return ";".join(parts) + ";\n"



# TRAY ICON  (build a small icon with Pillow)

def make_tray_icon():
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([4, 4, size-4, size-4], fill="#00c6ff")
    d.rectangle([20, 28, 44, 36], fill="#0b0f14")
    d.rectangle([28, 20, 36, 44], fill="#0b0f14")
    return img



# MAIN UI WINDOW

class HUDWindow:
    def __init__(self, sender: SerialSender):
        self.sender   = sender
        self.selected = load_settings()
        self.metrics  = {}
        self.running  = True

        self.root = tk.Tk()
        self.root.title("HUD Monitor")
        self.root.configure(bg=BG)
        self.root.geometry("460x560")
        self.root.resizable(False, False)
        self.root.overrideredirect(False)

        # keep on top toggle — off by default
        self.root.attributes("-topmost", False)

        # close = hide to tray (if tray available), else quit
        self.root.protocol("WM_DELETE_WINDOW", self._hide)

        self._build_ui()
        self._start_bg_thread()

        if HAS_TRAY:
            self._start_tray()

    
    #  UI BUILD 

    def _build_ui(self):
        root = self.root

        
        #  title bar 

        title_bar = tk.Frame(root, bg=BG, pady=12)
        title_bar.pack(fill="x", padx=20)

        tk.Label(title_bar, text="⬡  HUD MONITOR", bg=BG, fg=ACCENT,
                 font=("Courier New", 13, "bold")).pack(side="left")

        self.status_dot = tk.Label(title_bar, text="●", bg=BG, fg=MUTED,
                                   font=("Courier New", 10))
        self.status_dot.pack(side="right")
        self.status_lbl = tk.Label(title_bar, text="disconnected", bg=BG, fg=MUTED,
                                   font=("Courier New", 8))
        self.status_lbl.pack(side="right", padx=(0, 4))

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=20)

         
        #  live stats cards 
        
        stats_frame = tk.Frame(root, bg=BG)
        stats_frame.pack(fill="x", padx=20, pady=14)

        self.card_labels = {}   # key → (val_label, bar_canvas)
        for i, key in enumerate(ALL_METRICS):
            card = tk.Frame(stats_frame, bg=CARD, bd=0, highlightthickness=1,
                            highlightbackground=BORDER)
            card.grid(row=i//2*2, column=i%2, padx=5, pady=5, sticky="nsew")
            stats_frame.columnconfigure(i%2, weight=1)

            tk.Label(card, text=key, bg=CARD, fg=MUTED,
                     font=("Courier New", 8)).pack(anchor="w", padx=10, pady=(8,0))

            val = tk.Label(card, text="--", bg=CARD, fg=TEXT,
                           font=("Courier New", 20, "bold"))
            val.pack(anchor="w", padx=10)

            # bar (only for CPU/RAM/DISK)
            bar = None
            if key in ("CPU", "RAM", "DISK"):
                bar = tk.Canvas(card, bg=CARD, height=3, bd=0,
                                highlightthickness=0, width=160)
                bar.pack(fill="x", padx=10, pady=(2,8))
            else:
                tk.Label(card, text="", bg=CARD).pack(pady=4)

            self.card_labels[key] = (val, bar)

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(4,0))

        
        #  TFT selector 
        
        tk.Label(root, text="TFT DISPLAY  —  select up to 4",
                 bg=BG, fg=MUTED, font=("Courier New", 8)).pack(anchor="w", padx=24, pady=(10,4))

        sel_frame = tk.Frame(root, bg=BG)
        sel_frame.pack(fill="x", padx=20)

        self.check_vars = {}
        for key in ALL_METRICS:
            var = tk.BooleanVar(value=(key in self.selected))
            self.check_vars[key] = var

            cb = tk.Checkbutton(
                sel_frame, text=key, variable=var,
                bg=BG, fg=TEXT, selectcolor=CARD,
                activebackground=BG, activeforeground=ACCENT,
                font=("Courier New", 10, "bold"),
                command=self._on_check_change,
                cursor="hand2"
            )
            cb.pack(side="left", padx=8)

        self.sel_warn = tk.Label(root, text="", bg=BG, fg=WARN,
                                 font=("Courier New", 8))
        self.sel_warn.pack(anchor="w", padx=24)

        tk.Frame(root, bg=BORDER, height=1).pack(fill="x", padx=20, pady=(8,0))

        
        #  bottom bar 
        
        bot = tk.Frame(root, bg=BG, pady=10)
        bot.pack(fill="x", padx=20)

        tk.Button(bot, text="HIDE TO TRAY" if HAS_TRAY else "MINIMIZE",
                  bg=CARD, fg=MUTED, relief="flat", cursor="hand2",
                  font=("Courier New", 8),
                  command=self._hide).pack(side="left")

        tk.Button(bot, text="QUIT",
                  bg=CARD, fg=RED, relief="flat", cursor="hand2",
                  font=("Courier New", 8),
                  command=self._quit).pack(side="right")

    
    #  CHECK CHANGE 
    
    def _on_check_change(self):
        selected = [k for k, v in self.check_vars.items() if v.get()]
        if len(selected) > MAX_TFT_METRICS:
            # find last checked and uncheck it
            for k in reversed(ALL_METRICS):
                if self.check_vars[k].get() and k not in self.selected:
                    self.check_vars[k].set(False)
                    break
            selected = [k for k, v in self.check_vars.items() if v.get()]
            self.sel_warn.config(text=f"⚠  Max {MAX_TFT_METRICS} metrics for TFT display")
        else:
            self.sel_warn.config(text="")

        self.selected = selected
        save_settings(self.selected)

    
    #  BACKGROUND THREAD 

    def _start_bg_thread(self):
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self.running:
            t0 = time.monotonic()
            try:
                self.metrics = collect_metrics()
                line = format_for_tft(self.metrics, self.selected)
                self.sender.send(line)
                self.root.after(0, self._refresh_ui)
            except Exception:
                pass
            elapsed = time.monotonic() - t0
            time.sleep(max(0, UPDATE_MS / 1000 - elapsed))

    
    #  REFRESH UI 

    def _refresh_ui(self):
        for key, (val_lbl, bar) in self.card_labels.items():
            raw = self.metrics.get(key, "--")
            val_lbl.config(text=raw)

            # colour code
            if key in ("CPU", "RAM", "DISK"):
                pct = int(raw.replace("%", "") or 0)
                color = GREEN if pct < 60 else WARN if pct < 85 else RED
                val_lbl.config(fg=color)
                if bar:
                    bar.delete("all")
                    w = bar.winfo_width() or 160
                    filled = int(w * pct / 100)
                    bar.create_rectangle(0, 0, w, 3, fill=BORDER, outline="")
                    if filled > 0:
                        bar.create_rectangle(0, 0, filled, 3, fill=color, outline="")
            else:
                val_lbl.config(fg=TEXT)

        # serial status dot
        if self.sender.connected():
            self.status_dot.config(fg=GREEN)
            self.status_lbl.config(text="pico connected", fg=GREEN)
        else:
            self.status_dot.config(fg=RED)
            self.status_lbl.config(text="no pico", fg=MUTED)

        # update tray tooltip
        if HAS_TRAY and hasattr(self, "tray"):
            cpu = self.metrics.get("CPU", "--")
            ram = self.metrics.get("RAM", "--")
            try:
                self.tray.title = f"HUD  CPU {cpu}  RAM {ram}"
            except Exception:
                pass

    
    #  TRAY 
    
    def _start_tray(self):
        menu = pystray.Menu(
            pystray.MenuItem("Show",   self._show, default=True),
            pystray.MenuItem("Quit",   self._quit),
        )
        self.tray = pystray.Icon("HUD Monitor", make_tray_icon(),
                                 "HUD Monitor", menu)
        t = threading.Thread(target=self.tray.run, daemon=True)
        t.start()

    def _hide(self):
        self.root.withdraw()

    def _show(self, *_):
        self.root.after(0, self.root.deiconify)

    def _quit(self, *_):
        self.running = False
        self.sender.close()
        if HAS_TRAY and hasattr(self, "tray"):
            try: self.tray.stop()
            except Exception: pass
        self.root.after(0, self.root.destroy)

    def run(self):
        self.root.mainloop()



# SINGLE INSTANCE GUARD

def acquire_mutex():
    k = ctypes.windll.kernel32
    m = k.CreateMutexW(None, False, SINGLE_INSTANCE)
    if k.GetLastError() == 183:
        tk.Tk().withdraw()
        import tkinter.messagebox as mb
        mb.showinfo("HUD Monitor", "HUD Monitor is already running.")
        return None
    return m



# ENTRY

def main():
    mutex = acquire_mutex()
    if mutex is None:
        return

    sender = SerialSender()
    app    = HUDWindow(sender)

    try:
        app.run()
    finally:
        sender.close()
        ctypes.windll.kernel32.ReleaseMutex(mutex)


if __name__ == "__main__":
    main()