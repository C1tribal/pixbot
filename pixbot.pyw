"""Pixbot - start here.

    pixbot.pyw              opens the Pixbot app (and starts Pixbot on your desktop)
    pixbot.pyw --pet        starts only Pixbot on the desktop, no window
                            (this is what "Start Pixbot when Windows starts" uses)

(Pixbot.exe on the Releases page is this same file, bundled with PyInstaller.)
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if "--pet" in sys.argv:
    runpy.run_path(os.path.join(HERE, "pixbot_pet.pyw"), run_name="__main__")
else:
    runpy.run_path(os.path.join(HERE, "pixbot_app.pyw"), run_name="__main__")
