import tkinter as tk
from tkinter import messagebox
import ctypes
import ctypes.wintypes
import json
import time
from datetime import date
from pathlib import Path


# ============================================================
# MINIMAL WINDOWS SCREEN-TIME WIDGET
# ============================================================
# No external packages required.
#
# Features:
# - Minimal clock-style UI
# - Large HH MM display
# - Small arrow expands application usage
# - Fully custom resizable window
# - Resize from edges and corners
# - Drag from empty area
# - Always on top
# - Live screen-time tracking
# - Application usage
# - Saves data between launches
# - Reset button
# - Close button
# ============================================================


# -----------------------------
# Windows API
# -----------------------------

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


# -----------------------------
# Data
# -----------------------------

DATA_FILE = Path.home() / "screen_time_data.json"
IDLE_LIMIT = 5 * 60


def new_data():
    return {
        "date": str(date.today()),
        "total_seconds": 0.0,
        "applications": {}
    }


def load_data():
    if not DATA_FILE.exists():
        return new_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("date") != str(date.today()):
            return new_data()

        data.setdefault("total_seconds", 0.0)
        data.setdefault("applications", {})
        return data

    except Exception:
        return new_data()


data = load_data()


def save_data():
    try:
        temp = DATA_FILE.with_suffix(".tmp")

        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        temp.replace(DATA_FILE)

    except Exception:
        pass


# -----------------------------
# Application names
# -----------------------------

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
}


def get_application_name(title):
    if not title:
        return "Other"

    low = title.lower()

    for keyword, name in KNOWN_APPS.items():
        if keyword in low:
            return name

    return title.strip()[:22] or "Other"


# -----------------------------
# Formatting
# -----------------------------

def format_hm(seconds):
    total_minutes = int(seconds) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"{hours:02d}  {minutes:02d}"


def format_usage(seconds):
    total_minutes = int(seconds) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours:
        return f"{hours:02d}h {minutes:02d}m"

    return f"{minutes:02d}m"


# -----------------------------
# Colors
# -----------------------------
# TRANSPARENT is the "magic" color key. Every widget background painted
# with this exact color becomes fully see-through on Windows (via
# -transparentcolor below), so only the text/icons/bars are visible on
# the desktop -- no black card behind them.
#
# Windows requires this key color to be unique (not reused by any real
# UI element), so nothing else in the palette is allowed to match it.

TRANSPARENT = "#010203"
BG = TRANSPARENT          # kept as an alias so existing widget code below still works
CARD = TRANSPARENT        # the "card" look is gone -- cards are transparent too now
WHITE = "#F5F5F5"
MUTED = "#85898E"
DIM = "#55595E"
ACCENT = "#7CF59F"
IDLE = "#F0B15A"
BAR_BG = "#292C30"
BORDER = "#24272A"


# -----------------------------
# Window
# -----------------------------

root = tk.Tk()
root.title("Screen Time")
root.configure(bg=TRANSPARENT)
root.attributes("-topmost", True)

# Remove the normal Windows title bar.
# This gives the widget the very minimal appearance.
root.overrideredirect(True)

# Make every TRANSPARENT-colored pixel invisible, so the black
# rectangle disappears and only the text/icons/bars float on the
# desktop. This is a Windows-only color-key trick -- the window still
# receives clicks normally over the "transparent" areas, so dragging
# and resizing keep working.
try:
    root.attributes("-transparentcolor", TRANSPARENT)
except tk.TclError:
    # Not on Windows (or Tk build without color-key support) --
    # widget still works, it just keeps a solid background.
    pass

COMPACT_W = 330
COMPACT_H = 155

EXPANDED_W = 430
EXPANDED_H = 535

MIN_W = 260
MIN_H = 125

expanded = False

root.geometry(f"{COMPACT_W}x{COMPACT_H}+100+100")


# -----------------------------
# Windows rounded corners
# -----------------------------

def style_window():
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())

        # Rounded corners on Windows 11.
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2

        pref = ctypes.c_int(DWMWCP_ROUND)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(pref),
            ctypes.sizeof(pref)
        )
    except Exception:
        pass


# -----------------------------
# Dragging
# -----------------------------
# Why this is polling-based instead of the usual <Button-1>/<B1-Motion>
# bindings: with -transparentcolor set, Windows makes every
# TRANSPARENT-colored pixel click-through -- clicks on them fall
# straight to whatever is behind the widget, so Tkinter never even
# sees a press there. Only the opaque pixels (the actual digit/letter
# strokes) would receive a normal click, which is why dragging felt
# broken/"rippled" before: presses only landed intermittently, right
# on a letter edge.
#
# Instead we poll the real OS cursor position and mouse-button state
# directly, independent of which pixel is opaque or click-through.
# This makes the whole card draggable, including the empty space
# between the digits.

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def _get_cursor_pos():
    pt = _POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _left_button_down():
    # High bit set means the physical button is currently pressed.
    return bool(user32.GetAsyncKeyState(0x01) & 0x8000)


