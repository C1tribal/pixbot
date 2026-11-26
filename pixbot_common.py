"""Shared size / colour constants for Pixbot."""
import json as _json
import os as _os

PX = 4                      # pixels per unit (bigger number = bigger Pixbot)
try:                        # size chosen in the Pixbot app
    from pixbot_paths import SETTINGS_FILE as _SF
    with open(_SF,
              encoding="utf-8") as _f:
        PX = int(min(8, max(2, _json.load(_f).get("size", PX))))
except Exception:
    pass
HEAD = 10                   # room above the body for effects
SIDE = 9                    # room left/right for props
FOOT = 3                    # room under the feet (flips)
FEET = HEAD + 8             # canvas row of the feet
COLS, ROWS = 12 + 2 * SIDE, FEET + FOOT
CX = COLS / 2               # body centre column inside the window
W, H = COLS * PX, ROWS * PX
KEY = "#010203"             # transparent colour
ORANGE = "#D97757"
DARK_ORANGE = "#B85F42"
LIGHT = "#F2B49C"
EYE = "#000000"
GREY = "#5A5A5A"
RED = "#E5484D"
BLOCK = "#C9B79C"
GOLD = "#FFD166"
WOOD = "#8B5A2B"
DIRT = ("#8B5A2B", "#A0703F", "#6B4423", "#C9B79C")
DUST = ("#BFB6AE", "#D8D0C8", "#9E958D")
CODE_COLORS = ("#D97757", "#8FD3FF", "#B5E48C", "#FFD166", "#C3A6FF", "#BBBBBB")
FPS = 60
GRAVITY = 2600.0            # px/s^2
HALF = 6 * PX               # half of Pixbot's width incl. arms

__all__ = [n for n in dir() if n.isupper()]
