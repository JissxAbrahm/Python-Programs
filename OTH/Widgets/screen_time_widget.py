import tkinter as tk
from tkinter import messagebox
import ctypes
import ctypes.wintypes
import json
import time
from datetime import date
from pathlib import Path


# ============================================================
# SCREEN TIME WIDGET - WINDOWS
# ============================================================
# No third-party packages required.
#
# Features:
# - Windows 11-inspired dark/glass UI
# - Compact mode with large screen-time display
# - Right-arrow expands application usage
# - Live tracking
# - Detects keyboard/mouse activity
# - Stops counting after 5 minutes of inactivity
# - Application usage
# - Daily persistent data
# - Drag anywhere
# - Always on top
# - Reset today's data
# - Close button
#
# Data file:
#   C:\\Users\\<username>\\screen_time_data.json
# ============================================================


# ============================================================
# WINDOWS API
# ============================================================

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
        elapsed_ms = kernel32.GetTickCount() - info.dwTime
        return elapsed_ms / 1000.0

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


# ============================================================
# WINDOWS 11 WINDOW STYLING
# ============================================================

def enable_windows11_rounding():
    """
    Ask Windows 11 to use rounded corners.
    It safely does nothing on systems where the API is unavailable.
    """
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())

        # DWMWA_WINDOW_CORNER_PREFERENCE
        # 33 = corner preference
        # 2 = round
        DWMWA_WINDOW_CORNER_PREFERENCE = 33
        DWMWCP_ROUND = 2

        preference = ctypes.c_int(DWMWCP_ROUND)

        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(preference),
            ctypes.sizeof(preference)
        )
    except Exception:
        pass


def enable_dark_titlebar():
    try:
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())

        # Windows 10/11 immersive dark mode.
        # Different Windows builds have used 19 or 20.
        for attribute in (20, 19):
            value = ctypes.c_int(1)

            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )

            if result == 0:
                break

    except Exception:
        pass


# ============================================================
# DATA
# ============================================================

DATA_FILE = Path.home() / "screen_time_data.json"

# Consider the user idle after 5 minutes without keyboard/mouse input.
IDLE_LIMIT = 5 * 60


def new_data():
    return {
        "date": str(date.today()),
        "total_seconds": 0.0,
        "applications": {}
    }


def load_data():
    today = str(date.today())

    if not DATA_FILE.exists():
        return new_data()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)

        if saved.get("date") != today:
            return new_data()

        saved.setdefault("total_seconds", 0.0)
        saved.setdefault("applications", {})

        return saved

    except Exception:
        return new_data()


data = load_data()


def save_data():
    try:
        temp_file = DATA_FILE.with_suffix(".tmp")

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        temp_file.replace(DATA_FILE)

    except Exception as error:
        print("Could not save screen-time data:", error)


# ============================================================
# APPLICATION NAME
# ============================================================

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

    title_lower = title.lower()

    for keyword, app_name in KNOWN_APPS.items():
        if keyword in title_lower:
            return app_name

    # Keep unknown application names short.
    cleaned = title.strip()

    if not cleaned:
        return "Other"

    return cleaned[:24]


# ============================================================
# TIME FORMATTING
# ============================================================

def hours_minutes(seconds):
    total_minutes = int(seconds) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60

    return hours, minutes


def format_usage(seconds):
    hours, minutes = hours_minutes(seconds)

    if hours > 0:
        return f"{hours:02d}h {minutes:02d}m"

    return f"{minutes:02d}m"


def format_big_time(seconds):
    hours, minutes = hours_minutes(seconds)

    return f"{hours:02d}  {minutes:02d}"


# ============================================================
# COLORS / STYLE
# ============================================================

WINDOW_BG = "#08090A"
CARD_BG = "#121416"
CARD_BG_2 = "#181A1D"

WHITE = "#F4F4F4"
MUTED = "#898D92"
DIM = "#5F6368"

ACCENT = "#72F39A"
ACCENT_DIM = "#1D3526"

IDLE_COLOR = "#F2B45F"

BAR_BG = "#303236"
BORDER = "#292C30"


# ============================================================
# MAIN WINDOW
# ============================================================

root = tk.Tk()

root.title("Screen Time")

root.configure(bg=WINDOW_BG)

