#!/usr/bin/env python3
"""
Countdown Widget
=================
A tiny always-on-top desktop widget that counts down to a fixed target
date/time (default: 219 days from the first time you run it).

Key behavior
------------
- The target date is written to a config file the FIRST time you run
  this script. Every time after that, remaining time is recalculated
  from datetime.now() vs. that stored target -- so if the PC is shut
  down, sleeps, or the widget is closed, the next launch shows the
  exact real remaining time automatically (no drift, no manual sync).
- A dropdown (top-right of the widget) lets you switch the displayed
  unit between Days, Months (decimal, e.g. "7.23"), and Hours.
- The window is borderless, always-on-top, draggable, and sized to a
  small strip whose height is 60% of your taskbar height (edit
  TASKBAR_HEIGHT_PX below to match your real taskbar/dock height).

Usage
-----
    python countdown_widget.py                     # run the widget
    python countdown_widget.py --reset              # restart the 219-day countdown from right now
    python countdown_widget.py --install-autostart   # make it launch automatically when you log in

Assumptions (edit the CONFIG block if any of these don't match you):
    - Countdown length: 219 days, starting from the first run.
    - TASKBAR_HEIGHT_PX = 40 (typical Windows default at 100% scaling).
      Change this to your actual taskbar/dock height in pixels.
    - "Months" is shown as a decimal using an average month length
      (30.44 days), since calendar months vary in length.
"""

import json
import os
import sys
import argparse
import datetime
import tkinter as tk
from tkinter import ttk

# ---------------------------------------------------------------- CONFIG --
COUNTDOWN_DAYS = 219
TASKBAR_HEIGHT_PX = 40          # <-- set this to your real taskbar height
WIDGET_HEIGHT = max(18, int(TASKBAR_HEIGHT_PX * 0.6))   # 60% of taskbar
WIDGET_WIDTH = 220

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".countdown_widget")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DAYS_PER_MONTH = 30.44
# ----------------------------------------------------------------------- --


def load_or_create_target(reset=False):
    """Load the saved target datetime, or create a new one (now + N days)."""
    os.makedirs(CONFIG_DIR, exist_ok=True)
    now = datetime.datetime.now()

    if os.path.exists(CONFIG_FILE) and not reset:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        target = datetime.datetime.fromisoformat(data["target"])
    else:
        target = now + datetime.timedelta(days=COUNTDOWN_DAYS)
        data = {"target": target.isoformat(), "unit": "Days", "pos": None}
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f)

    return target, data


