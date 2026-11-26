"""Linux side of Pixbot's platform layer (see pixbot_os.py). Needs an X11 session or
XWayland (Tk always runs through X11) and the python-xlib package.

Like the Windows side, everything here only *reads* information: where the screens
and windows are, where the mouse is, whether a key is held down right now, the
battery level. Nothing is changed and nothing is recorded.

See-through windows: Tk can't make one colour transparent on Linux, so here each
frame is painted into a small in-memory picture and the window is cut to the exact
outline of what was drawn (the X11 "Shape" extension). Clicks go through the empty
parts, just like on Windows.
"""
import fcntl
import glob
import os
import shutil
import subprocess
import threading
import time

from Xlib import X, XK, display
from Xlib.protocol import event as xevent

NAME = "linux"

_lock = threading.RLock()
_d = display.Display()
_root = _d.screen().root
_atoms = {}


def _locked(fn):
    def wrap(*a, **kw):
        with _lock:
            return fn(*a, **kw)
    wrap.__name__ = fn.__name__
    wrap.__doc__ = fn.__doc__
    return wrap


def _atom(name):
    a = _atoms.get(name)
    if a is None:
        a = _atoms[name] = _d.intern_atom(name)
    return a


def _win(xid):
    return _d.create_resource_object("window", xid)


def _prop(w, name):
    try:
        p = w.get_full_property(_atom(name), X.AnyPropertyType)
    except Exception:
        return None
    return None if p is None else p.value


def _has(ext):
    try:
        return _d.has_extension(ext)
    except Exception:
        return False


# ---------------- see-through windows ----------------
def make_overlay(win, key):
    win.overrideredirect(True)
    try:
        win.attributes("-topmost", True)
    except Exception:
        pass
    win.config(bg=key)


def overlay_canvas(win, width, height, key):
    return ShapedCanvas(win, width, height, key)


def raise_top(win):
    try:
        win.lift()
    except Exception:
        pass


_FONT_FILES = {}
_FONT_DIRS = []


def _font_file(family):
    """A bold TrueType font that looks like `family` (bundled DejaVu first, then the system's)."""
    mono = family.lower() in ("consolas", "courier", "courier new", "monospace")
    key = "mono" if mono else "sans"
    if key in _FONT_FILES:
        return _FONT_FILES[key]
    names = ["DejaVuSansMono-Bold.ttf"] if mono else ["DejaVuSans-Bold.ttf"]
    path = None
    for d in _FONT_DIRS:
        for n in names:
            if os.path.exists(os.path.join(d, n)):
                path = os.path.join(d, n)
                break
        if path:
            break
    if not path and shutil.which("fc-match"):
        try:
            path = subprocess.run(["fc-match", "-f", "%{file}",
                                   ("monospace" if mono else "sans-serif") + ":bold"],
                                  capture_output=True, text=True, timeout=3).stdout.strip() or None
        except Exception:
            path = None
    _FONT_FILES[key] = path
    return path


