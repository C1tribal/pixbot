#!/usr/bin/env bash
# Builds dist/Pixbot-x86_64.AppImage from this source (run on Linux, e.g. Ubuntu 22.04):
#   sudo apt install python3-tk fonts-dejavu-core      # Tk for the windows, fonts for his words
#   python3 -m pip install -r requirements.txt pyinstaller
#   bash linux/build_appimage.sh
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="${PIXBOT_VERSION:-1.2.0}"
PY="${PYTHON:-python3}"

# fonts used to draw his words and speech bubbles (DejaVu: free licence, see fonts/LICENSE)
rm -rf build/fonts && mkdir -p build/fonts
for f in DejaVuSans-Bold.ttf DejaVuSansMono-Bold.ttf; do
  src="$(find /usr/share/fonts -name "$f" | head -1)"
  [ -n "$src" ] || { echo "missing font $f (install fonts-dejavu-core)"; exit 1; }
  cp "$src" build/fonts/
done
lic="$(find /usr/share/doc/fonts-dejavu-core -name 'copyright' | head -1 || true)"
[ -n "$lic" ] && cp "$lic" build/fonts/LICENSE

# 1) PyInstaller: Pixbot + Python + Tk in one folder
hidden=(pixbot_acts pixbot_catalog pixbot_common pixbot_movies pixbot_outfits pixbot_paint
        pixbot_paths pixbot_vision pixbot_os pixbot_linux
        numpy PIL PIL.Image PIL.ImageGrab PIL.ImageDraw PIL.ImageFont PIL.ImageTk
        tkinter tkinter.ttk tkinter.colorchooser webbrowser subprocess threading collections
        traceback shutil json math random runpy fcntl glob signal)
args=(--noconfirm --clean --onedir --windowed --name Pixbot
      --add-data "pixbot_pet.pyw:." --add-data "pixbot_app.pyw:."
      --add-data "pixbot.png:." --add-data "pixbot_links.json:."
      --add-data "build/fonts:fonts"
      --collect-submodules Xlib --paths .)
for h in "${hidden[@]}"; do args+=(--hidden-import "$h"); done
"$PY" -m PyInstaller "${args[@]}" pixbot.pyw

# 2) AppDir: the folder layout an AppImage expects
APPDIR=build/Pixbot.AppDir
rm -rf "$APPDIR" && mkdir -p "$APPDIR/usr/lib" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
cp -r dist/Pixbot "$APPDIR/usr/lib/pixbot"
cp linux/AppRun "$APPDIR/AppRun" && chmod +x "$APPDIR/AppRun"
cp linux/pixbot.desktop "$APPDIR/pixbot.desktop"
cp pixbot.png "$APPDIR/pixbot.png"
cp pixbot.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/pixbot.png"
ln -sf pixbot.png "$APPDIR/.DirIcon"

# 3) pack it (appimagetool from github.com/AppImage/appimagetool)
TOOL=build/appimagetool
if [ ! -x "$TOOL" ]; then
  curl -fsSL -o "$TOOL" \
    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
  chmod +x "$TOOL"
fi
rm -f dist/Pixbot-x86_64.AppImage
ARCH=x86_64 VERSION="$VERSION" APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" --no-appstream "$APPDIR" dist/Pixbot-x86_64.AppImage
echo "Built: dist/Pixbot-x86_64.AppImage"
