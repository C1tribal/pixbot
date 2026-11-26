"""Pixbot - start here.

    pixbot.pyw              starts Pixbot on your desktop
    pixbot.pyw --settings   opens the settings window

(The .exe on the Releases page is this same file, bundled with PyInstaller.)
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

if "--settings" in sys.argv:
    runpy.run_path(os.path.join(HERE, "pixbot_app.pyw"), run_name="__main__")
else:
    runpy.run_path(os.path.join(HERE, "pixbot_pet.pyw"), run_name="__main__")
