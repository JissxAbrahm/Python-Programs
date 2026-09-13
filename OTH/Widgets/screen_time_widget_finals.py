import tkinter as tk
from tkinter import messagebox
import ctypes
import ctypes.wintypes
import json
import time
from datetime import date
from pathlib import Path


# ============================================================
# MINIMAL SCREEN TIME WIDGET - WINDOWS 11
# ============================================================
# Compact design:
#
#   ● SCREEN TIME                         ×
#
#        00       18                    >
#       HOURS    MINUTES
#
# The compact box is intentionally tight around the content.
#
# Features:
#   - Minimal dark Windows 11-style widget
#   - Large hours/minutes display
#   - Right arrow opens application usage
#   - Close button
#   - Always on top
#   - Drag anywhere in the top area
#   - Resize from every edge and corner
#   - Live screen-time tracking
#   - Application usage tracking
#   - Persistent daily data
#   - Reset today's data
#
# No external Python packages are required.
# ============================================================


# ------------------------------------------------------------
# Windows API
# ------------------------------------------------------------

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.wintypes.UINT),
        ("dwTime", ctypes.wintypes.DWORD),
    ]


def get_idle_seconds():
    info = LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(LASTINPUTINFO)

    if user32.GetLastInputInfo(ctypes.byref(info)):
        return (kernel32.GetTickCount() - info.dwTime) / 1000.0

    return 0.0


def get_foreground_title():
    hwnd = user32.GetForegroundWindow()

    if not hwnd:
        return ""

    length = user32.GetWindowTextLengthW(hwnd)

    if length <= 0:
        return ""

    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, length + 1)

    return buffer.value


# ------------------------------------------------------------
# Data
# ------------------------------------------------------------

DATA_FILE = Path.home() / "screen_time_data.json"

# No keyboard/mouse input for 5 minutes = idle.
IDLE_LIMIT = 5 * 60


def empty_data():
    return {
        "date": str(date.today()),
        "total_seconds": 0.0,
        "applications": {}
    }


def load_data():
    if not DATA_FILE.exists():
        return empty_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            saved = json.load(file)

        if saved.get("date") != str(date.today()):
            return empty_data()

        saved.setdefault("total_seconds", 0.0)
        saved.setdefault("applications", {})

        return saved

    except Exception:
        return empty_data()


data = load_data()


def save_data():
    try:
        temporary = DATA_FILE.with_suffix(".tmp")

        with open(temporary, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)

        temporary.replace(DATA_FILE)

    except Exception:
        pass


# ------------------------------------------------------------
# Application detection
# ------------------------------------------------------------

KNOWN_APPS = {
    "visual studio code": "VS Code",
    "code -": "VS Code",

    "google chrome": "Chrome",
    "chrome": "Chrome",

    "mozilla firefox": "Firefox",
    "firefox": "Firefox",

    "microsoft edge": "Edge",
    "edge": "Edge",

    "windows terminal": "Terminal",
    "command prompt": "Command Prompt",
    "powershell": "PowerShell",

    "file explorer": "File Explorer",
    "settings": "Settings",
    "notepad": "Notepad",

    "discord": "Discord",
    "spotify": "Spotify",
    "steam": "Steam",

    "microsoft word": "Word",
    "microsoft excel": "Excel",
    "microsoft powerpoint": "PowerPoint",

    "figma": "Figma",
    "photoshop": "Photoshop",
    "adobe photoshop": "Photoshop",

    "github": "GitHub",
}


def get_application_name(title):
    if not title:
        return "Other"

    lower = title.lower()

    for keyword, name in KNOWN_APPS.items():
        if keyword in lower:
            return name

    title = title.strip()

    return title[:24] if title else "Other"


# ------------------------------------------------------------
# Time formatting
# ------------------------------------------------------------

def split_time(seconds):
    total_minutes = int(seconds) // 60

    hours = total_minutes // 60
    minutes = total_minutes % 60

    return hours, minutes


def format_big_time(seconds):
    hours, minutes = split_time(seconds)
    return f"{hours:02d}     {minutes:02d}"


