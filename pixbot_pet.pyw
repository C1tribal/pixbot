"""Pixbot desktop pet - a little robot critter living on your Windows or Linux screens.

Run:  pythonw pixbot.pyw              (needs: pip install -r requirements.txt)

Most of the time he lurks: wanders a bit, stops, and looks up at your cursor.
Every 30-80 seconds he does something special (60+ animations, game references
and moves).

He SEES your screen (a quick screenshot once a second): edges of video
thumbnails, cards, buttons, rows in File Explorer... become ledges he runs and
jumps across. Pictures (thumbnails) are things he points at. He grabs the
scrollbar of the window, climbs window borders and the screen edge, then
parachutes back down. He jumps onto the text box you click into.

Mouse: drag him, throw him (he bounces / wall-slides / wall-jumps).
Click = jump.  Right-click = menu with every animation.
"""
import collections
import json
import math
import os
import random
import sys
import threading
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pixbot_acts import Acts, ACTS, ACT_GROUPS  # noqa: E402
import pixbot_catalog as cat                    # noqa: E402
from pixbot_common import *                     # noqa: E402,F401,F403

try:
    import pixbot_vision
except Exception:                               # numpy / pillow missing
    pixbot_vision = None

# ====================== Windows / Linux helpers (pixbot_os.py) ======================
import pixbot_os as osl                                     # noqa: E402
from pixbot_os import (get_monitors, window_rect, frame_rect, alive, list_windows,  # noqa: E402
                       root_at, cursor_pos, last_input_tick)


def covers(r, m):
    return r[0] <= m[0] and r[1] <= m[1] and r[2] >= m[2] and r[3] >= m[3]


# ====================== behaviour tables ======================
BASE = {   # everyday behaviour: name: (weight, (min s, max s))
    "lurk": (30, (5, 10)), "watch": (24, (4, 9)), "idle": (8, (2, 5)),
    "walk": (10, (3, 7)), "run": (8, (1.2, 2.5)), "hopabout": (16, (0, 0)),
    "sprintslide": (26, (2.5, 2.5)), "ride": (18, (0, 0)), "chill": (14, (0, 0)),
}
MOVES = ["flip", "jump", "point", "hang", "dig", "parachute", "portal", "hop",
         "climb", "explore", "slingshot", "tbhang", "edgehang", "chase", "mimic",
         "cursorplay", "cursorplay", "cursorplay", "cursorplay"]
CURSOR_GAMES = ["reach", "grab", "jumparound", "slideunder", "kick", "bash", "chase", "propose",
                "tag", "highfive", "throwball", "hideseek"]
GROUNDISH = ("land", "skid", "slide", "pointing", "mimic", "clockpoint", "chase", "toclock",
             "runin", "visit", "waitcursor", "typealong", "reach", "ko", "slidein", "propose",
             "flee", "hiding", "found", "throwball", "petted", "startle", "welcome", "dizzy",
             "react")
CONTEXT_ACTS = {      # extra-likely picks depending on what you're doing
    "video": ["headphones", "pizza", "camera", "point", "read", "meditate"],
    "browser": ["inspect", "inspect", "read", "telescope", "point", "think", "mimic"],
    "files": ["inspect", "build", "broom"],
    "code": ["code", "code", "think", "error", "happy"],
    "chat": ["think", "code", "read", "wave"],
}
SPECIAL_GAP = (30, 80)       # seconds between special animations
HOP_COOLDOWN = 240           # seconds between voluntary screen changes


class Portal:
    PW, PH = 10, 16

    def __init__(self, root):
        self.win = tk.Toplevel(root)
        osl.make_overlay(self.win, KEY)
        self.cv = osl.overlay_canvas(self.win, self.PW * PX, self.PH * PX, KEY)
        self.cv.pack()
        self.win.withdraw()
        self.size, self.goal, self.t = 0.0, 0.0, 0.0
        self.rect = None

    def open_at(self, x, ground):
        x0, y0 = int(x - self.PW * PX / 2), int(ground - self.PH * PX)
        self.rect = (x0, y0, x0 + self.PW * PX, y0 + self.PH * PX)
        self.win.geometry(f"+{x0}+{y0}")
        self.win.deiconify()
        self.win.lift()
        self.win.master.lift()
        self.size, self.goal = 0.0, 1.0

    def close(self):
        self.goal = 0.0

    def update(self, dt):
        if self.goal == 0.0 and self.size <= 0.0:
            return
        self.t += dt
        self.size += (1 if self.goal > self.size else -1) * dt / 0.3
        self.size = max(0.0, min(1.0, self.size))
        if self.size <= 0.0 and self.goal == 0.0:
            self.win.withdraw()
            self.rect = None
            return
        cv, s = self.cv, self.size
        cv.delete("all")
        cx, cy = self.PW * PX / 2, self.PH * PX / 2
        rx, ry = (self.PW * PX / 2 - 2) * s, (self.PH * PX / 2 - 2) * s
        cv.create_oval(cx - rx, cy - ry, cx + rx, cy + ry, fill="#1B1030", outline=ORANGE, width=3)
        for i in range(3):
            k = (self.t * 1.6 + i / 3) % 1
            cv.create_oval(cx - rx * k, cy - ry * k, cx + rx * k, cy + ry * k,
                           outline=("#7B5CFF", "#C3A6FF", LIGHT)[i], width=2)


class Sprite:
    """A small transparent always-on-top window for things that fly around the whole
    screen on their own (paper plane, dragon, arrows...)."""

    def __init__(self, root, wu, hu):
        from pixbot_paint import Painter
        self.win = tk.Toplevel(root)
        osl.make_overlay(self.win, KEY)
        self.cv = osl.overlay_canvas(self.win, wu * PX, hu * PX, KEY)
        self.cv.pack()
        self.p = Painter(self.cv, PX)
        self.wu, self.hu = wu, hu

    def show(self, x, y, fn):
        self.win.geometry(f"+{int(x - self.wu * PX / 2)}+{int(y - self.hu * PX / 2)}")
        self.cv.delete("all")
        fn(self.p)

    def close(self):
        try:
            self.win.destroy()
        except Exception:
            pass


