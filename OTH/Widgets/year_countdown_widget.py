import tkinter as tk
from datetime import datetime, timedelta
import os
import sys

# ============================================================
# YEAR COUNTDOWN - Windows mini desktop widget
# Counts from the current real time to 1 Jan 2027 00:00:00.
# If you run this in another year, it automatically targets
# the start of the following year.
# ============================================================

BG = "#111111"
FG = "#F2F2F2"
MUTED = "#999999"
ACCENT = "#4DA3FF"

root = tk.Tk()
root.title("Year Countdown")
root.configure(bg=BG)
root.overrideredirect(True)
root.attributes("-topmost", True)
root.resizable(False, False)

mode = tk.StringVar(value="Days")

# ----- target -----
def target_time():
    now = datetime.now()
    return datetime(now.year + 1, 1, 1, 0, 0, 0)

# ----- calculations -----
def update():
    now = datetime.now()
    target = target_time()
    seconds = max(0.0, (target - now).total_seconds())

    days = seconds / 86400
    hours = seconds / 3600
    months = days / 30.436875  # average Gregorian month

    if mode.get() == "Days":
        number.config(text=f"{days:.2f}")
        unit.config(text="days")
    elif mode.get() == "Months":
        number.config(text=f"{months:.2f}")
        unit.config(text="months")
    else:
        number.config(text=f"{hours:,.1f}")
        unit.config(text="hours")

    root.after(250, update)

# ----- dragging -----
drag_x = 0
drag_y = 0

def drag_start(event):
    global drag_x, drag_y
    drag_x = event.x_root - root.winfo_x()
    drag_y = event.y_root - root.winfo_y()

def drag_move(event):
    root.geometry(
        f"+{event.x_root - drag_x}+{event.y_root - drag_y}"
    )

# ----- UI -----
frame = tk.Frame(root, bg=BG, height=28)
frame.pack(fill="both", expand=True)
frame.pack_propagate(False)

number = tk.Label(
    frame,
    text="Loading...",
    bg=BG,
    fg=FG,
    font=("Segoe UI Semibold", 10),
    padx=5
)
number.pack(side="left")

unit = tk.Label(
    frame,
    text="days",
    bg=BG,
    fg=MUTED,
    font=("Segoe UI", 8)
)
unit.pack(side="left", padx=(0, 2))

menu = tk.OptionMenu(frame, mode, "Days", "Months", "Hours")
menu.config(
    bg=BG,
    fg=FG,
    activebackground="#222222",
    activeforeground=FG,
    bd=0,
    highlightthickness=0,
    relief="flat",
    font=("Segoe UI", 8),
    padx=0,
    pady=0
)
menu["menu"].config(
    bg="#181818",
    fg=FG,
    activebackground=ACCENT,
    activeforeground="white",
    font=("Segoe UI", 9)
)
menu.pack(side="left")

close = tk.Button(
    frame,
    text="×",
    command=root.destroy,
    bg=BG,
    fg=MUTED,
    activebackground=BG,
    activeforeground=FG,
    bd=0,
    highlightthickness=0,
    font=("Segoe UI", 10),
    padx=4,
    pady=0
)
close.pack(side="right")

# Drag anywhere except the dropdown/button.
for w in (frame, number, unit):
    w.bind("<ButtonPress-1>", drag_start)
    w.bind("<B1-Motion>", drag_move)

# ----- right click menu -----
def context_menu(event):
    m = tk.Menu(root, tearoff=False, bg="#181818", fg=FG)
    m.add_command(label="Days", command=lambda: mode.set("Days"))
    m.add_command(label="Months", command=lambda: mode.set("Months"))
    m.add_command(label="Hours", command=lambda: mode.set("Hours"))
    m.add_separator()
    m.add_command(label="Exit", command=root.destroy)
    m.tk_popup(event.x_root, event.y_root)

for w in (root, frame, number, unit):
    w.bind("<Button-3>", context_menu)

# ----- startup -----
def install_startup():
    # Windows Startup folder; no administrator permission needed.
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return

    startup = os.path.join(
        appdata,
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup"
    )
    os.makedirs(startup, exist_ok=True)

    script = os.path.abspath(sys.argv[0])
    python_exe = sys.executable

    # pythonw.exe prevents a black console window on startup.
    pythonw = os.path.join(os.path.dirname(python_exe), "pythonw.exe")
    if not os.path.exists(pythonw):
        pythonw = python_exe

    launcher = os.path.join(startup, "YearCountdownWidget.cmd")

    with open(launcher, "w", encoding="utf-8") as f:
        f.write('@echo off\n')
        f.write(f'start "" "{pythonw}" "{script}"\n')

# Install startup only after the program itself has successfully loaded.
try:
    install_startup()
except Exception:
    pass

# ----- initial position -----
root.update_idletasks()
sw = root.winfo_screenwidth()
sh = root.winfo_screenheight()
ww = root.winfo_width()
wh = root.winfo_height()

root.geometry(f"+{sw - ww - 15}+{sh - wh - 50}")

update()
root.mainloop()