def format_usage(seconds):
    hours, minutes = split_time(seconds)

    if hours:
        return f"{hours:02d}h {minutes:02d}m"

    return f"{minutes:02d}m"


# ------------------------------------------------------------
# Appearance
# ------------------------------------------------------------

BG = "#090A0B"
PANEL = "#0C0D0E"
WHITE = "#F2F2F2"
MUTED = "#8A8E93"
DIM = "#55595E"
GREEN = "#6EF39A"
IDLE = "#F0B35E"
BAR_BG = "#292C30"
BORDER = "#292C30"


# ------------------------------------------------------------
# Window
# ------------------------------------------------------------

root = tk.Tk()

root.title("Screen Time")

root.configure(bg=BG)

root.overrideredirect(True)
root.attributes("-topmost", True)

try:
    root.attributes("-alpha", 0.98)
except Exception:
    pass


# The compact widget is deliberately close to the proportions
# of the reference image.
COMPACT_W = 310
COMPACT_H = 132

EXPANDED_W = 440
EXPANDED_H = 520

MIN_W = 260
MIN_H = 112

root.geometry(
    f"{COMPACT_W}x{COMPACT_H}+100+100"
)

expanded = False


# ------------------------------------------------------------
# Windows 11 rounded corners
# ------------------------------------------------------------

def apply_windows_style():
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())

        # DWMWA_WINDOW_CORNER_PREFERENCE
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2

        value = ctypes.c_int(DWMWCP_ROUND)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(value),
            ctypes.sizeof(value)
        )

    except Exception:
        pass


# ------------------------------------------------------------
# Custom resizing
# ------------------------------------------------------------
# The window has no standard title bar.
# bind_all() is used so the resize detection still works when
# the pointer is over a child widget.
#
# Resize by grabbing:
#   left / right / top / bottom edge
#   any corner
# ------------------------------------------------------------

RESIZE_ZONE = 7

resize_mode = None
resize_x = 0
resize_y = 0
resize_w = 0
resize_h = 0
resize_left = 0
resize_top = 0


def get_root_mouse_position(event):
    return (
        event.x_root - root.winfo_rootx(),
        event.y_root - root.winfo_rooty()
    )


def get_resize_mode(event):
    x, y = get_root_mouse_position(event)

    w = root.winfo_width()
    h = root.winfo_height()

    left = x <= RESIZE_ZONE
    right = x >= w - RESIZE_ZONE
    top = y <= RESIZE_ZONE
    bottom = y >= h - RESIZE_ZONE

    if top and left:
        return "nw"

    if top and right:
        return "ne"

    if bottom and left:
        return "sw"

    if bottom and right:
        return "se"

    if left:
        return "w"

    if right:
        return "e"

    if top:
        return "n"

    if bottom:
        return "s"

    return None


def resize_cursor(mode):
    return {
        "nw": "size_nw_se",
        "se": "size_nw_se",
        "ne": "size_ne_sw",
        "sw": "size_ne_sw",
        "w": "size_we",
        "e": "size_we",
        "n": "size_ns",
        "s": "size_ns",
        None: "arrow"
    }.get(mode, "arrow")


def resize_motion(event):
    if resize_mode:
        return

    mode = get_resize_mode(event)

    try:
        root.configure(cursor=resize_cursor(mode))
    except Exception:
        pass


def begin_resize(event):
    global resize_mode
    global resize_x, resize_y
    global resize_w, resize_h
    global resize_left, resize_top

    mode = get_resize_mode(event)

    if not mode:
        return

    resize_mode = mode

    resize_x = event.x_root
    resize_y = event.y_root

    resize_w = root.winfo_width()
    resize_h = root.winfo_height()

    resize_left = root.winfo_x()
    resize_top = root.winfo_y()

    root.configure(cursor=resize_cursor(mode))


def perform_resize(event):
    if not resize_mode:
        return

    dx = event.x_root - resize_x
    dy = event.y_root - resize_y

    width = resize_w
    height = resize_h

    left = resize_left
    top = resize_top

    if "e" in resize_mode:
        width = max(MIN_W, resize_w + dx)

    if "s" in resize_mode:
        height = max(MIN_H, resize_h + dy)

    if "w" in resize_mode:
        width = max(MIN_W, resize_w - dx)
        left = resize_left + resize_w - width

    if "n" in resize_mode:
        height = max(MIN_H, resize_h - dy)
        top = resize_top + resize_h - height

    root.geometry(
        f"{int(width)}x{int(height)}+{int(left)}+{int(top)}"
    )