root.resizable(False, False)

root.attributes("-topmost", True)

# Slight transparency for a glass-like appearance.
# Text remains crisp because the whole window is only lightly transparent.
try:
    root.attributes("-alpha", 0.97)
except Exception:
    pass


COMPACT_WIDTH = 350
COMPACT_HEIGHT = 175

EXPANDED_WIDTH = 430
EXPANDED_HEIGHT = 575

expanded = False

root.geometry(
    f"{COMPACT_WIDTH}x{COMPACT_HEIGHT}+100+100"
)


# ============================================================
# DRAGGING
# ============================================================

drag_start_x = 0
drag_start_y = 0


def start_drag(event):
    global drag_start_x, drag_start_y

    drag_start_x = event.x
    drag_start_y = event.y


def drag_window(event):
    x = root.winfo_x() + event.x - drag_start_x
    y = root.winfo_y() + event.y - drag_start_y

    root.geometry(f"+{x}+{y}")


# ============================================================
# HELPERS
# ============================================================

def make_button(parent, text, command, width=3):
    return tk.Button(
        parent,
        text=text,
        command=command,
        font=("Segoe UI", 14),
        bg=WINDOW_BG,
        fg=MUTED,
        activebackground=WINDOW_BG,
        activeforeground=WHITE,
        bd=0,
        relief="flat",
        highlightthickness=0,
        cursor="hand2",
        width=width
    )


# ============================================================
# HEADER
# ============================================================

header = tk.Frame(
    root,
    bg=WINDOW_BG,
    height=42
)

header.pack(
    fill="x",
    side="top"
)

header.bind("<Button-1>", start_drag)
header.bind("<B1-Motion>", drag_window)


logo = tk.Label(
    header,
    text="●",
    font=("Segoe UI", 10),
    bg=WINDOW_BG,
    fg=ACCENT
)

logo.pack(
    side="left",
    padx=(18, 7)
)


title = tk.Label(
    header,
    text="SCREEN TIME",
    font=("Segoe UI", 9, "bold"),
    bg=WINDOW_BG,
    fg=MUTED
)

title.pack(
    side="left"
)

title.bind("<Button-1>", start_drag)
title.bind("<B1-Motion>", drag_window)


# Close button
def close_application():
    save_data()
    root.destroy()


close_button = make_button(
    header,
    "×",
    close_application,
    2
)

close_button.pack(
    side="right",
    padx=(0, 10)
)


# ============================================================
# COMPACT VIEW
# ============================================================

compact_view = tk.Frame(
    root,
    bg=WINDOW_BG
)

compact_view.pack(
    fill="both",
    expand=True
)


# Big usage display
compact_display = tk.Frame(
    compact_view,
    bg=WINDOW_BG
)

compact_display.pack(
    fill="x",
    padx=24,
    pady=(2, 0)
)


am_label = tk.Label(
    compact_display,
    text="TODAY",
    font=("Segoe UI", 8, "bold"),
    bg=WINDOW_BG,
    fg=MUTED
)

am_label.place(
    x=0,
    y=6
)


big_time = tk.Label(
    compact_display,
    text="00  00",
    font=("Segoe UI", 48, "bold"),
    bg=WINDOW_BG,
    fg=WHITE
)

big_time.pack(
    anchor="w",
    pady=(0, 0)
)


hm_label = tk.Label(
    compact_display,
    text="HOURS                 MINUTES",
    font=("Segoe UI", 7, "bold"),
    bg=WINDOW_BG,
    fg=DIM
)

hm_label.pack(
    anchor="w",
    padx=(4, 0)
)


# Status
status_label = tk.Label(
    compact_view,
    text="●  Tracking",
    font=("Segoe UI", 8, "bold"),
    bg=WINDOW_BG,
    fg=ACCENT
)

status_label.pack(
    side="left",
    padx=(25, 0),
    pady=(5, 10)
)


# Arrow button
def toggle_expanded():
    global expanded

    expanded = not expanded

    if expanded:
        show_expanded()
    else:
        show_compact()