# Buttons (close/arrow/back/reset) are registered here after they're
# created below, so a click on them starts their own command instead
# of dragging the window.
NO_DRAG_WIDGETS = []

_drag_active = False
_drag_offset_x = 0
_drag_offset_y = 0
_button_was_down = False


def _widget_is_excluded(widget):
    while widget is not None:
        if widget in NO_DRAG_WIDGETS:
            return True
        widget = widget.master
    return False


def _point_in_resize_zone(rel_x, rel_y, w, h):
    return (
        rel_x <= RESIZE_BORDER
        or rel_x >= w - RESIZE_BORDER
        or rel_y <= RESIZE_BORDER
        or rel_y >= h - RESIZE_BORDER
    )


def poll_drag():
    global _drag_active, _drag_offset_x, _drag_offset_y, _button_was_down

    button_down = _left_button_down()

    if button_down and not _button_was_down:
        cx, cy = _get_cursor_pos()

        wx, wy = root.winfo_x(), root.winfo_y()
        ww, wh = root.winfo_width(), root.winfo_height()

        inside = wx <= cx <= wx + ww and wy <= cy <= wy + wh

        if inside:
            rel_x, rel_y = cx - wx, cy - wy
            widget = root.winfo_containing(cx, cy)

            if (
                not _widget_is_excluded(widget)
                and not _point_in_resize_zone(rel_x, rel_y, ww, wh)
            ):
                _drag_active = True
                _drag_offset_x = rel_x
                _drag_offset_y = rel_y

    elif not button_down:
        _drag_active = False

    if _drag_active and button_down:
        cx, cy = _get_cursor_pos()

        new_x = cx - _drag_offset_x
        new_y = cy - _drag_offset_y

        root.geometry(f"+{new_x}+{new_y}")

    _button_was_down = button_down

    root.after(15, poll_drag)


# -----------------------------
# Custom resizing
# -----------------------------
# The native title bar is removed, so resizing is handled here.
# Move to any edge/corner and drag.


RESIZE_BORDER = 8

resize_mode = None
resize_start_x = 0
resize_start_y = 0
resize_start_w = 0
resize_start_h = 0
resize_start_left = 0
resize_start_top = 0


def get_resize_mode(event):
    w = root.winfo_width()
    h = root.winfo_height()

    x = event.x
    y = event.y

    left = x <= RESIZE_BORDER
    right = x >= w - RESIZE_BORDER
    top = y <= RESIZE_BORDER
    bottom = y >= h - RESIZE_BORDER

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


def update_cursor(event):
    mode = get_resize_mode(event)

    cursors = {
        "nw": "size_nw_se",
        "se": "size_nw_se",
        "ne": "size_ne_sw",
        "sw": "size_ne_sw",
        "w": "size_we",
        "e": "size_we",
        "n": "size_ns",
        "s": "size_ns",
    }

    root.configure(cursor=cursors.get(mode, ""))


def start_resize(event):
    global resize_mode
    global resize_start_x, resize_start_y
    global resize_start_w, resize_start_h
    global resize_start_left, resize_start_top

    mode = get_resize_mode(event)

    if not mode:
        return

    resize_mode = mode

    resize_start_x = event.x_root
    resize_start_y = event.y_root

    resize_start_w = root.winfo_width()
    resize_start_h = root.winfo_height()

    resize_start_left = root.winfo_x()
    resize_start_top = root.winfo_y()


def resize_window(event):
    if not resize_mode:
        return

    dx = event.x_root - resize_start_x
    dy = event.y_root - resize_start_y

    w = resize_start_w
    h = resize_start_h
    x = resize_start_left
    y = resize_start_top

    if "e" in resize_mode:
        w = max(MIN_W, resize_start_w + dx)

    if "s" in resize_mode:
        h = max(MIN_H, resize_start_h + dy)

    if "w" in resize_mode:
        new_w = max(MIN_W, resize_start_w - dx)
        x = resize_start_left + (resize_start_w - new_w)
        w = new_w

    if "n" in resize_mode:
        new_h = max(MIN_H, resize_start_h - dy)
        y = resize_start_top + (resize_start_h - new_h)
        h = new_h

    root.geometry(f"{int(w)}x{int(h)}+{int(x)}+{int(y)}")


def stop_resize(event):
    global resize_mode
    resize_mode = None
    root.configure(cursor="")


# -----------------------------
# Main background
# -----------------------------

main = tk.Frame(
    root,
    bg=TRANSPARENT,
    highlightthickness=0
)

main.pack(fill="both", expand=True)