def end_resize(event):
    global resize_mode

    resize_mode = None

    root.configure(cursor="arrow")


root.bind_all("<Motion>", resize_motion, add="+")
root.bind_all("<ButtonPress-1>", begin_resize, add="+")
root.bind_all("<B1-Motion>", perform_resize, add="+")
root.bind_all("<ButtonRelease-1>", end_resize, add="+")


# ------------------------------------------------------------
# Dragging
# ------------------------------------------------------------

drag_x = 0
drag_y = 0


def begin_drag(event):
    global drag_x, drag_y

    if get_resize_mode(event):
        return

    drag_x = event.x_root
    drag_y = event.y_root


def perform_drag(event):
    if resize_mode:
        return

    # Only move if the mouse button was pressed in the header
    # or empty background.
    dx = event.x_root - drag_x
    dy = event.y_root - drag_y

    if abs(dx) < 1 and abs(dy) < 1:
        return

    x = root.winfo_x() + dx
    y = root.winfo_y() + dy

    root.geometry(f"+{x}+{y}")

    drag_x = event.x_root
    drag_y = event.y_root


# ------------------------------------------------------------
# Main surface
# ------------------------------------------------------------

surface = tk.Frame(
    root,
    bg=BG,
    highlightbackground=BORDER,
    highlightthickness=1
)

surface.pack(
    fill="both",
    expand=True
)


# ============================================================
# COMPACT VIEW
# ============================================================

compact = tk.Frame(
    surface,
    bg=BG
)

compact.pack(
    fill="both",
    expand=True
)


# Header
header = tk.Frame(
    compact,
    bg=BG,
    height=28
)

header.pack(
    fill="x",
    side="top"
)


header.bind("<ButtonPress-1>", begin_drag)
header.bind("<B1-Motion>", perform_drag)


green_dot = tk.Label(
    header,
    text="●",
    font=("Segoe UI", 7),
    bg=BG,
    fg=GREEN
)

green_dot.pack(
    side="left",
    padx=(14, 5),
    pady=4
)


title = tk.Label(
    header,
    text="SCREEN TIME",
    font=("Segoe UI", 8, "bold"),
    bg=BG,
    fg=MUTED
)

title.pack(
    side="left",
    pady=4
)


title.bind("<ButtonPress-1>", begin_drag)
title.bind("<B1-Motion>", perform_drag)


def close_application():
    save_data()
    root.destroy()


close_button = tk.Button(
    header,
    text="×",
    command=close_application,
    font=("Segoe UI", 12),
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    highlightthickness=0,
    cursor="hand2"
)

close_button.pack(
    side="right",
    padx=(0, 9),
    pady=1
)


# Main time area
time_area = tk.Frame(
    compact,
    bg=BG
)

time_area.pack(
    fill="both",
    expand=True,
    padx=(16, 10),
    pady=(0, 5)
)


# TODAY
today = tk.Label(
    time_area,
    text="TODAY",
    font=("Segoe UI", 6, "bold"),
    bg=BG,
    fg=DIM
)

today.place(
    x=1,
    y=1
)


# Large numbers
big_time = tk.Label(
    time_area,
    text="00     00",
    font=("Segoe UI", 42, "bold"),
    bg=BG,
    fg=WHITE
)

big_time.place(
    x=0,
    y=11
)


# Units
hours_label = tk.Label(
    time_area,
    text="HOURS",
    font=("Segoe UI", 6, "bold"),
    bg=BG,
    fg=DIM
)

hours_label.place(
    x=5,
    y=91
)


minutes_label = tk.Label(
    time_area,
    text="MINUTES",
    font=("Segoe UI", 6, "bold"),
    bg=BG,
    fg=DIM
)

minutes_label.place(
    x=142,
    y=91
)


# Arrow
def toggle_view():
    if expanded:
        show_compact()
    else:
        show_expanded()


