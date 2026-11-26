"""Where Pixbot keeps things.

RES_DIR  - files that ship with Pixbot (icon, default links). Inside the .exe when frozen.
DATA_DIR - your own settings and small runtime files: %APPDATA%\\Pixbot on Windows,
           ~/.config/Pixbot on Linux (nothing else is ever written anywhere on your PC)
"""
import os
import shutil
import sys

FROZEN = getattr(sys, "frozen", False)
SRC_DIR = os.path.dirname(os.path.abspath(sys.executable if FROZEN else __file__))
RES_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
IS_WIN = sys.platform == "win32"
if IS_WIN:
    DATA_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "Pixbot")
else:
    DATA_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                            "Pixbot")
os.makedirs(DATA_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(DATA_DIR, "pixbot_settings.json")
COMMAND_FILE = os.path.join(DATA_DIR, "pixbot_cmd.json")
PID_FILE = os.path.join(DATA_DIR, "pixbot.pid")
ICON_FILE = os.path.join(RES_DIR, "pixbot.ico")
ICON_PNG = os.path.join(RES_DIR, "pixbot.png")
# donation links: your own copy in DATA_DIR wins, otherwise the one that ships with Pixbot
LINKS_FILE = os.path.join(DATA_DIR, "pixbot_links.json")
DEFAULT_LINKS_FILE = os.path.join(RES_DIR, "pixbot_links.json")

# one-time move of settings that older versions kept next to the scripts
_old = os.path.join(SRC_DIR, "pixbot_settings.json")
if not os.path.exists(SETTINGS_FILE) and os.path.exists(_old):
    try:
        shutil.copyfile(_old, SETTINGS_FILE)
    except OSError:
        pass


def links_path():
    return LINKS_FILE if os.path.exists(LINKS_FILE) else DEFAULT_LINKS_FILE


def launch_cmd(settings=False):
    """Command line that starts Pixbot on the desktop (settings=False, no window)
    or opens the Pixbot app (settings=True) - works from source and as .exe."""
    flag = ["--settings"] if settings else ["--pet"]
    if os.environ.get("APPIMAGE"):              # Linux AppImage: start the .AppImage file itself
        return [os.environ["APPIMAGE"]] + flag
    if FROZEN:
        return [sys.executable] + flag
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if IS_WIN and os.path.exists(pyw) else sys.executable
    return [exe, os.path.join(RES_DIR, "pixbot.pyw")] + flag
