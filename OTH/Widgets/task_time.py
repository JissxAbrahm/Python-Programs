
import tkinter as tk
import ctypes
import json
import os
import time
from datetime import datetime

# =========================================================
# SETTINGS
# =========================================================

APP_FOLDER = os.path.join(
    os.environ["APPDATA"],
    "ScreenTimeWidget"
)

DATA_FILE = os.path.join(
    APP_FOLDER,
    "screen_time.json"
)

POSITION_FILE = os.path.join(
    APP_FOLDER,
    "position.json"
)

os.makedirs(APP_FOLDER, exist_ok=True)

# =========================================================
# DATA
# =========================================================

def get_today():
    return datetime.now().strftime("%Y-%m-%d")


def load_data():

    if not os.path.exists(DATA_FILE):
        return {
            "date": get_today(),
            "seconds": 0
        }

    try:

        with open(DATA_FILE, "r") as f:
            data = json.load(f)

        if data["date"] != get_today():

            data = {
                "date": get_today(),
                "seconds": 0
            }

        return data

    except:

        return {
            "date": get_today(),
            "seconds": 0
        }


data = load_data()

total_seconds = float(data["seconds"])


def save_data():

    with open(DATA_FILE, "w") as f:

        json.dump(
            {
                "date": get_today(),
                "seconds": int(total_seconds)
            },
            f
        )


# =========================================================
# WINDOWS IDLE TIME
# =========================================================

class LASTINPUTINFO(ctypes.Structure):

    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint)
    ]


def get_idle_seconds():

    info = LASTINPUTINFO()

    info.cbSize = ctypes.sizeof(LASTINPUTINFO)

    ctypes.windll.user32.GetLastInputInfo(
        ctypes.byref(info)
    )

    tick = ctypes.windll.kernel32.GetTickCount()

    return (tick - info.dwTime) / 1000


# =========================================================
# FORMAT TIME
# =========================================================

def format_time(seconds):

    seconds = int(seconds)

    hours = seconds // 3600

    minutes = (seconds % 3600) // 60

    return f"{hours:02d}h {minutes:02d}m"


# =========================================================
# WINDOW
# =========================================================

root = tk.Tk()

root.overrideredirect(True)

# ---------------------------------------------------------
# IMPORTANT:
# This exact color becomes transparent on Windows.
# ---------------------------------------------------------

TRANSPARENT = "#ff00ff"

root.configure(
    background=TRANSPARENT
)

root.wm_attributes(
    "-transparentcolor",
    TRANSPARENT
)

root.wm_attributes(
    "-topmost",
    True
)

root.resizable(False, False)


# =========================================================
# TEXT
# =========================================================

label = tk.Label(

    root,

    text=format_time(total_seconds),

    font=(
        "Segoe UI",
        10,
        "normal"
    ),

    foreground="white",

    background=TRANSPARENT,

    borderwidth=0,

    highlightthickness=0,

    padx=0,

    pady=0
)

label.pack()


# Force Tkinter to calculate the EXACT size
root.update_idletasks()


width = label.winfo_reqwidth()
height = label.winfo_reqheight()

root.geometry(
    f"{width}x{height}"
)


# =========================================================
# POSITION
# =========================================================

def load_position():

    try:

        with open(POSITION_FILE, "r") as f:
            position = json.load(f)

        x = position["x"]
        y = position["y"]

        root.geometry(
            f"{width}x{height}+{x}+{y}"
        )

    except:

        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()

        x = screen_width - width - 150
        y = screen_height - height - 15

        root.geometry(
            f"{width}x{height}+{x}+{y}"
        )


def save_position():

    try:

        with open(POSITION_FILE, "w") as f:

            json.dump(
                {
                    "x": root.winfo_x(),
                    "y": root.winfo_y()
                },
                f
            )

    except:
        pass


load_position()


# =========================================================
# DRAG
# =========================================================

drag_x = 0
drag_y = 0


def start_drag(event):

    global drag_x
    global drag_y

    drag_x = event.x
    drag_y = event.y


def drag(event):

    x = root.winfo_pointerx() - drag_x
    y = root.winfo_pointery() - drag_y

    root.geometry(
        f"+{x}+{y}"
    )


def stop_drag(event):

    save_position()


label.bind(
    "<Button-1>",
    start_drag
)

label.bind(
    "<B1-Motion>",
    drag
)

label.bind(
    "<ButtonRelease-1>",
    stop_drag
)


# =========================================================
# RIGHT CLICK MENU
# =========================================================

menu = tk.Menu(
    root,
    tearoff=0
)


def show_stats():

    window = tk.Toplevel(root)

    window.title(
        "Screen Time"
    )

    window.geometry(
        "300x180"
    )

    window.resizable(
        False,
        False
    )

    tk.Label(
        window,
        text="Today's Screen Time",
        font=(
            "Segoe UI",
            13,
            "bold"
        )
    ).pack(pady=(25, 5))

    tk.Label(
        window,
        text=format_time(total_seconds),
        font=(
            "Segoe UI",
            25,
            "bold"
        )
    ).pack(pady=10)

    tk.Label(
        window,
        text=get_today(),
        font=(
            "Segoe UI",
            9
        )
    ).pack()


def reset_time():

    global total_seconds

    total_seconds = 0

    save_data()

    label.config(
        text=format_time(
            total_seconds
        )
    )


def exit_program():

    save_data()

    save_position()

    root.destroy()


menu.add_command(
    label="Screen Time",
    command=show_stats
)

menu.add_separator()

menu.add_command(
    label="Reset Today",
    command=reset_time
)

menu.add_separator()

menu.add_command(
    label="Exit",
    command=exit_program
)


def right_click(event):

    menu.tk_popup(
        event.x_root,
        event.y_root
    )


label.bind(
    "<Button-3>",
    right_click
)


# =========================================================
# SCREEN TIME UPDATE
# =========================================================

last_time = time.time()


def update():

    global total_seconds
    global last_time

    current_time = time.time()

    elapsed = current_time - last_time

    last_time = current_time

    # Count usage only if there was keyboard/mouse
    # activity within the previous 60 seconds.

    if get_idle_seconds() < 60:

        total_seconds += elapsed

        save_data()

    label.config(
        text=format_time(
            total_seconds
        )
    )

    root.update_idletasks()

    root.after(
        1000,
        update
    )


# =========================================================
# KEEP ON TOP
# =========================================================

def keep_on_top():

    root.wm_attributes(
        "-topmost",
        True
    )

    root.after(
        3000,
        keep_on_top
    )


# =========================================================
# START
# =========================================================

update()

keep_on_top()

root.mainloop()