arrow_button = tk.Button(
    compact_view,
    text="›",
    command=toggle_expanded,
    font=("Segoe UI", 28),
    bg=WINDOW_BG,
    fg=WHITE,
    activebackground=WINDOW_BG,
    activeforeground=ACCENT,
    bd=0,
    relief="flat",
    highlightthickness=0,
    cursor="hand2"
)

arrow_button.pack(
    side="right",
    padx=(0, 18),
    pady=(0, 3)
)


# ============================================================
# EXPANDED VIEW
# ============================================================

expanded_view = tk.Frame(
    root,
    bg=WINDOW_BG
)


# Expanded header
expanded_header = tk.Frame(
    expanded_view,
    bg=WINDOW_BG,
    height=38
)

expanded_header.pack(
    fill="x"
)

expanded_header.bind("<Button-1>", start_drag)
expanded_header.bind("<B1-Motion>", drag_window)


back_button = tk.Button(
    expanded_header,
    text="‹",
    command=toggle_expanded,
    font=("Segoe UI", 22),
    bg=WINDOW_BG,
    fg=MUTED,
    activebackground=WINDOW_BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    highlightthickness=0,
    cursor="hand2"
)

back_button.pack(
    side="left",
    padx=(10, 0)
)


expanded_title = tk.Label(
    expanded_header,
    text="SCREEN TIME",
    font=("Segoe UI", 9, "bold"),
    bg=WINDOW_BG,
    fg=MUTED
)

expanded_title.pack(
    side="left",
    padx=4
)

expanded_title.bind("<Button-1>", start_drag)
expanded_title.bind("<B1-Motion>", drag_window)


# Expanded total card
total_card = tk.Frame(
    expanded_view,
    bg=CARD_BG,
    highlightbackground=BORDER,
    highlightthickness=1
)

total_card.pack(
    fill="x",
    padx=18,
    pady=(4, 14)
)


expanded_today = tk.Label(
    total_card,
    text="TODAY'S USAGE",
    font=("Segoe UI", 9, "bold"),
    bg=CARD_BG,
    fg=MUTED
)

expanded_today.pack(
    anchor="w",
    padx=20,
    pady=(16, 0)
)


expanded_big_time = tk.Label(
    total_card,
    text="00  00",
    font=("Segoe UI", 43, "bold"),
    bg=CARD_BG,
    fg=WHITE
)

expanded_big_time.pack(
    anchor="w",
    padx=20
)


expanded_units = tk.Label(
    total_card,
    text="HOURS                 MINUTES",
    font=("Segoe UI", 7, "bold"),
    bg=CARD_BG,
    fg=DIM
)

expanded_units.pack(
    anchor="w",
    padx=(24, 0),
    pady=(0, 14)
)


# ============================================================
# APPLICATION USAGE
# ============================================================

apps_title = tk.Label(
    expanded_view,
    text="APPLICATION USAGE",
    font=("Segoe UI", 9, "bold"),
    bg=WINDOW_BG,
    fg=MUTED
)

apps_title.pack(
    anchor="w",
    padx=20,
    pady=(0, 7)
)


apps_frame = tk.Frame(
    expanded_view,
    bg=WINDOW_BG
)

apps_frame.pack(
    fill="x",
    padx=20
)


def create_app_row(name, seconds, maximum):

    row = tk.Frame(
        apps_frame,
        bg=WINDOW_BG,
        height=51
    )

    row.pack(
        fill="x",
        pady=3
    )

    row.pack_propagate(False)


    name_label = tk.Label(
        row,
        text=name,
        font=("Segoe UI", 9),
        bg=WINDOW_BG,
        fg=WHITE,
        anchor="w"
    )

    name_label.place(
        x=0,
        y=0,
        width=180,
        height=20
    )


    time_label = tk.Label(
        row,
        text=format_usage(seconds),
        font=("Segoe UI", 9),
        bg=WINDOW_BG,
        fg=MUTED,
        anchor="e"
    )

    time_label.place(
        x=315,
        y=0,
        width=65,
        height=20
    )


    bar_bg = tk.Frame(
        row,
        bg=BAR_BG,
        height=5
    )

    bar_bg.place(
        x=0,
        y=28,
        width=380,
        height=5
    )


    percentage = seconds / maximum if maximum else 0
    percentage = max(0, min(percentage, 1))

    bar_width = int(380 * percentage)

    if seconds > 0 and bar_width < 2:
        bar_width = 2


    bar = tk.Frame(
        row,
        bg=ACCENT,
        height=5
    )

    bar.place(
        x=0,
        y=28,
        width=bar_width,
        height=5
    )


