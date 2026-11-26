"""Looks at the virtual screen during the CI smoke test (see smoke_test.sh)."""
import os
import sys

import numpy as np
from PIL import ImageGrab
from Xlib import X, display

out, what = sys.argv[1], sys.argv[2]
img = ImageGrab.grab(xdisplay=os.environ["DISPLAY"]).convert("RGB")
img.save(out)
a = np.asarray(img).astype(int)


def count(rgb, tol=0):
    return int((np.abs(a - np.array(rgb)).max(axis=2) <= tol).sum())


key = count((1, 2, 3))                       # the see-through colour: must never be visible
body = count((0x7F, 0xA3, 0xC2), 2)          # Pixbot's steel blue
eyes = count((0x7C, 0xF3, 0xFF), 2)

d = display.Display()
root = d.screen().root
titles = []
for xid in root.get_full_property(d.intern_atom("_NET_CLIENT_LIST"), X.AnyPropertyType).value:
    w = d.create_resource_object("window", xid)
    p = w.get_full_property(d.intern_atom("_NET_WM_NAME"), X.AnyPropertyType)
    titles.append(p.value.decode() if p and isinstance(p.value, bytes) else str(p.value if p else ""))

ok = key == 0 and body > 40 and eyes > 4
if what == "app":
    ok = ok and "Pixbot" in titles
msg = (f"{what}: robot pixels={body}, eye pixels={eyes}, see-through-colour pixels={key}, "
       f"windows={titles}")
print(("::notice::" if ok else "::error::") + msg)
sys.exit(0 if ok else 1)
