"""Windows side of Pixbot's platform layer (see pixbot_os.py).

Everything here only *reads* information from Windows: where the screens and
windows are, where the mouse is, whether a key is held down right now, the
battery level. Nothing is changed and nothing is recorded.
"""
import ctypes
import ctypes.wintypes as wt
import os

NAME = "windows"

# ---------------- process setup ----------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass
try:
    ctypes.windll.winmm.timeBeginPeriod(1)        # smoother 60 fps timers
except Exception:
    pass

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
dwmapi = ctypes.windll.dwmapi
user32.GetForegroundWindow.restype = wt.HWND
user32.WindowFromPoint.restype = wt.HWND
user32.WindowFromPoint.argtypes = [wt.POINT]
user32.GetAncestor.restype = wt.HWND
user32.GetAncestor.argtypes = [wt.HWND, wt.UINT]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.UINT), ("dwTime", wt.DWORD)]


def _t(r):
    return (r.left, r.top, r.right, r.bottom)


# ---------------- see-through windows ----------------
def make_overlay(win, key):
    """Borderless, always on top, and every pixel of colour `key` is see-through."""
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.attributes("-transparentcolor", key)
    win.config(bg=key)


def overlay_canvas(win, width, height, key):
    import tkinter as tk
    return tk.Canvas(win, width=width, height=height, bg=key, highlightthickness=0, bd=0)


def raise_top(win):
    win.attributes("-topmost", False)
    win.attributes("-topmost", True)


# ---------------- screens ----------------
def get_monitors():
    """[(monitor rect, work area rect)], left to right. Work area = without the taskbar."""
    out = []
    proc = ctypes.WINFUNCTYPE(ctypes.c_int, wt.HMONITOR, wt.HDC,
                              ctypes.POINTER(wt.RECT), wt.LPARAM)

    def cb(hmon, hdc, rect, lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            out.append((_t(mi.rcMonitor), _t(mi.rcWork)))
        return 1

    user32.EnumDisplayMonitors(None, None, proc(cb), 0)
    out.sort(key=lambda m: (m[0][0], m[0][1]))
    return out


# ---------------- windows ----------------
IGNORED_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                   "Windows.UI.Core.CoreWindow", "TopLevelWindowForOverflowXamlIsland"}


def window_rect(hwnd):
    r = wt.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
        return None
    return _t(r)


def frame_rect(hwnd):
    """The visible window frame (without the invisible resize border)."""
    r = wt.RECT()
    if dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), 9, ctypes.byref(r), ctypes.sizeof(r)) == 0:
        return _t(r)
    return window_rect(hwnd)


def is_cloaked(hwnd):
    v = ctypes.c_int(0)
    dwmapi.DwmGetWindowAttribute(wt.HWND(hwnd), 14, ctypes.byref(v), ctypes.sizeof(v))
    return v.value != 0


def is_window(hwnd):
    return bool(user32.IsWindow(hwnd))


def alive(hwnd):
    return bool(user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd)
                and not user32.IsIconic(hwnd))


def window_pid(hwnd):
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def window_class(hwnd):
    cls = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, cls, 256)
    return cls.value


def window_title(hwnd):
    buf = ctypes.create_unicode_buffer(300)
    user32.GetWindowTextW(hwnd, buf, 300)
    return buf.value


def list_windows(my_pid):
    """Normal app windows on screen, topmost first: [(handle, frame rect)]."""
    out = []
    proc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(h, lp):
        try:
            if not h or not user32.IsWindowVisible(h) or user32.IsIconic(h):
                return True
            if user32.GetWindowTextLengthW(h) == 0:
                return True
            if user32.GetWindowLongW(h, -20) & 0x80:      # tool windows
                return True
            if window_pid(h) == my_pid:
                return True
            if window_class(h) in IGNORED_CLASSES or is_cloaked(h):
                return True
            r = frame_rect(h)
            if r and r[2] - r[0] >= 150 and r[3] - r[1] >= 80:
                out.append((h, r))
        except Exception:
            pass
        return True

    user32.EnumWindows(proc(cb), 0)
    return out