class CountdownWidget:
    UNITS = ["Days", "Months", "Hours"]

    def __init__(self, target, data):
        self.target = target
        self.data = data
        self._drag_origin = (0, 0)

        self.root = tk.Tk()
        self.root.overrideredirect(True)      # no title bar -> stays tiny
        self.root.attributes("-topmost", True)
        self.root.configure(bg="#1e1e1e")
        self._place_window()

        self.unit_var = tk.StringVar(value=self.data.get("unit", "Days"))

        self.time_label = tk.Label(
            self.root, text="", fg="white", bg="#1e1e1e",
            font=("Segoe UI", 9, "bold"), anchor="w"
        )
        self.time_label.pack(side="left", padx=(8, 2), fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("default")
        self.combo = ttk.Combobox(
            self.root, textvariable=self.unit_var, values=self.UNITS,
            width=6, state="readonly", font=("Segoe UI", 8)
        )
        self.combo.pack(side="right", padx=(0, 4))
        self.combo.bind("<<ComboboxSelected>>", self._on_unit_change)

        self._make_draggable()
        self.root.bind("<Button-3>", lambda e: self.root.destroy())  # right-click to close

        self._tick()
        self.root.mainloop()

    # -- placement -----------------------------------------------------
    def _place_window(self):
        pos = self.data.get("pos")
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if pos:
            x, y = pos
        else:
            x = sw - WIDGET_WIDTH - 12
            y = sh - TASKBAR_HEIGHT_PX - WIDGET_HEIGHT - 6
        self.root.geometry(f"{WIDGET_WIDTH}x{WIDGET_HEIGHT}+{x}+{y}")

    def _make_draggable(self):
        def start(e):
            self._drag_origin = (e.x, e.y)

        def move(e):
            x = self.root.winfo_x() + e.x - self._drag_origin[0]
            y = self.root.winfo_y() + e.y - self._drag_origin[1]
            self.root.geometry(f"+{x}+{y}")

        def stop(e):
            self.data["pos"] = [self.root.winfo_x(), self.root.winfo_y()]
            self._save()

        self.time_label.bind("<ButtonPress-1>", start)
        self.time_label.bind("<B1-Motion>", move)
        self.time_label.bind("<ButtonRelease-1>", stop)

    # -- countdown logic -------------------------------------------------
    def _tick(self):
        now = datetime.datetime.now()          # always re-synced to real time
        remaining = self.target - now
        if remaining.total_seconds() <= 0:
            self.time_label.config(text="Countdown finished")
        else:
            self.time_label.config(text=self._format(remaining))
        self.root.after(1000, self._tick)

    def _format(self, remaining):
        total_seconds = remaining.total_seconds()
        days = total_seconds / 86400
        hours = total_seconds / 3600
        months = total_seconds / (86400 * DAYS_PER_MONTH)

        unit = self.unit_var.get()
        if unit == "Days":
            d = int(days)
            h = int(round((days - d) * 24))
            return f"{d}d {h}h left"
        elif unit == "Months":
            return f"{months:.2f} mo left"
        elif unit == "Hours":
            return f"{hours:.1f} h left"
        return ""

    def _on_unit_change(self, event=None):
        self.data["unit"] = self.unit_var.get()
        self._save()

    def _save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f)


def install_autostart():
    """Register this script to launch automatically at login/startup."""
    script_path = os.path.abspath(__file__)
    py = sys.executable

    if sys.platform.startswith("win"):
        startup = os.path.join(
            os.environ["APPDATA"],
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )
        bat_path = os.path.join(startup, "countdown_widget.bat")
        with open(bat_path, "w") as f:
            f.write(f'start "" "{py}" "{script_path}"\n')
        print(f"Installed autostart entry: {bat_path}")

    elif sys.platform == "darwin":
        plist_dir = os.path.join(os.path.expanduser("~"), "Library/LaunchAgents")
        os.makedirs(plist_dir, exist_ok=True)
        plist_path = os.path.join(plist_dir, "com.user.countdownwidget.plist")
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.user.countdownwidget</string>
<key>ProgramArguments</key><array><string>{py}</string><string>{script_path}</string></array>
<key>RunAtLoad</key><true/>
</dict></plist>"""
        with open(plist_path, "w") as f:
            f.write(plist)
        print(f"Installed autostart entry: {plist_path}")
        print(f"Run: launchctl load {plist_path}  (or log out/in)")

    else:
        autostart_dir = os.path.join(os.path.expanduser("~"), ".config/autostart")
        os.makedirs(autostart_dir, exist_ok=True)
        desktop_path = os.path.join(autostart_dir, "countdown_widget.desktop")
        with open(desktop_path, "w") as f:
            f.write(f"""[Desktop Entry]
Type=Application
Exec={py} {script_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Countdown Widget
""")
        print(f"Installed autostart entry: {desktop_path}")


def main():
    parser = argparse.ArgumentParser(description="Small always-on-top countdown widget.")
    parser.add_argument("--reset", action="store_true",
                         help="Restart the 219-day countdown from right now.")
    parser.add_argument("--install-autostart", action="store_true",
                         help="Make the widget launch automatically at login/startup.")
    args = parser.parse_args()

    if args.install_autostart:
        install_autostart()
        return

    target, data = load_or_create_target(reset=args.reset)
    CountdownWidget(target, data)


if __name__ == "__main__":
    main()
