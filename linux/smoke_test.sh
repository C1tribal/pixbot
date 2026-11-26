#!/usr/bin/env bash
# CI check for the AppImage: runs Pixbot on a virtual X screen (Xvfb + a window manager)
# and checks that he shows up, that his window is see-through around him, and that
# nothing crashed.   Usage: xvfb-run -a -s "-screen 0 1600x900x24" bash linux/smoke_test.sh
set -u
cd "$(dirname "$0")/.."
export APPIMAGE_EXTRACT_AND_RUN=1
export HOME="$(mktemp -d)"
APP="$PWD/dist/Pixbot-Linux.AppImage"
mkdir -p build/smoke
xsetroot -solid "#3CA05A"
openbox >/dev/null 2>&1 &
sleep 2

# 1) the pet on its own
"$APP" --pet > build/smoke/pet.log 2>&1 &
PET=$!
sleep 25
python3 linux/smoke_check.py build/smoke/pet.png pet
R1=$?
kill $PET 2>/dev/null; sleep 2; pkill -f "Pixbot" 2>/dev/null; sleep 1

# 2) opening Pixbot normally: the app window opens and starts the pet
"$APP" > build/smoke/app.log 2>&1 &
sleep 25
python3 linux/smoke_check.py build/smoke/app.png app
R2=$?
pkill -f "Pixbot" 2>/dev/null; sleep 1

FAIL=0
for f in build/smoke/pet.log build/smoke/app.log; do
  if grep -q "Traceback" "$f"; then
    echo "::error::Python error in $f"; cat "$f"; FAIL=1
  fi
done
[ $R1 -eq 0 ] && [ $R2 -eq 0 ] || FAIL=1
exit $FAIL