arrow = tk.Button(
    time_area,
    text="›",
    command=toggle_view,
    font=("Segoe UI", 25),
    bg=BG,
    fg=WHITE,
    activebackground=BG,
    activeforeground=GREEN,
    bd=0,
    relief="flat",
    highlightthickness=0,
    cursor="hand2"
)

arrow.place(
    relx=1.0,
    x=-6,
    y=40,
    anchor="e"
)


# ============================================================
# EXPANDED VIEW
# ============================================================

expanded_frame = tk.Frame(
    surface,
    bg=BG
)


expanded_header = tk.Frame(
    expanded_frame,
    bg=BG,
    height=30
)

expanded_header.pack(
    fill="x"
)

expanded_header.bind("<ButtonPress-1>", begin_drag)
expanded_header.bind("<B1-Motion>", perform_drag)


back_button = tk.Button(
    expanded_header,
    text="‹",
    command=toggle_view,
    font=("Segoe UI", 20),
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    cursor="hand2"
)

back_button.pack(
    side="left",
    padx=(8, 0)
)


expanded_title = tk.Label(
    expanded_header,
    text="SCREEN TIME",
    font=("Segoe UI", 8, "bold"),
    bg=BG,
    fg=MUTED
)

expanded_title.pack(
    side="left",
    padx=3
)


expanded_close = tk.Button(
    expanded_header,
    text="×",
    command=close_application,
    font=("Segoe UI", 12),
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    cursor="hand2"
)

expanded_close.pack(
    side="right",
    padx=(0, 9)
)


# ------------------------------------------------------------
# Expanded total
# ------------------------------------------------------------

total_panel = tk.Frame(
    expanded_frame,
    bg=PANEL,
    highlightbackground=BORDER,
    highlightthickness=1
)

total_panel.pack(
    fill="x",
    padx=18,
    pady=(5, 14)
)


expanded_today = tk.Label(
    total_panel,
    text="TODAY",
    font=("Segoe UI", 8, "bold"),
    bg=PANEL,
    fg=MUTED
)

expanded_today.pack(
    anchor="w",
    padx=18,
    pady=(12, 0)
)


expanded_time = tk.Label(
    total_panel,
    text="00     00",
    font=("Segoe UI", 38, "bold"),
    bg=PANEL,
    fg=WHITE
)

expanded_time.pack(
    anchor="w",
    padx=18
)


expanded_units = tk.Label(
    total_panel,
    text="HOURS              MINUTES",
    font=("Segoe UI", 6, "bold"),
    bg=PANEL,
    fg=DIM
)

expanded_units.pack(
    anchor="w",
    padx=22,
    pady=(0, 12)
)


# ------------------------------------------------------------
# App usage
# ------------------------------------------------------------

app_title = tk.Label(
    expanded_frame,
    text="APP USAGE",
    font=("Segoe UI", 8, "bold"),
    bg=BG,
    fg=MUTED
)

app_title.pack(
    anchor="w",
    padx=20
)


apps_frame = tk.Frame(
    expanded_frame,
    bg=BG
)

apps_frame.pack(
    fill="x",
    padx=20,
    pady=(7, 0)
)


def create_app_row(name, seconds, maximum):

    row = tk.Frame(
        apps_frame,
        bg=BG,
        height=43
    )

    row.pack(
        fill="x",
        pady=2
    )

    row.pack_propagate(False)


    name_label = tk.Label(
        row,
        text=name,
        font=("Segoe UI", 8),
        bg=BG,
        fg=WHITE,
        anchor="w"
    )

    name_label.place(
        x=0,
        y=0,
        width=155,
        height=18
    )


    time_label = tk.Label(
        row,
        text=format_usage(seconds),
        font=("Segoe UI", 8),
        bg=BG,
        fg=MUTED,
        anchor="e"
    )

    time_label.place(
        relx=1,
        x=-1,
        y=0,
        width=62,
        height=18
    )


    background_bar = tk.Frame(
        row,
        bg=BAR_BG,
        height=4
    )

    background_bar.place(
        x=0,
        y=26,
        relwidth=1,
        width=-70,
        height=4
    )


    ratio = seconds / maximum if maximum else 0
    ratio = max(0, min(ratio, 1))

    progress = tk.Frame(
        row,
        bg=GREEN,
        height=4
    )

    progress.place(
        x=0,
        y=26,
        relwidth=ratio,
        height=4
    )