def root_at(x, y):
    """The top-level window under a screen point."""
    h = user32.WindowFromPoint(wt.POINT(int(x), int(y)))
    return user32.GetAncestor(h, 2) if h else None


def foreground_window():
    return user32.GetForegroundWindow() or None


def fullscreen_candidate(hwnd, my_pid):
    """Rect of a window that could be a fullscreen app (not the desktop / taskbar / us)."""
    if not hwnd or window_pid(hwnd) == my_pid or window_class(hwnd) in IGNORED_CLASSES:
        return None
    return window_rect(hwnd)


def exe_of(hwnd):
    """Program name of a window, lower case without '.exe' (e.g. 'chrome')."""
    hp = kernel32.OpenProcess(0x1000, False, window_pid(hwnd))
    exe = ""
    if hp:
        n = wt.DWORD(300)
        buf = ctypes.create_unicode_buffer(300)
        if kernel32.QueryFullProcessImageNameW(hp, 0, buf, ctypes.byref(n)):
            exe = os.path.basename(buf.value).lower()
        kernel32.CloseHandle(hp)
    return exe[:-4] if exe.endswith(".exe") else exe


# ---------------- mouse / keyboard (state only, nothing is recorded) ----------------
def cursor_pos():
    p = wt.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return p.x, p.y


def last_input_tick():
    """A number that changes whenever you use the mouse or keyboard."""
    li = LASTINPUTINFO()
    li.cbSize = ctypes.sizeof(LASTINPUTINFO)
    user32.GetLastInputInfo(ctypes.byref(li))
    return li.dwTime


def mouse_down():
    return bool((user32.GetAsyncKeyState(1) & 0x8000) or (user32.GetAsyncKeyState(2) & 0x8000))


def backspace_tapped():
    """Was Backspace pressed since the last call?"""
    return bool(user32.GetAsyncKeyState(8) & 1)


def capslock_on():
    return bool(user32.GetKeyState(0x14) & 1)


_TYPING_KEYS = list(range(0x41, 0x5B)) + list(range(0x30, 0x3A)) + [0x20, 0xBE, 0xBC]


def typing_keys_down():
    """Which letter / digit / space keys are held right now - only used to tell typing
    (many different keys) from gaming (a few keys like WASD). Never stored as text."""
    return [vk for vk in _TYPING_KEYS if user32.GetAsyncKeyState(vk) & 0x8000]


# ---------------- other things he notices ----------------
def clipboard_seq():
    """Changes every time something is copied (the clipboard itself is never read)."""
    return user32.GetClipboardSequenceNumber()


class _SPS(ctypes.Structure):
    _fields_ = [("ac", ctypes.c_byte), ("flag", ctypes.c_byte), ("pct", ctypes.c_byte),
                ("saver", ctypes.c_byte), ("life", wt.DWORD), ("full", wt.DWORD)]


def power():
    """(on charger, battery %) or None without a battery."""
    sps = _SPS()
    if kernel32.GetSystemPowerStatus(ctypes.byref(sps)) and not (sps.flag & 128):
        return sps.ac == 1, sps.pct & 0xFF
    return None


# ---------------- one copy at a time ----------------
_mutexes = []


def single_instance(name):
    """True if no other copy holds `name` (and claims it for this process)."""
    m = kernel32.CreateMutexW(None, False, "Local\\" + name)
    if kernel32.GetLastError() == 183:
        return False
    _mutexes.append(m)
    return True


def focus_existing(title):
    h = user32.FindWindowW(None, title)
    if h:
        user32.ShowWindow(h, 9)              # restore if minimised
        user32.SetForegroundWindow(h)


def pid_running(pid):
    h = kernel32.OpenProcess(0x1000, False, pid)
    if not h:
        return False
    code = ctypes.c_ulong()
    kernel32.GetExitCodeProcess(h, ctypes.byref(code))
    kernel32.CloseHandle(h)
    return code.value == 259