class ShapedCanvas:
    """Drop-in for the few tk.Canvas calls Pixbot's drawing uses (create_rectangle / oval /
    arc / polygon / line / text, delete("all"), bind, pack). Shapes are collected during a
    frame, painted with Pillow once the frame is done, shown as one picture, and the window
    is cut to the painted pixels."""

    def __init__(self, win, width, height, key):
        import tkinter as tk
        self.win, self.w, self.h = win, int(width), int(height)
        self.real = tk.Canvas(win, width=self.w, height=self.h, bg=key, highlightthickness=0, bd=0)
        try:
            from PIL import ImageTk
            self.photo = ImageTk.PhotoImage("RGBA", (self.w, self.h))
        except Exception as e:
            import sys
            print(f"pixbot: no ImageTk ({e!r}), using PNG frames", file=sys.stderr)
            self._png = True
            self.photo = tk.PhotoImage(width=self.w, height=self.h)
        self.real.create_image(0, 0, anchor="nw", image=self.photo)
        self.ops = []
        self._job = None
        self._rects = None
        self._colors = {}
        self._fonts = {}
        try:
            self._scale = float(self.real.tk.call("tk", "scaling"))
        except Exception:
            self._scale = 96 / 72
        self.real.bind("<Map>", lambda e: self._reshape(force=True), add="+")

    # ---- tk.Canvas look-alike ----
    def __getattr__(self, name):
        return getattr(self.real, name)

    def pack(self, *a, **kw):
        return self.real.pack(*a, **kw)

    def bind(self, *a, **kw):
        return self.real.bind(*a, **kw)

    def delete(self, *tags):
        self.ops.clear()
        self._dirty()

    def _add(self, kind, args, kw):
        flat = []
        for a in args:
            if isinstance(a, (list, tuple)):
                for b in a:
                    if isinstance(b, (list, tuple)):
                        flat.extend(b)
                    else:
                        flat.append(b)
            else:
                flat.append(a)
        self.ops.append((kind, [float(v) for v in flat], kw))
        self._dirty()
        return len(self.ops)

    def create_rectangle(self, *a, **kw):
        return self._add("rect", a, kw)

    def create_oval(self, *a, **kw):
        return self._add("oval", a, kw)

    def create_arc(self, *a, **kw):
        return self._add("arc", a, kw)

    def create_polygon(self, *a, **kw):
        return self._add("poly", a, kw)

    def create_line(self, *a, **kw):
        return self._add("line", a, kw)

    def create_text(self, *a, **kw):
        return self._add("text", a, kw)

    # ---- painting ----
    def _dirty(self):
        if self._job is None:
            self._job = self.real.after_idle(self.flush)

    def _rgb(self, c):
        if not c:
            return None
        v = self._colors.get(c)
        if v is None:
            try:
                r, g, b = self.real.winfo_rgb(c)
                v = (r >> 8, g >> 8, b >> 8, 255)
            except Exception:
                v = (0, 0, 0, 255)
            self._colors[c] = v
        return v

    def _font(self, spec):
        from PIL import ImageFont
        if isinstance(spec, str):
            spec = (spec, 10)
        family, size = spec[0], int(spec[1]) if len(spec) > 1 else 10
        px = max(5, round(abs(size) * (self._scale if size > 0 else 1)))
        k = (family, px)
        f = self._fonts.get(k)
        if f is None:
            path = _font_file(family)
            try:
                f = ImageFont.truetype(path, px) if path else ImageFont.load_default(px)
            except Exception:
                f = ImageFont.load_default()
            self._fonts[k] = f
        return f

    @staticmethod
    def _smooth(pts):
        """Tk's smooth=True line: a quadratic B-spline through the midpoints."""
        p = list(zip(pts[0::2], pts[1::2]))
        if len(p) < 3:
            return pts
        out = [p[0]]
        for i in range(1, len(p) - 1):
            a = p[0] if i == 1 else ((p[i - 1][0] + p[i][0]) / 2, (p[i - 1][1] + p[i][1]) / 2)
            c = p[-1] if i == len(p) - 2 else ((p[i][0] + p[i + 1][0]) / 2, (p[i][1] + p[i + 1][1]) / 2)
            b = p[i]
            for k in range(1, 9):
                t = k / 8
                out.append(((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * b[0] + t * t * c[0],
                            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * b[1] + t * t * c[1]))
        return [v for q in out for v in q]

    def _text(self, dr, c, kw):
        text = str(kw.get("text", ""))
        fill = self._rgb(kw.get("fill", "black"))
        if not text or not fill:
            return
        spec = kw.get("font", ("sans", 10))
        if isinstance(spec, (list, tuple)) and not any(ch.isalnum() for ch in text):
            spec = ("sans",) + tuple(spec[1:])          # symbols (music notes, hearts...): DejaVu Sans
        font = self._font(spec)
        wrap = float(kw.get("width", 0) or 0)
        lines = []
        for para in text.split("\n"):
            if wrap <= 0:
                lines.append(para)
                continue
            cur = ""
            for word in para.split(" "):
                trial = word if not cur else cur + " " + word
                if cur and dr.textlength(trial, font=font) > wrap:
                    lines.append(cur)
                    cur = word
                else:
                    cur = trial
            lines.append(cur)
        asc, desc = font.getmetrics()
        lh = asc + desc
        widths = [dr.textlength(s, font=font) for s in lines]
        bw, bh = max(widths or [0]), lh * len(lines)
        anchor = kw.get("anchor", "center")
        x, y = c[0], c[1]
        x0 = x - bw / 2 if anchor in ("center", "n", "s") else (x - bw if "e" in anchor else x)
        y0 = y - bh / 2 if anchor in ("center", "e", "w") else (y - bh if "s" in anchor else y)
        just = kw.get("justify", "left")
        for i, (s, lw) in enumerate(zip(lines, widths)):
            lx = x0 + (bw - lw) / 2 if just == "center" else (x0 + bw - lw if just == "right" else x0)
            dr.text((lx, y0 + i * lh), s, font=font, fill=fill)

    def flush(self):
        self._job = None
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        for kind, c, kw in self.ops:
            try:
                if kind == "text":
                    self._text(dr, c, kw)
                    continue
                width = float(kw.get("width", 1) or 0)
                if kind == "line":
                    pts = self._smooth(c) if kw.get("smooth") else c
                    col = self._rgb(kw.get("fill", "black"))
                    if col and len(pts) >= 4:
                        dr.line(pts, fill=col, width=max(1, round(width)), joint="curve")
                    continue
                if kind == "poly":
                    fill = self._rgb(kw.get("fill", "black"))
                    outline = self._rgb(kw.get("outline", ""))
                    if len(c) >= 6:
                        dr.polygon(c, fill=fill, outline=outline)
                    continue
                fill = self._rgb(kw.get("fill", ""))
                outline = self._rgb(kw.get("outline", "black"))
                x0, y0, x1, y1 = (round(v) for v in c[:4])
                x0, x1 = min(x0, x1), max(x0, x1)
                y0, y1 = min(y0, y1), max(y0, y1)
                lw = max(1, round(width)) if outline else 0
                h = lw // 2
                box = [x0 - h, y0 - h, x1 - 1 + h, y1 - 1 + h] if outline else [x0, y0, x1 - 1, y1 - 1]
                if box[2] < box[0] or box[3] < box[1]:
                    continue
                if kind == "rect":
                    dr.rectangle(box, fill=fill, outline=outline, width=lw)
                elif kind == "oval":
                    dr.ellipse(box, fill=fill, outline=outline, width=lw)
                elif kind == "arc":
                    start, ext = float(kw.get("start", 0)), float(kw.get("extent", 90))
                    a0, a1 = -(start + ext), -start
                    if ext < 0:
                        a0, a1 = a1, a0
                    dr.pieslice(box, a0, a1, fill=fill, outline=outline, width=lw)
            except Exception:
                pass
        self._show(img)
        self._mask = img.getchannel("A")
        self._reshape()

    def _show(self, img):
        """Put the painted frame on screen. Pillow's fast path first; if that isn't
        available, hand Tk the frame as a PNG (Tk 8.6 reads PNG itself)."""
        if not getattr(self, "_png", False):
            try:
                self.photo.paste(img)
                return
            except Exception as e:
                import sys
                print(f"pixbot: ImageTk paste failed ({e!r}), using PNG frames", file=sys.stderr)
                self._png = True
                import tkinter as tk
                self.photo = tk.PhotoImage(width=self.w, height=self.h)
                self.real.delete("all")
                self.real.create_image(0, 0, anchor="nw", image=self.photo)
        import base64
        import io
        buf = io.BytesIO()
        img.save(buf, "PNG", compress_level=0)
        self.photo.configure(data=base64.b64encode(buf.getvalue()), format="png")

    def _reshape(self, force=False):
        mask = getattr(self, "_mask", None)
        if mask is None:
            return
        import numpy as np
        a = np.asarray(mask) > 0
        rects, open_ = [], {}
        for y in range(a.shape[0]):
            row = a[y]
            nxt = {}
            if row.any():
                d = np.diff(np.concatenate(([0], row.astype(np.int8), [0])))
                for s, e in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
                    k = (int(s), int(e))
                    if k in open_:                      # same run as the row above: grow it
                        i = open_[k]
                        x, ry, w, h = rects[i]
                        rects[i] = (x, ry, w, h + 1)
                        nxt[k] = i
                    else:
                        nxt[k] = len(rects)
                        rects.append((k[0], y, k[1] - k[0], 1))
            open_ = nxt
        if not force and rects == self._rects:
            return
        try:
            if not self.win.winfo_ismapped():
                self._rects = None
                return
            xid = int(self.win.wm_frame(), 16)
        except Exception:
            return
        with _lock:
            try:
                _win(xid).shape_rectangles(0, 0, 0, 0, 0, rects)     # Set, Bounding, Unsorted
                _d.flush()
                self._rects = rects
            except Exception:
                self._rects = None


# ---------------- screens ----------------
_mon_cache = (0.0, None)


@_locked
def _screen_rects():
    out = []
    try:
        mons = _root.xrandr_get_monitors(is_active=True).monitors
        out = [(m.x, m.y, m.x + m.width_in_pixels, m.y + m.height_in_pixels) for m in mons]
    except Exception:
        try:
            res = _root.xrandr_get_screen_resources()
            for c in res.crtcs:
                ci = _d.xrandr_get_crtc_info(c, res.config_timestamp)
                if ci.mode and ci.width and ci.height:
                    out.append((ci.x, ci.y, ci.x + ci.width, ci.y + ci.height))
        except Exception:
            pass
    if not out:
        s = _d.screen()
        out = [(0, 0, s.width_in_pixels, s.height_in_pixels)]
    return sorted(set(out))


@_locked
def _struts():
    """Space panels / docks reserve at the screen edges: [(x0, y0, x1, y1)]."""
    out = []
    s = _d.screen()
    sw, sh = s.width_in_pixels, s.height_in_pixels
    for xid in _prop(_root, "_NET_CLIENT_LIST") or []:
        w = _win(xid)
        v = _prop(w, "_NET_WM_STRUT_PARTIAL")
        if v is not None and len(v) >= 12:
            l, r, t, b = v[0:4]
            if l:
                out.append((0, v[4], l, v[5] + 1))
            if r:
                out.append((sw - r, v[6], sw, v[7] + 1))
            if t:
                out.append((v[8], 0, v[9] + 1, t))
            if b:
                out.append((v[10], sh - b, v[11] + 1, sh))
            continue
        v = _prop(w, "_NET_WM_STRUT")
        if v is not None and len(v) >= 4:
            l, r, t, b = v[0:4]
            if l:
                out.append((0, 0, l, sh))
            if r:
                out.append((sw - r, 0, sw, sh))
            if t:
                out.append((0, 0, sw, t))
            if b:
                out.append((0, sh - b, sw, sh))
    return out


def get_monitors():
    """[(monitor rect, work area rect)], left to right. Work area = without panels / docks."""
    global _mon_cache
    now = time.monotonic()
    if _mon_cache[1] is not None and now - _mon_cache[0] < 2.0:
        return list(_mon_cache[1])
    out = []
    struts = _struts()
    wa = _prop(_root, "_NET_WORKAREA")
    for m in _screen_rects():
        l, t, r, b = m
        for sx0, sy0, sx1, sy1 in struts:
            if sx1 <= m[0] or sx0 >= m[2] or sy1 <= m[1] or sy0 >= m[3]:
                continue
            if sx1 - sx0 >= sy1 - sy0:               # horizontal panel
                if sy0 <= m[1] + 1:
                    t = max(t, sy1)
                else:
                    b = min(b, sy0)
            else:                                    # vertical panel
                if sx0 <= m[0] + 1:
                    l = max(l, sx1)
                else:
                    r = min(r, sx0)
        if wa is not None and len(wa) >= 4:          # e.g. GNOME's top bar isn't a dock window
            wx0, wy0, wx1, wy1 = wa[0], wa[1], wa[0] + wa[2], wa[1] + wa[3]
            nl, nt, nr, nb = max(l, wx0), max(t, wy0), min(r, wx1), min(b, wy1)
            if nr - nl > 200 and nb - nt > 200:
                l, t, r, b = nl, nt, nr, nb
        if r - l < 200 or b - t < 200:
            l, t, r, b = m
        out.append((m, (l, t, r, b)))
    out.sort(key=lambda x: (x[0][0], x[0][1]))
    _mon_cache = (now, out)
    return list(out)


# ---------------- windows ----------------
_SKIP_TYPES = {"_NET_WM_WINDOW_TYPE_DESKTOP", "_NET_WM_WINDOW_TYPE_DOCK",
               "_NET_WM_WINDOW_TYPE_TOOLBAR", "_NET_WM_WINDOW_TYPE_MENU",
               "_NET_WM_WINDOW_TYPE_UTILITY", "_NET_WM_WINDOW_TYPE_SPLASH",
               "_NET_WM_WINDOW_TYPE_NOTIFICATION", "_NET_WM_WINDOW_TYPE_DROPDOWN_MENU",
               "_NET_WM_WINDOW_TYPE_POPUP_MENU", "_NET_WM_WINDOW_TYPE_TOOLTIP"}
_info = {}      # xid -> (pid, class, skip?) - these never change for a window


def _static(xid):
    v = _info.get(xid)
    if v is None:
        w = _win(xid)
        pid = (_prop(w, "_NET_WM_PID") or [0])[0]
        try:
            cls = (w.get_wm_class() or ("", ""))[1] or ""
        except Exception:
            cls = ""
        types = _prop(w, "_NET_WM_WINDOW_TYPE") or []
        names = set()
        for a in types:
            try:
                names.add(_d.get_atom_name(a))
            except Exception:
                pass
        v = _info[xid] = (pid, cls, bool(names & _SKIP_TYPES))
        if len(_info) > 2000:
            _info.clear()
    return v


def _state(w):
    out = set()
    for a in _prop(w, "_NET_WM_STATE") or []:
        try:
            out.add(_d.get_atom_name(a))
        except Exception:
            pass
    return out


@_locked
def window_rect(xid):
    try:
        w = _win(xid)
        g = w.get_geometry()
        t = _root.translate_coords(w, 0, 0)
    except Exception:
        return None
    x, y = t.x, t.y
    return (x, y, x + g.width, y + g.height)


@_locked
def frame_rect(xid):
    """The visible window: with the title bar the window manager adds, without shadows."""
    r = window_rect(xid)
    if r is None:
        return None
    w = _win(xid)
    l, t, rr, b = r
    fe = _prop(w, "_NET_FRAME_EXTENTS")
    if fe is not None and len(fe) >= 4:
        l, rr, t, b = l - fe[0], rr + fe[1], t - fe[2], b + fe[3]
    ge = _prop(w, "_GTK_FRAME_EXTENTS")
    if ge is not None and len(ge) >= 4:
        l, rr, t, b = l + ge[0], rr - ge[1], t + ge[2], b - ge[3]
    return (l, t, rr, b)


@_locked
def is_window(xid):
    try:
        _win(xid).get_geometry()
        return True
    except Exception:
        return False


def _desktop_ok(w, cur):
    d = _prop(w, "_NET_WM_DESKTOP")
    return cur is None or d is None or d[0] in (cur, 0xFFFFFFFF)


@_locked
def alive(xid):
    try:
        w = _win(xid)
        if w.get_attributes().map_state != X.IsViewable:
            return False
    except Exception:
        return False
    return "_NET_WM_STATE_HIDDEN" not in _state(w)


@_locked
def window_pid(xid):
    try:
        return _static(xid)[0]
    except Exception:
        return 0


@_locked
def window_class(xid):
    try:
        return _static(xid)[1]
    except Exception:
        return ""


@_locked
def window_title(xid):
    w = _win(xid)
    v = _prop(w, "_NET_WM_NAME")
    if v is None:
        v = _prop(w, "WM_NAME")
    if isinstance(v, bytes):
        v = v.decode("utf-8", "replace")
    return v or ""


_snap = (0.0, [])


@_locked
def _visible():
    """Visible app windows on this desktop, topmost first: [(xid, frame rect, skip?)]."""
    global _snap
    now = time.monotonic()
    if now - _snap[0] < 0.2:
        return _snap[1]
    cur = (_prop(_root, "_NET_CURRENT_DESKTOP") or [None])[0]
    ids = _prop(_root, "_NET_CLIENT_LIST_STACKING")
    if ids is None:
        ids = _prop(_root, "_NET_CLIENT_LIST") or []
    out = []
    for xid in reversed(list(ids)):
        try:
            w = _win(xid)
            if not alive(xid) or not _desktop_ok(w, cur):
                continue
            r = frame_rect(xid)
            if r:
                out.append((xid, r, _static(xid)[2]))
        except Exception:
            pass
    _snap = (now, out)
    return out


@_locked
def list_windows(my_pid):
    """Normal app windows on screen, topmost first: [(handle, frame rect)]."""
    out = []
    for xid, r, skip in _visible():
        try:
            if skip or _static(xid)[0] == my_pid or not window_title(xid):
                continue
            if r[2] - r[0] >= 150 and r[3] - r[1] >= 80:
                out.append((xid, r))
        except Exception:
            pass
    return out


@_locked
def root_at(x, y):
    """The top-level window under a screen point."""
    for xid, r, skip in _visible():
        if r[0] <= x < r[2] and r[1] <= y < r[3]:
            return xid
    return None


@_locked
def foreground_window():
    v = _prop(_root, "_NET_ACTIVE_WINDOW")
    return v[0] if v is not None and len(v) and v[0] else None


@_locked
def fullscreen_candidate(xid, my_pid):
    """Rect of a window that is fullscreen (a game, a video...), not the desktop / us."""
    try:
        pid, cls, skip = _static(xid)
    except Exception:
        return None
    if skip or pid == my_pid or "_NET_WM_STATE_FULLSCREEN" not in _state(_win(xid)):
        return None
    return window_rect(xid)


def exe_of(xid):
    """Program name of a window, lower case (e.g. 'firefox')."""
    pid = window_pid(xid)
    if not pid:
        return (window_class(xid) or "").lower()
    try:
        exe = os.path.basename(os.readlink(f"/proc/{pid}/exe")).lower()
    except OSError:
        try:
            exe = open(f"/proc/{pid}/comm").read().strip().lower()
        except OSError:
            exe = (window_class(xid) or "").lower()
    return exe


# ---------------- mouse / keyboard (state only, nothing is recorded) ----------------
@_locked
def _pointer():
    return _root.query_pointer()


def cursor_pos():
    try:
        p = _pointer()
        return p.root_x, p.root_y
    except Exception:
        return 0, 0


_idle = {"n": 0, "at": None, "fallback": None}


@_locked
def last_input_tick():
    """A number that changes whenever you use the mouse or keyboard."""
    try:
        idle = _root.screensaver_query_info().idle
    except Exception:
        idle = None
    if idle is None:                    # no screensaver extension: watch the mouse + keys instead
        try:
            sig = (cursor_pos(), tuple(_d.query_keymap()), _pointer().mask)
        except Exception:
            return _idle["n"]
        if sig != _idle["fallback"]:
            _idle["fallback"] = sig
            _idle["n"] += 1
        return _idle["n"]
    at = time.monotonic() * 1000 - idle        # when the last input happened
    if _idle["at"] is None or at > _idle["at"] + 5:
        _idle["n"] += 1
    if _idle["at"] is None or at > _idle["at"]:
        _idle["at"] = at
    return _idle["n"]


def mouse_down():
    try:
        return bool(_pointer().mask & (X.Button1Mask | X.Button3Mask))
    except Exception:
        return False


def capslock_on():
    try:
        return bool(_pointer().mask & X.LockMask)
    except Exception:
        return False


_codes = {}


@_locked
def _keycodes():
    if not _codes:
        names = [chr(c) for c in range(ord("a"), ord("z") + 1)] + [str(i) for i in range(10)]
        names += ["space", "period", "comma"]
        typing = []
        for n in names:
            kc = _d.keysym_to_keycode(XK.string_to_keysym(n))
            if kc:
                typing.append(kc)
        _codes["typing"] = typing
        _codes["bs"] = _d.keysym_to_keycode(XK.string_to_keysym("BackSpace"))
        _codes["bs_was"] = False
    return _codes


@_locked
def _keymap():
    try:
        return _d.query_keymap()
    except Exception:
        return [0] * 32


def _down(km, kc):
    return bool(kc) and bool(km[kc >> 3] & (1 << (kc & 7)))


def backspace_tapped():
    """Was Backspace pressed since the last call?"""
    c = _keycodes()
    now = _down(_keymap(), c["bs"])
    tapped = now and not c["bs_was"]
    c["bs_was"] = now
    return tapped


def typing_keys_down():
    """Which letter / digit / space keys are held right now - only used to tell typing
    (many different keys) from gaming (a few keys like WASD). Never stored as text."""
    km = _keymap()
    return [kc for kc in _keycodes()["typing"] if _down(km, kc)]


# ---------------- other things he notices ----------------
_clip = {"n": 0, "setup": False, "owner": None}


@_locked
def clipboard_seq():
    """Changes every time something is copied (the clipboard itself is never read)."""
    sel = _atom("CLIPBOARD")
    if not _clip["setup"]:
        _clip["setup"] = True
        try:
            _d.xfixes_query_version()
            _root.xfixes_select_selection_input(sel, 1)       # SetSelectionOwnerNotifyMask
            _d.flush()
            _clip["xfixes"] = True
        except Exception:
            _clip["xfixes"] = False
    if _clip.get("xfixes"):
        try:
            while _d.pending_events():
                _d.next_event()
                _clip["n"] += 1
        except Exception:
            pass
    else:
        try:
            owner = _d.get_selection_owner(sel)
            owner = getattr(owner, "id", owner)
            if owner != _clip["owner"]:
                _clip["owner"] = owner
                _clip["n"] += 1
        except Exception:
            pass
    return _clip["n"]


def _read(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return ""


def power():
    """(on charger, battery %) or None without a battery."""
    bats = [b for b in glob.glob("/sys/class/power_supply/*") if _read(b + "/type") == "Battery"]
    if not bats:
        return None
    try:
        pct = int(_read(bats[0] + "/capacity") or 100)
    except ValueError:
        pct = 100
    status = _read(bats[0] + "/status")
    ac = status in ("Charging", "Full") or any(
        _read(m + "/online") == "1" for m in glob.glob("/sys/class/power_supply/*")
        if _read(m + "/type") in ("Mains", "USB"))
    return ac, pct


_audio = {"t": 0.0, "on": False}


def audio_level():
    """1.0 while some app is playing sound (a playback stream that isn't paused), else 0.
    Asks PulseAudio / PipeWire (`pactl`) once a second; no sound is ever recorded."""
    now = time.monotonic()
    if now - _audio["t"] >= 1.0:
        _audio["t"] = now
        on = False
        if shutil.which("pactl"):
            try:
                out = subprocess.run(["pactl", "list", "sink-inputs"], capture_output=True,
                                     text=True, timeout=2,
                                     env=dict(os.environ, LC_ALL="C")).stdout
                on = any(line.strip() == "Corked: no" for line in out.splitlines())
            except Exception:
                on = False
        _audio["on"] = on
    return 1.0 if _audio["on"] else 0.0


# ---------------- one copy at a time ----------------
_locks = []


def single_instance(name):
    """True if no other copy holds `name` (and claims it for this process)."""
    base = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    path = os.path.join(base, f"{name}-{os.getuid()}.lock")
    try:
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    _locks.append(fd)
    return True


@_locked
def focus_existing(title):
    for xid in _prop(_root, "_NET_CLIENT_LIST") or []:
        try:
            if window_title(xid) != title:
                continue
            ev = xevent.ClientMessage(window=_win(xid), client_type=_atom("_NET_ACTIVE_WINDOW"),
                                      data=(32, [2, X.CurrentTime, 0, 0, 0]))
            _root.send_event(ev, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            _d.flush()
            return
        except Exception:
            pass


def pid_running(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:
        cmd = open(f"/proc/{pid}/cmdline", "rb").read().lower()
    except OSError:
        return True
    return b"pixbot" in cmd
