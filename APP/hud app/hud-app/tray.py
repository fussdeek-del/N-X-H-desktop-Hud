import threading
import tkinter as tk
from tkinter import messagebox

import pystray
from PIL import Image, ImageDraw

from config import (
    BG_COLOR,
    CARD_BG,
    GRAPH_BG,
    MAX_VISIBLE_METRICS,
    MUTED_TEXT,
    TEXT_COLOR,
    UPDATE_INTERVAL_MS,
    WINDOW_SIZE,
    WINDOW_TITLE,
)


METRIC_OPTIONS = {
    "cpu": {"title": "CPU", "suffix": "%", "color": "#3da5ff"},
    "ram": {"title": "Memory", "suffix": "%", "color": "#b455ff"},
    "disk": {"title": "Disk Active", "suffix": "%", "color": "#59d65f"},
    "drive_used": {"title": "Drive Used", "suffix": "%", "color": "#9acb32"},
    "fps": {"title": "FPS", "suffix": "", "color": "#ffb84d"},
    "network": {"title": "Network", "suffix": " Kbps", "color": "#ff7676"},
    "time": {"title": "Time", "suffix": "", "color": "#00d2a0"},
}


class TrayApp:
    def __init__(self, state):
        self.state = state
        self.root = None
        self.icon = None
        self.metric_vars = {}
        self.cards = {}
        self.selected_keys = ["cpu", "ram", "disk", "time"]

    def run(self):
        self.root = tk.Tk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.root.attributes("-topmost", True)
        self.root.wm_attributes("-toolwindow", True)

        self._build_window()
        self._start_tray_icon()
        self._refresh_ui()
        self.root.mainloop()

    def _build_window(self):
        header = tk.Frame(self.root, bg=BG_COLOR, padx=12, pady=10)
        header.pack(fill="x")

        tk.Label(
            header,
            text=WINDOW_TITLE,
            bg=BG_COLOR,
            fg=TEXT_COLOR,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            header,
            text=f"Select up to {MAX_VISIBLE_METRICS} metrics",
            bg=BG_COLOR,
            fg=MUTED_TEXT,
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        selector = tk.Frame(self.root, bg=BG_COLOR, padx=12, pady=4)
        selector.pack(fill="x")

        for index, key in enumerate(METRIC_OPTIONS):
            var = tk.BooleanVar(value=key in self.selected_keys)
            checkbox = tk.Checkbutton(
                selector,
                text=METRIC_OPTIONS[key]["title"],
                variable=var,
                command=lambda metric_key=key: self._toggle_metric(metric_key),
                bg=BG_COLOR,
                fg=TEXT_COLOR,
                selectcolor=GRAPH_BG,
                activebackground=BG_COLOR,
                activeforeground=TEXT_COLOR,
                anchor="w",
                font=("Segoe UI", 9),
            )
            checkbox.grid(row=index // 2, column=index % 2, sticky="w", padx=(0, 12), pady=2)
            self.metric_vars[key] = var

        self.grid_frame = tk.Frame(self.root, bg=BG_COLOR, padx=12, pady=10)
        self.grid_frame.pack(fill="both", expand=True)
        self._rebuild_cards()

        footer = tk.Label(
            self.root,
            text="Close hides to tray. Tray menu can reopen or quit.",
            bg=BG_COLOR,
            fg=MUTED_TEXT,
            font=("Segoe UI", 8),
            anchor="w",
            padx=12,
            pady=6,
        )
        footer.pack(fill="x")

    def _toggle_metric(self, key):
        is_selected = self.metric_vars[key].get()
        if is_selected:
            if key not in self.selected_keys:
                if len(self.selected_keys) >= MAX_VISIBLE_METRICS:
                    self.metric_vars[key].set(False)
                    messagebox.showinfo(WINDOW_TITLE, f"Only {MAX_VISIBLE_METRICS} metrics can be shown at once.")
                    return
                self.selected_keys.append(key)
        else:
            if key in self.selected_keys:
                self.selected_keys.remove(key)

        self._rebuild_cards()

    def _rebuild_cards(self):
        for child in self.grid_frame.winfo_children():
            child.destroy()

        self.cards = {}
        for index, key in enumerate(self.selected_keys):
            row = index // 2
            column = index % 2
            card = tk.Frame(self.grid_frame, bg=CARD_BG, highlightthickness=1, highlightbackground=METRIC_OPTIONS[key]["color"])
            card.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)

            self.grid_frame.grid_columnconfigure(column, weight=1)
            self.grid_frame.grid_rowconfigure(row, weight=1)

            title = tk.Label(
                card,
                text=METRIC_OPTIONS[key]["title"],
                bg=CARD_BG,
                fg=MUTED_TEXT,
                font=("Segoe UI", 9),
                anchor="w",
                padx=10,
                pady=8,
            )
            title.pack(fill="x")

            value = tk.Label(
                card,
                text="--",
                bg=CARD_BG,
                fg=TEXT_COLOR,
                font=("Segoe UI", 20, "bold"),
                anchor="w",
                padx=10,
                pady=8,
            )
            value.pack(fill="both", expand=True)

            self.cards[key] = value

    def _start_tray_icon(self):
        self.icon = pystray.Icon(
            "hud_app",
            self._create_icon(),
            WINDOW_TITLE,
            menu=pystray.Menu(
                pystray.MenuItem("Show HUD", self.show_window, default=True),
                pystray.MenuItem("Hide HUD", self.hide_window),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", self.quit_app),
            ),
        )
        threading.Thread(target=self.icon.run, daemon=True).start()

    def _refresh_ui(self):
        for key, label in self.cards.items():
            label.config(text=self._format_metric(key))

        if self.state["running"] and self.root:
            self.root.after(UPDATE_INTERVAL_MS, self._refresh_ui)

    def _format_metric(self, key):
        meta = METRIC_OPTIONS[key]
        value = self.state.get(key, "--")
        return f"{value}{meta['suffix']}"

    def show_window(self, icon=None, item=None):
        if self.root:
            self.root.after(0, self._show_window)

    def _show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide_window(self, icon=None, item=None):
        if self.root:
            self.root.after(0, self.root.withdraw)

    def quit_app(self, icon=None, item=None):
        self.state["running"] = False
        if self.icon:
            self.icon.stop()
        if self.root:
            self.root.after(0, self.root.destroy)

    @staticmethod
    def _create_icon():
        image = Image.new("RGBA", (64, 64), (20, 24, 32, 0))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((8, 8, 56, 56), radius=10, fill=(19, 24, 32), outline=(0, 210, 120), width=3)
        draw.line((18, 44, 28, 30, 36, 36, 46, 18), fill=(0, 210, 120), width=4)
        return image