def update_application_list():

    for widget in apps_frame.winfo_children():
        widget.destroy()


    apps = data.get("applications", {})

    sorted_apps = sorted(
        apps.items(),
        key=lambda item: item[1],
        reverse=True
    )


    # Show top 6.
    top_apps = sorted_apps[:6]


    if not top_apps:

        empty = tk.Label(
            apps_frame,
            text="No application usage recorded yet",
            font=("Segoe UI", 9),
            bg=WINDOW_BG,
            fg=MUTED
        )

        empty.pack(
            pady=18
        )

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


# ============================================================
# EXPANDED FOOTER
# ============================================================

footer_separator = tk.Frame(
    expanded_view,
    bg=BORDER,
    height=1
)

footer_separator.pack(
    fill="x",
    padx=20,
    pady=(12, 8)
)


footer = tk.Frame(
    expanded_view,
    bg=WINDOW_BG
)

footer.pack(
    fill="x",
    padx=20
)


expanded_status = tk.Label(
    footer,
    text="●  Tracking",
    font=("Segoe UI", 9, "bold"),
    bg=WINDOW_BG,
    fg=ACCENT
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
    font=("Segoe UI", 9),
    bg=WINDOW_BG,
    fg=MUTED,
    activebackground=WINDOW_BG,
    activeforeground=WHITE,
    bd=0,
    relief="flat",
    highlightthickness=0,
    cursor="hand2"
)

reset_button.pack(
    side="right"
)


# ============================================================
# VIEW SWITCHING
# ============================================================

def show_compact():

    global expanded

    expanded = False

    expanded_view.pack_forget()

    compact_view.pack(
        fill="both",
        expand=True
    )

    root.geometry(
        f"{COMPACT_WIDTH}x{COMPACT_HEIGHT}+"
        f"{root.winfo_x()}+{root.winfo_y()}"
    )

    arrow_button.config(
        text="›"
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

    root.geometry(
        f"{EXPANDED_WIDTH}x{EXPANDED_HEIGHT}+"
        f"{root.winfo_x()}+{root.winfo_y()}"
    )

    update_application_list()

    update_display()


# ============================================================
# DISPLAY UPDATE
# ============================================================

def update_display():

    total = data.get("total_seconds", 0)

    compact_time = format_big_time(total)
    expanded_time = format_big_time(total)


    big_time.config(
        text=compact_time
    )

    expanded_big_time.config(
        text=expanded_time
    )


    idle = get_idle_seconds()


    if idle < IDLE_LIMIT:

        status_text = "●  Tracking"
        color = ACCENT

    else:

        status_text = "●  Idle"
        color = IDLE_COLOR


    status_label.config(
        text=status_text,
        fg=color
    )

    expanded_status.config(
        text=status_text,
        fg=color
    )


    if expanded:
        update_application_list()


# ============================================================
# TRACKING LOOP
# ============================================================

last_update = time.monotonic()
last_save = time.monotonic()


def tracking_loop():

    global last_update
    global last_save


    now = time.monotonic()

    elapsed = now - last_update

    last_update = now


    idle = get_idle_seconds()


    if idle < IDLE_LIMIT:

        # Add active time.
        data["total_seconds"] += elapsed


        # Find current application.
        title = get_foreground_title()

        application = get_application_name(title)


        if application not in data["applications"]:

            data["applications"][application] = 0.0


        data["applications"][application] += elapsed


    # Save approximately every 10 seconds.
    if now - last_save >= 10:

        save_data()

        last_save = now


    update_display()


    root.after(
        1000,
        tracking_loop
    )


# ============================================================
# WINDOW SETUP
# ============================================================

def finish_window_setup():

    enable_windows11_rounding()
    enable_dark_titlebar()


root.after(
    100,
    finish_window_setup
)


# ============================================================
# CLOSE EVENT
# ============================================================

root.protocol(
    "WM_DELETE_WINDOW",
    close_application
)


# ============================================================
# START
# ============================================================

update_display()

tracking_loop()

root.mainloop()
