"""Pixbot's platform layer: one set of functions, with a Windows version
(pixbot_win.py) and a Linux version (pixbot_linux.py).

Both only read information (screens, windows, mouse position, which keys are held,
battery). See each file for exactly what is asked of the system.
"""
import os
import sys

IS_WIN = sys.platform == "win32"

if IS_WIN:
    from pixbot_win import *            # noqa: F401,F403
    from pixbot_win import NAME         # noqa: F401
else:
    import pixbot_linux
    from pixbot_linux import *          # noqa: F401,F403
    from pixbot_linux import NAME       # noqa: F401
    _res = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    pixbot_linux._FONT_DIRS.append(os.path.join(_res, "fonts"))