def update_apps():

    for widget in apps_frame.winfo_children():
        widget.destroy()

    apps = data.get("applications", {})

    top_apps = sorted(
        apps.items(),
        key=lambda item: item[1],
        reverse=True
    )[:6]

    if not top_apps:

        tk.Label(
            apps_frame,
            text="No application usage yet",
            font=("Segoe UI", 8),
            bg=BG,
            fg=MUTED
        ).pack(pady=18)

        return

    maximum = max(
        seconds for _, seconds in top_apps
    )

    for name, seconds in top_apps:
        create_app_row(
            name,
            seconds,
            maximum
        )


# ------------------------------------------------------------
# Expanded footer
# ------------------------------------------------------------

separator = tk.Frame(
    expanded_frame,
    bg=BORDER,
    height=1
)

separator.pack(
    fill="x",
    padx=20,
    pady=(12, 8)
)


footer = tk.Frame(
    expanded_frame,
    bg=BG
)

footer.pack(
    fill="x",
    padx=20
)


expanded_status = tk.Label(
    footer,
    text="●  Tracking",
    font=("Segoe UI", 8, "bold"),
    bg=BG,
    fg=GREEN
)

expanded_status.pack(
    side="left"
)


def reset_data():

    answer = messagebox.askyesno(
        "Reset Screen Time",
        "Reset today's screen-time data?"
    )

    if not answer:
        return

    data["date"] = str(date.today())
    data["total_seconds"] = 0.0
    data["applications"] = {}

    save_data()
    update_display()


reset_button = tk.Button(
    footer,
    text="Reset  ↻",
    command=reset_data,
    font=("Segoe UI", 8),
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    cursor="hand2"
)

reset_button.pack(
    side="right"
)


# ============================================================
# VIEW SWITCHING
# ============================================================

def set_size(width, height):
    x = root.winfo_x()
    y = root.winfo_y()

    root.geometry(
        f"{width}x{height}+{x}+{y}"
    )


def show_compact():
    global expanded

    expanded = False

    expanded_frame.pack_forget()

    compact.pack(
        fill="both",
        expand=True
    )

    set_size(
        COMPACT_W,
        COMPACT_H
    )

    update_display()


def show_expanded():
    global expanded

    expanded = True

    compact.pack_forget()

    expanded_frame.pack(
        fill="both",
        expand=True
    )

    set_size(
        EXPANDED_W,
        EXPANDED_H
    )

    update_apps()
    update_display()


# ============================================================
# Display update
# ============================================================

def update_display():

    total = data.get("total_seconds", 0.0)

    display = format_big_time(total)

    big_time.config(
        text=display
    )

    expanded_time.config(
        text=display
    )


    if get_idle_seconds() < IDLE_LIMIT:

        color = GREEN
        status_text = "●  Tracking"

    else:

        color = IDLE
        status_text = "●  Idle"


    green_dot.config(
        fg=color
    )

    expanded_status.config(
        text=status_text,
        fg=color
    )


    if expanded:
        update_apps()


# ============================================================
# Tracking
# ============================================================

last_update = time.monotonic()
last_save = time.monotonic()


def tracking_loop():

    global last_update
    global last_save

    now = time.monotonic()

    elapsed = now - last_update

    last_update = now


    if get_idle_seconds() < IDLE_LIMIT:

        data["total_seconds"] += elapsed

        title_text = get_foreground_title()

        app = get_application_name(title_text)

        data["applications"].setdefault(
            app,
            0.0
        )

        data["applications"][app] += elapsed


    # Save every 10 seconds.
    if now - last_save >= 10:

        save_data()

        last_save = now


    update_display()

    root.after(
        1000,
        tracking_loop
    )


# ============================================================
# Start
# ============================================================

root.after(
    100,
    apply_windows_style
)

update_display()

tracking_loop()

root.mainloop()