# -----------------------------
# Header
# -----------------------------

header = tk.Frame(main, bg=BG, height=28)
header.pack(fill="x", side="top")



# Small green status dot
dot = tk.Label(
    header,
    text="●",
    font=("Segoe UI", 8),
    bg=BG,
    fg=ACCENT
)

dot.pack(side="left", padx=(14, 5), pady=5)


header_title = tk.Label(
    header,
    text="SCREEN TIME",
    font=("Segoe UI", 8, "bold"),
    bg=BG,
    fg=MUTED
)

header_title.pack(side="left", pady=5)



# Close
def close_application():
    save_data()
    root.destroy()


close_button = tk.Button(
    header,
    text="×",
    command=close_application,
    font=("Segoe UI", 13),
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    cursor="hand2",
    padx=5
)

close_button.pack(side="right", padx=(0, 7))
NO_DRAG_WIDGETS.append(close_button)


# -----------------------------
# Compact display
# -----------------------------

compact_view = tk.Frame(main, bg=TRANSPARENT)
compact_view.pack(fill="both", expand=True)

# The whole compact card (not just the thin header strip) should be
# draggable, since with the black background gone there's no longer
# an obvious "title bar" to grab.


today_label = tk.Label(
    compact_view,
    text="TODAY",
    font=("Segoe UI", 7, "bold"),
    bg=TRANSPARENT,
    fg=DIM
)

today_label.place(x=17, y=34)


big_time = tk.Label(
    compact_view,
    text="00  00",
    font=("Segoe UI", 46, "bold"),
    bg=TRANSPARENT,
    fg=WHITE
)

big_time.place(x=15, y=42)


units = tk.Label(
    compact_view,
    text="HOURS              MINUTES",
    font=("Segoe UI", 6, "bold"),
    bg=TRANSPARENT,
    fg=DIM
)

units.place(x=22, y=112)


status = tk.Label(
    compact_view,
    text="●",
    font=("Segoe UI", 8),
    bg=TRANSPARENT,
    fg=ACCENT
)

status.place(
    relx=1.0,
    x=-60,
    y=114
)


# -----------------------------
# Arrow
# -----------------------------

def toggle_expanded():
    global expanded

    if expanded:
        show_compact()
    else:
        show_expanded()


arrow = tk.Button(
    compact_view,
    text="›",
    command=toggle_expanded,
    font=("Segoe UI", 24),
    bg=BG,
    fg=WHITE,
    activebackground=BG,
    activeforeground=ACCENT,
    bd=0,
    relief="flat",
    highlightthickness=0,
    cursor="hand2"
)

arrow.place(
    relx=1.0,
    x=-30,
    y=55
)
NO_DRAG_WIDGETS.append(arrow)


# -----------------------------
# Expanded view
# -----------------------------

expanded_view = tk.Frame(
    main,
    bg=BG
)


# Expanded header
expanded_header = tk.Frame(
    expanded_view,
    bg=BG,
    height=30
)

expanded_header.pack(fill="x")



back = tk.Button(
    expanded_header,
    text="‹",
    command=toggle_expanded,
    font=("Segoe UI", 20),
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    cursor="hand2"
)

back.pack(side="left", padx=(8, 0))
NO_DRAG_WIDGETS.append(back)


expanded_header_title = tk.Label(
    expanded_header,
    text="SCREEN TIME",
    font=("Segoe UI", 8, "bold"),
    bg=BG,
    fg=MUTED
)

expanded_header_title.pack(side="left", padx=3)


# Expanded close
expanded_close = tk.Button(
    expanded_header,
    text="×",
    command=close_application,
    font=("Segoe UI", 13),
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    cursor="hand2"
)

expanded_close.pack(side="right", padx=8)
NO_DRAG_WIDGETS.append(expanded_close)


# Expanded total (no card/box behind it -- just transparent text now)
total_box = tk.Frame(
    expanded_view,
    bg=CARD,
    highlightthickness=0
)

total_box.pack(
    fill="x",
    padx=18,
    pady=(5, 18)
)


usage_title = tk.Label(
    total_box,
    text="TODAY'S USAGE",
    font=("Segoe UI", 8, "bold"),
    bg=CARD,
    fg=MUTED
)

usage_title.pack(anchor="w", padx=18, pady=(13, 0))


expanded_time = tk.Label(
    total_box,
    text="00  00",
    font=("Segoe UI", 40, "bold"),
    bg=CARD,
    fg=WHITE
)

expanded_time.pack(anchor="w", padx=18)


expanded_units = tk.Label(
    total_box,
    text="HOURS              MINUTES",
    font=("Segoe UI", 6, "bold"),
    bg=CARD,
    fg=DIM
)

expanded_units.pack(anchor="w", padx=21, pady=(0, 13))


