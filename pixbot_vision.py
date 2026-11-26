"""Screen vision for Pixbot.

Takes a screenshot of one monitor (kept in memory only - never written to
disk) and finds:
  ledges   : horizontal edges he can stand on (thumbnail tops, cards, rows...)
  pictures : big detailed rectangles (video thumbnails, images)
  icons    : small detailed blobs (logos, app icons) with their main colour
Works for any app because it only looks at pixels.
"""
import os
import sys

import numpy as np
from PIL import ImageGrab

STEP = 2               # analyse at half resolution
EDGE = 20              # brightness jump that counts as an edge
MIN_RUN = 50           # shortest ledge in real pixels
BLOCK = 12             # block size (analysis px) for picture detection
IBLOCK = 6             # block size for icon detection


def _runs(row, min_len):
    if not row.any():
        return []
    d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    keep = (ends - starts) >= min_len
    return list(zip(starts[keep], ends[keep]))


def _blobs(busy):
    """Connected groups of True cells -> list of (y0, x0, y1, x1, count)."""
    bh, bw = busy.shape
    seen = np.zeros_like(busy)
    out = []
    for by in range(bh):
        for bx in range(bw):
            if not busy[by, bx] or seen[by, bx]:
                continue
            stack, n = [(by, bx)], 0
            seen[by, bx] = True
            y0 = y1 = by
            x0 = x1 = bx
            while stack:
                cy, cx = stack.pop()
                n += 1
                y0, y1, x0, x1 = min(y0, cy), max(y1, cy), min(x0, cx), max(x1, cx)
                for ny, nx in ((cy + 1, cx), (cy - 1, cx), (cy, cx + 1), (cy, cx - 1)):
                    if 0 <= ny < bh and 0 <= nx < bw and busy[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
            out.append((y0, x0, y1 + 1, x1 + 1, n))
    return out


def scan(mon, masks=(), top_clear=70, bottom=None):
    l, t, r, b = mon
    bottom = bottom or b
    if sys.platform == "win32":
        img = ImageGrab.grab(bbox=(l, t, r, bottom), all_screens=True)
    else:   # X11: ask the X server directly (never falls back to a screenshot tool / temp file)
        img = ImageGrab.grab(bbox=(l, t, r, bottom), xdisplay=os.environ.get("DISPLAY", ":0"))
    img = img.convert("RGB")
    rgb = np.asarray(img)[::STEP, ::STEP]
    a = rgb.astype(np.int16).mean(axis=2).astype(np.int16)
    h, w = a.shape
    for mx0, my0, mx1, my1 in masks:
        x0, x1 = max(0, (mx0 - l) // STEP), min(w, (mx1 - l) // STEP + 1)
        y0, y1 = max(0, (my0 - t) // STEP), min(h, (my1 - t) // STEP + 1)
        if x0 < x1 and y0 < y1:
            a[y0:y1, x0:x1] = a[max(0, y0 - 1), x0:x1] if y0 > 0 else 0

    # ---- ledges ----
    g = np.abs(np.diff(a, axis=0)) > EDGE
    ledges, last = [], {}
    for y in range(int(top_clear / STEP), h - 2):
        for s, e in _runs(g[y], MIN_RUN // STEP):
            sy = t + (y + 1) * STEP
            key = (s // 8, e // 8)
            if key in last and sy - last[key] <= 6:
                continue
            last[key] = sy
            ledges.append((sy, l + s * STEP, l + e * STEP))

    # ---- pictures (big busy rectangles) ----
    pictures = []
    bh, bw = h // BLOCK, w // BLOCK
    std = a[:bh * BLOCK, :bw * BLOCK].reshape(bh, BLOCK, bw, BLOCK).std(axis=(1, 3))
    for y0, x0, y1, x1, n in _blobs(std > 30):
        fill = n / ((y1 - y0) * (x1 - x0))
        pw, ph = (x1 - x0) * BLOCK * STEP, (y1 - y0) * BLOCK * STEP
        if fill > 0.65 and 70 <= pw <= 900 and 60 <= ph <= 700:
            pictures.append((l + x0 * BLOCK * STEP, t + y0 * BLOCK * STEP,
                             l + x1 * BLOCK * STEP, t + y1 * BLOCK * STEP))

    # ---- icons / logos (small colourful blobs) ----
    icons = []
    ih, iw = h // IBLOCK, w // IBLOCK
    cells = rgb[:ih * IBLOCK, :iw * IBLOCK].astype(np.int16)
    mx = cells.max(axis=2)
    mn = cells.min(axis=2)
    sat = ((mx - mn) > 60).reshape(ih, IBLOCK, iw, IBLOCK).mean(axis=(1, 3)) > 0.25
    for y0, x0, y1, x1, n in _blobs(sat):
        pw, ph = (x1 - x0) * IBLOCK * STEP, (y1 - y0) * IBLOCK * STEP
        if 20 <= pw <= 160 and 16 <= ph <= 120 and n / ((y1 - y0) * (x1 - x0)) > 0.4:
            crop = rgb[y0 * IBLOCK:y1 * IBLOCK, x0 * IBLOCK:x1 * IBLOCK].reshape(-1, 3).astype(np.int16)
            colourful = crop[(crop.max(axis=1) - crop.min(axis=1)) > 60]
            col = colourful.mean(axis=0) if len(colourful) else crop.mean(axis=0)
            icons.append(((l + x0 * IBLOCK * STEP, t + y0 * IBLOCK * STEP,
                           l + x1 * IBLOCK * STEP, t + y1 * IBLOCK * STEP),
                          "#%02x%02x%02x" % tuple(int(v) for v in col)))
    ledges.sort(key=lambda e: -(e[2] - e[1]))
    return ledges[:120], pictures[:30], icons[:30]