class Pixbot(Acts):
    def __init__(self):
        self.root = tk.Tk(className="Pixbot")
        self.root.title("Pixbot pet")
        osl.make_overlay(self.root, KEY)
        self.cv = osl.overlay_canvas(self.root, W, H, KEY)
        self.cv.pack()
        self.portal = Portal(self.root)

        self.my_pid = os.getpid()
        self.monitors = get_monitors()
        self.mon = self.monitors[0][0]
        for m, _ in self.monitors:
            if m[0] == 0 and m[1] == 0:
                self.mon = m
        l, _, r, b = self.work()
        self.x = float(random.randint(l + 150, max(l + 151, r - 150)))
        self.fy = float(b)
        self.vx = self.vy = 0.0
        self.dir = 1
        self.support = {"kind": "taskbar", "mon": self.mon}
        self.platforms, self.windows = [], []
        self.vis_plats, self.vis_pics, self.vis_small, self.vis_icons = [], [], [], []
        self.context = "other"
        self.last_clock = -999.0
        self.wc, self.wc_phase, self.wc_t = None, "cling", 0.0
        self.mimic_color, self.mimic_aspect = ORANGE, 1.0
        self.hide_side = 1
        self.last_input_all = last_input_tick()
        self.user_active = 0.0
        self.keys = collections.deque(maxlen=200)
        self.key_pulse = 0
        self.last_key = -99.0
        self.prev_cur = cursor_pos()
        self.idle_visited = False
        self.visit_then = "wait"
        self.prev_context = "other"
        self.after_land = None
        self.leap_pose = None
        self.bonk_t = -99.0
        self.hops_left = 0
        self.grab_prev = None
        self.cur_move = 0.0
        self.on_pogo = False
        self.pogo_left = 0.0
        self.sprites = {}
        self.portal2 = Portal(self.root)
        self.ride = "cloud"
        self.path = []
        self.plane = None
        self.dragon = None
        self.pg = None
        self.force_slide = False
        self.gaming = False
        self.fg_fullscreen = False
        self.game_monitors = set()
        self.keycodes = collections.deque(maxlen=200)
        self.force = False
        self.trick = None
        self.react_kind = "ooh"
        self.pending_react = None
        self.react_cool = {}
        self.prev_hwnds = None
        self.clip_seq = osl.clipboard_seq()
        self.power = None
        self.session_start = 0.0
        self.bs_presses = collections.deque(maxlen=30)
        self.greeted = set()
        self.popups = []
        self.found_you = False
        self.sub_win = True
        self.audio_last = -99.0
        self.media_act = None
        self.hover_t = 0.0
        self.prev_buttons = 0
        self.long_idle = False
        self.propose_moved = 0.0
        self.inputs = collections.deque(maxlen=3000)
        self.calm_since = 0.0
        self.settings = cat.load()
        self.apply_look()
        self.settings_mtime = self.mtime(cat.SETTINGS_FILE)
        self.cmd_mtime = self.mtime(cat.COMMAND_FILE)
        self.next_special = random.uniform(*cat.special_gap(self.settings["frequency"])) / 2
        try:
            with open(cat.PID_FILE, "w") as f:
                f.write(str(os.getpid()))
        except Exception:
            pass
        self.state, self.st, self.dur = "watch", 0.0, 3.0
        self.sub = None
        self.clock = 0.0
        self.blink, self.next_blink = 0.0, random.uniform(2, 5)
        self.plan = None
        self.target = None
        self.launch = (0.0, 0.0)
        self.leap = None
        self.spin, self.rot, self.spin_T, self.spin_next = 0, 0.0, 1.0, 0
        self.climb = None
        self.hang = None
        self.particles = []
        self.drag = None
        self.samples = collections.deque(maxlen=8)
        self.fs_windows = {}
        self.busy = set()
        self.last_hop = time.perf_counter() - HOP_COOLDOWN / 2
        self.next_special = random.uniform(15, 30)
        self.bag = []
        self.dust_timer = 0.0
        self.hclip = None
        self.invisible = False
        self.edge_choice = None
        self.focus = None
        self.focus_seen = None
        self.last_perch = -99.0
        self.box_lost = 0.0
        self.last_input = last_input_tick()
        self.typing_t = -9.0
        self.fired = set()
        self.wx = self.wy = 0
        self.vis_miss = 0
        self.last = time.perf_counter()
        self.cursor = cursor_pos()

        self.cv.bind("<ButtonPress-1>", self.on_press)
        self.cv.bind("<B1-Motion>", self.on_drag)
        self.cv.bind("<ButtonRelease-1>", self.on_release)
        self.cv.bind("<Button-3>", self.menu)

        threading.Thread(target=self.focus_thread, daemon=True).start()
        threading.Thread(target=self.audio_thread, daemon=True).start()
        threading.Thread(target=self.vision_thread, daemon=True).start()
        self.root.after(0, self.tick)
        self.root.after(3000, self.keep_on_top)
        self.root.after(200, self.watch_screens)

    # ====================== settings from the Pixbot app ======================
    @staticmethod
    def mtime(path):
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0

    def enabled(self, name):
        return self.settings["enabled"].get(name, True)

    def apply_look(self):
        col = str(self.settings.get("color") or ORANGE)
        try:
            cat.shade(col, 0.8)
        except Exception:
            col = ORANGE
        self.body_color = col
        self.dark_color = cat.shade(col, 0.78)
        self.outfit = self.settings.get("outfit") or {}
        new_scale = max(0.8, min(3.0, float(self.settings.get("text_size", cat.DEFAULTS["text_size"]))))
        if getattr(self, "text_scale", None) not in (None, new_scale) and hasattr(self, "sprites"):
            self.kill_sprite("caption")                    # rebuild caption bubble at the new size
            self.kill_sprite("words")
        self.text_scale = new_scale

    # ---------- effect windows ----------
    def show_sprite(self, name, wu, hu, x, y, fn):
        sp = self.sprites.get(name)
        if sp is None:
            sp = self.sprites[name] = Sprite(self.root, wu, hu)
        sp.show(x, y, fn)

    def kill_sprite(self, name):
        sp = self.sprites.pop(name, None)
        if sp:
            sp.close()

    def kill_all_sprites(self):
        for n in list(self.sprites):
            self.kill_sprite(n)

    def weight(self, name):
        """how much more / less you want to see this (favourites & dislikes)"""
        if name in self.settings.get("dislikes", []):
            return self.settings.get("dislike_level", 2) / 10.0
        if name in self.settings.get("favorites", []):
            return float(self.settings.get("fav_boost", 4))
        return 1.0

    def dial(self, key):
        """behaviour dial from the app, as 0..1"""
        return max(0.0, min(1.0, float(self.settings.get(key, cat.DEFAULTS[key])) / 10.0))

    def hop_cooldown(self):
        return 60 + (1 - self.dial("screenhop")) * 420

    def poll_app(self):
        m = self.mtime(cat.SETTINGS_FILE)
        if m != self.settings_mtime:
            self.settings_mtime = m
            old = self.settings["frequency"]
            self.settings = cat.load()
            self.apply_look()
            if self.settings["frequency"] != old:
                self.next_special = self.clock + random.uniform(*cat.special_gap(self.settings["frequency"]))
        m = self.mtime(cat.COMMAND_FILE)
        if m != self.cmd_mtime:
            self.cmd_mtime = m
            try:
                with open(cat.COMMAND_FILE, encoding="utf-8") as f:
                    cmd = json.load(f)
            except Exception:
                cmd = {}
            if cmd.get("quit"):
                self.quit()
            name = cmd.get("play")
            if name and self.state != "hidden":
                if not self.on_ground():
                    self.support = {"kind": "taskbar", "mon": self.mon}
                    self.fy = self.work()[3]
                    self.plan, self.leap, self.hclip, self.invisible = None, None, None, False
                    self.set_state("watch", 1)
                self.do_special(name, force=True)

    def available(self):
        """Should Pixbot be on screen right now? (the 'when is he around' dial)"""
        mode = self.settings["availability"]
        idle = self.clock - self.user_active
        if mode == "paused":
            return False
        if mode == "idle":
            return idle >= self.settings["idle_seconds"]
        if mode == "light":
            recent = sum(1 for t in self.inputs if self.clock - t < 10)
            typing = sum(1 for t in self.keys if self.clock - t < 10) / 2 / 10
            busy = recent > 150 or typing > 1.0
            if busy:
                self.calm_since = self.clock
            return self.clock - self.calm_since > 8
        return True

    def quit(self):
        try:
            os.remove(cat.PID_FILE)
        except OSError:
            pass
        self.root.destroy()

    # ====================== screens & windows ======================
    def work(self, mon=None):
        mon = mon or self.mon
        for m, w in self.monitors:
            if m == mon:
                return w
        return self.monitors[0][1]

    def monitor_at(self, x):
        for m, _ in self.monitors:
            if m[0] <= x < m[2]:
                return m
        return min(self.monitors, key=lambda mw: abs((mw[0][0] + mw[0][2]) / 2 - x))[0]

    def bounds(self):
        return (min(m[0] for m, _ in self.monitors), max(m[2] for m, _ in self.monitors))

    def adjacent(self, a, b):
        return a[2] == b[0] or b[2] == a[0]

    NOT_GAMES = {"chrome", "firefox", "msedge", "brave", "opera", "vivaldi", "arc", "vlc", "mpv",
                 "spotify", "explorer", "powerpnt", "mpc-hc64", "potplayermini64", "wmplayer",
                 "video.ui", "applicationframehost", "code", "obs64", "obs", "discord", "teams",
                 "zoom", "netflix", "photos",
                 # Linux
                 "chromium", "chromium-browser", "chrome-sandbox", "firefox-bin", "firefox-esr",
                 "brave-browser", "librewolf", "epiphany", "totem", "celluloid", "smplayer",
                 "haruna", "mplayer", "kodi.bin", "kodi", "eog", "gwenview", "loupe", "evince",
                 "okular", "libreoffice", "soffice.bin", "gnome-shell", "plasmashell",
                 "nautilus", "dolphin", "thunar", "nemo", "electron", "zoom.real", "slack"}

    def exe_of(self, hwnd):
        try:
            return osl.exe_of(hwnd)
        except Exception:
            return ""

    def update_gaming(self):
        """Is a fullscreen GAME running (not a browser / video player)?"""
        fg = osl.foreground_window()
        self.fg_fullscreen = bool(fg) and fg in self.fs_windows
        games = []
        for h in self.fs_windows:
            exe = self.exe_of(h)
            if exe and exe not in self.NOT_GAMES:
                games.append(h)
        self.gaming = bool(games)
        self.game_monitors = {self.fs_windows[h] for h in games}

    def fullscreen_monitors(self):
        hwnd = osl.foreground_window()
        if hwnd:
            r = osl.fullscreen_candidate(hwnd, self.my_pid)
            if r:
                for m, _ in self.monitors:
                    if covers(r, m):
                        self.fs_windows[hwnd] = m
        for h, m in list(self.fs_windows.items()):
            r = window_rect(h)
            if not alive(h) or not r or not covers(r, m):
                del self.fs_windows[h]
        return set(self.fs_windows.values())

    def build_platforms(self):
        wins = list_windows(self.my_pid)
        self.windows = wins
        plats = []
        for i, (h, r) in enumerate(wins):
            y = r[1]
            mon = self.monitor_at((r[0] + r[2]) / 2)
            mtop, wb = mon[1], self.work(mon)[3]
            if y - mtop < FEET * PX + 10 or y > wb - 30 or covers(r, mon):
                continue
            segs = [(r[0], r[2])]
            for h2, r2 in wins[:i]:
                if r2[1] - 2 <= y < r2[3]:
                    nxt = []
                    for a, b in segs:
                        if r2[2] <= a or r2[0] >= b:
                            nxt.append((a, b))
                        else:
                            if r2[0] > a:
                                nxt.append((a, r2[0]))
                            if r2[2] < b:
                                nxt.append((r2[2], b))
                    segs = nxt
            for a, b in segs:
                if b - a >= 12 * PX:
                    plats.append({"kind": "win", "hwnd": h, "y": y, "x0": a, "x1": b,
                                  "left": r[0], "off0": a - r[0], "off1": b - r[0]})
        self.platforms = plats

    def taskbars(self):
        return [{"kind": "taskbar", "mon": m, "y": w[3], "x0": w[0], "x1": w[2]}
                for m, w in self.monitors]

    def all_platforms(self):
        return self.platforms + self.vis_plats + self.taskbars()

    def vision_thread(self):
        if pixbot_vision is None:
            return
        while True:
            try:
                mon = self.mon
                w = self.work(mon)
                masks = [(self.wx - 4, self.wy - 4, self.wx + W + 4, self.wy + H + 4)]
                if self.portal.rect:
                    masks.append(self.portal.rect)
                if mon in self.busy or self.state == "hidden" or not self.settings["screen_reading"]:
                    self.vis_plats, self.vis_pics, self.vis_small, self.vis_icons = [], [], [], []
                else:
                    # screenshot lives only in memory and is thrown away right after
                    ledges, pics, icons = pixbot_vision.scan(mon, masks, top_clear=FEET * PX + 10,
                                                            bottom=w[3] - 4)
                    self.vis_plats = [{"kind": "vis", "y": y, "x0": a, "x1": b}
                                      for y, a, b in ledges if b - a >= 2 * HALF]
                    self.vis_small = [{"kind": "vis", "y": y, "x0": a, "x1": b}
                                      for y, a, b in ledges if b - a < 2 * HALF]
                    self.vis_pics = pics
                    self.vis_icons = icons
            except Exception:
                pass
            time.sleep(0.5)

    def watch_screens(self):
        try:
            self.monitors = get_monitors() or self.monitors
            keys = [m for m, _ in self.monitors]
            if self.mon not in keys:
                self.mon = keys[0]
            self.busy = busy = self.fullscreen_monitors()
            self.update_gaming()
            free = [m for m in keys if m not in busy]
            self.build_platforms()
            self.cursor = cursor_pos()
            self.watch_for_reactions()

            sp = self.support
            if sp and sp["kind"] == "win":
                match = [p for p in self.platforms if p["hwnd"] == sp["hwnd"]
                         and p["x0"] - 4 <= self.x <= p["x1"] + 4]
                if match:
                    sp["off0"], sp["off1"] = match[0]["off0"], match[0]["off1"]
                elif self.on_ground():
                    self.fall()
            elif sp and sp["kind"] == "vis" and self.on_ground() and self.clock > sp.get("grace", 0):
                near = [p for p in self.vis_plats if p["x0"] - 130 <= self.x <= p["x1"] + 130
                        and abs(p["y"] - sp["y"]) <= 260]
                best = min(near, key=lambda p: abs(p["y"] - sp["y"])) if near else None
                if best and abs(best["y"] - sp["y"]) <= 12:
                    sp["y"] = best["y"]                  # tiny shift: just stay on it
                    sp["x0"] = min(sp["x0"], best["x0"])
                    sp["x1"] = max(sp["x1"], best["x1"])
                    self.vis_miss = 0
                elif best:
                    # the page moved (scrolling...): jump after the ledge in a hurry
                    self.vis_miss = 0
                    dy = best["y"] - self.fy
                    T = max(0.28, math.sqrt(2 * max(0.0, -dy) / GRAVITY) * 1.15)
                    tx = min(max(self.x, best["x0"] + HALF), best["x1"] - HALF)
                    self.leap_to(tx, best["y"], ("land", dict(best)), T=T)
                else:
                    self.vis_miss += 1
                    if self.vis_miss >= 2:                 # nothing to stand on: drop down
                        self.vis_miss = 0
                        self.fall()
            self.context = self.foreground_context()
            self.prev_context = self.context
            # a fullscreen GAME is running -> grab a controller and play along until it closes
            if (self.gaming and self.media_act is None and self.plan is None and self.state in BASE
                    and self.mon not in self.busy and self.enabled("gamereact")):
                self.force = True
                started = self.start_special("gaming")
                self.force = False
                if started:
                    self.media_act = "gaming"
                    self.dur = 10 ** 6
            if self.media_act == "gaming":
                if self.state == "gaming" and self.dur > 10 ** 5 and not self.gaming:
                    self.dur = self.st + 1.6          # game closed: show win / game over
                    self.media_act = None
                elif self.state != "gaming":
                    self.media_act = None
            # music / video playing -> react, and keep it up until you pause
            media = self.context in ("video", "music") and self.audio_playing() and not self.gaming
            if (media and self.media_act is None and self.plan is None and self.state in BASE
                    and self.enabled("videoreact")):
                if self.context == "music":
                    picks = ["dance", "listen", "headphones", "rockstar", "dj"]
                else:
                    picks = ["popcorn", "popcorn", "listen", "dance", "headphones"]
                picks = [p for p in picks if self.enabled(p)] or ["listen"]
                pick = random.choice(picks)
                self.force = True
                started = self.start_special(pick)
                self.force = False
                if started:
                    self.media_act = pick
                    self.dur = 10 ** 6
            if self.media_act not in (None, "gaming") and self.state == self.media_act \
                    and self.dur > 10 ** 5:
                if not self.audio_playing() or self.context not in ("video", "music"):
                    self.dur = self.st + 1.0        # paused / switched away: wrap it up
                    self.media_act = None
            elif self.media_act not in (None, "gaming") and self.state != self.media_act:
                self.media_act = None

            on_taskbar = sp is not None and sp["kind"] == "taskbar"
            moving = self.plan is not None or self.state in (
                "drag", "dig", "peek", "climb", "edgeclimb", "chute", "hang", "offscreen")
            self.poll_app()
            avail = self.available()
            if self.state == "hidden":
                if free and avail:
                    self.root.deiconify()
                    self.root.attributes("-topmost", True)
                    self.run_in(self.mon if self.mon in free else random.choice(free))
            elif not avail and self.plan != "hide" and self.state not in ("runoff", "drag"):
                # not his time to be around: leave (run off if he can, otherwise just go)
                if on_taskbar and self.on_ground():
                    l, _, r, _ = self.work()
                    self.hide_side = -1 if self.x - l < r - self.x else 1
                    self.dir = self.hide_side
                    self.plan = "hide"
                    self.set_state("runoff")
                else:
                    self.plan = None
                    self.set_state("hidden")
                    self.particles.clear()
                    self.root.withdraw()
            elif self.mon in busy and not moving and self.on_ground():
                if not on_taskbar:
                    self.fall()                            # drop down to the taskbar first
                elif free:
                    tgt = min(free, key=lambda m: abs(m[0] - self.mon[0]))
                    self.change_screen(tgt, fast=True,
                                       method="leap" if self.adjacent(self.mon, tgt) else "portal")
                else:                                      # single screen: run off the side
                    l, _, r, _ = self.work()
                    self.hide_side = -1 if self.x - l < r - self.x else 1
                    self.dir = self.hide_side
                    self.plan = "hide"
                    self.set_state("runoff")
            elif self.plan in ("travel", "dig", "portal") and self.target in busy:
                others = [m for m in free if m != self.mon]
                self.target = others[0] if others else (self.mon if self.mon in free else None)
            self.check_focus()
        except Exception:
            pass
        finally:
            self.root.after(400, self.watch_screens)

    # ---------- text box perching (UI Automation) ----------
    def focus_thread(self):
        if not osl.IS_WIN:                     # text-box finding uses Windows UI Automation
            return
        try:
            import comtypes
            import comtypes.client
            comtypes.CoInitialize()
            comtypes.client.GetModule("UIAutomationCore.dll")
            from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation
            uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
        except Exception:
            return
        while True:
            try:
                el = uia.GetFocusedElement()
                r = el.CurrentBoundingRectangle
                self.focus = (el.CurrentControlType, (r.left, r.top, r.right, r.bottom),
                              el.CurrentProcessId)
            except Exception:
                self.focus = None
            time.sleep(0.35)

    # ---------- noticing what you do (windows, clipboard, battery, time, ...) ----------
    def queue_react(self, kind, toggle, cooldown, target_x=None):
        if not self.enabled(toggle) or self.clock - self.react_cool.get(kind, -1e9) < cooldown:
            return
        self.react_cool[kind] = self.clock
        self.pending_react = (kind, target_x)

    def watch_for_reactions(self):
        # windows opening / closing
        hw = {h: r for h, r in self.windows if (r[2] - r[0]) * (r[3] - r[1]) > 300 * 200}
        if self.prev_hwnds is not None:
            new = [h for h in hw if h not in self.prev_hwnds]
            gone = [h for h in self.prev_hwnds if h not in hw and not osl.is_window(h)]
            if new:
                r = hw[new[0]]
                self.queue_react("ooh", "newwindow", 20, (r[0] + r[2]) / 2)
            elif gone:
                r = self.prev_hwnds[gone[0]]
                self.queue_react("bye", "closewindow", 20, (r[0] + r[2]) / 2)
        self.prev_hwnds = hw
        # clipboard (copy)
        seq = osl.clipboard_seq()
        if seq != self.clip_seq:
            self.clip_seq = seq
            self.queue_react("copied", "clipboard", 25)
        # battery / charger
        pw = osl.power()
        if pw:
            ac, pct = pw
            if self.power is not None and ac and not self.power[0]:
                self.queue_react("charging", "battery", 30)
            elif not ac and pct <= 20:
                self.queue_react("lowbattery", "battery", 600)
            self.power = (ac, pct)
        # greetings by time of day (once a day each)
        now = time.localtime()
        day = now.tm_yday
        active = self.clock - self.user_active < 5
        if active and 5 <= now.tm_hour < 11 and ("m", day) not in self.greeted:
            self.greeted.add(("m", day))
            self.queue_react("morning", "greetings", 0)
        if active and (now.tm_hour == 12 or (now.tm_hour == 13 and now.tm_min < 30)) \
                and ("l", day) not in self.greeted:
            self.greeted.add(("l", day))
            self.queue_react("lunch", "greetings", 0)
        # long stretch at the computer -> suggest a break (every hour of activity)
        if self.clock - self.user_active > 300:
            self.session_start = self.clock
        elif self.clock - self.session_start > 3600:
            self.session_start = self.clock
            self.queue_react("break", "breakreminder", 0)

    def audio_thread(self):
        """Is sound playing right now? (so music/video reactions last until you pause)"""
        if not osl.IS_WIN:
            while True:
                try:
                    if osl.audio_level() > 0.01:
                        self.audio_last = self.clock
                except Exception:
                    pass
                time.sleep(0.5)
        try:
            import comtypes
            from ctypes import POINTER, cast
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioMeterInformation
            comtypes.CoInitialize()
        except Exception:
            return
        meter = None
        while True:
            try:
                if meter is None:
                    sp = AudioUtilities.GetSpeakers()
                    dev = getattr(sp, "_dev", None) or getattr(sp, "dev", None) or sp
                    meter = cast(dev.Activate(IAudioMeterInformation._iid_, CLSCTX_ALL, None),
                                 POINTER(IAudioMeterInformation))
                if meter.GetPeakValue() > 0.01:
                    self.audio_last = self.clock
            except Exception:
                meter = None
                time.sleep(2)
            time.sleep(0.25)

    def really_typing(self):
        """Typing text - not gaming. Needs a fast key rate AND lots of different keys
        (games hammer a few keys like WASD), and nothing fullscreen."""
        if self.gaming or self.fg_fullscreen:
            return False
        rate = sum(1 for k in self.keys if self.clock - k < 2.0) / 4.0
        distinct = {vk for t, vk in self.keycodes if self.clock - t < 4.0}
        return rate >= 2.0 and len(distinct) >= 6

    def audio_playing(self):
        return self.clock - self.audio_last < 3.0

    def box_ok(self, r):
        w, h = r[2] - r[0], r[3] - r[1]
        if not (40 < w < 2200 and 12 < h < 320):
            return False
        mon = self.monitor_at((r[0] + r[2]) / 2)
        return mon not in self.busy and r[1] - mon[1] > FEET * PX + 10

    def check_focus(self):
        f = self.focus
        box = f[1] if f and f[0] in (50004, 50003) and f[2] != self.my_pid else None
        if box and not self.box_ok(box):
            box = None
        if self.state == "perch":
            sp = self.support
            if box and abs(box[1] - sp["y"]) < 3 and abs(box[0] - sp["x0"]) < 3:
                sp["y"], sp["x0"], sp["x1"] = box[1], box[0], box[2]
                self.box_lost = 0.0
            else:
                self.box_lost += 0.4
                if self.box_lost > 1.2:
                    self.hop_down()
            return
        if box and box != self.focus_seen:
            self.focus_seen = box
            if (self.plan is None and self.state in BASE and self.clock - self.last_perch > 4
                    and self.enabled("textbox")):
                self.last_perch = self.clock
                plat = {"kind": "box", "y": box[1], "x0": box[0], "x1": box[2]}
                tx = min(max((box[0] + box[2]) / 2, box[0] + 3 * PX), box[2] - 3 * PX)
                self.leap_to(tx, box[1], ("perch", plat))
        elif not box:
            self.focus_seen = None

    def foreground_context(self):
        """What are you doing right now? -> video / browser / files / code / chat / other"""
        try:
            h = osl.foreground_window()
            if not h:
                return "other"
            title = osl.window_title(h).lower()
            exe = self.exe_of(h)
            if exe in ("spotify", "applemusic", "itunes", "rhythmbox", "lollypop", "amarok",
                       "elisa", "clementine", "strawberry", "audacious") or any(
                    w in title for w in ("music", "official audio", "official video", "lyrics",
                                         "(audio)", "- topic", "remix", "soundcloud", "playlist")):
                return "music"
            if any(w in title for w in ("youtube", "netflix", "twitch", "prime video", "disney+"))                     or exe in ("vlc", "mpv", "totem", "celluloid", "smplayer", "haruna", "mplayer"):
                return "video"
            if exe in ("chrome", "firefox", "msedge", "brave", "opera", "vivaldi", "arc",
                       "chromium", "chromium-browser", "firefox-bin", "firefox-esr",
                       "brave-browser", "librewolf", "epiphany"):
                return "browser"
            if exe in ("explorer", "nautilus", "dolphin", "thunar", "nemo", "pcmanfm", "caja"):
                return "files"
            if exe in ("code", "devenv", "pycharm64", "idea64", "cursor", "windowsterminal",
                       "powershell", "cmd", "sublime_text", "gnome-terminal-server", "konsole",
                       "kitty", "alacritty", "xterm", "wezterm-gui", "tilix", "xfce4-terminal",
                       "terminator", "ptyxis", "pycharm", "idea", "kate", "gedit", "nvim", "vim"):
                return "code"
        except Exception:
            pass
        return "other"

    def run_in(self, mon):
        """Come back after hiding: run in from the side of the screen."""
        self.mon = mon
        self.support = {"kind": "taskbar", "mon": mon}
        l, _, r, b = self.work()
        side = self.hide_side
        self.x = (r + HALF * 2) if side > 0 else (l - HALF * 2)
        self.fy = b
        self.dir = -side
        self.plan = None
        self.invisible = False
        self.set_state("runin", 1.2)

    def hop_down(self):
        self.support = None
        self.dir = random.choice([-1, 1])
        self.start_jump(self.dir * 160, -520)

    # ====================== travel ======================
    def change_screen(self, target, fast=False, method=None):
        if method is None:
            methods = ["dig", "portal"] + (["leap", "leap"] if self.adjacent(self.mon, target) else [])
            method = random.choice(methods)
        if method == "leap" and not self.adjacent(self.mon, target):
            method = "dig"
        self.target, self.fast = target, fast
        if target != self.mon:
            self.last_hop = self.clock
        if method == "leap":
            self.plan = "travel"
            self.dir = 1 if (target[0] + target[2]) / 2 > self.x else -1
            self.set_state("leave")
        elif method == "dig":
            self.plan = "dig"
            self.set_state("dig")
        else:
            self.plan = "portal"
            if target == self.mon:
                self.dir = random.choice([-1, 1])
            else:
                self.dir = -1 if (target[0] + target[2]) / 2 > self.x else 1
            l, _, r, _ = self.work()
            self.portal_x = (l if self.dir < 0 else r) - self.dir * 5 * PX
            self.portal_open = False
            self.set_state("portal_in")

    def emerge(self, mon, x=None):
        self.mon = mon
        self.support = {"kind": "taskbar", "mon": mon}
        l, _, r, b = self.work()
        self.x = x if x is not None else (l + r) / 2
        self.fy = b + 8.5 * PX
        self.vx = self.vy = 0.0
        self.dir = random.choice([-1, 1])
        self.plan = "emerge"
        self.set_state("peek")

    def parachute_in(self, mon):
        self.mon = mon
        l, t, r, _ = mon[0], mon[1], mon[2], mon[3]
        self.x = random.uniform(l + 150, r - 150)
        self.fy = t + 1.0 * PX
        self.vx = self.vy = 0.0
        self.support = None
        self.plan = None
        self.invisible = False
        self.set_state("chute")

    # ====================== state helpers ======================
    def set_state(self, s, dur=None):
        if self.sprites and s != self.state:
            self.kill_all_sprites()
        if s not in ("crouch", "leapto", "air", "pogo"):
            self.on_pogo = False
        self.state, self.st = s, 0.0
        self.dur = dur if dur is not None else 10 ** 9
        self.edge_choice = None
        self.fired = set()
        if s != "air":
            self.spin, self.rot = 0, 0.0

    def once(self, key):
        if key in self.fired:
            return False
        self.fired.add(key)
        return True

    def on_ground(self):
        return self.state in BASE or self.state in ACTS or self.state in GROUNDISH

    def fall(self):
        self.support = None
        self.vy = 0.0
        self.set_state("air")

    TRICKS = ["frontflip", "backflip", "twist", "starjump", "glide", "cannonball", "split"]

    def start_jump(self, vx, vy, spin=0):
        self.launch = (vx, vy)
        self.leap = None
        self.trick = None
        # sometimes do a move in the air instead of a plain jump
        if (spin == 0 and vy < -450 and self.enabled("tricks") and self.leap_pose is None
                and random.random() < 0.15 + 0.35 * self.dial("energy")):
            self.trick = random.choice(self.TRICKS)
            if self.trick == "frontflip":
                spin = 1 if vx >= 0 else -1
            elif self.trick == "backflip":
                spin = -1 if vx >= 0 else 1
        self.spin_next = spin
        self.set_state("crouch", 0.09)

    def leap_to(self, tx, ty, then, T=None, spin=0):
        dx, dy = tx - self.x, ty - self.fy
        if T is None:
            T = min(max(math.hypot(dx, dy) / 1100, 0.42), 1.15)
            if dy < 0:
                T = max(T, math.sqrt(2 * -dy / GRAVITY) * 1.2)
        vx = dx / T
        vy = (dy - 0.5 * GRAVITY * T * T) / T
        if abs(dx) > 5:
            self.dir = 1 if dx > 0 else -1
        self.start_jump(vx, vy, spin)
        self.leap = (tx, ty, vx, vy, T, then)

    # ---------- choosing what to do ----------
    CHILL = ["code", "gaming", "relax", "relax", "read", "coffee", "headphones", "meditate"]

    def pick_next(self):
        energy = self.dial("energy")         # 0 = very calm ... 1 = hyper
        home = self.dial("home")             # 0 = taskbar lover ... 1 = loves it up top
        resting = self.clock < getattr(self, "rest_until", 0)
        if self.clock >= self.next_special and not resting:
            self.next_special = self.clock + random.uniform(*cat.special_gap(self.settings["frequency"]))
            if self.do_special():
                # after anything special he takes a breather - longer the calmer he is
                self.rest_until = self.clock + self.dur + random.uniform(4, 10) * (1.6 - 1.3 * energy)
                return
        on_bar = self.support is not None and self.support["kind"] == "taskbar"
        move_ok = not resting and random.random() < 0.15 + 0.85 * energy   # calm = mostly stays put
        if move_ok and on_bar and random.random() < 0.05 + 0.85 * home and self.enabled("explore"):
            if self.try_explore(up=True):    # head back up onto windows / page content
                return
        if move_ok and on_bar and random.random() < 0.12 * home * energy and self.enabled("ceiling") \
                and self.start_special("ceiling"):
            return
        if move_ok and not on_bar and self.support is not None and random.random() < 0.35 * (1 - home):
            self.hop_down()                  # taskbar lover: comes back down
            return
        names = list(BASE)
        calm = 1 - energy
        mult = {"lurk": 0.3 + 0.7 * energy, "watch": 0.8 + 2.4 * calm, "idle": 0.6 + 1.6 * calm,
                "chill": 0.3 + 2.2 * calm,
                "walk": 0.03 + 1.2 * energy, "run": 2.0 * max(0.0, energy - 0.15),
                "hopabout": 0.03 + 1.6 * energy,
                "sprintslide": (0.02 + 2.2 * energy) if self.enabled("slides") else 0.0,
                "ride": 2.0 * self.dial("transport") * (0.25 + 0.75 * energy)}
        if resting:                          # resting: only calm things
            for k in ("walk", "run", "hopabout", "sprintslide", "ride"):
                mult[k] = 0.0
        weights = [BASE[n][0] * max(0.0, mult[n]) for n in names]
        for _ in range(6):
            s = random.choices(names, weights)[0]
            if s == "chill":                          # long relaxed idle activity
                opts = [a for a in self.CHILL if self.enabled(a)]
                if opts:
                    a = random.choices(opts, [self.weight(o) + 0.01 for o in opts])[0]
                    self.force = True
                    ok = self.start_special(a)
                    self.force = False
                    if ok:
                        self.dur = random.uniform(15, 40) * (0.6 + 0.8 * calm)
                        return
                continue
            if s == "hopabout":
                hang_ok = self.enabled("edgehang")
                if hang_ok and random.random() < 0.3 and self.try_edgehang():
                    return
                if self.enabled("explore") and self.try_explore(near=True):
                    return
                if hang_ok and self.try_edgehang():          # only small spots nearby
                    return
                continue
            if s == "ride":                           # use a means of transport
                if self.start_ride():
                    return
                continue
            if s == "sprintslide":                    # short sprint that ends in a slide
                geo = self.surface()
                if geo:
                    y, x0, x1 = geo
                    self.dir = 1 if (x1 - self.x) > (self.x - x0) else -1
                self.force_slide = True
                return self.set_state("run", 2.5)
            if s in ("walk", "run"):
                self.dir = random.choice([-1, 1])
            if s == "lurk":
                cx = self.cursor[0]
                self.dir = (1 if cx > self.x else -1) if abs(cx - self.x) > 120 and random.random() < 0.6 \
                    else random.choice([-1, 1])
            lo, hi = BASE[s][1]
            dur = random.uniform(lo, hi)
            if s in ("watch", "idle"):                # calm = longer quiet stretches
                dur *= 1 + 2.0 * calm
            return self.set_state(s, dur)
        self.set_state("watch", 4 + 6 * calm)

    def do_special(self, name=None, force=False):
        """Play one special animation / move. Uses a shuffled bag so every
        animation comes up before any repeats. force=True ignores the on/off switches
        (used by the app's preview buttons)."""
        self.force = force
        try:
            return self._do_special(name)
        finally:
            self.force = False

    def allowed(self, s):
        if self.force or s == "cursorplay":
            return True
        return self.enabled(s)

    def _do_special(self, name=None):
        if name is None:
            now = time.localtime()
            late = (now.tm_hour, now.tm_min) >= (0, 1) and now.tm_hour < 6
            if late and self.clock - self.last_clock > 240 and self.start_special("clock"):
                self.last_clock = self.clock
                return True
            if random.random() < 0.5 * self.dial("cursor") ** 1.5 and self.start_special("cursorplay"):
                return True
            picks = CONTEXT_ACTS.get(self.context)
            if picks and random.random() < 0.45 and self.start_special(random.choice(picks)):
                return True
        for _ in range(len(ACTS) + len(MOVES)):
            if name is None:
                if not self.bag:                     # favourites go in several times,
                    bag = []                         # disliked ones only sometimes
                    for n in list(ACTS) + MOVES:
                        w = self.weight(n)
                        if w < 1.0:
                            if random.random() < w:
                                bag.append(n)
                        else:
                            bag += [n] * max(1, int(round(w)))
                    random.shuffle(bag)
                    self.bag = bag or ["wave"]
                s = self.bag.pop()
            else:
                s = name
            if self.start_special(s):
                return True
            if name is not None:
                return False
        return False

    def start_special(self, s):
        if not self.allowed(s):
            return False
        on_bar = self.support is not None and self.support["kind"] == "taskbar"
        if s == "jump":
            self.dir = random.choice([-1, 1])
            self.start_jump(self.dir * random.uniform(80, 260), -random.uniform(650, 950))
            return True
        if s == "flip":
            self.dir = random.choice([-1, 1])
            self.start_jump(self.dir * random.uniform(40, 160), -random.uniform(850, 1000),
                            spin=random.choice([1, -1]))
            return True
        if s == "explore":
            return self.try_explore()
        if s == "climb":
            return self.try_climb()
        if s == "point":
            return self.try_point()
        if s == "hang":
            return self.try_hang()
        if s in ("parachute", "ceiling"):
            if not on_bar:
                return False
            self.edge_after = "offscreen" if s == "parachute" else "ceiling"
            self.set_state("toedge")
            l, _, r, _ = self.work()
            self.dir = -1 if self.x - l < r - self.x else 1
            return True
        if s == "clock":
            prim = next((m for m, _ in self.monitors if m[0] == 0 and m[1] == 0), None)
            if not (on_bar and prim and self.support["mon"] == prim):
                return False
            self.clock_x = self.work(prim)[2] - 150
            self.dir = 1 if self.clock_x > self.x else -1
            self.set_state("toclock")
            return True
        if s == "tbhang":
            if not on_bar:
                return False
            self.fy = self.work()[3]
            self.support = None
            self.set_state("tbhang", random.uniform(4, 7))
            return True
        if s == "edgehang":
            return self.try_edgehang()
        if s == "chase":
            if not self.support:
                return False
            self.set_state("chase", random.uniform(4, 6))
            return True
        if s == "mimic":
            return self.try_mimic()
        if s in ("cloud", "jetpack"):
            return self.start_fly(s)
        if s == "portalgun":
            if not self.support:
                return False
            self.set_state("pgun", 10 ** 6)
            return True
        if s == "smokebomb":
            if not self.support:
                return False
            self.set_state("smoke", 10 ** 6)
            return True
        if s == "cursorplay" or s in CURSOR_GAMES:
            return self.cursor_game(None if s == "cursorplay" else s)
        if s == "dig":
            if not on_bar:
                return False
            self.change_screen(self.mon, method="dig")
            return True
        if s == "portal":
            if not on_bar:
                return False
            others = [m for m, _ in self.monitors if m != self.mon and m not in self.busy]
            tgt = random.choice(others) if others and self.clock - self.last_hop > self.hop_cooldown() and self.dial("screenhop") > 0 \
                else self.mon
            self.change_screen(tgt, method="portal")
            return True
        if s == "hop":
            others = [m for m, _ in self.monitors if m != self.mon and m not in self.busy]
            if not (others and on_bar and self.clock - self.last_hop > self.hop_cooldown() and self.dial("screenhop") > 0):
                return False
            self.change_screen(random.choice(others))
            return True
        if s in ACTS:
            if s == "slingshot" and not self.support:
                return False
            self.prepare_act(s)
            self.set_state(s, random.uniform(*ACTS[s]))
            return True
        return False

    def prepare_act(self, s):
        self.sub = random.choice(["squat", "curl", "jacks"]) if s == "train" else None
        if s in ("walk", "run", "inspect", "skate",
                 "soccer", "broom", "missioncomplete"):
            self.dir = random.choice([-1, 1])
        if s == "code":
            self.code_lines = [(random.randint(0, 3), random.randint(2, 9),
                                random.choice(CODE_COLORS)) for _ in range(24)]
        if s == "gaming":
            self.sub_win = random.random() < 0.6
        if s == "paint":
            self.paint_dots = [(random.uniform(0.3, 3.3), random.uniform(0.3, 2.9),
                                random.choice(CODE_COLORS)) for _ in range(30)]

    # ---------- moves that use the screen ----------
    def try_explore(self, near=False, up=False):
        if up:                              # prefer the highest reachable spots
            ups = []
            for p in self.all_platforms():
                if p["kind"] == "taskbar" or p["x1"] - p["x0"] < 2 * HALF + 8:
                    continue
                if self.monitor_at((p["x0"] + p["x1"]) / 2) in self.busy:
                    continue
                dy = p["y"] - self.fy
                tx = random.uniform(p["x0"] + HALF, p["x1"] - HALF)
                if -850 < dy < -80 and abs(tx - self.x) < 1000:
                    ups.append((p, tx, -dy))
            if not ups:
                return False
            ups.sort(key=lambda c: -c[2])
            p, tx, _ = random.choice(ups[:max(3, len(ups) // 3)])
            self.leap_to(tx, p["y"], ("land", dict(p)), spin=random.choice([0, 0, 0, 1, -1]))
            return True
        cands = []
        for p in self.all_platforms():
            if p["x1"] - p["x0"] < 2 * HALF + 8:
                continue
            if self.monitor_at((p["x0"] + p["x1"]) / 2) in self.busy:
                continue
            sp = self.support
            if sp and sp["kind"] == p["kind"] and abs(p["y"] - self.fy) < 6:
                continue
            tx = random.uniform(p["x0"] + HALF, p["x1"] - HALF)
            dy = p["y"] - self.fy
            if near:
                if abs(tx - self.x) > 520 or dy < -380 or dy > 450 or abs(dy) < 20:
                    continue
            elif abs(tx - self.x) > 1100 or dy < -850 or abs(dy) < 20:
                continue
            cands.append((p, tx))
        if not cands:
            return False
        p, tx = random.choice(cands)
        self.leap_to(tx, p["y"], ("land", dict(p)),
                     spin=random.choice([0, 0, 0, 0, 1, -1]) if not near else 0)
        return True

    def try_point(self):
        """Jump onto the top edge of a picture (e.g. a video thumbnail) and point at it."""
        opts = []
        for x0, y0, x1, y1 in self.vis_pics:
            if x1 - x0 < 2 * HALF or y0 - self.mon[1] < FEET * PX + 10:
                continue
            if y0 - self.fy < -850 or abs(((x0 + x1) / 2) - self.x) > 1200:
                continue
            opts.append((x0, y0, x1, y1))
        if not opts:
            return False
        x0, y0, x1, y1 = random.choice(opts)
        left = abs(self.x - x0) < abs(self.x - x1)
        tx = x0 + HALF if left else x1 - HALF
        plat = {"kind": "vis", "y": y0, "x0": x0, "x1": x1, "grace": self.clock + 9}
        self.point_dir = 1 if left else -1
        self.leap_to(tx, y0, ("point", plat))
        return True

    def try_hang(self):
        """Grab the scrollbar on the right side of the window under him."""
        mon = self.mon
        for h, r in self.windows:
            if r[0] <= (mon[0] + mon[2]) / 2 <= r[2] and r[2] - r[0] > 500 and r[3] - r[1] > 400:
                bar_x = r[2] - 8
                if bar_x > mon[2] or bar_x < mon[0] + 200:
                    continue
                lo = r[1] + 140
                hi = min(r[3], self.work()[3]) - 160
                if hi <= lo:
                    return False
                gy = random.uniform(lo, hi)
                if gy - self.fy < -850:
                    gy = self.fy - 700
                self.hang = {"x": bar_x - 22}
                self.leap_to(bar_x - 22, gy, ("hang", None))
                return True
        return False

    def try_climb(self):
        lo, hi = self.bounds()
        opts = []
        for h, r in self.windows[:12]:
            if self.monitor_at((r[0] + r[2]) / 2) in self.busy:
                continue
            for side in (-1, 1):
                wall = r[0] if side < 0 else r[2]
                cx = wall + side * HALF
                if not (lo + HALF <= cx <= hi - HALF) or abs(cx - self.x) > 900:
                    continue
                grab = min(self.fy, r[3])
                if grab - r[1] < 80 or self.fy - grab > 600:
                    continue
                inside = wall - side * 4
                pts = (grab - 10, (grab + r[1]) / 2, r[1] + 12)
                if all(root_at(inside, y) == h for y in pts):
                    opts.append((h, r, side, wall, cx, grab))
        if not opts:
            return False
        h, r, side, wall, cx, grab = random.choice(opts)
        edge = "left" if side < 0 else "right"

        def wall_x(h=h, edge=edge):
            rr = frame_rect(h) if alive(h) else None
            return None if not rr else (rr[0] if edge == "left" else rr[2])

        def top_y(h=h):
            rr = frame_rect(h) if alive(h) else None
            return rr[1] if rr else None
        self.wc = {"wall": wall_x, "top": top_y, "side": -side, "after": "vault", "hwnd": h}
        self.leap_to(wall - (-side) * 5.4 * PX, grab, ("wallclimb", None),
                     T=0.5 if abs(cx - self.x) > 60 else 0.3)
        return True

    def try_edgehang(self):
        """Grab the edge of a small box / picture and dangle from it."""
        opts = []
        for p in self.vis_small + self.vis_plats:
            for cx in (p["x0"] + 2 * PX, p["x1"] - 2 * PX):
                feet = p["y"] + 10.4 * PX
                dy = feet - self.fy
                if abs(cx - self.x) < 520 and -380 < dy < 400 and feet < self.work()[3] - 10:
                    opts.append((cx, feet, p))
        for x0, y0, x1, y1 in self.vis_pics:
            for cx in (x0 + 2 * PX, x1 - 2 * PX):
                feet = y0 + 10.4 * PX
                if abs(cx - self.x) < 520 and -380 < feet - self.fy < 400 and feet < self.work()[3] - 10:
                    opts.append((cx, feet, {"kind": "vis", "y": y0, "x0": x0, "x1": x1}))
        if not opts:
            return False
        cx, feet, p = random.choice(opts)
        self.ledge = dict(p, grace=self.clock + 12)
        self.leap_to(cx, feet, ("lhang", None))
        return True

    # ---------- playing with your cursor ----------
    def cursor_reachable(self):
        cx, cy = cursor_pos()
        self.cursor = (cx, cy)
        return (self.monitor_at(cx) == self.mon and self.fy - 650 < cy < self.fy - 30
                and self.mon[0] + HALF < cx < self.mon[2] - HALF)

    def cursor_game(self, game=None):
        if not self.support or not self.cursor_reachable():
            return False
        if game is None:
            games = [g for g in CURSOR_GAMES if self.enabled(g)]
            if not games:
                return False
            game = random.choice(games)
        if game == "chase":
            self.set_state("chase", random.uniform(4, 6))
            return True
        self.visit_then = game
        self.set_state("visit", 8)
        return True

    def at_cursor(self, game):
        """He has run under the cursor - now do the game."""
        cx, cy = self.cursor
        if game == "wait":
            return self.set_state("waitcursor", 10 ** 6)
        if not self.cursor_reachable() and game != "reach":
            return self.set_state("watch", 3)
        if game == "reach":
            return self.set_state("reach", 4.5)
        if game == "propose":
            self.propose_moved, self.propose_yes = 0.0, None
            return self.set_state("propose", 9.5)
        if game == "tag":
            return self.leap_to(cx, cy + 7 * PX, ("tag", None))
        if game == "highfive":
            self.leap_pose = "highfive"
            return self.leap_to(cx, cy + 9 * PX, ("highfive", None))
        if game == "throwball":
            return self.set_state("throwball", 2.2)
        if game == "hideseek":
            self.found_you = False
            return self.set_state("hiding", 10)
        if game == "grab":
            self.grab_prev = (cx, cy)
            return self.leap_to(cx, cy + 10.4 * PX, ("cursorhang", None))
        if game in ("kick", "bash"):
            self.leap_pose = game
            return self.leap_to(cx, cy + 7 * PX, ("bonk", None))
        if game == "jumparound":
            self.hops_left = 4
            return self.next_hop()
        if game == "slideunder":
            self.slide_target = cx                       # back up first, then sprint + slide
            self.dir = -1 if cx > self.x else 1
            self.set_state("slidein", 3.0)
            self.slide_phase = "back"
            return

    def next_hop(self):
        cx, _ = self.cursor
        geo = self.surface() if self.support else None
        if not geo:
            self.hops_left = 0
            return
        y, x0, x1 = geo
        side = 1 if self.x < cx else -1
        tx = min(max(cx + side * random.uniform(70, 120), x0 + HALF), x1 - HALF)
        self.hops_left -= 1
        self.after_land = "jumparound" if self.hops_left > 0 else None
        plat = dict(self.support) if self.support["kind"] != "taskbar" else \
            {"kind": "taskbar", "mon": self.support["mon"], "y": y, "x0": x0, "x1": x1}
        self.leap_to(tx, y, ("land", plat), T=0.55, spin=random.choice([0, 0, side]))

    # ---------- transport ----------
    RIDES = ["skate", "pogo", "cloud", "jetpack", "portalgun", "smokebomb"]

    def start_ride(self):
        rides = [r for r in self.RIDES if self.enabled(r)]
        if not rides:
            return False
        r = random.choices(rides, [self.weight(x) + 0.01 for x in rides])[0]
        if not self.start_special(r):
            return False
        if r in ("skate", "pogo"):                    # 'how long each ride lasts' dial
            self.dur = 5 + 55 * self.dial("ride_length") ** 1.3
        return True

    def start_fly(self, kind):
        """golden cloud / jetpack: fly a path around the screen, then land on the taskbar"""
        if not self.support:
            return False
        l, top, r, g = self.work()
        n = 2 + int(self.dial("ride_length") * 12)       # longer flights with the ride-length dial
        x, pts = self.x, []
        d = self.dir if random.random() < 0.6 else -self.dir
        for _ in range(n):
            step = random.uniform(260, 620)
            if not (l + 120 < x + d * step < r - 120):
                d = -d
            x = min(max(x + d * step, l + 120), r - 120)
            y = g - random.uniform(160, max(200, min(620, g - top - 180)))
            pts.append((x, y))
        pts.append((min(max(x + d * 200, l + 120), r - 120), g))
        self.path, self.ride = pts, kind
        self.support = None
        self.puff(self.x, self.fy, 8, DUST, 160)
        self.set_state("fly", 10 ** 6)
        return True

    def try_mimic(self):
        opts = []
        for (x0, y0, x1, y1), col in self.vis_icons:
            if y0 - self.mon[1] < FEET * PX + 10:
                continue
            if abs((x0 + x1) / 2 - self.x) < 1100 and y0 - self.fy > -800:
                opts.append(((x0, y0, x1, y1), col))
        if not opts:
            return False
        (x0, y0, x1, y1), col = random.choice(opts)
        self.mimic_color = col
        self.mimic_aspect = max(0.4, min(2.5, (x1 - x0) / max(1, (y1 - y0))))
        plat = {"kind": "vis", "y": y0, "x0": min(x0, (x0 + x1) / 2 - HALF),
                "x1": max(x1, (x0 + x1) / 2 + HALF), "grace": self.clock + 9}
        self.leap_to((x0 + x1) / 2, y0, ("mimic", plat))
        return True

    # ---------- particles ----------
    def puff(self, x, y, n, colors, spread=160, up=(60, 260), size=(0.5, 1.0), life=0.45, grav=0.55):
        for _ in range(n):
            self.particles.append([x + random.uniform(-6, 6), y,
                                   random.uniform(-spread, spread),
                                   -random.uniform(*up), life * random.uniform(0.7, 1.2),
                                   random.choice(colors), random.uniform(*size) * PX, grav])

    def smoke(self, x, y, n):
        """a billowing cloud: big soft particles that drift up and slow down"""
        self.puff(x, y, n, ("#C8C8C8", "#DADADA", "#A8A8A8", "#E8E8E8"), 150, (10, 90),
                  (1.6, 3.2), 1.6, grav=-0.02)

    def wp(self, ux, uy):
        """canvas units -> world pixels"""
        return self.wx + ux * PX, self.wy + uy * PX

    # ====================== landing ======================
    def land_on(self, plat, vx, vy):
        if getattr(self, "trick", None) and random.random() < 0.3:
            self.popups.append(("nice!", self.x, self.fy - 10 * PX, self.clock, GOLD))
        self.trick = None
        self.spin, self.rot = 0, 0.0
        self.support = plat if plat["kind"] != "taskbar" else {"kind": "taskbar", "mon": plat["mon"]}
        self.fy = plat["y"]
        if plat["kind"] == "taskbar":
            self.mon = plat["mon"]
        self.puff(self.x, self.fy, 6 if vy < 900 else 12, DUST, 200)
        if vy > 1500 and self.plan is None:
            self.support = None
            self.vx, self.vy = vx * 0.6, -vy * 0.42
            self.set_state("air")
            return
        if self.after_land == "ko":
            self.after_land = None
            self.vx = 0.0
            self.puff(self.x, self.fy, 10, DUST, 220)
            return self.set_state("ko", 3.4)
        if self.after_land == "pogo":                 # lands still on the pogo stick: keep bouncing
            self.after_land = None
            self.vx = 0.0
            left = getattr(self, "pogo_left", 0)
            if left > 0.8:
                self.on_pogo = False
                return self.set_state("pogo", left)
        if self.after_land in ("flee", "happy", "dizzy"):
            what, self.after_land = self.after_land, None
            self.vx = 0.0
            if what == "flee":
                self.dir = 1 if self.x > self.cursor[0] else -1
                return self.set_state("flee", 4.0)
            return self.set_state(what, 2.4)
        if self.after_land == "jumparound":
            self.vx = 0.0
            if self.hops_left > 0:
                return self.next_hop()
            self.after_land = None
        travelled = self.plan == "travel"
        if self.plan in ("travel", "emerge"):
            self.plan = None
        if abs(vx) > 140 or travelled:                      # slides to a stop more often now
            self.vx = vx if abs(vx) > 140 else self.dir * 420
            if abs(self.vx) < 320 and self.enabled("slides"):
                self.vx = (1 if self.vx > 0 else -1) * 320
            self.dir = 1 if self.vx > 0 else -1
            self.set_state("skid")
        else:
            self.vx = 0.0
            self.set_state("land", 0.18)

    def surface(self):
        sp = self.support
        if sp is None:
            return None
        if sp["kind"] == "taskbar":
            w = self.work(sp["mon"])
            return w[3], w[0], w[2]
        if sp["kind"] in ("box", "vis"):
            return sp["y"], sp["x0"], sp["x1"]
        h = sp["hwnd"]
        r = frame_rect(h) if alive(h) else None
        if not r:
            return None
        dx = r[0] - sp["left"]
        if dx:
            self.x += dx
            sp["left"] = r[0]
        return r[1], r[0] + sp["off0"], r[0] + sp["off1"]

    def find_landing(self, prev, new):
        best = None
        for p in self.all_platforms():
            if prev <= p["y"] + 1 and new >= p["y"] and p["x0"] - 4 <= self.x <= p["x1"] + 4:
                if best is None or p["y"] < best["y"]:
                    best = p
        if best is None:
            g = self.work(self.monitor_at(self.x))[3]
            if new > g + 4:
                best = {"kind": "taskbar", "mon": self.monitor_at(self.x), "y": g}
        return best

    # ====================== main loop ======================
    def tick(self):
        now = time.perf_counter()
        dt = min(now - self.last, 0.05)
        self.last = now
        self.clock += dt
        self.st += dt
        try:
            self.track_input()
            self.portal.update(dt)
            if self.state != "hidden":
                self.update(dt)
                self.update_particles(dt)
                self.wx = int(round(self.x - CX * PX))
                self.wy = int(round(self.fy - FEET * PX - self.lift()))
                self.root.geometry(f"{W}x{H}+{self.wx}+{self.wy}")
                self.draw(self.wx, self.wy)
        except Exception:
            import traceback
            traceback.print_exc()
            self.support = {"kind": "taskbar", "mon": self.mon}
            self.fy = self.work()[3]
            self.plan, self.hclip, self.invisible = None, None, False
            self.set_state("watch", 2.0)
        spent = (time.perf_counter() - now) * 1000
        self.root.after(max(1, int(1000 / FPS - spent)), self.tick)

    def track_input(self):
        """What are you doing? (idle / moving the mouse / typing) - runs even while hidden."""
        cur = cursor_pos()
        self.cur_move = math.hypot(cur[0] - self.prev_cur[0], cur[1] - self.prev_cur[1])
        tick = last_input_tick()
        buttons = osl.mouse_down()
        if buttons and not self.prev_buttons:                 # you clicked near him (not on him)
            dist = math.hypot(cur[0] - self.x, cur[1] - (self.fy - 4 * PX))
            if 5 * PX < dist < 220:
                self.want_startle = True
        self.prev_buttons = buttons
        if osl.backspace_tapped():                            # backspace mashing -> facepalm
            self.bs_presses.append(self.clock)
            if sum(1 for t in self.bs_presses if self.clock - t < 2.5) >= 7:
                self.bs_presses.clear()
                self.queue_react("facepalm", "backspace", 30)
        if osl.capslock_on() and self.clock - self.last_key < 0.5:
            if sum(1 for t in self.keys if self.clock - t < 3) >= 8:   # typing with caps lock on
                self.queue_react("caps", "capslock", 120)
        if tick != self.last_input_all:
            self.last_input_all = tick
            if self.clock - self.user_active > 120:          # you were away for a while
                self.want_welcome = True
            self.user_active = self.clock
            self.inputs.append(self.clock)
            buttons = osl.mouse_down()
            if cur == self.prev_cur and not buttons:          # input without mouse movement = a key
                self.keys.append(self.clock)
                self.key_pulse += 1
                self.last_key = self.clock
                for vk in osl.typing_keys_down():            # which key? (typing uses many)
                    self.keycodes.append((self.clock, vk))
            if self.idle_visited:
                self.idle_visited = False
        self.prev_cur = cur
        self.cursor = cur

    def lift(self):
        s, t = self.state, self.st
        fn = getattr(self, "lift_" + s, None)
        if fn:
            return fn(t) * PX
        if s == "perch" and self.clock - self.typing_t < 0.25:
            return 0.5 * PX
        return 0

    def physics(self, dt):
        prev = self.fy
        self.vy += GRAVITY * dt
        self.vx *= (1 - 0.15 * dt)
        self.x += self.vx * dt
        self.fy += self.vy * dt
        if self.spin:
            self.rot = self.spin * 360 * min(self.st / self.spin_T, 1.0)
        lo, hi = self.bounds()
        self.mon = self.monitor_at(self.x)
        if self.x < lo + HALF or self.x > hi - HALF:
            side = -1 if self.x < lo + HALF else 1
            self.x = lo + HALF if side < 0 else hi - HALF
            if abs(self.vx) > 500 and self.plan is None and not self.spin:
                self.dir = side
                self.vx, self.vy = 0.0, min(self.vy, 60.0)
                self.set_state("wall", random.uniform(0.6, 1.1))
                return
            self.vx = -self.vx * 0.5
        top = self.mon[1]
        if self.fy - 9 * PX < top and self.vy < 0:
            self.fy = top + 9 * PX
            self.vy = -self.vy * 0.3
        if self.vy > 0:
            best = self.find_landing(prev, self.fy)
            if best:
                self.land_on(dict(best), self.vx, self.vy)

    def update(self, dt):
        s = self.state
        self.next_blink -= dt
        if self.next_blink <= 0:
            self.blink, self.next_blink = 0.12, random.uniform(2, 6)
        self.blink = max(0.0, self.blink - dt)

        cur = self.cursor
        if self.user_active == self.clock and self.idle_visited is False and s == "waitcursor":
            self.set_state("wave", 1.5)
            s = "wave"

        if s == "drag":
            return

        if s == "cursorhang":                              # holding on to your cursor!
            px_, py_ = self.grab_prev
            moved = math.hypot(cur[0] - px_, cur[1] - py_)
            self.grab_prev = cur
            if moved > 28 or self.st >= self.dur or self.monitor_at(cur[0]) != self.mon:
                self.vx = max(-1500, min(1500, (cur[0] - px_) * 40))
                self.vy = max(-1200, min(800, (cur[1] - py_) * 40))
                self.support = None
                return self.set_state("air")
            self.x, self.fy = cur[0], cur[1] + 10.4 * PX
            return

        if s == "crouch":
            if self.st >= self.dur:
                self.support = None
                self.vx, self.vy = self.launch
                self.puff(self.x, self.fy, 5, DUST, 120)
                spin = self.spin_next
                self.set_state("leapto" if self.leap else "air")
                if spin:
                    self.spin = spin
                    self.spin_T = max(2 * -self.vy / GRAVITY * 0.9, 0.3)
                if self.leap:
                    self.leap = (self.x, self.fy) + self.leap[2:]
                    self.spin_T = self.leap[4] * 0.95
            return

        if s == "leapto":
            x0, y0, vx, vy, T, then = self.leap
            t = min(self.st, T)
            self.x = x0 + vx * t
            self.fy = y0 + vy * t + 0.5 * GRAVITY * t * t
            self.vx, self.vy = vx, vy + GRAVITY * t
            self.mon = self.monitor_at(self.x)
            if self.spin:
                self.rot = self.spin * 360 * min(self.st / self.spin_T, 1.0)
            if self.st >= T:
                kind, data = then
                self.leap = None
                if kind == "land":
                    self.land_on(data, self.vx * 0.3, self.vy)
                elif kind == "perch":
                    self.support = data
                    self.box_lost = 0.0
                    self.puff(self.x, self.fy, 6, DUST, 150)
                    self.set_state("perch", 40)
                elif kind == "point":
                    self.support = data
                    self.dir = self.point_dir
                    self.puff(self.x, self.fy, 6, DUST, 150)
                    self.set_state("pointing", random.uniform(3.5, 5.5))
                elif kind == "climb" or kind == "wallclimb":
                    self.wc_phase, self.wc_t = "cling", 0.0
                    self.set_state("wallclimb")
                elif kind == "lhang":
                    self.support = None
                    self.hang_x = self.x
                    self.set_state("lhang", random.uniform(3, 6))
                elif kind == "mimic":
                    self.support = data
                    self.puff(self.x, self.fy, 6, DUST, 150)
                    self.set_state("mimic", 5.0)
                elif kind == "cursorhang":
                    self.support = None
                    self.grab_prev = cursor_pos()
                    self.set_state("cursorhang", random.uniform(4, 7))
                elif kind in ("tag", "highfive"):
                    self.leap_pose = None
                    word = "tag!" if kind == "tag" else "clap!"
                    self.popups.append((word, self.x, self.fy - 11 * PX, self.clock, GOLD))
                    self.puff(self.x, self.fy - 10 * PX, 6, (GOLD, "#FFFFFF"), 160, (60, 200))
                    self.support = None
                    self.vx, self.vy = -self.dir * 200, 100
                    self.after_land = "flee" if kind == "tag" else "happy"
                    self.set_state("air")
                elif kind == "bonk":                       # missed! bounce off and get knocked out
                    self.leap_pose = None
                    self.bonk_t = self.clock
                    self.bonk_at = (self.x, self.fy - 8 * PX)
                    self.support = None
                    self.vx, self.vy = -self.dir * 260, 150
                    self.after_land = "ko"
                    self.set_state("air")
                elif kind == "hang":
                    self.support = None
                    self.dir = 1
                    self.set_state("hang", random.uniform(4, 8))
            return

        if s == "air":
            self.physics(dt)
            return

        if s == "chute":                                   # floats all the way down to the taskbar
            self.fy += 95 * dt
            self.x += math.sin(self.st * 1.3) * 40 * dt
            self.mon = self.monitor_at(self.x)
            g = self.work()[3]
            if self.fy >= g:
                self.land_on({"kind": "taskbar", "mon": self.mon, "y": g}, 0, 200)
            return

        if s == "hang":
            self.x = self.hang["x"]
            self.fy += 14 * dt
            if self.st >= self.dur:
                self.fall()
            return

        if s == "wall":
            self.vy = min(self.vy + 600 * dt, 180)
            self.fy += self.vy * dt
            self.dust_timer -= dt
            if self.dust_timer <= 0:
                self.dust_timer = 0.06
                self.puff(self.x + self.dir * HALF * 0.8, self.fy - 4 * PX, 1, DUST, 30, (0, 40))
            g = self.work(self.monitor_at(self.x))[3]
            if self.fy >= g:
                self.land_on({"kind": "taskbar", "mon": self.monitor_at(self.x), "y": g}, 0, 100)
            elif self.st >= self.dur:
                self.dir = -self.dir
                self.start_jump(self.dir * 420, -820)
            return

        if s == "climb":
            c = self.climb
            h = c["hwnd"]
            r = frame_rect(h) if alive(h) else None
            if not r:
                return self.fall()
            self.x = r[0] + c["off"]
            self.dir = -c["side"]
            self.fy -= 130 * dt
            if self.fy <= r[1] + 2 * PX:
                inside = -c["side"]
                plats = [p for p in self.platforms if p["hwnd"] == h]
                wall = r[0] if c["side"] < 0 else r[2]
                tx = wall + inside * (HALF + 4 * PX)
                plat = next((p for p in plats if p["x0"] + HALF <= tx <= p["x1"] - HALF), None)
                if plat:
                    self.leap_to(tx, plat["y"], ("land", dict(plat)), T=0.38)
                else:
                    self.support = None
                    self.vx, self.vy = inside * 150, -450
                    self.set_state("air")
            return

        if s == "toedge":                                  # run to the screen edge ...
            l, _, r, g = self.work()
            self.fy = g
            self.x += self.dir * 330 * dt
            self.run_dust(dt)
            edge = l if self.dir < 0 else r
            if abs(self.x - edge) <= 7 * PX:
                mon = self.mon
                after = getattr(self, "edge_after", "offscreen")
                top = (lambda m=mon: m[1] - 2 * PX) if after == "offscreen" else \
                    (lambda m=mon: m[1] + 10.4 * PX)
                self.wc = {"wall": (lambda e=edge: e), "top": top,
                           "side": self.dir, "after": after, "hwnd": None}
                self.support = None                         # ... jump onto it ...
                self.wc_phase, self.wc_t = "hop", 0.0
                self.vy = -700
                self.set_state("wallclimb")
            return

        if s == "wallclimb":                               # platformer style: slide, hop, slide...
            wall = self.wc["wall"]()
            top = self.wc["top"]()
            if wall is None or top is None:
                return self.fall()
            side = self.wc["side"]
            base_x = wall - side * 5.4 * PX
            self.wc_t += dt
            if self.wc_phase == "cling":
                self.x = base_x
                self.fy += 75 * dt                          # slides down the wall
                self.dust_timer -= dt
                if self.dust_timer <= 0:
                    self.dust_timer = 0.05
                    self.puff(wall - side * PX, self.fy - 5 * PX, 1, DUST, 25, (0, 40), (0.4, 0.7), 0.3)
                if self.wc_t > 0.32:
                    self.wc_phase, self.wc_t, self.vy = "hop", 0.0, -700.0
                    self.puff(wall - side * PX, self.fy - 2 * PX, 3, DUST, 60, (20, 80))
            else:
                self.vy += GRAVITY * dt
                self.fy += self.vy * dt
                away = math.sin(math.pi * min(self.wc_t / 0.3, 1.0)) * 14
                self.x = base_x - side * away
                if self.vy > 0 and self.wc_t > 0.18:
                    self.wc_phase, self.wc_t = "cling", 0.0
            g = self.work(self.monitor_at(self.x))[3]
            if self.fy > g:
                self.fy = g
            if self.wc["after"] == "ceiling" and self.fy <= top + 2 * PX:   # grab the top of the screen
                self.fy = top
                self.x = wall - side * 7 * PX
                l, _, r, _ = self.work()
                self.ceil_x = random.uniform(l + 200, r - 200)
                self.dir = 1 if self.ceil_x > self.x else -1
                return self.set_state("ceiling", random.uniform(7, 12))
            if self.fy <= top + 2 * PX:                     # made it to the top
                if self.wc["after"] == "offscreen":
                    self.invisible = True
                    self.set_state("offscreen", random.uniform(0.8, 2.0))
                else:
                    inside = side
                    tx = wall + inside * (HALF + 4 * PX)
                    plat = next((p for p in self.platforms if p["hwnd"] == self.wc["hwnd"]
                                 and p["x0"] + HALF <= tx <= p["x1"] - HALF), None)
                    if plat:
                        self.leap_to(tx, plat["y"], ("land", dict(plat)), T=0.38)
                    else:
                        self.support = None
                        self.vx, self.vy = inside * 150, -450
                        self.set_state("air")
            return

        if s == "ceiling":                                 # monkey-bars along the top of the screen
            self.fy = self.mon[1] + 10.4 * PX
            moving = abs(self.ceil_x - self.x) > 10
            if moving and int(self.st / 0.3) % 2 == 0:
                self.x += self.dir * 110 * dt
            if not moving and self.st < self.dur - 1.5:
                l, _, r, _ = self.work()
                self.ceil_x = random.uniform(l + 200, r - 200)
                self.dir = 1 if self.ceil_x > self.x else -1
            if self.st >= self.dur:
                if random.random() < 0.5:
                    self.start_jump(self.dir * 120, 0, spin=random.choice([1, -1]))
                else:
                    self.fall()
            return

        if s == "tbhang":                                  # hanging off the taskbar's top edge
            g = self.work()[3]
            if self.st < self.dur - 0.5:
                self.fy = g + 10.4 * PX
            else:                                          # pull back up
                k = (self.st - (self.dur - 0.5)) / 0.5
                self.fy = g + 10.4 * PX * (1 - min(k, 1))
                if k >= 1:
                    self.land_on({"kind": "taskbar", "mon": self.mon, "y": g}, 0, 100)
            return

        if s == "lhang":                                   # hanging off a box edge
            p = self.ledge
            self.x = self.hang_x
            if self.st < self.dur - 0.5:
                self.fy = p["y"] + 10.4 * PX
            elif p["x1"] - p["x0"] >= 2 * HALF:            # room on top: pull up onto it
                k = (self.st - (self.dur - 0.5)) / 0.5
                self.fy = p["y"] + 10.4 * PX * (1 - min(k, 1))
                if k >= 1:
                    self.x = min(max(self.x, p["x0"] + HALF), p["x1"] - HALF)
                    self.land_on(dict(p), 0, 100)
            else:                                          # no room: let go and drop
                self.fall()
            return

        if s == "offscreen":                               # ... and parachute back in
            if self.st >= self.dur:
                free = [m for m, _ in self.monitors if m not in self.busy] or [self.mon]
                self.parachute_in(self.mon if self.mon in free else free[0])
            return

        if s == "fly":                                     # golden cloud / jetpack ride
            if not self.path:
                return self.fall()
            tx, ty = self.path[0]
            speed = 240 if self.ride == "cloud" else 380
            dx, dy = tx - self.x, ty - self.fy
            dist = math.hypot(dx, dy)
            if abs(dx) > 4:
                self.dir = 1 if dx > 0 else -1
            if dist <= speed * dt:
                self.x, self.fy = tx, ty
                self.path.pop(0)
                if not self.path:                          # touched down
                    mon = self.monitor_at(self.x)
                    g = self.work(mon)[3]
                    self.puff(self.x, g, 10, DUST, 200)
                    return self.land_on({"kind": "taskbar", "mon": mon, "y": g}, 0, 100)
            else:
                self.x += dx / dist * speed * dt
                self.fy += dy / dist * speed * dt
            self.fy += math.sin(self.st * 3) * 12 * dt
            self.mon = self.monitor_at(self.x)
            if self.ride == "jetpack":
                self.dust_timer -= dt
                if self.dust_timer <= 0:
                    self.dust_timer = 0.03
                    jx = self.x - self.dir * 5.2 * PX
                    self.puff(jx, self.fy - 2 * PX, 2, ("#FF8C1A", GOLD, "#BBBBBB"), 40, (-260, -120),
                              (0.4, 0.8), 0.35)
            return

        if s == "pgun":                                    # aim the portal gun, fire twice
            if self.st > 0.8 and self.pg is None:
                l, _, r, g0 = self.work()
                if not (l + 140 < self.x + self.dir * 100 < r - 140):
                    self.dir = -self.dir
                ax = self.x + self.dir * 100
                others = [m for m, _ in self.monitors if m != self.mon and m not in self.busy]
                if others and random.random() < 0.6:
                    bmon = random.choice(others)
                else:
                    bmon = self.mon
                bl, _, br, bg = self.work(bmon)
                bx = random.uniform(bl + 200, br - 200)
                if bmon == self.mon and abs(bx - self.x) < 400:
                    bx = l + 220 if self.x > (l + r) / 2 else r - 220
                self.pg = {"ax": ax, "ay": self.fy, "bx": bx, "by": bg, "bmon": bmon}
                self.portal.open_at(ax, self.fy)
                self.portal2.open_at(bx, bg)
            if self.st > 1.4:
                self.set_state("pg_in", 10 ** 6)
            return

        if s == "pg_in":
            self.x += self.dir * 260 * dt
            self.hclip = (self.pg["ax"], self.dir)
            if (self.x - self.dir * HALF - self.pg["ax"]) * self.dir > 0:
                self.portal.close()
                self.invisible = True
                self.set_state("pg_gap", 0.3)
            return

        if s == "pg_gap":
            if self.st >= self.dur:
                pg = self.pg
                self.mon = pg["bmon"]
                self.support = {"kind": "taskbar", "mon": pg["bmon"]}
                self.fy = pg["by"]
                self.x = pg["bx"] - self.dir * HALF * 1.2
                self.hclip = (pg["bx"], -self.dir)
                self.invisible = False
                self.set_state("pg_out", 10 ** 6)
            return

        if s == "pg_out":
            self.x += self.dir * 260 * dt
            if (self.x - self.dir * HALF - self.pg["bx"]) * self.dir > 10:
                self.hclip = None
                self.portal2.close()
                self.pg = None
                self.set_state("land", 0.2)
            return

        if s == "smoke":                                   # ninja smoke bomb teleport
            # 0.5 s: bomb hits the floor -> smoke billows up around him for a moment...
            if 0.5 <= self.st < 1.0:
                self.dust_timer -= dt
                if self.dust_timer <= 0:
                    self.dust_timer = 0.04
                    self.smoke(self.x + random.uniform(-4, 4) * PX, self.fy - random.uniform(0, 6) * PX, 4)
            if self.st >= 0.5 and self.once("poof1"):
                self.smoke(self.x, self.fy - 2 * PX, 18)
                self.popups.append(("poof!", self.x, self.fy - 10 * PX, self.clock, "#FFFFFF"))
            if self.st >= 0.85 and self.once("vanish"):    # ...then he vanishes inside it
                self.invisible = True
            if self.st >= 1.9 and self.once("arrive"):     # smoke appears where he's going first
                others = [m for m, _ in self.monitors if m != self.mon and m not in self.busy]
                mon = random.choice(others) if others and random.random() < 0.6 else self.mon
                l, _, r, g = self.work(mon)
                self.mon = mon
                self.x = random.uniform(l + 150, r - 150)
                self.fy = g
                self.support = {"kind": "taskbar", "mon": mon}
                self.smoke(self.x, g - 2 * PX, 26)
                self.popups.append(("poof!", self.x, g - 10 * PX, self.clock, "#FFFFFF"))
            if self.st >= 2.25:                            # steps out of the smoke
                self.invisible = False
                self.set_state("land", 0.4)
            return

        if s == "runoff":                                  # fullscreen on the only screen
            l, _, r, g = self.work()
            self.fy = g
            self.x += self.dir * 520 * dt
            self.run_dust(dt)
            if self.x < l - 2 * HALF or self.x > r + 2 * HALF:
                self.plan = None
                self.set_state("hidden")
                self.particles.clear()
                self.root.withdraw()
            return

        if s == "dig":
            g = self.work()[3]
            depth = min(self.st / 1.1, 1.0) * 8.6 * PX
            self.fy = g + depth
            self.dust_timer -= dt
            if self.dust_timer <= 0 and self.st < 1.1:
                self.dust_timer = 0.05
                self.puff(self.x, g, 2, DIRT, 220, (250, 520), (0.5, 0.9), 0.6)
            if self.st >= 1.4:
                if self.plan == "hide" or self.target is None:
                    self.plan = None
                    self.set_state("hidden")
                    self.particles.clear()
                    self.root.withdraw()
                elif self.target == self.mon and self.plan == "dig":
                    if random.random() < 0.5:
                        self.parachute_in(self.mon)
                    else:
                        l, _, r, _ = self.work()
                        self.emerge(self.mon, random.uniform(l + 150, r - 150))
                else:
                    if random.random() < 0.25:
                        self.parachute_in(self.target)
                    else:
                        self.emerge(self.target)
            return

        if s == "peek":
            g = self.work()[3]
            hidden, eyes = g + 8.5 * PX, g + (8 - 2.6) * PX
            if self.st < 0.5:
                self.fy = hidden + (eyes - hidden) * (self.st / 0.5) ** 0.6
            elif self.st >= 2.2:
                self.puff(self.x, g, 14, DIRT, 240, (250, 560), (0.5, 0.9), 0.6)
                self.vx, self.vy = self.dir * 140, -900
                self.support = None
                self.set_state("air")
            return

        if s == "leave":
            l, _, r, g = self.work()
            self.fy = g
            self.x += self.dir * (560 if self.fast else 430) * dt
            self.run_dust(dt)
            edge = r if self.dir > 0 else l
            if abs(edge - self.x) < HALF + 30:
                self.start_jump(self.dir * 560, -760)
            return

        if s == "portal_in":
            l, _, r, g = self.work()
            self.fy = g
            self.x += self.dir * 430 * dt
            self.run_dust(dt)
            if not self.portal_open and abs(self.portal_x - self.x) < 220:
                self.portal.open_at(self.portal_x, g)
                self.portal_open = True
            if self.portal_open:
                self.hclip = (self.portal_x, self.dir)
            if (self.x - self.dir * HALF - self.portal_x) * self.dir > 0:
                self.portal.close()
                self.invisible = True
                self.set_state("portal_gap", 0.45)
            return

        if s == "portal_gap":
            if self.st >= self.dur:
                tgt = self.target or self.mon
                self.mon = tgt
                self.support = {"kind": "taskbar", "mon": tgt}
                l, _, r, g = self.work()
                self.exit_x = (r if self.dir < 0 else l) + self.dir * 5 * PX
                self.portal.open_at(self.exit_x, g)
                self.x = self.exit_x - self.dir * HALF * 1.2
                self.fy = g
                self.hclip = (self.exit_x, -self.dir)
                self.invisible = False
                self.set_state("portal_out")
            return

        if s == "portal_out":
            if self.st < 0.3:
                return
            self.x += self.dir * 430 * dt
            self.run_dust(dt)
            if (self.x - self.dir * HALF - self.exit_x) * self.dir > 10:
                self.hclip = None
                self.portal.close()
                self.plan = None
                self.set_state("run", 0.8)
            return

        # ---------------- standing on something ----------------
        geo = self.surface()
        if geo is None:
            return self.fall()
        y, x0, x1 = geo
        self.fy = y
        if self.support["kind"] == "taskbar":
            self.mon = self.support["mon"]

        # reactions to you: petting, clicks, coming back, fast mouse, typing, idle
        if s in BASE and self.plan is None:
            if self.pending_react:
                kind, tx = self.pending_react
                self.pending_react = None
                self.react_kind = kind
                if tx is not None and abs(tx - self.x) > 20:
                    self.dir = 1 if tx > self.x else -1
                return self.set_state("react", 3.2)
            if getattr(self, "want_welcome", False):
                self.want_welcome = False
                if self.enabled("welcomeback"):
                    return self.set_state("welcome", 3.0)
            if getattr(self, "want_startle", False):
                self.want_startle = False
                if self.enabled("clickstartle"):
                    return self.set_state("startle", 1.1)
            over = abs(cur[0] - self.x) < 5 * PX and self.fy - 9 * PX < cur[1] < self.fy
            self.hover_t = self.hover_t + dt if over else 0.0
            if self.hover_t > 0.8 and self.enabled("hoverpet"):
                self.hover_t = 0.0
                return self.set_state("petted", 3.5)
            if (self.cur_move > 55 and self.enabled("fastmouse")
                    and math.hypot(cur[0] - self.x, cur[1] - (self.fy - 4 * PX)) < 160):
                away = 1 if self.x > cur[0] else -1
                self.popups.append(("whoa!", self.x, self.fy - 11 * PX, self.clock, "#FFFFFF"))
                self.support = None
                self.vx, self.vy = away * 520, -560
                self.after_land = "dizzy"
                return self.set_state("air")
            if self.really_typing() and self.enabled("typealong"):
                return self.set_state("typealong", 10 ** 6)
            if (self.clock - self.user_active > 15 and not self.idle_visited and self.enabled("idlevisit")
                    and self.monitor_at(cur[0]) == self.mon):
                self.idle_visited = True
                self.visit_then = "wait"
                return self.set_state("visit", 12)

        if s in ("skid", "slide"):
            sign = 1 if self.vx > 0 else -1
            self.vx -= sign * (1500 if s == "skid" else 650) * dt
            if self.vx * sign <= 30:
                self.vx = 0.0
                self.set_state("land", 0.15)
            self.x += self.vx * dt
            self.dust_timer -= dt
            if self.dust_timer <= 0:
                self.dust_timer = 0.03
                self.puff(self.x + sign * 2 * PX, self.fy, 1, DUST, 80, (40, 160), (0.5, 1.0), 0.35)
        elif s == "land":
            if self.st >= self.dur:
                self.pick_next()
            return
        elif s == "perch":
            tick = last_input_tick()
            if tick != self.last_input:
                self.last_input = tick
                self.typing_t = self.clock
            if self.st >= self.dur:
                self.hop_down()
            return
        else:
            if s == "toclock":
                if abs(self.x - self.clock_x) < 12:
                    self.dir = 1
                    return self.set_state("clockpoint", 7.0)
                self.dir = 1 if self.clock_x > self.x else -1
            if s == "chase":
                cx, cy = self.cursor
                if abs(cx - self.x) > 30:
                    self.dir = 1 if cx > self.x else -1
                if abs(cx - self.x) < 260 and self.fy - 600 < cy < self.fy - 60 and self.st > 0.6:
                    self.support = None                     # leap at the cursor!
                    dx, dy = cx - self.x, cy + 4 * PX - self.fy
                    T = max(0.35, math.sqrt(2 * max(0.0, -dy) / GRAVITY))
                    self.start_jump(dx / T, (dy - 0.5 * GRAVITY * T * T) / T)
                    return
            if s == "runin" and self.st < 0.2:
                self.invisible = False
            if s == "pogo" and self.st > 1.2 and random.random() < dt * 0.55:
                left = self.dur - self.st                # big pogo bounce onto something nearby
                if left > 2.0 and self.try_explore(near=True):
                    self.on_pogo, self.pogo_left, self.after_land = True, left, "pogo"
                    return
            lo_b, hi_b = x0 + HALF, x1 - HALF
            if s == "visit":
                tx = min(max(cur[0], lo_b), hi_b)
                self.dir = 1 if tx > self.x else -1
                if abs(tx - self.x) < 30 or self.st >= self.dur:
                    return self.at_cursor(self.visit_then)
            elif s == "slidein":
                if self.slide_phase == "back":
                    self.dir = -1 if self.slide_target > self.x else 1
                    far = abs(self.slide_target - self.x) > 260
                    stuck = self.x <= lo_b + 2 or self.x >= hi_b - 2
                    if far or stuck or self.st > 1.4:
                        self.slide_phase = "go"
                        self.dir = 1 if self.slide_target > self.x else -1
                elif abs(self.slide_target - self.x) < 170:
                    self.vx = self.dir * 720                 # baseball slide under the cursor
                    return self.set_state("slide")
            elif s in ("waitcursor", "reach", "ko"):
                if abs(cur[0] - self.x) > 25:
                    self.dir = 1 if cur[0] > self.x else -1
            elif s == "propose":
                if self.st < 2 and abs(cur[0] - self.x) > 25:
                    self.dir = 1 if cur[0] > self.x else -1
                if 2.0 < self.st < 5.0:                       # did you answer (move the mouse)?
                    self.propose_moved += self.cur_move
                elif self.st >= 5.0 and self.propose_yes is None:
                    self.propose_yes = self.propose_moved > 25
            elif s == "typealong":
                if self.clock - self.last_key > 2.5 or self.gaming or self.fg_fullscreen:
                    return self.pick_next()
            elif s == "flee":
                self.dir = 1 if self.x > cur[0] else -1
            elif s == "throwball" and self.st >= 1.8:
                self.popups.append(("BONK!", self.x, self.fy - 10 * PX, self.clock, GOLD))
                return self.set_state("ko", 2.6)
            elif s == "hiding" and self.st > 1.5:
                near = abs(cur[0] - self.x) < 150 and abs(cur[1] - self.fy) < 350
                if near or self.st >= self.dur:
                    self.found_you = near
                    return self.set_state("found", 2.4)
            speed = self.ground_speed(s, self.st)
            self.x += self.dir * speed * dt
            if abs(speed) > 220:
                self.run_dust(dt)
            # every so often a run / walk turns into a slide
            if s in ("run", "walk", "lurk", "flee", "chase") and speed > 0 and self.enabled("slides"):
                chance = {"run": 0.55, "flee": 0.4, "chase": 0.25, "walk": 0.1, "lurk": 0.05}[s]
                forced = s == "run" and getattr(self, "force_slide", False) and self.st > 0.7
                if forced or (self.st > 0.5 and random.random() < chance * dt * (0.05 + 1.6 * self.dial("energy"))):
                    self.force_slide = False
                    edge = x1 - self.x if self.dir > 0 else self.x - x0
                    if edge > 200:                              # room to slide
                        self.vx = self.dir * random.uniform(560, 760)
                        return self.set_state("slide")
            hook = getattr(self, "upd_" + s, None)
            if hook:
                hook(dt, self.st)
                if self.state != s or self.support is None:   # the animation moved him on
                    return
            if s == "watch" and abs(self.cursor[0] - self.x) > 40:
                self.dir = 1 if self.cursor[0] > self.x else -1

        lo_x, hi_x = x0 + HALF * 0.7, x1 - HALF * 0.7
        if self.support["kind"] == "taskbar":
            lo_x, hi_x = x0 + HALF, x1 - HALF
        if self.x < lo_x or self.x > hi_x:
            going_out = (self.x < lo_x and self.dir < 0) or (self.x > hi_x and self.dir > 0) \
                or (s == "skid")
            if self.support["kind"] != "taskbar" and going_out and s in ("walk", "run", "lurk", "skid", "skate", "pogo"):
                if s == "pogo":                          # bounces right off the edge and keeps going
                    self.edge_choice = True
                    self.on_pogo, self.pogo_left, self.after_land = True, self.dur - self.st, "pogo"
                if self.edge_choice is None:                  # up-top lovers rarely walk off
                    self.edge_choice = random.random() < 0.35 - 0.3 * self.dial("home") or s == "skid"
                if self.edge_choice:
                    self.support = None
                    self.vx = self.dir * max(abs(self.vx), abs(self.ground_speed(s, self.st)), 140)
                    self.vy = -120.0
                    self.set_state("air")
                    return
            self.x = min(max(self.x, lo_x), hi_x)
            if s == "skid":
                self.vx = 0.0
            elif going_out:
                self.dir = -self.dir
                self.edge_choice = None

        if s != "skid" and self.st >= self.dur:
            if s == "slingshot":
                self.support = None
                self.vx, self.vy = self.dir * 820, -980
                self.puff(self.x, self.fy, 10, DUST, 200)
                self.set_state("air")
                return
            self.pick_next()

    def ground_speed(self, s, t):
        if s == "walk":
            return 95
        if s == "run":
            return 320
        if s == "lurk":                       # calm = short shuffles, long pauses
            return 50 if (t % 3.2) < 1.5 * (0.25 + 0.75 * self.dial("energy")) else 0
        if s == "inspect":
            return 50 if (t % 1.8) < 0.7 else 0
        if s in ("toclock", "runin"):
            return 300
        if s == "visit":
            return 380
        if s == "flee":
            return 340
        if s == "slidein":
            return 300 if self.slide_phase == "back" else 420
        if s == "reach":
            return 60 if abs(self.cursor[0] - self.x) > 25 else 0
        if s == "chase":
            return 300 if abs(self.cursor[0] - self.x) > 30 else 0
        fn = getattr(self, "speed_" + s, None)
        return fn(t) if fn else 0

    def run_dust(self, dt):
        self.dust_timer -= dt
        if self.dust_timer <= 0:
            self.dust_timer = 0.08
            self.puff(self.x - self.dir * 3 * PX, self.fy, 1, DUST, 40, (30, 110), (0.6, 1.1), 0.35)

    def update_particles(self, dt):
        keep = []
        for p in self.particles:
            p[4] -= dt
            if p[4] <= 0:
                continue
            g_ = p[7] if len(p) > 7 else 0.55
            p[3] += GRAVITY * g_ * dt
            if g_ < 0.1:                                   # smoke: slows down and hangs in the air
                p[2] *= (1 - 2.5 * dt)
                p[3] *= (1 - 2.0 * dt)
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            keep.append(p)
        self.particles = keep[-100:]

    def keep_on_top(self):
        if self.state != "hidden":
            osl.raise_top(self.root)
        self.root.after(3000, self.keep_on_top)

    # ====================== mouse ======================
    def on_press(self, e):
        if self.state in ("hidden", "portal_gap", "offscreen"):
            return
        self.drag = (e.x_root, e.y_root, self.x, self.fy, False)
        self.samples.clear()
        self.samples.append((time.perf_counter(), e.x_root, e.y_root))

    def on_drag(self, e):
        if not self.drag:
            return
        sx, sy, ox, oy, moved = self.drag
        self.samples.append((time.perf_counter(), e.x_root, e.y_root))
        if not moved and abs(e.x_root - sx) + abs(e.y_root - sy) > 4:
            moved = True
            self.drag = (sx, sy, ox, oy, True)
            self.plan, self.target, self.leap, self.hclip = None, None, None, None
            self.invisible = False
            self.portal.close()
            self.support = None
            self.set_state("drag")
        if moved:
            lo, hi = self.bounds()
            self.x = min(max(ox + e.x_root - sx, lo + HALF), hi - HALF)
            self.mon = self.monitor_at(self.x)
            self.fy = min(oy + e.y_root - sy, self.work()[3])

    def on_release(self, e):
        if not self.drag:
            return
        moved = self.drag[4]
        self.drag = None
        if moved:
            now = time.perf_counter()
            pts = [p for p in self.samples if now - p[0] < 0.1] or list(self.samples)
            vx = vy = 0.0
            if len(pts) >= 2 and pts[-1][0] > pts[0][0]:
                dtm = pts[-1][0] - pts[0][0]
                vx = (pts[-1][1] - pts[0][1]) / dtm
                vy = (pts[-1][2] - pts[0][2]) / dtm
            cap = 4000.0
            self.vx = max(-cap, min(cap, vx))
            self.vy = max(-cap, min(cap, vy))
            if abs(self.vx) > 60:
                self.dir = 1 if self.vx > 0 else -1
            self.set_state("air")
        elif self.on_ground() or self.state == "perch":
            self.start_jump(self.dir * 150, -900)

    def menu(self, e):
        m = tk.Menu(self.root, tearoff=0)

        def run(name):
            if self.on_ground():
                self.do_special(name)

        for group, names in ACT_GROUPS.items():
            sub = tk.Menu(m, tearoff=0)
            for n in names:
                sub.add_command(label=n.capitalize(), command=lambda nn=n: run(nn))
            m.add_cascade(label=group, menu=sub)
        mv = tk.Menu(m, tearoff=0)
        for n, label in (("jump", "Jump"), ("flip", "Flip"), ("explore", "Jump onto something"),
                         ("point", "Point at a picture"), ("hang", "Hang on the scrollbar"),
                         ("climb", "Climb a window"), ("parachute", "Climb out + parachute"),
                         ("dig", "Dig + pop up"), ("portal", "Portal"), ("slingshot", "Slingshot")):
            mv.add_command(label=label, command=lambda nn=n: run(nn))
        others = [mm for mm, _ in self.monitors if mm != self.mon]
        if others:
            for label, meth in (("Leap to other screen", "leap"), ("Dig to other screen", "dig"),
                                ("Portal to other screen", "portal")):
                mv.add_command(label=label, command=lambda mt=meth: self.on_ground()
                               and self.support and self.support["kind"] == "taskbar"
                               and self.change_screen(others[0], method=mt))
        m.add_cascade(label="Moves", menu=mv)
        m.add_separator()
        m.add_command(label="Settings...", command=self.open_app)
        m.add_command(label="Quit", command=self.quit)
        m.tk_popup(e.x_root, e.y_root)

    def open_app(self):
        import subprocess
        import pixbot_paths
        subprocess.Popen(pixbot_paths.launch_cmd(settings=True), cwd=pixbot_paths.DATA_DIR,
                         env=pixbot_paths.child_env())


if __name__ == "__main__":
    # only one Pixbot at a time
    if not osl.single_instance("PixbotDesktopPet"):
        sys.exit(0)
    Pixbot().root.mainloop()