# -----------------------------
# App usage
# -----------------------------

apps_title = tk.Label(
    expanded_view,
    text="APPLICATION USAGE",
    font=("Segoe UI", 8, "bold"),
    bg=BG,
    fg=MUTED
)

apps_title.pack(anchor="w", padx=20)


apps_frame = tk.Frame(
    expanded_view,
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

    row.pack(fill="x", pady=2)
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
        width=150,
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
        relx=1.0,
        x=-2,
        y=0,
        width=60,
        height=18
    )

    bar_bg = tk.Frame(
        row,
        bg=BAR_BG,
        height=4
    )

    bar_bg.place(
        x=0,
        y=26,
        relwidth=1,
        width=-62,
        height=4
    )

    ratio = seconds / maximum if maximum else 0
    ratio = max(0, min(1, ratio))

    bar = tk.Frame(
        row,
        bg=ACCENT,
        height=4
    )

    bar.place(
        x=0,
        y=26,
        relwidth=ratio,
        height=4
    )


def update_application_list():

    for widget in apps_frame.winfo_children():
        widget.destroy()

    apps = data.get("applications", {})

    sorted_apps = sorted(
        apps.items(),
        key=lambda item: item[1],
        reverse=True
    )[:6]

    if not sorted_apps:

        tk.Label(
            apps_frame,
            text="No application usage yet",
            font=("Segoe UI", 8),
            bg=BG,
            fg=MUTED
        ).pack(pady=18)

        return

    maximum = max(seconds for _, seconds in sorted_apps)

    for name, seconds in sorted_apps:
        create_app_row(name, seconds, maximum)


# -----------------------------
# Footer
# -----------------------------

separator = tk.Frame(
    expanded_view,
    bg=BORDER,
    height=1
)

separator.pack(
    fill="x",
    padx=20,
    pady=(14, 8)
)


footer = tk.Frame(
    expanded_view,
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
    fg=ACCENT
)

expanded_status.pack(side="left")


def reset_data():

    if not messagebox_ask_reset():
        return

    data["date"] = str(date.today())
    data["total_seconds"] = 0.0
    data["applications"] = {}

    save_data()
    update_display()


def messagebox_ask_reset():
    # A tiny custom confirmation keeps the main widget borderless.
    answer = messagebox.askyesno(
        "Reset Screen Time",
        "Reset today's screen-time data?"
    )

    return answer


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

reset_button.pack(side="right")
NO_DRAG_WIDGETS.append(reset_button)


# -----------------------------
# Switching views
# -----------------------------

def set_geometry(width, height):
    x = root.winfo_x()
    y = root.winfo_y()

    root.geometry(
        f"{width}x{height}+{x}+{y}"
    )


def show_compact():
    global expanded

    expanded = False

    expanded_view.pack_forget()

    compact_view.pack(
        fill="both",
        expand=True
    )

    set_geometry(
        COMPACT_W,
        COMPACT_H
    )

    update_display()


def show_expanded():
    global expanded

    expanded = True

    compact_view.pack_forget()

    expanded_view.pack(
        fill="both",
        expand=True
    )

    set_geometry(
        EXPANDED_W,
        EXPANDED_H
    )

    update_application_list()
    update_display()


# -----------------------------
# Display
# -----------------------------

def update_display():

    total = data.get("total_seconds", 0.0)

    display_time = format_hm(total)

    big_time.config(
        text=display_time
    )

    expanded_time.config(
        text=display_time
    )

    if get_idle_seconds() < IDLE_LIMIT:

        color = ACCENT
        text = "●  Tracking"

    else:

        color = IDLE
        text = "●  Idle"

    status.config(
        fg=color
    )

    expanded_status.config(
        text=text,
        fg=color
    )

    if expanded:
        update_application_list()


# -----------------------------
# Tracking
# -----------------------------

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

        title = get_foreground_title()

        app = get_application_name(title)

        data["applications"].setdefault(
            app,
            0.0
        )

        data["applications"][app] += elapsed

    if now - last_save >= 10:

        save_data()
        last_save = now

    update_display()

    root.after(
        1000,
        tracking_loop
    )


# -----------------------------
# Bind resizing to entire window
# -----------------------------

def bind_recursive(widget):
    widget.bind("<Motion>", update_cursor, add="+")
    widget.bind("<ButtonPress-1>", start_resize, add="+")
    widget.bind("<B1-Motion>", resize_window, add="+")
    widget.bind("<ButtonRelease-1>", stop_resize, add="+")


# We bind the resize area to the main surface.
# Buttons continue to receive their own clicks.
bind_recursive(main)


# -----------------------------
# Start
# -----------------------------

root.after(100, style_window)

update_display()

tracking_loop()
poll_drag()

root.mainloop()
