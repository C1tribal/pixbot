"""Pixbot's drawing code and his library of animations.

Every animation <name> can define any of:
    pose_<name>(P, t, d)        tweak the body pose (P is a dict)
    back_<name>(t, d, g)        draw props behind him
    front_<name>(t, d, g)       draw props / costume in front of him
    lift_<name>(t)              hop height in units
    speed_<name>(t)             walking speed in px/s (+ = the way he faces)
    upd_<name>(dt, t)           extra per-frame logic (particles, turning...)
t = seconds since the animation started, d = facing (+1 right / -1 left).
"""
import math
import random

from pixbot_common import *  # noqa: F401,F403
import pixbot_outfits

# animations that bring their own hat / face / outfit, so his clothes step aside
NO_HAT = {"cooking", "guard", "pullups", "bench", "curls", "pushups",
          "jumprope", "boxing", "deadlift", "train", "headphones", "dj", 
          "measure",
          "stretchy", "squish", "dizzyspin", "trip"}
NO_FACE = {"missioncomplete", "peekaboo",
           "dizzyspin", "dizzy", "trip"}
NO_BODY = {"bench", "pushups",
           "measure", "stretchy", "squish", "trip"}


class _Colors:
    body_color = "#7FA3C2"
    dark_color = "#5E7D96"

ACT_GROUPS = {
    "Classic": ["wave", "dance", "think", "code", "build", "juggle", "train", "inspect",
                "happy", "error"],
    "Games": [
              "saucers", 
              "missioncomplete", "slingshot"],
    "Fun": ["yawn", "read", "coffee", "fish", "skate", "guitar", "paint", "bubbles", "soccer",
            "plant", "sneeze", "meditate", "camera", "pizza", "balloon", "raincloud", "broom",
            "telescope", "paperplane", "headphones"],
    "Reactions": ["guard", "popcorn", "listen"],
    "Gym": ["pullups", "bench", "curls", "pushups", "jumprope", "boxing", "deadlift"],
    "Silly": ["measure", "stretchy", "squish", "dizzyspin", "trip", "peekaboo", "moonwalk",
              "hiccups"],
    "Activities": ["rockstar", "cooking", "gaming", "dj", "yoga", "drawing"],
    "Power forms": [
                    "rollball"],
}
ACTS = {   # name: (min seconds, max seconds)
    "wave": (2.5, 2.5), "dance": (7, 7), "think": (3.5, 5), "code": (9, 14),
    "build": (4.5, 6.5), "juggle": (5, 7), "train": (6, 9), "inspect": (6, 10),
    "happy": (2.4, 2.4), "error": (2, 2),
    
    
    "saucers": (7, 7),
    
    "missioncomplete": (7, 7), "slingshot": (2.2, 2.2),
    "yawn": (3.5, 3.5), "read": (8, 8), "coffee": (7, 7), "fish": (10, 10), "skate": (6, 6),
    "guitar": (7, 7), "paint": (9, 9), "bubbles": (6, 6), "soccer": (7, 7), "plant": (9, 9),
    "sneeze": (4, 4), "meditate": (8, 8), "camera": (5, 5), "pizza": (6, 6),
    "balloon": (9, 9), "raincloud": (7, 7), "broom": (7, 7), "telescope": (6, 6),
    "paperplane": (5, 5), "headphones": (8, 8),
    "pullups": (9, 9), "bench": (10, 10), "curls": (8, 8),
    "guard": (14, 14), "popcorn": (25, 25), "listen": (8, 8),
    "pushups": (8, 8), "jumprope": (7, 7), "boxing": (8, 8), "deadlift": (8, 8),
    "dizzyspin": (5, 5), "trip": (5, 5), "peekaboo": (6, 6), "moonwalk": (5, 5),
    "hiccups": (6, 6),
    "rockstar": (9, 9), "cooking": (9, 9), "gaming": (10, 10), "dj": (9, 9),
    "yoga": (9, 9), "drawing": (8, 8),
    "measure": (8, 8), "stretchy": (6, 6), "squish": (5, 5),
    
    
    
}
SYM = "Segoe UI Symbol"


def para(p, h):
    """parabola 0 -> h -> 0 for p in 0..1"""
    return 4 * h * p * (1 - p) if 0 <= p <= 1 else 0.0


def ease(p):
    p = min(max(p, 0.0), 1.0)
    return p * p * (3 - 2 * p)


class Acts(_Colors):
    # ================= drawing primitives (in units) =================
    def rect(self, x, y, w, h, color=None):
        if color is None:
            color = self.body_color
        if self.rot:
            a = math.radians(self.rot)
            c, s = math.cos(a), math.sin(a)
            pts = []
            for px_, py_ in ((x, y), (x + w, y), (x + w, y + h), (x, y + h)):
                dx, dy = px_ - self.pcx, py_ - self.pcy
                pts += [(self.pcx + dx * c - dy * s) * PX, (self.pcy + dx * s + dy * c) * PX]
            self.cv.create_polygon(pts, fill=color, outline="")
            return
        x0, y0 = x * PX, y * PX
        x1, y1 = (x + w) * PX, min((y + h) * PX, self.clip)
        if self.hclip_px is not None:
            hx, side = self.hclip_px
            if side > 0:
                x1 = min(x1, hx)
            else:
                x0 = max(x0, hx)
        x0, y0, x1, y1 = round(x0), round(y0), round(x1), round(y1)
        if y1 <= y0 or x1 <= x0:
            return
        self.cv.create_rectangle(x0, y0, x1, y1, fill=color, outline="")

    R = rect

    def O(self, x, y, w, h, fill="", outline="", width=1):
        if (y + h) * PX > self.clip + 1 and y * PX >= self.clip:
            return
        self.cv.create_oval(x * PX, y * PX, (x + w) * PX, (y + h) * PX,
                            fill=fill, outline=outline, width=width)

    def A(self, x, y, w, h, start, extent, fill, outline=""):
        self.cv.create_arc(x * PX, y * PX, (x + w) * PX, (y + h) * PX, start=start,
                           extent=extent, fill=fill, outline=outline, style="pieslice")

    def Pg(self, pts, fill, outline=""):
        flat = [v * PX for p in pts for v in p]
        self.cv.create_polygon(flat, fill=fill, outline=outline)

    def L(self, pts, color, width=2):
        flat = [v * PX for p in pts for v in p]
        self.cv.create_line(flat, fill=color, width=width)

    def T(self, x, y, s, size, color=ORANGE, font="Consolas"):
        if y * PX >= self.clip:
            return
        scale = getattr(self, "text_scale", 1.0)
        if any(ch.isalnum() for ch in s) and hasattr(self, "words"):
            # words go to a bigger see-through overlay so large text never gets cut off
            self.words.append((x, y, s, max(6, round(size * scale)), color, font))
            return
        size = max(5, round(size * min(scale, 1.6)))
        self.cv.create_text(x * PX, y * PX, text=s, fill=color, font=(font, size, "bold"))

    WORDS_PAD_X, WORDS_PAD_Y = 30, 14                  # overlay margin around his window (units)

    def draw_words(self, wx, wy):
        words = getattr(self, "words", [])
        if not words:
            self.kill_sprite("words")
            return
        px_, py_ = self.WORDS_PAD_X, self.WORDS_PAD_Y
        wu, hu = COLS + 2 * px_, ROWS + py_ + 2
        cx = wx - px_ * PX + wu * PX / 2
        cy = wy - py_ * PX + hu * PX / 2

        def paint(p, words=list(words)):
            for x, y, s, size, color, font in words:
                fx, fy = (x + px_) * PX, (y + py_) * PX
                fy = max(fy, size * 0.9)
                for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):      # dark outline: readable anywhere
                    p.cv.create_text(fx + ox, fy + oy, text=s, fill="#111111", font=(font, size, "bold"))
                p.cv.create_text(fx, fy, text=s, fill=color, font=(font, size, "bold"))
        self.show_sprite("words", wu, hu, cx, cy, paint)

    def text(self, x, y, s, size, color=ORANGE):
        self.T(x, y, s, size, color)

    def M(self, off, w):
        """x of a prop `off` units in front of his centre (negative = behind)."""
        return CX + off if self.dir > 0 else CX - off - w

    # ================= pose =================
    def steps(self, P, t, d, period, stride, lift, bob):
        ph = int(t / period) % 4
        a = [0, 1, 0, -1][ph] * stride * d
        P["leg_dx"] = [a, -a, a, -a]
        b = bob if ph % 2 else 0.0
        P["legs"] = [2 - b] * 4
        if ph == 1:
            P["legs"][0] -= lift; P["legs"][2] -= lift
        elif ph == 3:
            P["legs"][1] -= lift; P["legs"][3] -= lift
        return ph

    def follow_cursor(self, P):
        cx, cy = self.cursor
        if abs(cx - self.x) > 30:
            P["eye_dx"] = 0.34 if cx > self.x else -0.34
        if cy < self.fy - 9 * PX:
            P["eye_dy"] = -0.45 if abs(cx - self.x) < 600 else -0.3
        elif cy > self.fy:
            P["eye_dy"] = 0.35

    def set_arm(self, P, side, y, x=0.0):
        """side +1 = the arm on his facing side, -1 = the back arm.
        x > 0 moves the arm the way he faces."""
        if (side > 0) == (self.dir > 0):
            P["arm_r"], P["arm_rx"] = y, x * self.dir
        else:
            P["arm_l"], P["arm_lx"] = y, x * self.dir

    def pose(self):
        s, t, d = self.state, self.st, self.dir
        P = dict(bw=8.0, bh=6.0, legs=[2.0] * 4, leg_dx=[0.0] * 4, lean=0.0,
                 arm_l=2.0, arm_r=2.0, arm_lx=0.0, arm_rx=0.0,
                 eye_dx=0.0, eye_dy=0.0, eye_h=1.0, eyes="open", shake=0.0,
                 color=self.body_color, eye_color=EYE, arm_color=None, leg_color=None,
                 shape="box", hide_all=False,
                 hide_eyes=False, sink=0.0, rise=0.0, rot=0.0, suit=False, shades=False,
                 brows=False, mouth=0.0, visor=False)

        if s == "walk":
            self.steps(P, t, d, 0.13, 0.5, 0.5, 0.25)
            P["eye_dx"] = 0.34 * d
        elif s == "lurk":
            if (t % 3.2) < 1.5:
                self.steps(P, t, d, 0.17, 0.4, 0.4, 0.2)
                P["eye_dx"] = 0.34 * d
            else:
                self.follow_cursor(P)
        elif s == "watch":
            b = 0.2 * (int(t / 0.8) % 2)
            P["legs"] = [2 - b] * 4
            self.follow_cursor(P)
        elif s in ("run", "leave", "portal_in", "portal_out", "toedge"):
            ph = self.steps(P, t, d, 0.055, 0.9, 0.9, 0.35)
            P["lean"], P["bh"] = 0.9, 5.7
            P["eye_dx"] = 0.5 * d
            front, back = (0.8, 3.0) if ph in (0, 1) else (3.0, 0.8)
            if d > 0:
                P["arm_r"], P["arm_l"], P["arm_rx"], P["arm_lx"] = front, back, 0.4, -0.4
            else:
                P["arm_l"], P["arm_r"], P["arm_lx"], P["arm_rx"] = front, back, -0.4, 0.4
        elif s == "skid":
            P["lean"] = -0.8
            P["leg_dx"] = [0.7 * d] * 4
            P["legs"] = [1.6] * 4
            P["arm_l"] = P["arm_r"] = 1.0
            P["arm_lx"] = P["arm_rx"] = -0.5 * d
            P["eye_dx"] = 0.34 * d
        elif s == "idle":
            b = 0.25 * (int(t / 0.7) % 2)
            P["legs"] = [2 - b] * 4
            self.follow_cursor(P)
        elif s == "peek":
            P["eye_dx"] = [0, -0.34, -0.34, 0, 0.34, 0.34][int(t / 0.35) % 6] if t > 0.5 else 0
        elif s == "crouch":
            P.update(bw=9.2, bh=4.8, legs=[1.2] * 4, arm_l=2.8, arm_r=2.8)
        elif s == "land":
            k = 1 - min(t / self.dur, 1)
            P.update(bw=8 + 1.6 * k, bh=6 - 1.6 * k, legs=[2 - 0.8 * k] * 4,
                     arm_l=2 + k, arm_r=2 + k)
        elif s in ("air", "leapto"):
            vy = self.vy
            if self.spin:
                P.update(bw=8.4, bh=5.6, legs=[1.0] * 4, arm_l=1.0, arm_r=1.0)
            elif vy < -350:
                P.update(bw=7.0, bh=7.0, legs=[2.4] * 4, arm_l=0.3, arm_r=0.3)
                P["leg_dx"] = [0.4, 0.2, -0.2, -0.4]
            elif vy < 350:
                P.update(bw=8.6, bh=5.6, legs=[1.0] * 4, arm_l=1.2, arm_r=1.2)
            else:
                P.update(bw=7.6, bh=6.4, legs=[2.6] * 4, arm_l=0.0, arm_r=0.0)
            P["eye_dx"] = 0.34 * (1 if self.vx > 40 else -1 if self.vx < -40 else 0)
            P["eye_dy"] = -0.3 if vy < 0 else 0.3
            trick = getattr(self, "trick", None)
            if trick and not self.spin:                        # moves in the air
                if trick == "twist":                           # spins round like a top
                    k = abs(math.cos(t * 14))
                    P.update(bw=2 + 6 * k, legs=[2.2] * 4, arm_l=0.6, arm_r=0.6)
                    P["hide_eyes"] = math.sin(t * 14) < 0
                elif trick == "starjump":
                    P.update(arm_l=-0.6, arm_r=-0.6, legs=[2.4] * 4)
                    P["arm_lx"], P["arm_rx"] = -1.2, 1.2
                    P["leg_dx"] = [-1.4, -0.7, 0.7, 1.4]
                    P["eyes"] = "^"
                elif trick == "glide":
                    P.update(rot=70 * d, legs=[2.6] * 4)
                    self.set_arm(P, 1, 0.4, 1.4)
                    self.set_arm(P, -1, 0.4, 3.0)
                    P["brows"] = True
                elif trick == "cannonball":
                    P.update(bw=8.6, bh=5.0, legs=[0.6] * 4, arm_l=3.2, arm_r=3.2)
                    P["arm_lx"], P["arm_rx"] = 1.6, -1.6
                    P["eye_h"] = 0.25
                elif trick == "split":
                    P.update(legs=[2.4, 1.0, 1.0, 2.4], arm_l=0.0, arm_r=0.0)
                    P["leg_dx"] = [-2.0, -0.6, 0.6, 2.0]
                    P["eyes"] = "^"
            if s == "leapto" and self.leap_pose == "kick":     # flying kick
                P.update(bw=8, bh=6, rot=-18 * d, brows=True)
                P["legs"] = [1.0, 1.0, 2.6, 2.6] if d > 0 else [2.6, 2.6, 1.0, 1.0]
                P["leg_dx"] = [0, 0, 1.6 * d, 1.6 * d] if d > 0 else [1.6 * d, 1.6 * d, 0, 0]
                P["arm_l"] = P["arm_r"] = 1.0
            elif s == "leapto" and self.leap_pose == "highfive":
                self.set_arm(P, 1, -2.2, 0.4)
                P["eyes"] = "^"
            elif s == "leapto" and self.leap_pose == "bash":   # head-first charge
                P.update(bw=8, bh=6, rot=22 * d, brows=True, legs=[1.4] * 4)
                P["arm_l"] = P["arm_r"] = 3.2
                P["arm_lx"] = P["arm_rx"] = -1.0 * d
        elif s == "wall":
            P.update(bw=7.4, bh=6.2)
            if d > 0:
                P["arm_r"], P["arm_l"] = 0.4, 2.6
            else:
                P["arm_l"], P["arm_r"] = 0.4, 2.6
            P["eye_dx"] = -0.34 * d
            P["legs"] = [1.6, 2.0, 1.6, 2.0]
        elif s in ("climb", "edgeclimb"):
            hand = int(t / 0.16) % 2
            P["arm_l"], P["arm_r"] = (0.2, 1.8) if hand else (1.8, 0.2)
            P["legs"] = [2.0, 1.4, 2.0, 1.4] if hand else [1.4, 2.0, 1.4, 2.0]
            P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.4
        elif s == "dig":
            P["eye_dy"] = 0.5
            dig = int(t / 0.09) % 2
            P["arm_l"], P["arm_r"] = (3.6, 2.6) if dig else (2.6, 3.6)
            P["arm_lx"], P["arm_rx"] = 0.5, -0.5
            P["shake"] = 0.15 if dig else -0.15
        elif s == "perch":
            P["legs"] = [1.3] * 4
            if self.clock - self.typing_t < 0.6:
                P["eye_dx"] = [-0.34, 0.34][int(self.clock / 0.15) % 2]
                P["eye_dy"] = 0.45
            else:
                self.follow_cursor(P)
        elif s == "pointing":
            self.set_arm(P, 1, 3.2, 1.0)
            P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.5
            P["legs"] = [1.8] * 4
        elif s == "hang":
            P.update(arm_l=-2.4, arm_r=-2.4, legs=[2.5] * 4)
            sw = math.sin(t * 2.4)
            P["leg_dx"] = [0.5 * sw] * 4
            P["shake"] = 0.25 * sw
            P["eye_dx"] = [0.34, 0, -0.34, 0][int(t / 0.9) % 4]
        elif s == "chute":
            P.update(arm_l=0.3, arm_r=0.3, legs=[2.5] * 4)
            P["leg_dx"] = [0.3 * math.sin(t * 3)] * 4
            P["eye_dx"] = [0.34, 0, -0.34, 0][int(t / 0.7) % 4]
            P["eye_dy"] = 0.4
        elif s == "drag":
            P.update(arm_l=0.0, arm_r=0.0)
            w = 0.5 * (int(t / 0.12) % 2)
            P["legs"] = [2.6, 2.6 - w, 2.6, 2.6 - w]
        elif s == "waitcursor":                          # waiting under your idle cursor
            self.follow_cursor(P)
            tap = int(t / 0.3) % 2
            P["legs"] = [2.0, 2.0, 2.0 - 0.5 * tap, 2.0] if d > 0 else [2.0, 2.0 - 0.5 * tap, 2.0, 2.0]
            if int(t / 6) % 3 == 2 and (t % 6) < 1.5:
                self.set_arm(P, 1, 0.0 if int(t / 0.18) % 2 else 0.6)
        elif s == "reach":                               # stretching up for the cursor
            self.follow_cursor(P)
            P["eye_dy"] = -0.45
            k = 0.5 + 0.5 * math.sin(t * 3)
            P.update(bh=6 + 2.5 * k, legs=[2.4] * 4)
            self.set_arm(P, 1, -2.0 - 0.8 * k, 0.3)
            if int(t / 1.5) % 2:
                self.set_arm(P, -1, -1.0, 0.2)
        elif s == "ko":                                  # knocked out, stars round his head
            if t < 2.6:
                P.update(bh=3.6, bw=10.0, legs=[0.4] * 4, arm_l=2.2, arm_r=2.2)
                P["arm_lx"], P["arm_rx"] = -0.8, 0.8
                P["eyes"] = "x"
            else:
                P["shake"] = 0.4 if int(t / 0.05) % 2 else -0.4
                P["eyes"] = "x" if t < 3.0 else "open"
        elif s == "slide":                               # baseball slide under the cursor
            P.update(bh=4.2, bw=9.0, lean=-1.1, legs=[1.0] * 4)
            P["leg_dx"] = [1.4 * d] * 4
            P["arm_l"] = P["arm_r"] = 0.6
            P["arm_lx"] = P["arm_rx"] = -0.8 * d
            P["eye_dy"] = -0.45
        elif s == "cursorhang":                          # holding on to your cursor
            P.update(arm_l=-2.4, arm_r=-2.4, legs=[2.6] * 4)
            P["arm_lx"], P["arm_rx"] = 1.6, -1.6
            sw = math.sin(t * 3)
            P["leg_dx"] = [0.6 * sw] * 4
            P["eye_dy"] = -0.45
            P["eyes"] = "^" if int(t / 1.2) % 2 else "open"
        elif s == "typealong":                           # typing along with you
            P["legs"] = [1.0] * 4
            tap = self.key_pulse % 2
            P["arm_l"], P["arm_r"] = (3.4, 3.9) if tap else (3.9, 3.4)
            P["arm_lx"], P["arm_rx"] = 0.7, -0.7
            P["eye_dy"] = 0.5
            P["eye_dx"] = [-0.34, 0.34][self.key_pulse // 3 % 2]
        elif s in ("pg_in", "pg_out"):                   # strolling through his portals
            self.steps(P, t, d, 0.13, 0.5, 0.5, 0.25)
            P["eye_dx"] = 0.34 * d
        elif s in ("chase", "runoff", "runin", "toclock", "visit", "slidein"):
            ph = self.steps(P, t, d, 0.06, 0.8, 0.8, 0.3)
            P["lean"], P["eye_dx"] = 0.7, 0.5 * d
            if s == "chase":
                P["eye_dy"] = -0.4
        elif s == "wallclimb":
            side = self.wc["side"]
            if self.wc_phase == "cling":                 # wall slide: tilted, pressed on
                P["rot"] = 14 * side
                P.update(bw=7.6, bh=6.2)
                if side > 0:
                    P["arm_r"], P["arm_l"], P["arm_rx"] = 0.6, 2.6, -0.4
                else:
                    P["arm_l"], P["arm_r"], P["arm_lx"] = 0.6, 2.6, 0.4
                P["legs"] = [1.4, 2.0, 1.4, 2.0] if side > 0 else [2.0, 1.4, 2.0, 1.4]
                P["eye_dx"], P["eye_dy"] = -0.34 * side, -0.4
            else:                                        # the little hop up the wall
                P.update(bw=7.0, bh=7.0, legs=[2.4] * 4, arm_l=0.2, arm_r=0.2)
                P["rot"] = -6 * side
                P["eye_dy"] = -0.4
        elif s in ("tbhang", "lhang"):
            P.update(arm_l=-2.4, arm_r=-2.4)
            sw = math.sin(t * 2.2)
            kick = int(t / 0.25) % 2 if s == "tbhang" and int(t / 2) % 2 else 0
            P["legs"] = [2.5, 2.5 - 0.8 * kick, 2.5, 2.5 - 0.8 * kick]
            P["leg_dx"] = [0.5 * sw] * 4
            P["shake"] = 0.2 * sw
            self.follow_cursor(P)
            if self.st > self.dur - 0.5:
                P["eye_dy"] = -0.4
                P["arm_l"] = P["arm_r"] = -1.6
        elif s == "clockpoint":
            self.set_arm(P, 1, 3.0, 1.0)
            P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.5
            if 3.5 < t < 5.0:
                k = math.sin(math.pi * (t - 3.5) / 1.5)
                P["mouth"] = k
                P["eye_h"] = 0.25
                self.set_arm(P, -1, 2 - 2.6 * k)

        fn = getattr(self, "pose_" + s, None)
        if fn:
            fn(P, t, d)
        if self.blink and P["eyes"] == "open" and s != "dig":
            P["eye_h"] = min(P["eye_h"], 0.25)
        return P

    # ================= draw =================
    def draw(self, wx, wy):
        s, t, d = self.state, self.st, self.dir
        cv = self.cv
        cv.delete("all")
        self.words = []                          # words above his head (drawn in an overlay)
        if self.invisible:                       # he's gone, but his smoke / dust stays
            for p in self.particles:
                px, py, sz = p[0] - wx, p[1] - wy, p[6]
                cv.create_rectangle(px, py, px + sz, py + sz, fill=p[5], outline="")
            self.clip = 10 ** 6
            self.draw_popups(wx, wy)             # "poof!" still shows
            self.draw_words(wx, wy)
            return
        if s in ("dig", "peek"):
            self.clip = self.work()[3] - wy
        elif self.support is not None and s not in ("crouch",):
            self.clip = self.fy - wy + 0.5
        else:
            self.clip = 10 ** 6
        self.hclip_px = (self.hclip[0] - wx, self.hclip[1]) if self.hclip else None

        for p in self.particles:
            px, py, sz = p[0] - wx, p[1] - wy, p[6]
            cv.create_rectangle(px, py, px + sz, py + sz, fill=p[5], outline="")

        P = self.pose()
        if P["sink"] > 0:
            self.clip = min(self.clip, FEET * PX + 0.5)
        bw, bh = P["bw"], P["bh"]
        sx = bw / 8.0
        body_bot = FEET - P["rise"] - max(P["legs"]) + P["sink"]
        body_top = body_bot - bh
        bl = CX - bw / 2 + P["shake"]
        lean = P["lean"] * d
        ascale = bh / 6.0
        self.pcx, self.pcy = CX, body_top + bh / 2
        spin_rot = self.rot if (s in ("air", "leapto") and self.spin) else 0.0
        self.rot = 0.0

        def shear(yy):
            return lean * min(max((body_bot - yy) / bh, 0.0), 1.0)

        ly = body_top + P["arm_l"] * ascale
        ry = body_top + P["arm_r"] * ascale
        lx = bl - 2 + shear(ly + 1) + P["arm_lx"]
        rx = bl + bw + shear(ry + 1) + P["arm_rx"]
        ey = body_top + 1 * ascale + P["eye_dy"]
        g = dict(bl=bl, bw=bw, bh=bh, bt=body_top, bb=body_bot, ey=ey, asc=ascale, sx=sx,
                 al=ly, ar=ry, hl=(lx + 1, ly + 1), hr=(rx + 1, ry + 1), P=P,
                 Lu=self.lift() / PX)
        g["hf"] = g["hr"] if d > 0 else g["hl"]          # hand on the facing side
        g["hb"] = g["hl"] if d > 0 else g["hr"]          # back hand
        self.g = g

        back = getattr(self, "back_" + s, None)
        if back:
            back(t, d, g)

        # his clothes (chosen in the app) - movie scenes bring their own costume
        outfit = pixbot_movies.scene_outfit(s) or getattr(self, "outfit", None)
        wear = bool(outfit) and not P["hide_all"] and not (P["rot"] or spin_rot) and P["shape"] == "box"
        skip = ({"hat"} if s in NO_HAT else set()) | ({"face"} if s in NO_FACE or P["shades"]
                                                       or P["visor"] else set()) \
            | ({"body"} if s in NO_BODY or P["suit"] else set())
        og = {"bl": bl, "bw": bw, "bt": body_top, "bh": bh, "ey": ey, "d": d}
        if wear:
            pixbot_outfits.draw(self, outfit, og, "back", skip)

        self.rot = P["rot"] or spin_rot
        col = P["color"]
        if not P["hide_all"]:
            metal = P["leg_color"] or self.dark_color
            # two sturdy robot legs with flat feet
            for i, off in ((0, 1.0), (2, 5.2)):
                ln = (P["legs"][i] + P["legs"][i + 1]) / 2
                if ln > 0.05:
                    lx_ = bl + off * sx + (P["leg_dx"][i] + P["leg_dx"][i + 1]) / 2
                    self.rect(lx_, body_bot, 1.6, ln, metal)
                    self.rect(lx_ - 0.3, body_bot + ln - 0.5, 2.2, 0.5, "#2B3440")
            # arms: little round mitts on short connectors
            for ax, ay, side in ((lx, ly, -1), (rx, ry, 1)):
                arm = P["arm_color"] or col
                if not self.rot:
                    self.L([(bl + (bw if side > 0 else 0), body_top + 2.2 * ascale), (ax + 1, ay + 1)],
                           "#4A5562", 2)
                    self.O(ax + 0.2, ay + 0.2, 1.6, 1.6, fill=arm, outline="#2B3440")
                else:
                    self.rect(ax + 0.2, ay + 0.2, 1.6, 1.6, arm)
            # antenna with a blinking bulb
            if not self.rot:
                tip = (CX + shear(body_top) + 0.6 * d, body_top - 2.2)
                self.L([(CX + shear(body_top), body_top), tip], "#4A5562", 2)
                bulb = "#FF5A5A" if int(self.clock * 1.5) % 2 else "#FFD166"
                self.O(tip[0] - 0.55, tip[1] - 0.55, 1.1, 1.1, fill=bulb)
            # body: a boxy robot head-body with bolts
            if P["shape"] == "oval" and not self.rot:
                self.O(bl, body_top, bw, bh, fill=col)
            else:
                n = 6 if lean else 1
                for i in range(n):
                    y0 = body_top + bh * i / n
                    self.rect(bl + shear(y0 + bh / n / 2), y0, bw, bh / n + 0.02, col)
                self.rect(bl + shear(body_top), body_top, bw, 0.35, self.dark_color)
                for bx_, by_ in ((bl + 0.3, body_top + 0.6), (bl + bw - 0.7, body_top + 0.6),
                                 (bl + 0.3, body_bot - 0.8), (bl + bw - 0.7, body_bot - 0.8)):
                    self.rect(bx_ + shear(by_), by_, 0.4, 0.4, "#2B3440")
            if P["suit"]:
                st = body_top + 2.8 * ascale
                self.rect(bl, st, bw, body_bot - st, "#151515")
                if not self.rot:
                    self.Pg([(CX - 1.1, st), (CX + 1.1, st), (CX, st + 1.8)], "#FFFFFF")
                self.rect(CX - 0.25, st + 0.2, 0.5, 2.0, "#2E6FD8")
            # face screen with glowing eyes
            scr_y = body_top + 0.6 * ascale
            scr_h = 2.6 * ascale
            self.rect(bl + 0.9 * sx + shear(scr_y + 1), scr_y, bw - 1.8 * sx, scr_h, "#1B2430")
            glow = P["eye_color"] if P["eye_color"] != EYE else "#7CF3FF"
            q = 1 / 3
            if not P["hide_eyes"] and not P["shades"] and not P["visor"]:
                for ex in (bl + 1.6 * sx, bl + bw - 1.6 * sx - 1):
                    ex += P["eye_dx"] * 0.8 + shear(ey + 0.5)
                    if P["eyes"] == "x":
                        for dx, dy in ((0, 0), (2, 0), (1, 1), (0, 2), (2, 2)):
                            self.rect(ex + dx * q, ey + dy * q, q, q, glow)
                    elif P["eyes"] == "^":
                        for dx, dy in ((0, 1), (1, 0), (2, 1)):
                            self.rect(ex + dx * q, ey + dy * q, q, q, glow)
                    else:
                        h = P["eye_h"]
                        self.rect(ex, ey + (1 - h), 1, h, glow)
                    if P["brows"]:
                        inner = 1 if ex < CX else -1
                        self.rect(ex - 0.2, ey - 0.6 + (0.3 if inner > 0 else 0), 0.7, 0.3, glow)
                        self.rect(ex + 0.5, ey - 0.6 + (0 if inner > 0 else 0.3), 0.7, 0.3, glow)
            if P["shades"]:
                pixbot_outfits.sunglasses(self, {"bl": bl, "bw": bw, "ey": ey}, "front")
            if P["visor"]:
                self.rect(bl + 0.7, ey - 0.4, bw - 1.4, 1.8, "#9AD9F0")
            if P["mouth"] > 0.05:                             # mouth shows up on the screen
                m = P["mouth"]
                self.rect(CX - 0.6 + P["eye_dx"], scr_y + scr_h - 0.7 - 0.5 * m, 1.2, 0.25 + 0.5 * m, glow)
        self.rot = 0.0
        if wear:
            pixbot_outfits.draw(self, outfit, og, "front", skip)

        front = getattr(self, "front_" + s, None)
        if front:
            front(t, d, g)
        self.draw_popups(wx, wy)
        if self.clock - self.bonk_t < 0.7:               # "BONK!" where he hit the cursor
            bx, by = self.bonk_at
            self.T((bx - wx) / PX, (by - wy) / PX - (self.clock - self.bonk_t) * 4, "BONK!", 9, GOLD)
        self.draw_words(wx, wy)

    # ================= reactions to you =================
    def front_ko(self, t, d, g):
        if t < 3.0:
            cx, cy = CX, g["bt"] - 1.2
            for i in range(3):
                a = t * 5 + i * 2.1
                self.T(cx + math.cos(a) * 4.0, cy + math.sin(a) * 1.0, "★", 8,
                       (GOLD, "#FFFFFF", GOLD)[i], SYM)

    def front_typealong(self, t, d, g):
        self.R(CX - 5, FEET - 0.8, 10, 0.8, GREY)
        for k in range(6):
            lit = (self.key_pulse + k) % 6 == 0 and self.clock - self.last_key < 0.15
            self.R(CX - 4.5 + k * 1.6, FEET - 0.65, 1.1, 0.4, LIGHT if lit else "#7A7A7A")
        rate = sum(1 for k in self.keys if self.clock - k < 2.0) / 4.0
        wpm = int(rate * 60 / 5)
        if wpm:
            self.T(CX, 1.6, f"{wpm} wpm", 7, GOLD if wpm > 60 else "#FFFFFF")

    def front_waitcursor(self, t, d, g):
        if int(t / 6) % 3 == 1 and (t % 6) < 1.5:
            self.T(CX + 5 * d, g["bt"] - 2, "?", 9, "#FFFFFF")

    def front_cursorhang(self, t, d, g):
        if int(t / 0.8) % 3 == 0:
            self.T(CX + 6, g["bt"] + 1, "got it!", 6, GOLD)

    def front_slide(self, t, d, g):
        if t < 0.6:
            self.T(CX - 6 * d, g["bt"] - 1, "whoosh", 6, "#FFFFFF")

    # ================= base / move props =================
    def front_pointing(self, t, d, g):
        hx, hy = g["hf"]
        self.R(hx + d * 1.0 - 0.3, hy + 0.2, 0.6, 0.6)                 # pointing finger
        bob = 0.5 * math.sin(t * 8)
        self.T(hx + d * 1.6, FEET - 4.2 + bob, "▼", 10, GOLD, SYM)
        if int(t / 0.5) % 2:
            self.T(CX, g["bt"] - 2.2, "!", 9, GOLD)

    def back_chute(self, t, d, g):
        bt = g["bt"]
        cx, top = CX + 0.4 * math.sin(t * 1.3), bt - 9.0
        for i in range(4):
            self.A(cx - 7, top, 14, 9, i * 45, 45, ORANGE if i % 2 == 0 else "#FFFFFF")
        self.Pg([(cx - 7, top + 4.5), (cx + 7, top + 4.5), (cx + 7, top + 4.9), (cx - 7, top + 4.9)],
                self.dark_color)
        for sx_, hand in ((-7, g["hl"]), (-2.5, g["hl"]), (2.5, g["hr"]), (7, g["hr"])):
            self.L([(cx + sx_, top + 4.7), hand], "#8A8A8A", 1)

    def front_hang(self, t, d, g):
        # little hands wrapped round the scrollbar
        self.R(CX + 5.2, g["al"] - 0.2, 1.6, 0.6, self.dark_color)

    # ======================================================================
    # ============================ CLASSIC ================================
    # ======================================================================
    def pose_wave(self, P, t, d):
        self.set_arm(P, 1, 0.0 if int(t / 0.18) % 2 else 0.6)

    # --- dance: a little routine of 7 moves under a disco ball ---
    def pose_dance(self, P, t, d):
        move, u = int(t / 1.0) % 7, t % 1.0
        beat = int(t / 0.25) % 2
        P["eyes"] = "^"
        if move == 0:                                   # side steps
            P["shake"] = 1.2 * math.sin(2 * math.pi * u)
            P["legs"] = [2.0, 1.4, 2.0, 1.4] if beat else [1.4, 2.0, 1.4, 2.0]
            P["arm_l"], P["arm_r"] = 1.4, 1.4
            P["arm_lx"], P["arm_rx"] = -0.6, 0.6
        elif move == 1:                                 # disco point
            side = 1 if u < 0.5 else -1
            if side > 0:
                P["arm_r"], P["arm_rx"], P["arm_l"], P["arm_lx"] = -1.6, 0.8, 3.2, 0.6
            else:
                P["arm_l"], P["arm_lx"], P["arm_r"], P["arm_rx"] = -1.6, -0.8, 3.2, -0.6
            P["lean"] = 0.4 * side * d
        elif move == 2:                                 # spin
            P["rot"] = 360 * ease(u)
            P["arm_l"] = P["arm_r"] = 1.0
        elif move == 3:                                 # wavy arms
            P["arm_l"] = 1.3 + 1.3 * math.sin(t * 14)
            P["arm_r"] = 1.3 + 1.3 * math.sin(t * 14 + 2)
            P["bh"] = 6 + 0.4 * math.sin(t * 14)
        elif move == 4:                                 # jump
            P["arm_l"] = P["arm_r"] = 0.0
            if u > 0.75:
                P.update(bw=9, bh=5, legs=[1.4] * 4)
        elif move == 5:                                 # hip sway
            P["lean"] = 0.7 if beat else -0.7
            P["arm_l"] = P["arm_r"] = 2.6
            P["arm_lx"], P["arm_rx"] = 0.5, -0.5
        else:                                           # kicks
            k = int(t / 0.25) % 2
            P["legs"] = [2.0, 2.0, 1.0, 1.0] if k else [1.0, 1.0, 2.0, 2.0]
            P["leg_dx"] = [0, 0, 1.3, 1.3] if k else [-1.3, -1.3, 0, 0]
            P["arm_l"] = P["arm_r"] = 0.6

    def lift_dance(self, t):
        move, u = int(t / 1.0) % 7, t % 1.0
        if move == 4:
            return para(u / 0.75, 3.0) if u < 0.75 else 0
        return 0.4 if int(t / 0.25) % 2 == 0 else 0

    def back_dance(self, t, d, g):
        self.L([(CX, 0), (CX, 1.2)], "#AAAAAA", 1)
        self.O(CX - 1.5, 1.2, 3, 3, fill="#C8C8C8", outline="#888888")
        for i in range(4):
            a = t * 3 + i * 1.6
            self.R(CX - 0.4 + math.cos(a) * 1.0, 2.4 + math.sin(a) * 0.9, 0.5, 0.5, "#FFFFFF")
        cols = ("#FF6B8B", "#8FD3FF", GOLD, "#B5E48C", "#C3A6FF")
        for i in range(6):
            a = t * 1.8 + i * 1.05
            self.R(CX + math.cos(a) * 11, FEET - 4 + math.sin(a * 1.3) * 3.5, 0.7, 0.7, cols[i % 5])

    def pose_think(self, P, t, d):
        P["eye_dx"], P["eye_dy"] = 0.34, -0.5
        P["arm_r"] = 1.0

    def front_think(self, t, d, g):
        for i in range(int(t / 0.4) % 4):
            self.R(CX - 2 + i * 1.5, g["bt"] - 2.5 + (i % 2) * 0.3, 0.7, 0.7, LIGHT)

    # --- coding on a laptop next to him ---
    def pose_code(self, P, t, d):
        P["legs"] = [1.0] * 4
        P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.45
        tap = int(t / 0.09) % 2
        self.set_arm(P, 1, 3.3 if tap else 3.8, 0.9)
        self.set_arm(P, -1, 3.8 if tap else 3.3, -0.2)
        if int(t / 3.1) % 3 == 2:
            P["eye_dy"] = -0.4
            P["eye_dx"] = 0.0

    def front_code(self, t, d, g):
        """A proper laptop next to him: silver keyboard deck + lid with a lit screen."""
        k = max(min(t / 0.6, (self.dur - t) / 0.6, 1.0), 0.0)
        w = 7.0
        x = self.M(4.6 + (1 - k) * 7, w)
        # keyboard deck (seen slightly from above: a flat trapezoid)
        self.Pg([(x - 0.3, FEET), (x + w + 0.3, FEET), (x + w - 0.3, FEET - 1.1), (x + 0.3, FEET - 1.1)],
                "#BFC4CB", "#8C9198")
        for row in range(2):
            for col in range(7):
                self.R(x + 0.7 + col * 0.82 + row * 0.15, FEET - 0.95 + row * 0.42, 0.6, 0.28, "#4A4F57")
        self.R(x + w / 2 - 0.9, FEET - 0.15, 1.8, 0.12, "#9AA0A8")       # touchpad lip
        lid_h = 5.2 * k
        if lid_h < 0.3:
            return
        top = FEET - 1.1 - lid_h
        # lid: silver bezel, dark screen, tilted back a little
        self.Pg([(x + 0.3, FEET - 1.1), (x + w - 0.3, FEET - 1.1), (x + w - 0.1, top), (x + 0.1, top)],
                "#A9AFB7", "#7E848C")
        sx0, sx1, sy0, sy1 = x + 0.6, x + w - 0.6, top + 0.45, FEET - 1.5
        if sy1 - sy0 < 0.3:
            return
        self.R(sx0, sy0, sx1 - sx0, sy1 - sy0, "#111820")
        self.R(x + w / 2 - 0.15, top + 0.12, 0.3, 0.2, "#333333")         # webcam
        if k >= 1.0:
            self.R(sx0, sy0, sx1 - sx0, 0.4, "#2A3340")                    # editor tab bar
            self.R(sx0 + 0.2, sy0 + 0.1, 1.2, 0.2, ORANGE)
            first = int(t / 0.35)
            for i in range(5):
                indent, length, col = self.code_lines[(first + i) % len(self.code_lines)]
                yy = sy0 + 0.7 + i * 0.6
                if yy + 0.3 > sy1:
                    break
                self.R(sx0 + 0.3 + indent * 0.35, yy, min(length * 0.45, sx1 - sx0 - 0.6 - indent * 0.35), 0.28, col)
            if int(t / 0.4) % 2:
                self.R(sx0 + 0.3, min(sy0 + 0.7 + 5 * 0.6, sy1 - 0.45), 0.3, 0.4, LIGHT)
        # little glow on his face from the screen
        self.R(CX + d * 3.2 - 0.3, g["ey"] + 1.6, 0.6, 1.2, "#8FB8D8")

    # ================= small reactions to what you do =================
    REACT_TEXT = {
        "ooh": "ooh, new window!", "bye": "bye!", "copied": "copied!", "lowbattery": "battery low!",
        "charging": "charging!", "morning": "good morning!", "lunch": "lunch time?",
        "break": "take a break?", "facepalm": "oops...", "caps": "WHY ARE WE SHOUTING",
    }

    def pose_react(self, P, t, d):
        k = self.react_kind
        if k == "ooh":
            P["eye_dy"] = -0.3
            P["eye_dx"] = 0.34 * d
            P["arm_l"] = P["arm_r"] = 0.6
        elif k == "bye":
            self.set_arm(P, 1, 0.0 if int(t / 0.18) % 2 else 0.6)
            P["eye_dx"] = 0.34 * d
        elif k == "copied":
            P["arm_l"] = P["arm_r"] = -1.2
            P["eyes"] = "^"
        elif k == "lowbattery":
            P["eye_dy"] = 0.4
            P["shake"] = 0.15 if int(t / 0.08) % 2 else -0.15
        elif k == "charging":
            P["eyes"] = "^"
            P["arm_l"] = P["arm_r"] = 0.0
        elif k in ("morning", "break"):
            s = math.sin(math.pi * min(t / 2.2, 1))
            P["arm_l"] = P["arm_r"] = 2.0 - 3.2 * s
            P.update(bh=6 + 0.6 * s)
            P["eye_h"] = 0.25 if s > 0.3 else 1.0
            P["mouth"] = s if k == "morning" else 0
        elif k == "lunch":
            self.set_arm(P, 1, 1.6, -0.6)
            P["eyes"] = "^"
        elif k == "facepalm":
            self.set_arm(P, 1, 0.6, -2.6)
            P["eye_h"] = 0.25
        elif k == "caps":
            P["arm_l"] = P["arm_r"] = -0.8
            P["arm_lx"], P["arm_rx"] = -0.6, 0.6
            P["mouth"] = 1.0
            P["shake"] = 0.3 if int(t / 0.05) % 2 else -0.3

    def lift_react(self, t):
        if self.react_kind in ("copied", "charging", "ooh"):
            return para(t / 0.5, 1.5) if t < 0.5 else 0
        return 0

    def front_react(self, t, d, g):
        k = self.react_kind
        self.T(CX, 1.4, self.REACT_TEXT.get(k, "!"), 5 if k == "caps" else 6,
               GOLD if k != "lowbattery" else RED)
        bt = g["bt"]
        if k == "copied":
            self.R(CX - 1.4, bt - 4.2, 2.8, 3.2, "#FFFFFF")
            for i in range(3):
                self.R(CX - 1.0, bt - 3.7 + i * 0.8, 2.0, 0.2, "#999999")
        elif k in ("lowbattery", "charging"):
            x, y = CX + 5.5 * d - 1.4, bt - 2.5
            self.R(x, y, 2.8, 1.4, "#DDDDDD")
            self.R(x + 0.2, y + 0.2, 2.4, 1.0, "#222222")
            self.R(x + 2.8, y + 0.4, 0.3, 0.6, "#DDDDDD")
            lvl = 0.5 if k == "lowbattery" else 2.4 * min(t / 2.0, 1)
            self.R(x + 0.2, y + 0.2, lvl, 1.0, RED if k == "lowbattery" else "#7BD88F")
            if k == "charging":
                self.T(x + 1.4, y + 0.7, "⚡", 7, GOLD, SYM)
        elif k == "facepalm":                                   # hand over his eyes
            self.R(CX - 3.2, g["ey"] - 0.6, 6.4, 1.8, self.dark_color)
            self.R(CX - 3.2, g["ey"] - 0.6, 6.4, 0.3, self.body_color)
        elif k == "lunch":
            hx, hy = g["hf"]
            self.R(hx - 1.0, hy - 1.6, 2.4, 0.5, "#E8B04A")
            self.R(hx - 1.0, hy - 1.1, 2.4, 0.3, "#5EC639")
            self.R(hx - 1.0, hy - 0.8, 2.4, 0.4, "#C0392B")
            self.R(hx - 1.0, hy - 0.4, 2.4, 0.5, "#E8B04A")

    def pose_build(self, P, t, d):
        P["eye_dx"] = 0.34 * d
        self.set_arm(P, 1, 0.0 if int(t / 0.27) % 2 == 0 else 2.5)

    def back_build(self, t, d, g):
        bx = self.M(6.6, 2.5)
        self.R(bx, FEET - 2.5, 2.5, 2.5, BLOCK)
        self.R(bx, FEET - 1.4, 2.5, 0.3, "#A8957A")

    def front_build(self, t, d, g):
        hx, hy = g["hf"]
        if int(t / 0.27) % 2 == 0:
            self.L([(hx, hy), (hx + d * 0.3, hy - 2.4)], WOOD, 3)
            self.R(hx + d * 0.3 - 0.9, hy - 3.0, 1.8, 0.8, GREY)
        else:
            self.L([(hx, hy), (hx + d * 2.4, hy + 0.2)], WOOD, 3)
            self.R(hx + d * 2.4 - 0.4, hy - 0.8, 0.8, 1.8, GREY)
            if int(t / 0.27) % 4 == 1:
                self.T(CX + 8 * d, FEET - 3.5, "*", 9, GOLD)

    def pose_juggle(self, P, t, d):
        P["eye_dy"] = -0.5
        P["arm_l"] = 1.0 + 1.0 * (int(t / 0.33) % 2)
        P["arm_r"] = 1.0 + 1.0 * ((int(t / 0.33) + 1) % 2)

    def front_juggle(self, t, d, g):
        for i, col in enumerate((LIGHT, GOLD, "#8FD3FF")):
            p = (t / 1.5 + i / 3) % 1
            self.R(CX - 0.5 - 5.0 * math.cos(2 * math.pi * p),
                   g["bt"] - 1.2 - 4.2 * abs(math.sin(2 * math.pi * p)), 1, 1, col)

    def pose_train(self, P, t, d):
        if self.sub == "squat":
            k = (1 - math.cos(t * 2 * math.pi / 0.9)) / 2
            P.update(legs=[2 - 1.2 * k] * 4, bw=8 + 0.5 * k, bh=6 - 0.4 * k,
                     arm_l=1.5, arm_r=1.5, arm_lx=0.4 * k, arm_rx=-0.4 * k)
        elif self.sub == "curl":
            up = (1 - math.cos(t * 2 * math.pi / 0.8)) / 2
            P["arm_l"] = P["arm_r"] = 3.2 - 2.6 * up
        else:
            up = int(t / 0.25) % 2 == 0
            P["arm_l"] = P["arm_r"] = 0.0 if up else 2.6
            P["leg_dx"] = [-0.8, -0.4, 0.4, 0.8] if up else [0.0] * 4
        P["eye_dy"] = -0.2

    def lift_train(self, t):
        return 0.7 if self.sub == "jacks" and int(t / 0.25) % 2 == 0 else 0

    def upd_train(self, dt, t):
        if random.random() < dt * 1.2:
            self.puff(self.x + random.uniform(-3, 3) * PX, self.fy - 8 * PX, 1,
                      ("#8FD3FF",), 40, (40, 90), (0.5, 0.7), 0.5)

    def front_train(self, t, d, g):
        self.bandana(t, d, g)
        if self.sub == "curl":
            for hx, hy in (g["hl"], g["hr"]):
                self.R(hx - 1.3, hy + 0.6, 2.6, 0.5, GREY)
                self.R(hx - 1.6, hy + 0.2, 0.6, 1.3, "#333333")
                self.R(hx + 1.0, hy + 0.2, 0.6, 1.3, "#333333")
        elif self.sub == "squat":
            self.T(CX, g["bt"] - 2.5, str(int(t / 0.9) % 10 + 1), 8, LIGHT)

    def pose_inspect(self, P, t, d):
        if (t % 1.8) < 0.7:
            self.steps(P, t, d, 0.16, 0.4, 0.4, 0.2)
        P["eye_dx"] = 0.34 * d
        self.set_arm(P, 1, 2.4, 0.4)

    def front_inspect(self, t, d, g):
        walking = (t % 1.8) < 0.7
        bl, bw, ey = g["bl"], g["bw"], g["ey"]
        if walking:
            lx, ly = CX + d * 7.2, FEET - 2.2
        else:
            scan = math.sin(t * 3) * 0.8
            eye_x = (bl + bw - 1.5) if d > 0 else (bl + 1.5)
            lx, ly = eye_x + d * 1.6 + scan * 0.3, ey + 0.5 + scan * 0.3
        hx, hy = g["hf"]
        r = 3.0                                          # big magnifying glass
        if walking:
            ly = FEET - 3.4
        self.L([(hx, hy), (lx - d * 0.6, ly + r)], "#5C3A1E", 5)
        self.O(lx - r, ly - r, 2 * r, 2 * r, fill="#DDF3FF", outline="#4A4A4A", width=4)
        self.O(lx - r + 0.6, ly - r + 0.6, 1.4, 1.0, fill="#FFFFFF")
        if not walking:
            self.R(lx - 1.3, ly - 1.3, 2.6, 2.6, EYE)
            self.R(lx - 0.8, ly - 1.0, 0.7, 0.7, "#FFFFFF")
            if (t % 1.8) > 1.3:
                self.T(CX, g["bt"] - 2.5, "!" if int(t / 1.8) % 3 == 2 else "?", 9, GOLD)

    def pose_happy(self, P, t, d):
        P["arm_l"] = P["arm_r"] = 0.0
        P["eyes"] = "^"

    def lift_happy(self, t):
        return abs(math.sin(t * 5.5)) * 1.4

    def front_happy(self, t, d, g):
        if int(t / 0.2) % 2:
            self.T(CX - 7, g["bt"] - 1, "+", 9, GOLD)
            self.T(CX + 7, g["bt"] - 2, "+", 9, GOLD)

    def pose_error(self, P, t, d):
        P["shake"] = (0.3 if int(t / 0.05) % 2 else -0.3) if t < 1.0 else 0.0
        P["eyes"] = "x"

    def front_error(self, t, d, g):
        self.R(CX - 0.4, g["bt"] - 4.5, 0.8, 2.3, RED)
        self.R(CX - 0.4, g["bt"] - 1.8, 0.8, 0.7, RED)

    # ======================================================================
    # ============================== GAMES =================================
    # ======================================================================


































    # --- Saucer shooter: little saucers drift overhead, he zaps them ---
    INVADER = ("..XXX..", ".XXXXX.", "XX.X.XX", ".X...X.")   # little original saucers

    def pose_saucers(self, P, t, d):
        P["eye_dy"] = -0.45
        if any(k - 0.25 < t < k + 0.05 for k in (1.8, 3.6, 5.4)):
            P["arm_l"] = P["arm_r"] = 0.0

    def speed_saucers(self, t):
        return 70 * (1 if math.sin(t * 2) > 0 else -1)

    def front_saucers(self, t, d, g):
        shift = 1.5 * math.sin(t * 2)
        for i, ox in enumerate((-6, 0, 6)):
            kill = (1.8, 3.6, 5.4)[i]
            ax, ay = CX + ox + shift, 1.2
            if t < kill:
                for row, line in enumerate(self.INVADER):
                    for col, ch in enumerate(line):
                        if ch == "X":
                            self.R(ax - 1.2 + col * 0.35, ay + row * 0.35, 0.35, 0.35, "#7CFC00")
                if kill - 0.25 < t:
                    self.L([(CX, g["bt"] - 0.3), (ax, ay + 1.4)], "#7CFC00", 2)
            elif t < kill + 0.4:
                self.T(ax, ay + 0.8, "*", 10, "#FFFFFF")















    # --- Crash: spin-attack a crate, fruit pops out ---


    # --- Mission complete: shades, strut, big banner ---
    def pose_missioncomplete(self, P, t, d):
        P["shades"] = True
        if t < 3.5:
            self.steps(P, t, d, 0.18, 0.5, 0.5, 0.3)
            P["lean"] = -0.2

    def speed_missioncomplete(self, t):
        return 70 if t < 3.5 else 0

    def front_missioncomplete(self, t, d, g):
        if t >= 3.6:
            self.T(CX, 2.2, "MISSION COMPLETE!", 7, GOLD)
        if t >= 4.3:
            self.T(CX, 4.4, "STYLE +100", 6, "#FFFFFF")

    # --- Slingshot launch (real physics flight afterwards) ---
    def pose_slingshot(self, P, t, d):
        P["brows"] = True
        if t > 0.8:
            k = min((t - 0.8) / 0.8, 1)
            P["shake"] = -d * 2.2 * k
            P.update(bw=8 + 0.6 * k, bh=6 - 0.6 * k)

    def back_slingshot(self, t, d, g):
        sx = self.M(-9.0, 2.6)
        self.R(sx + 0.95, FEET - 5.0, 0.7, 5.0, "#7A4A20")
        self.L([(sx + 1.3, FEET - 4.6), (sx + 0.1, FEET - 7.2)], "#7A4A20", 4)
        self.L([(sx + 1.3, FEET - 4.6), (sx + 2.5, FEET - 7.2)], "#7A4A20", 4)
        back_x = g["bl"] if d > 0 else g["bl"] + g["bw"]
        for tip in (sx + 0.1, sx + 2.5):
            self.L([(tip, FEET - 7.0), (back_x, g["bt"] + 3)], "#3A2010", 2)

    # ======================================================================
    # ============================== FUN ===================================
    # ======================================================================
    def pose_yawn(self, P, t, d):
        k = math.sin(math.pi * min(max((t - 0.3) / 2.2, 0), 1))
        P.update(bh=6 + 0.6 * k, bw=8 - 0.4 * k)
        P["arm_l"] = P["arm_r"] = 2.0 - 3.0 * k
        if k > 0.2:
            P["eye_h"] = 0.25
        P["mouth"] = k

    def pose_read(self, P, t, d):
        P["legs"] = [1.2] * 4
        P["arm_l"] = P["arm_r"] = 3.0
        P["arm_lx"], P["arm_rx"] = 0.8, -0.8
        P["eye_dy"] = 0.6
        P["eye_dx"] = -0.34 + 0.68 * ((t % 0.9) / 0.9)

    def front_read(self, t, d, g):
        by = g["bt"] + 3.0
        self.R(CX - 3.3, by, 6.6, 2.7, "#7A3E1D")
        self.R(CX - 3.0, by + 0.15, 2.9, 2.3, "#F5EBD7")
        self.R(CX + 0.1, by + 0.15, 2.9, 2.3, "#F5EBD7")
        for i in range(3):
            self.R(CX - 2.7, by + 0.5 + i * 0.6, 2.3, 0.15, "#9A8F80")
            self.R(CX + 0.4, by + 0.5 + i * 0.6, 2.3, 0.15, "#9A8F80")
        c = t % 2.5
        if c > 2.0:
            w = 2.9 * (1 - (c - 2.0) / 0.5 * 2) if c < 2.25 else -2.9 * ((c - 2.25) / 0.25)
            x0 = CX + 0.1 if w > 0 else CX + w
            self.R(x0, by + 0.05, abs(w), 2.4, "#FFFFFF")

    def coffee_sip(self, t):
        return 1.4 < (t % 2.4) < 2.2

    def pose_coffee(self, P, t, d):
        if self.coffee_sip(t):
            self.set_arm(P, 1, 1.3, -1.8)
            P["eye_h"] = 0.25
        else:
            self.set_arm(P, 1, 2.8, 0.3)
            if 2.2 < (t % 2.4) or (t % 2.4) < 0.4:
                P["eyes"] = "^"

    def front_coffee(self, t, d, g):
        hx, hy = g["hf"]
        mx = hx - 0.7 + (d * 0.6 if not self.coffee_sip(t) else -d * 0.2)
        my = hy - 1.2
        self.R(mx, my, 1.4, 1.6, "#FFFFFF")
        self.R(mx + (1.4 if d > 0 else -0.4), my + 0.4, 0.4, 0.8, "#FFFFFF")
        self.R(mx + 0.1, my + 0.1, 1.2, 0.3, "#6B4423")
        if not self.coffee_sip(t):
            for k in range(2):
                p = (t * 0.8 + k * 0.5) % 1
                self.R(mx + 0.3 + k * 0.6 + 0.3 * math.sin(p * 6), my - 0.4 - p * 2.4, 0.3, 0.5, "#DDDDDD")

    def pose_fish(self, P, t, d):
        self.set_arm(P, 1, 1.0, 0.3)
        P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.3
        if 6.0 < t < 6.6:
            P["eyes"] = "open"
            P["eye_dy"] = 0.5
        if t >= 7.8:
            P["arm_l"] = P["arm_r"] = -0.6
            P["eyes"] = "^"

    def front_fish(self, t, d, g):
        hx, hy = g["hf"]
        tip = (hx + d * 5.5, g["bt"] - 3.2)
        if t < 7.8:
            self.L([(hx, hy), tip], "#6B4423", 2)
            bob = 0.15 * math.sin(t * 4) + (0.6 if 6.0 < t < 6.6 else 0)
            by = FEET - 0.9 + bob
            if t < 6.6:
                self.L([tip, (tip[0], by)], "#CCCCCC", 1)
                self.R(tip[0] - 0.35, by, 0.7, 0.35, "#FFFFFF")
                self.R(tip[0] - 0.35, by + 0.35, 0.7, 0.35, RED)
            if 6.0 < t < 6.6:
                self.T(tip[0], by - 2, "!", 9, GOLD)
            if 6.6 <= t < 7.8:
                p = (t - 6.6) / 1.2
                fx = tip[0] + (CX - tip[0]) * p
                fy = FEET - 1 - para(p, 6) - p * 4
                self.draw_fish(fx, fy, d)
        else:
            self.draw_fish(CX, g["bt"] - 3.4, d)

    def draw_fish(self, x, y, d):
        self.O(x - 1.2, y - 0.5, 2.4, 1.0, fill="#6FC3FF")
        tx = x - d * 1.2
        self.Pg([(tx, y), (tx - d * 0.8, y - 0.6), (tx - d * 0.8, y + 0.6)], "#4FA3DF")
        self.R(x + d * 0.6 - 0.15, y - 0.25, 0.3, 0.3, EYE)

    def pose_skate(self, P, t, d):
        P["rise"] = 0.9
        P["legs"] = [1.4] * 4
        P["arm_l"] = P["arm_r"] = 1.4
        P["arm_lx"], P["arm_rx"] = -0.6, 0.6
        P["eye_dx"] = 0.34 * d
        P["lean"] = 0.3

    def speed_skate(self, t):
        return 230

    def lift_skate(self, t):
        c = t % 2.0
        return para((c - 1.2) / 0.5, 2.5) if 1.2 < c < 1.7 else 0

    def front_skate(self, t, d, g):
        self.R(CX - 4.5, FEET - 0.95, 9, 0.5, "#5A3A22")
        self.R(CX - 4.8, FEET - 1.15, 0.5, 0.4, "#5A3A22")
        self.R(CX + 4.3, FEET - 1.15, 0.5, 0.4, "#5A3A22")
        self.R(CX - 3.5, FEET - 0.45, 0.9, 0.45, "#DDDDDD")
        self.R(CX + 2.6, FEET - 0.45, 0.9, 0.45, "#DDDDDD")

    def pose_guitar(self, P, t, d):
        self.set_arm(P, 1, 1.2, 1.2)
        strum = int(t / 0.12) % 2
        self.set_arm(P, -1, 3.0 if strum else 3.6, 2.6)
        if int(t / 1.5) % 2:
            P["eyes"] = "^"

    def lift_guitar(self, t):
        return 0.4 if int(t / 0.48) % 2 == 0 else 0

    def front_guitar(self, t, d, g):
        bt = g["bt"]
        bx = CX - d * 1.0
        self.O(bx - 2.2, bt + 2.8, 4.4, 3.2, fill="#A0522D", outline="#6B3A1E")
        self.O(bx - 0.6, bt + 3.8, 1.2, 1.2, fill="#3B1F0E")
        self.L([(bx, bt + 4.4), (CX + d * 6.2, bt + 0.8)], "#6B4423", 4)
        self.R(CX + d * 6.2 - 0.5, bt + 0.3, 1.0, 1.0, "#3B1F0E")
        for i in range(3):
            p = (t * 0.7 + i / 3) % 1
            self.T(CX + d * (2 + 5 * p) + math.sin(p * 9) * 0.5, bt - 1 - 6 * p,
                   "♪" if i % 2 else "♫", 9, ("#FFFFFF", GOLD, "#8FD3FF")[i], SYM)

    def pose_paint(self, P, t, d):
        if t < 8:
            dab = int(t / 0.3) % 2
            self.set_arm(P, 1, 1.6 if dab else 2.2, 0.6 if dab else 0.2)
            P["eye_dx"] = 0.34 * d
        else:
            P["eyes"] = "^"

    def back_paint(self, t, d, g):
        ex = self.M(6.2, 4.0)
        self.L([(ex + 0.4, FEET), (ex + 2.0, FEET - 6.6)], WOOD, 3)
        self.L([(ex + 3.6, FEET), (ex + 2.0, FEET - 6.6)], WOOD, 3)

    def front_paint(self, t, d, g):
        ex = self.M(6.2, 4.0)
        cy = FEET - 6.4
        self.R(ex - 0.15, cy - 0.15, 4.3, 3.9, "#C9B79C")
        self.R(ex, cy, 4.0, 3.6, "#FFFFFF")
        for i in range(min(int(t * 3.5), len(self.paint_dots))):
            px_, py_, col = self.paint_dots[i]
            self.R(ex + px_, cy + py_, 0.6, 0.6, col)
        if t < 8:
            hx, hy = g["hf"]
            self.L([(hx, hy), (ex + (0.4 if d > 0 else 3.6), cy + 1.8)], "#C0A080", 2)

    def pose_bubbles(self, P, t, d):
        self.set_arm(P, 1, 1.6, -0.8)
        P["eye_dx"] = 0.34 * d
        P["mouth"] = 0.3 if (t % 0.5) < 0.25 else 0.0

    def front_bubbles(self, t, d, g):
        hx, hy = g["hf"]
        rx, ry = hx + d * 0.6, hy - 1.0
        self.O(rx - 0.5, ry - 0.5, 1.0, 1.0, outline="#9AD9F0", width=2)
        for k in range(int(t / 0.5) + 1):
            age = t - k * 0.5
            if 0 <= age < 2.5:
                bx = rx + d * age * 2.5 + math.sin(age * 3 + k) * 0.6
                by = ry - age * 2.2
                sz = min(0.6 + age * 0.4, 1.5)
                self.O(bx - sz / 2, by - sz / 2, sz, sz, outline="#9AD9F0", width=1)
                self.R(bx - sz / 4, by - sz / 4, 0.25, 0.25, "#FFFFFF")

    def pose_soccer(self, P, t, d):
        if t < 5:
            self.steps(P, t, d, 0.1, 0.6, 0.6, 0.25)
            P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.4
        elif t < 5.4:
            P["leg_dx"] = [0.0, 0.0, 1.2 * d, 1.2 * d]
            P["legs"] = [2, 2, 1.4, 1.4]
        else:
            P["arm_l"] = P["arm_r"] = 0.0
            P["eyes"] = "^"

    def speed_soccer(self, t):
        return 140 if t < 5 else 0

    def lift_soccer(self, t):
        return abs(math.sin((t - 5.8) * 6)) * 1.2 if t > 5.8 else 0

    def front_soccer(self, t, d, g):
        if t < 5.3:
            bx = CX + d * (5.2 + 0.8 * abs(math.sin(t * 5)))
            by = FEET - 1.6
        else:
            p = (t - 5.3)
            if p > 1.2:
                if t > 6:
                    self.T(CX, 2.4, "GOAL!", 9, GOLD)
                return
            bx = CX + d * (5.2 + p * 14)
            by = FEET - 1.6 - para(p / 1.2, 7) + g["Lu"]
        self.O(bx - 0.8, by - 0.8, 1.6, 1.6, fill="#FFFFFF", outline="#222222")
        a = t * 8 * d
        self.R(bx + math.cos(a) * 0.35 - 0.25, by + math.sin(a) * 0.35 - 0.25, 0.5, 0.5, "#222222")

    def pose_plant(self, P, t, d):
        if t < 6.5:
            self.set_arm(P, 1, 2.2, 0.6)
            P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.4
        else:
            P["eyes"] = "^"
            P["arm_l"] = P["arm_r"] = 0.4

    def front_plant(self, t, d, g):
        px_ = self.M(7.0, 2.4)
        self.R(px_, FEET - 1.8, 2.4, 1.8, "#B5552E")
        self.R(px_ - 0.2, FEET - 2.1, 2.8, 0.4, "#C8663A")
        h = min(max(t - 1, 0) / 5, 1) * 4.5
        if h > 0.1:
            self.R(px_ + 1.0, FEET - 2.1 - h, 0.4, h, "#3E9A27")
        if h > 1.5:
            self.R(px_ + 0.2, FEET - 2.1 - h * 0.5, 0.8, 0.4, "#5EC639")
            self.R(px_ + 1.4, FEET - 2.1 - h * 0.7, 0.8, 0.4, "#5EC639")
        if t > 6.5:
            fy = FEET - 2.1 - h - 1.2
            self.O(px_ + 0.6, fy, 1.2, 1.2, fill="#FF7EB6")
            self.R(px_ + 1.0, fy + 0.4, 0.4, 0.4, GOLD)
        if t < 6.5:
            hx, hy = g["hf"]
            self.R(hx - 0.6, hy - 0.4, 1.6, 1.2, "#8A9AA8")
            sp = (hx + d * 2.2, hy - 0.8)
            self.L([(hx + d * 0.8, hy), sp], "#8A9AA8", 2)
            for k in range(3):
                p = (t * 2 + k / 3) % 1
                self.R(sp[0] + d * p * 0.8, sp[1] + p * (FEET - 2.4 - sp[1]), 0.25, 0.4, "#6FA8FF")

    def pose_sneeze(self, P, t, d):
        if t < 2.0:
            P["lean"] = -(t / 2) * 0.6
            P["eye_dy"] = -0.3
            if t > 1.4:
                P["eye_h"] = 0.25
            P["mouth"] = 0.2 + 0.3 * (t / 2)
        elif t < 2.4:
            P["eyes"] = "^"
            P["shake"] = 0.4 if int(t / 0.04) % 2 else -0.4
            P["lean"] = 0.5
        else:
            P["eye_dx"] = -0.34 * d

    def speed_sneeze(self, t):
        return -260 if 2.0 < t < 2.25 else 0

    def upd_sneeze(self, dt, t):
        if t > 2.0 and self.once("achoo"):
            self.puff(self.x + self.dir * 4 * PX, self.fy - 5 * PX, 10, ("#DDEEFF", "#FFFFFF"),
                      60, (20, 60), (0.3, 0.5), 0.5)
            for p in self.particles[-10:]:
                p[2] = self.dir * random.uniform(150, 320)

    def front_sneeze(self, t, d, g):
        if t < 2.0:
            txt = "a-" if t < 0.9 else "aa-" if t < 1.4 else "AAH-"
            if t > 0.4:
                self.T(CX - d * 2, g["bt"] - 2.5, txt, 7, "#FFFFFF")
        elif t < 3.0:
            self.T(CX + d * 3, g["bt"] - 2.5, "CHOO!", 8, GOLD)

    def pose_meditate(self, P, t, d):
        P["legs"] = [0.8] * 4
        P["arm_l"] = P["arm_r"] = 3.0
        P["arm_lx"], P["arm_rx"] = -0.5, 0.5
        P["eye_h"] = 0.25

    def lift_meditate(self, t):
        return min(t / 1.0, 1) * (1.5 + 0.6 * math.sin(t * 1.6))

    def back_meditate(self, t, d, g):
        cx, cy = CX, g["bt"] + 3
        for i in range(2):
            p = ((t * 0.5) + i * 0.5) % 1
            r = 4 + 4 * p
            self.O(cx - r, cy - r * 0.8, 2 * r, 1.6 * r, outline=(GOLD if p < 0.5 else LIGHT), width=1)

    def pose_camera(self, P, t, d):
        self.set_arm(P, 1, 1.4, 0.6)
        self.set_arm(P, -1, 1.4, 8.6)
        if 2.0 < t < 2.5 or 3.6 < t < 4.1:
            P["eyes"] = "^"

    def front_camera(self, t, d, g):
        hx, hy = g["hf"]
        cx = hx - (2.6 if d > 0 else 0)
        cy = g["ey"] - 0.4
        self.R(cx, cy, 2.6, 1.8, "#2B2B2B")
        self.O(cx + (1.6 if d > 0 else 0.2) - 0.1, cy + 0.3, 1.2, 1.2, fill="#6A6A6A", outline="#999999")
        self.R(cx + 0.3, cy - 0.4, 0.8, 0.4, "#444444")
        if 2.0 < t < 2.15 or 3.6 < t < 3.75:
            fx = hx + d * 3
            self.O(fx - 3, cy - 2.5, 6, 6, fill="#FFFFFF")
            self.T(CX, g["bt"] - 2.5, "click", 6, "#FFFFFF")

    def pose_pizza(self, P, t, d):
        self.set_arm(P, 1, 2.2, -0.6)
        c = t % 1.5
        if t < 4.5:
            P["mouth"] = 0.8 if 1.0 < c < 1.3 else 0.15
            P["eye_dx"] = 0.34 * d
        else:
            P["eyes"] = "^"
            self.set_arm(P, -1, 4.0, 2.5)

    def front_pizza(self, t, d, g):
        if t >= 4.5:
            return
        bites = min(int(t / 1.5), 3)
        k = 1 - bites * 0.28
        hx, hy = g["hf"]
        tip = (hx - d * 0.4, hy - 1.2)
        base = hx + d * 2.6 * k
        self.Pg([tip, (base, hy - 1.2 - 1.2 * k), (base, hy - 1.2 + 1.2 * k)], "#F4C95D", "#C4862E")
        self.R(hx + d * 1.2 * k - 0.25, hy - 1.4, 0.5, 0.5, "#C0392B")
        if bites and (t % 1.5) < 0.1 and self.once(f"crumb{bites}"):
            self.puff(self.x + self.dir * 3 * PX, self.fy - 5 * PX, 4, ("#F4C95D", "#C4862E"), 60, (40, 90))

    BALLOON_POP = 7.6

    def lift_balloon(self, t):
        # floats higher and higher (up to ~90 units = 360 px) before the balloon pops
        if t < 1:
            return 0
        k = ease((t - 1) / (self.BALLOON_POP - 1))
        return 90 * k * k + 1.2 * math.sin(t * 2)

    def upd_balloon(self, dt, t):
        if 1 < t < self.BALLOON_POP:
            self.x += math.sin(t * 1.3) * 25 * dt          # drifts with the wind
        if t >= self.BALLOON_POP and self.once("popfall"):
            wx, wy = self.wp(CX + self.dir * 2, 1.5)
            self.puff(wx, wy, 10, (RED, "#FF9A9E"), 200, (60, 220))
            self.balloon_fall_t = self.clock
            self.fy -= self.lift_balloon(self.BALLOON_POP - 0.001) * PX
            self.support = None
            self.vx, self.vy = 0.0, -150.0
            self.set_state("air")                          # ...and down he goes

    def pose_balloon(self, P, t, d):
        self.set_arm(P, 1, 0.0)
        P["legs"] = [2.4] * 4
        P["leg_dx"] = [0.3 * math.sin(t * 4)] * 4
        if t > 1:
            P["eye_dy"] = 0.4 if t > 4 else -0.3          # looks down once it gets high
            P["eyes"] = "^" if t < 4 else "open"

    def front_balloon(self, t, d, g):
        hx, hy = g["hf"]
        bx, by = hx + d * 0.8, max(g["bt"] - 7.5, 0.2)
        self.L([(hx, hy - 0.8), (bx, by + 3.6)], "#DDDDDD", 1)
        self.O(bx - 1.5, by, 3, 3.6, fill=RED)
        self.R(bx - 0.9, by + 0.6, 0.5, 0.8, "#FF9A9E")
        if t > 5.5:
            self.T(CX - 6 * d, g["bt"] + 1, "uh oh", 6, "#FFFFFF")

    def pose_raincloud(self, P, t, d):
        if t < 4.5:
            P["eye_dy"] = 0.45
            P["eye_h"] = 0.7
            P["arm_l"] = P["arm_r"] = 3.0
            P["legs"] = [1.7] * 4
        else:
            P["eyes"] = "^"
            P["arm_l"] = P["arm_r"] = 0.0

    def lift_raincloud(self, t):
        return abs(math.sin((t - 4.6) * 5)) * 1.0 if t > 4.6 else 0

    def front_raincloud(self, t, d, g):
        bt = g["bt"]
        cy = bt - 6.0
        if t < 4.5:
            for x, y, w, h in ((-4, 0, 4, 2.6), (-1.5, -1.0, 4, 3), (1, 0, 3.6, 2.6)):
                self.O(CX + x, cy + y, w, h, fill="#8A8F98")
            for i in range(6):
                x = CX - 3.5 + i * 1.4
                y = cy + 2.2 + ((t * 2.2 + i * 0.37) % 1) * (bt - cy - 2.6)
                self.R(x, y, 0.2, 0.8, "#6FA8FF")
        else:
            sx, sy = CX + 3.5, cy
            self.O(sx - 1.6, sy - 1.6, 3.2, 3.2, fill=GOLD)
            for a in range(0, 360, 45):
                ra = math.radians(a + t * 60)
                self.L([(sx + math.cos(ra) * 2.0, sy + math.sin(ra) * 2.0),
                        (sx + math.cos(ra) * 2.8, sy + math.sin(ra) * 2.8)], GOLD, 2)

    def pose_broom(self, P, t, d):
        P["arm_l"] = P["arm_r"] = 3.0
        P["arm_lx"] = P["arm_rx"] = 0.8 * d
        P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.4
        self.steps(P, t, d, 0.25, 0.3, 0.3, 0.1)

    def speed_broom(self, t):
        return 25

    def upd_broom(self, dt, t):
        self.dust_timer -= dt
        if self.dust_timer <= 0:
            self.dust_timer = 0.15
            self.puff(self.x + self.dir * 5 * PX, self.fy, 2, DUST, 70, (20, 80), (0.4, 0.8), 0.5)

    def front_broom(self, t, d, g):
        sweep = math.sin(t * 6) * 1.0
        top = (CX - d * 1.0, g["bt"] + 1.5)
        bot = (CX + d * (4.8 + sweep), FEET - 0.9)
        self.L([top, bot], WOOD, 3)
        self.Pg([(bot[0] - 1.0, bot[1] - 0.2), (bot[0] + 1.0, bot[1] - 0.2),
                 (bot[0] + 1.4, FEET), (bot[0] - 1.4, FEET)], "#D9B44A")

    def telescope_angle(self):
        cx, cy = self.cursor
        a = math.atan2(cy - (self.fy - 7 * PX), cx - self.x)
        a = min(max(a, math.radians(-160)), math.radians(-20))
        return a

    def pose_telescope(self, P, t, d):
        a = self.telescope_angle()
        self.dir = 1 if math.cos(a) >= 0 else -1
        P["eye_dx"], P["eye_dy"] = 0.34 * self.dir, -0.3
        self.set_arm(P, 1, 2.0, 0.6)

    def front_telescope(self, t, d, g):
        a = self.telescope_angle()
        ex = (g["bl"] + g["bw"] - 1.3) if d > 0 else (g["bl"] + 1.3)
        start = (ex + d * 1.0, g["ey"] + 0.5)
        end = (start[0] + math.cos(a) * 5.5, start[1] + math.sin(a) * 5.5)
        mid = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
        for fx in (-1.5, 0, 1.5):
            self.L([mid, (mid[0] + fx, FEET)], "#555555", 2)
        self.L([start, end], "#3A4A6A", 5)
        self.L([(end[0] - math.cos(a) * 0.6, end[1] - math.sin(a) * 0.6), end], "#8FB0E0", 6)
        if t > 3.5 and int(t / 0.3) % 2:
            self.T(CX, g["bt"] - 2.5, "!", 9, GOLD)

    def pose_paperplane(self, P, t, d):
        if t < 2.0:
            P["arm_l"] = P["arm_r"] = 3.0
            P["arm_lx"], P["arm_rx"] = 0.9, -0.9
            P["eye_dy"] = 0.5
        elif t < 2.4:
            self.set_arm(P, 1, 0.6, -0.6)
        else:
            P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.3
            if t > 3.5:
                P["eyes"] = "^"

    def front_paperplane(self, t, d, g):
        bt = g["bt"]
        if t < 1.0:
            self.R(CX - 2, bt + 2.6, 4, 2.6, "#FFFFFF")
        elif t < 2.4:
            k = 1 - (t - 1.0) / 1.4 * 0.5
            self.Pg([(CX - 1.8 * k, bt + 3.6), (CX + 1.8 * k, bt + 3.6), (CX, bt + 2.4)], "#FFFFFF")
        else:
            p = t - 2.4
            px_ = CX + d * (4 + p * 9)
            py_ = bt + 1 - p * 2.5 + math.sin(p * 4) * 0.6
            self.Pg([(px_ + d * 1.3, py_), (px_ - d * 1.0, py_ - 0.6),
                     (px_ - d * 0.6, py_), (px_ - d * 1.0, py_ + 0.5)], "#FFFFFF", "#BBBBBB")

    def pose_headphones(self, P, t, d):
        beat = int(t / 0.45) % 2
        if beat:
            P.update(bh=5.7, bw=8.3)
        P["eyes"] = "^" if int(t / 1.8) % 2 else "open"
        P["eye_h"] = 0.25 if P["eyes"] == "open" else 1.0
        P["shake"] = 0.3 * math.sin(t * math.pi / 0.45)

    def lift_headphones(self, t):
        return 0.4 if int(t / 0.45) % 2 == 0 else 0

    def front_headphones(self, t, d, g):
        bl, bw, bt = g["bl"], g["bw"], g["bt"]
        self.L([(bl + 0.2, bt + 1.6), (bl + 0.5, bt - 0.8), (bl + bw - 0.5, bt - 0.8),
                (bl + bw - 0.2, bt + 1.6)], "#222222", 3)
        self.R(bl - 0.5, bt + 1.0, 1.1, 2.0, "#333333")
        self.R(bl + bw - 0.6, bt + 1.0, 1.1, 2.0, "#333333")
        self.R(bl - 0.3, bt + 1.3, 0.5, 1.4, RED)
        self.R(bl + bw - 0.2, bt + 1.3, 0.5, 1.4, RED)
        for i in range(2):
            p = (t * 0.6 + i / 2) % 1
            self.T(CX + (5 if i else -5) + math.sin(p * 8) * 0.6, bt - 1 - 6 * p,
                   "♪", 9, ("#FFFFFF", GOLD)[i], SYM)

    # ======================================================================
    # ======================= GYM (with ninja bandana) =====================
    # ======================================================================
    def bandana(self, t, d, g):
        bl, bw, bt = g["bl"], g["bw"], g["bt"]
        self.R(bl - 0.1, bt + 0.25, bw + 0.2, 0.75, "#1A1A1A")
        kx = bl - 0.1 if d > 0 else bl + bw + 0.1
        f1 = 0.35 * math.sin(t * 9)
        f2 = 0.35 * math.sin(t * 9 + 1.3)
        self.R(kx - 0.4, bt + 0.2, 0.8, 0.85, "#1A1A1A")
        self.Pg([(kx, bt + 0.5), (kx - d * 2.6, bt + 0.1 + f1), (kx - d * 2.4, bt + 0.7 + f1)], "#1A1A1A")
        self.Pg([(kx, bt + 0.7), (kx - d * 2.2, bt + 1.0 + f2), (kx - d * 1.9, bt + 1.5 + f2)], "#1A1A1A")

    def upd_sweat(self, dt, rate=1.5):
        if random.random() < dt * rate:
            self.puff(self.x + random.uniform(-3, 3) * PX, self.fy - 8 * PX - self.lift(), 1,
                      ("#8FD3FF",), 40, (40, 90), (0.5, 0.7), 0.5)

    # --- pull-ups: two good reps, the third one fails ---
    BAR_Y = 3.4

    def pullup_rise(self, t):
        if t < 0.6:
            return 1.0 * ease(t / 0.6)
        for t0, up, down in ((0.6, 1.2, 0.8), (2.6, 1.7, 0.7)):
            if t0 <= t < t0 + up:
                return 1.0 + 2.8 * ease((t - t0) / up)
            if t0 + up <= t < t0 + up + down:
                return 3.8 - 2.8 * ease((t - t0 - up) / down)
        if 5.0 <= t < 7.4:
            return 1.0 + 1.5 * ease((t - 5.0) / 2.4)
        if 7.4 <= t < 7.8:
            return 2.5 - 1.5 * ease((t - 7.4) / 0.4)
        if 7.8 <= t < 8.4:
            return 1.0
        return max(0.0, 1.0 - (t - 8.4) / 0.3)

    def pose_pullups(self, P, t, d):
        r = self.pullup_rise(t)
        P["rise"], P["legs"] = r, [2.2] * 4
        body_top = FEET - r - 2.2 - 6
        if t < 8.4:
            P["arm_l"] = P["arm_r"] = (self.BAR_Y - 0.6 - body_top)
            P["arm_lx"], P["arm_rx"] = 1.0, -1.0
            P["eye_dy"] = -0.45
            if 5.0 <= t < 7.4:
                P["shake"] = 0.2 if int(t / 0.05) % 2 else -0.2
                P["eye_h"] = 0.4
            if 7.4 <= t < 8.4:
                P["eyes"] = "x"
        else:
            P["eyes"] = "x"
            P["arm_l"] = P["arm_r"] = 3.0

    def upd_pullups(self, dt, t):
        self.upd_sweat(dt, 2.5 if t > 5 else 1.0)

    def back_pullups(self, t, d, g):
        for x in (CX - 8.5, CX + 8.1):
            self.R(x, self.BAR_Y, 0.5, FEET - self.BAR_Y, "#6A6A6A")
        self.R(CX - 8.7, self.BAR_Y - 0.3, 17.4, 0.5, "#A8A8A8")

    def front_pullups(self, t, d, g):
        self.bandana(t, d, g)
        n = 1 if t < 2.6 else 2 if t < 5.0 else 3
        txt = str(n) if n < 3 else ("3..." if t < 7.4 else "nope")
        self.T(CX + 7 * d, 1.6, txt, 8, "#FFFFFF" if n < 3 else RED)

    # --- bench press (seen from his feet end) ---
    def bench_k(self, t):
        for t0, up, down in ((0.8, 0.7, 0.6), (2.1, 0.8, 0.6), (3.5, 1.0, 0.6), (5.1, 2.6, 0.9)):
            cap = 0.7 if up > 2 else 1.0
            if t0 <= t < t0 + up:
                return ease((t - t0) / up) * cap
            if t0 + up <= t < t0 + up + down:
                return (1 - ease((t - t0 - up) / down)) * cap
        return 0.0

    def pose_bench(self, P, t, d):
        k = self.bench_k(t)
        P.update(bh=4.2, bw=9.0, legs=[0.0] * 4, rise=2.4)
        body_top = FEET - 2.4 - 4.2
        bar_y = body_top - 1.4 - 3.0 * k
        P["arm_l"] = P["arm_r"] = (bar_y + 0.2 - body_top) / (4.2 / 6.0)
        P["arm_lx"], P["arm_rx"] = 0.6, -0.6
        P["eye_dy"] = -0.35
        if 5.1 <= t < 8.6:
            P["shake"] = 0.18 if int(t / 0.05) % 2 else -0.18
            P["eye_h"] = 0.4
        if t > 8.6:
            P["eyes"] = "^"

    def upd_bench(self, dt, t):
        self.upd_sweat(dt, 2.0 if t > 5 else 0.8)

    def back_bench(self, t, d, g):
        self.R(CX - 6, FEET - 2.4, 12, 0.9, "#333333")
        self.R(CX - 5.5, FEET - 1.5, 0.7, 1.5, "#555555")
        self.R(CX + 4.8, FEET - 1.5, 0.7, 1.5, "#555555")
        for x in (CX - 7.6, CX + 7.0):
            self.R(x, FEET - 9.5, 0.6, 7.1, "#555555")

    def front_bench(self, t, d, g):
        self.bandana(t, d, g)
        k = self.bench_k(t)
        bar_y = g["bt"] - 1.4 - 3.0 * k
        self.R(CX - 11, bar_y, 22, 0.45, "#A8A8A8")
        for side in (-1, 1):
            for off, h, c in ((9.4, 3.2, "#222222"), (10.4, 2.4, "#3A3A3A")):
                x = CX + side * off - (0 if side > 0 else 0.9)
                self.R(x, bar_y + 0.22 - h / 2, 0.9, h, c)
        rep = sum(1 for t0 in (1.5, 2.9, 4.5, 8.6) if t > t0)
        self.T(CX, 1.4, str(rep) if t < 5.1 or t > 8.6 else "4...", 8, "#FFFFFF")

    # --- dumbbell curls, alternating arms ---
    def pose_curls(self, P, t, d):
        slow = t > 5.5
        per = 1.6 if slow else 1.0
        k = (1 - math.cos(t * 2 * math.pi / per)) / 2
        P["arm_l"] = 3.2 - 2.8 * k
        P["arm_r"] = 3.2 - 2.8 * (1 - k)
        P["eye_dy"] = -0.2
        if slow:
            P["shake"] = 0.15 if int(t / 0.05) % 2 else -0.15
            P["eye_h"] = 0.4

    def upd_curls(self, dt, t):
        self.upd_sweat(dt, 2.0)

    def front_curls(self, t, d, g):
        self.bandana(t, d, g)
        for hx, hy in (g["hl"], g["hr"]):
            self.R(hx - 1.6, hy + 0.5, 3.2, 0.55, "#9A9A9A")
            self.R(hx - 2.0, hy - 0.2, 0.8, 2.0, "#222222")
            self.R(hx + 1.2, hy - 0.2, 0.8, 2.0, "#222222")
        self.T(CX + 7 * d, 1.6, str(int(t / 1.0) + 1) if t < 5.5 else "...", 8, "#FFFFFF")

    # ======================================================================
    # ============================== SILLY =================================
    # ======================================================================
    def pose_measure(self, P, t, d):
        P["eye_dx"] = 0.34 * d
        if t < 1.0:
            P["eye_dy"] = -0.4
        elif t < 3.4:
            k = ease((t - 1.0) / 1.6) if t < 2.8 else 1.0
            P.update(bh=6 + 8 * k, legs=[2 + 0.4 * k] * 4, bw=8 - 1.0 * k)
            P["eye_dy"] = -0.4
        elif t < 4.0:
            k = (t - 3.4) / 0.6
            P.update(bh=6 - 1.5 * math.sin(math.pi * k), bw=8 + 1.5 * math.sin(math.pi * k))
        elif t < 6.4:
            k = ease((t - 4.0) / 1.6) if t < 5.6 else 1.0
            P.update(bw=8 + 12 * k, bh=6 - 1.0 * k)
        elif t < 7.2:
            k = ease((t - 6.4) / 0.5)
            P.update(bw=8 + 10 * k, bh=6 + 7 * k)
            P["eyes"] = "x" if t > 6.9 else "open"
        else:
            P["eyes"] = "^"

    def upd_measure(self, dt, t):
        if t > 7.2 and self.once("pop"):
            self.puff(self.x, self.fy - 5 * PX, 10, DUST + (LIGHT,), 200, (100, 300))

    def front_measure(self, t, d, g):
        x = self.M(10.6, 0.8)
        top = 1.0
        self.R(x, top, 0.8, FEET - top, GOLD)
        for i in range(int(FEET - top)):
            self.R(x, FEET - i - 0.1, 0.5 if i % 2 else 0.8, 0.15, "#5A4A00")
        if 2.8 < t < 3.4:
            self.T(CX, 0.8, "taller?", 6, "#FFFFFF")
        elif 5.6 < t < 6.4:
            self.T(CX, 0.8, "wider?", 6, "#FFFFFF")
        elif t > 7.2:
            self.T(CX, 1.4, "nah, I'm good", 6, GOLD)

    def pose_stretchy(self, P, t, d):
        cx, cy = self.cursor
        P["eye_dx"] = 0.34 if cx > self.x else -0.34
        P["eye_dy"] = -0.45
        k = math.sin(math.pi * min(t / 5.0, 1))
        P.update(bh=6 + 8 * k, bw=8 - 2.5 * k)
        self.set_arm(P, 1, -1.5 * k)
        if t > 5.2:
            P["eyes"] = "^"

    def front_stretchy(self, t, d, g):
        if 1.5 < t < 4.5 and int(t / 0.3) % 2:
            self.T(CX + 5 * d, 1.4, "almost...", 6, "#FFFFFF")

    def pose_squish(self, P, t, d):
        if t < 1.2:
            k = ease(t / 1.2)
            P.update(bh=6 - 4.6 * k, bw=8 + 8 * k, legs=[2 - 1.8 * k] * 4)
        elif t < 3.0:
            P.update(bh=1.4, bw=16, legs=[0.2] * 4)
            P["eye_dx"] = [-0.34, 0.34][int(t / 0.4) % 2]
            P["eye_dy"] = -0.6
        elif t < 3.5:
            k = ease((t - 3.0) / 0.5)
            P.update(bh=1.4 + 7 * k, bw=16 - 9.5 * k)
        else:
            k = max(0.0, 1 - (t - 3.5) / 1.2)
            w = math.cos((t - 3.5) * 14)
            P.update(bh=6 + 2.5 * k * w, bw=8 - 1.5 * k * w)
            P["eyes"] = "^"

    def lift_squish(self, t):
        return para((t - 3.2) / 0.7, 3.0) if 3.2 < t < 3.9 else 0

    def front_squish(self, t, d, g):
        if 3.3 < t < 4.3:
            self.T(CX, 1.4, "BOING!", 8, GOLD)

    # --- mimic a logo / icon he is standing on (its colour + proportions) ---
    def pose_mimic(self, P, t, d):
        P["eye_dy"] = 0.5 if t < 0.6 else 0
        if 0.6 <= t < 1.0:
            P["shake"] = 0.4 if int(t / 0.04) % 2 else -0.4
        if 1.0 <= t < 4.2:
            a = self.mimic_aspect
            P.update(color=self.mimic_color, bw=min(max(8 * a ** 0.6, 4), 16),
                     bh=min(max(6 / a ** 0.4, 3), 11), legs=[1.2] * 4)
            P["eyes"] = "^"
            P["arm_l"] = P["arm_r"] = 0.0 if int(t / 0.5) % 2 else 1.0

    def upd_mimic(self, dt, t):
        if t > 4.2 and self.once("unmimic"):
            self.puff(self.x, self.fy - 4 * PX, 10, (self.mimic_color, LIGHT), 160, (80, 240))

    def front_mimic(self, t, d, g):
        if 1.2 < t < 4.2:
            self.T(CX, 1.4, "ta-da!", 8, GOLD)

    # --- late at night: point at the clock ---
    def front_clockpoint(self, t, d, g):
        hx, hy = g["hf"]
        self.T(hx + d * 2.0, FEET - 2.6 + 0.4 * math.sin(t * 8), "↘" if d > 0 else "↙", 11, GOLD, SYM)
        if t < 3.5:
            self.T(CX - d * 1.5, 1.4, "it's late!", 6, "#FFFFFF")
        elif t > 5.0:
            self.T(CX - d * 1.5, 1.4, "go to sleep?", 6, "#FFFFFF")
            self.T(CX - d * 6, 4.0, "z", 7 + int(t * 3) % 3, LIGHT)

    def front_tbhang(self, t, d, g):
        if self.st > self.dur - 0.5:
            return
        for hx, hy in (g["hl"], g["hr"]):
            self.R(hx - 0.8, hy - 1.2, 1.6, 0.5, self.dark_color)

    front_lhang = front_tbhang

    # ======================================================================
    # ========= POWER FORMS (Pixbot gets a power; original designs) =========
    # ======================================================================
































    # ======================================================================
    # ============================ REACTIONS ===============================
    # ======================================================================
    # --- PC security guard: checklist, patrols the taskbar tapping icons ---
    def pose_guard(self, P, t, d):
        if t < 3.0:                                       # reads the checklist
            self.set_arm(P, 1, 2.6, -1.4)
            self.set_arm(P, -1, 2.8, 1.0)
            P["eye_dy"] = 0.5
        elif t < 12.0:
            c = (t - 3.0) % 2.2
            if c < 1.2:
                self.steps(P, t, d, 0.15, 0.5, 0.5, 0.2)
                P["eye_dx"] = 0.34 * d
            else:                                         # pokes the icon under him
                poke = (c - 1.2) < 0.5
                self.set_arm(P, 1, 4.6 if poke else 3.2, 0.8)
                P.update(bh=5.4, legs=[1.6] * 4)
                P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.6
        else:                                             # salute
            self.set_arm(P, 1, -0.6, -1.6)
            P["eyes"] = "^"

    def speed_guard(self, t):
        return 75 if 3.0 <= t < 12.0 and ((t - 3.0) % 2.2) < 1.2 else 0

    def front_guard(self, t, d, g):
        bl, bw, bt = g["bl"], g["bw"], g["bt"]
        self.R(bl - 0.2, bt - 1.1, bw + 0.4, 1.3, "#1F2A44")             # guard cap
        self.R(bl + bw - 0.8 if d > 0 else bl - 1.8, bt - 0.05, 2.6, 0.4, "#141C2E")
        self.R(CX - 0.4, bt - 0.9, 0.8, 0.6, GOLD)
        self.R(CX + 1.2 * d - 0.4, bt + 3.4, 0.8, 0.9, GOLD)             # badge
        if t < 3.0:
            x = CX - 2.0
            self.R(x, bt + 2.4, 4.0, 3.4, "#8B5A2B")                     # clipboard
            self.R(x + 0.3, bt + 2.8, 3.4, 2.8, "#FFFFFF")
            self.R(x + 1.4, bt + 2.2, 1.2, 0.4, GREY)
            for i in range(3):
                yy = bt + 3.1 + i * 0.85
                self.R(x + 0.6, yy, 0.5, 0.5, "#CCCCCC")
                self.R(x + 1.4, yy + 0.15, 2.0, 0.2, "#999999")
                if t > 0.8 + i * 0.7:
                    self.T(x + 0.85, yy + 0.2, "✓", 6, "#2FA84F", SYM)
        elif t < 12.0:
            c = (t - 3.0) % 2.2
            if c >= 1.4:
                self.T(CX + d * 3.2, FEET - 4.2 - (c - 1.4) * 2, "✓", 9, "#3FD06A", SYM)
        else:
            self.T(CX, 1.4, "all secure!", 7, GOLD)

    # --- pulls up a chair and eats popcorn while you watch ---
    def popcorn_k(self, t):
        return min(t / 1.0, (self.dur - t) / 1.0, 1.0)

    def pose_popcorn(self, P, t, d):
        k = self.popcorn_k(t)
        P["rise"] = 1.6 * k
        P["legs"] = [2.0 - 1.0 * k] * 4
        P["eye_dy"] = -0.35                                # eyes on the video
        P["eye_dx"] = 0.0
        c = t % 2.6
        if k >= 1.0 and 1.6 < c < 2.2:                     # handful of popcorn
            self.set_arm(P, 1, 1.0, -1.8)
            P["mouth"] = 0.6 if c > 1.9 else 0.2
        else:
            self.set_arm(P, 1, 3.0, -0.6)
        self.set_arm(P, -1, 3.2, 1.6)
        if int(t / 9) % 4 == 3 and (t % 9) < 1.0:
            P["eyes"] = "^"

    def upd_popcorn(self, dt, t):
        if t > 3 and self.dur > t + 1.2 and self.context not in ("video", "music") \
                and self.dur > 1000:
            self.dur = t + 1.0                             # you stopped watching: put it away
        if t % 2.6 > 2.15 and self.once(f"crumb{int(t / 2.6)}"):
            self.puff(self.x + self.dir * 2 * PX, self.fy - 6 * PX - self.lift(), 2,
                      ("#FFF6D8", "#F4D35E"), 60, (30, 80), (0.4, 0.6))

    def back_popcorn(self, t, d, g):
        k = self.popcorn_k(t)
        if k <= 0:
            return
        cx = CX - d * (1 - k) * 10
        seat = FEET - 2.6
        self.R(cx - 4.5, seat, 9, 0.8, "#8B5A2B")                        # seat
        bx = cx - d * 4.5 - (0.8 if d > 0 else 0)
        self.R(bx, seat - 6.0, 0.8, 6.0, "#7A4A20")                       # chair back
        for lx_ in (cx - 4.2, cx + 3.6):
            self.R(lx_, seat + 0.8, 0.6, FEET - seat - 0.8, "#7A4A20")

    def front_popcorn(self, t, d, g):
        if self.popcorn_k(t) < 1.0:
            return
        hx, hy = g["hb"]
        x = hx - 1.2
        y = hy - 1.6
        self.Pg([(x, y), (x + 2.6, y), (x + 2.2, y + 2.6), (x + 0.4, y + 2.6)], "#FFFFFF")
        for i in range(3):
            self.R(x + 0.35 + i * 0.75, y, 0.35, 2.6, RED)
        for i in range(4):
            self.O(x + 0.1 + i * 0.6, y - 0.7 + (i % 2) * 0.2, 0.8, 0.8, fill="#FFF6D8")

    # --- listens closely to music / a video ---
    def pose_listen(self, P, t, d):
        P["lean"] = 0.3
        self.set_arm(P, 1, 0.5, -1.0)                       # hand cupped by his "ear"
        P["eye_h"] = 0.25
        beat = int(t / 0.5) % 2
        if beat:
            P.update(bh=5.8)
        if t > 5.5:
            P["eyes"] = "^"
            P["eye_h"] = 1.0

    def lift_listen(self, t):
        return 0.3 if int(t / 0.5) % 2 == 0 else 0

    def front_listen(self, t, d, g):
        for i in range(3):
            p = (t * 0.6 + i / 3) % 1
            x = CX + d * (12 - 7 * p)
            y = g["bt"] + 0.5 - math.sin(p * 6) * 0.8
            self.T(x, y, "♪" if i % 2 else "♫", 9, ("#FFFFFF", GOLD, "#8FD3FF")[i], SYM)

    # --- proposing to your cursor (move the mouse = "yes") ---
    def pose_propose(self, P, t, d):
        yes = getattr(self, "propose_yes", None)
        if t < 5.0 or yes is None:
            k = ease(t / 0.6)                             # down on one knee
            if d > 0:
                P["legs"] = [2.0, 2.0, 2.0 - 1.2 * k, 2.0 - 1.2 * k]
            else:
                P["legs"] = [2.0 - 1.2 * k, 2.0 - 1.2 * k, 2.0, 2.0]
            P["rise"] = -0.6 * k
            P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.45
            if t > 0.9:
                self.set_arm(P, 1, 1.4, 1.2)               # holding out the ring
            if 2.0 < t < 5.0 and int(t / 0.8) % 2:
                P["eye_h"] = 0.7                           # nervous blink
        elif yes:                                          # YES!
            P["eyes"] = "^"
            P["arm_l"] = P["arm_r"] = 0.0
        else:                                              # ...no answer
            P["eye_dy"] = 0.55
            P["legs"] = [1.8] * 4
            P["arm_l"] = P["arm_r"] = 3.2

    def lift_propose(self, t):
        if t >= 5.0 and getattr(self, "propose_yes", None):
            return abs(math.sin((t - 5.0) * 6)) * 1.6
        return 0

    def front_propose(self, t, d, g):
        yes = getattr(self, "propose_yes", None)
        hx, hy = g["hf"]
        if t > 0.9 and (t < 5.0 or yes is None or yes):
            bx, by = hx + d * 0.9 - 0.9, hy - 1.6
            self.R(bx, by + 0.7, 1.8, 1.1, "#8E1B2E")      # little ring box
            opened = t > 1.6
            if opened:
                self.R(bx, by - 0.2, 1.8, 0.9, "#6E1424")   # lid flipped up
                self.O(bx + 0.45, by + 0.15, 0.9, 0.9, outline=GOLD, width=2)
                if int(t / 0.25) % 2:
                    self.T(bx + 1.3, by - 0.5, "*", 8, "#FFFFFF")
            else:
                self.R(bx, by + 0.3, 1.8, 0.5, "#6E1424")
        if 1.6 < t < 5.0:
            for i in range(3):
                p = (t * 0.5 + i / 3) % 1
                self.T(CX + (i - 1) * 3 + math.sin(p * 6) * 0.6, g["bt"] - 1 - 6 * p, "♥", 8,
                       ("#FF6B8B", "#FF9AB0", "#FF4D6D")[i], SYM)
            if t > 2.0:
                self.T(CX - 6 * d, 1.4, "will you...?", 6, "#FFFFFF")
        elif t >= 5.0 and yes:
            self.T(CX, 1.4, "YES!!", 9, "#FF6B8B")
            for i in range(6):
                a = t * 3 + i
                self.T(CX + math.cos(a) * 7, g["bt"] - 1 + math.sin(a * 1.3) * 2, "♥", 8,
                       ("#FF6B8B", "#FF9AB0")[i % 2], SYM)
        elif t >= 5.0:
            self.T(CX, 1.4, "...ok", 6, "#AAAAAA")

    # ======================================================================
    # ============================ MORE GYM ================================
    # ======================================================================
    def pushup_k(self, t):
        per = 1.1 if t < 5.5 else 2.2
        return (1 - math.cos(2 * math.pi * t / per)) / 2      # 0 = up, 1 = down

    def pose_pushups(self, P, t, d):
        k = self.pushup_k(t)
        P.update(bh=4.4, bw=9.0, legs=[0.1] * 4, rise=2.6 - 1.8 * k)
        P["arm_l"] = P["arm_r"] = 2.6
        P["eye_dy"] = 0.4
        if t > 5.5:
            P["shake"] = 0.15 if int(t / 0.05) % 2 else -0.15
            P["eye_h"] = 0.4

    def upd_pushups(self, dt, t):
        self.upd_sweat(dt, 2.0 if t > 5.5 else 0.8)

    def back_pushups(self, t, d, g):
        y = g["ar"] + 1.0
        for x in (g["bl"] - 2, g["bl"] + g["bw"]):           # straight arms down to the floor
            self.R(x, y, 2, FEET - y)

    def front_pushups(self, t, d, g):
        self.bandana(t, d, g)
        n = int(t / 1.1) + 1 if t < 5.5 else 5
        self.T(CX + 7 * d, 1.6, str(n) if t < 5.5 else "5...", 8, "#FFFFFF")

    def pose_jumprope(self, P, t, d):
        if t < 5.8:
            P["arm_l"], P["arm_r"] = 3.0, 3.0
            P["arm_lx"], P["arm_rx"] = -0.6, 0.6
            P["legs"] = [2.0] * 4
        else:                                               # tangled up
            P["eyes"] = "x"
            P["legs"] = [1.2, 2.0, 1.2, 2.0]
            P["shake"] = 0.3 if int(t / 0.06) % 2 else -0.3

    def lift_jumprope(self, t):
        if t >= 5.8:
            return 0
        u = (t % 0.5) / 0.5
        return para((u - 0.3) / 0.5, 1.6) if 0.3 < u < 0.8 else 0

    def front_jumprope(self, t, d, g):
        self.bandana(t, d, g)
        (lx, ly), (rx, ry) = g["hl"], g["hr"]
        if t < 5.8:
            a = 2 * math.pi * ((t % 0.5) / 0.5)
            low = FEET + 0.3 + g["Lu"]
            y = (g["bt"] - 3.0) + (low - (g["bt"] - 3.0)) * (1 - math.cos(a)) / 2
            self.cv.create_line(lx * PX, ly * PX, CX * PX, y * PX, rx * PX, ry * PX,
                                fill="#E5484D", width=2, smooth=True)
        else:
            self.L([(lx, ly), (CX - 1, FEET - 1), (CX + 1, FEET - 0.5), (rx, ry)], "#E5484D", 2)
            self.T(CX, 1.6, "oops", 7, "#FFFFFF")

    def pose_boxing(self, P, t, d):
        P["legs"] = [1.8] * 4
        P["brows"] = True
        P["eye_dx"] = 0.34 * d
        punch = int(t / 0.3) % 2
        self.set_arm(P, 1, 2.0, 2.4 if punch else 0.2)
        self.set_arm(P, -1, 2.2, 6.0 if not punch else -0.2)

    def upd_boxing(self, dt, t):
        self.upd_sweat(dt, 1.2)

    def back_boxing(self, t, d, g):
        swing = 0.6 * math.sin(t * 10)
        bx = self.M(9.0, 3.2) + swing * d
        self.L([(bx + 1.6 - swing * d, 0), (bx + 1.6, 3.0)], "#888888", 2)
        self.R(bx, 3.0, 3.2, 8.5, "#B03030")
        self.R(bx, 3.0, 3.2, 0.6, "#802020")
        self.R(bx, 10.9, 3.2, 0.6, "#802020")

    def front_boxing(self, t, d, g):
        self.bandana(t, d, g)
        for hx, hy in (g["hl"], g["hr"]):
            self.R(hx - 1.2, hy - 1.2, 2.4, 2.4, "#C0392B")        # gloves
        if int(t / 0.3) % 4 == 1:
            self.T(self.M(8.5, 0), 4.0, "pow!", 7, GOLD)

    def deadlift_k(self, t):
        if t < 1.0:
            return 0.0
        if t < 4.5:
            return ease((t - 1.0) / 3.5)
        if t < 6.0:
            return 1.0
        return max(0.0, 1 - (t - 6.0) / 0.3)

    def pose_deadlift(self, P, t, d):
        k = self.deadlift_k(t)
        P.update(bh=6 - 1.2 * (1 - k), legs=[1.2 + 0.8 * k] * 4)
        bar_y = FEET - 1.4 - 4.0 * k
        body_top = FEET - P["legs"][0] - P["bh"]
        P["arm_l"] = P["arm_r"] = (bar_y - 1.0 - body_top) / (P["bh"] / 6)
        P["arm_lx"], P["arm_rx"] = 0.8, -0.8
        P["eye_dy"] = -0.2
        if 1.0 < t < 4.5:
            P["shake"] = 0.2 if int(t / 0.05) % 2 else -0.2
            P["eye_h"] = 0.4
        if 4.5 <= t < 6.0:
            P["eyes"] = "^"

    def upd_deadlift(self, dt, t):
        self.upd_sweat(dt, 2.0)
        if t > 6.0 and self.once("clang"):
            self.puff(self.x, self.fy, 12, DUST, 260, (60, 200))

    def front_deadlift(self, t, d, g):
        self.bandana(t, d, g)
        k = self.deadlift_k(t)
        bar_y = FEET - 1.4 - 4.0 * k
        self.R(CX - 10, bar_y, 20, 0.45, "#A8A8A8")
        for side in (-1, 1):
            x = CX + side * 8.6 - (0 if side > 0 else 1.0)
            self.R(x, bar_y + 0.22 - 1.4, 1.0, 2.8, "#222222")
        if 4.5 <= t < 6.0:
            self.T(CX, 1.6, "+1", 8, GOLD)
        elif t >= 6.0:
            self.T(CX, 1.6, "CLANG", 8, "#FFFFFF")

    # ======================================================================
    # ============================ MORE SILLY ==============================
    # ======================================================================
    def pose_dizzyspin(self, P, t, d):
        if t < 2.5:
            P["rot"] = 360 * (t / 2.5) ** 2 * 4
            P["arm_l"] = P["arm_r"] = 0.6
        else:
            P["shake"] = 1.0 * math.sin(t * 5)
            P["lean"] = 0.5 * math.sin(t * 5 + 1)
            P["hide_eyes"] = True

    def front_dizzyspin(self, t, d, g):
        if t >= 2.5:
            for ex in (g["bl"] + 1.5, g["bl"] + g["bw"] - 1.5):
                self.T(ex + g["P"]["shake"] * 0, g["ey"] + 0.5, "@", 8, EYE)
            for i in range(3):
                a = t * 4 + i * 2.1
                self.T(CX + math.cos(a) * 4, g["bt"] - 1.2 + math.sin(a) * 0.8, "★", 7, GOLD, SYM)

    def pose_trip(self, P, t, d):
        if t < 1.2:
            self.steps(P, t, d, 0.13, 0.5, 0.5, 0.25)
            P["eye_dx"] = 0.34 * d
        elif t < 1.5:
            P["rot"] = 85 * d * ease((t - 1.2) / 0.3)
            P["arm_l"] = P["arm_r"] = 0.0
        elif t < 3.6:
            P["rot"] = 85 * d
            P["eyes"] = "x"
            P["rise"] = -1.0
        else:
            P["rot"] = 85 * d * (1 - ease((t - 3.6) / 0.5))
            P["eyes"] = "^" if t > 4.2 else "open"

    def speed_trip(self, t):
        return 110 if t < 1.3 else 0

    def front_trip(self, t, d, g):
        if 1.6 < t < 3.6:
            self.T(CX, 2.2, "ow", 8, "#FFFFFF")

    def pose_peekaboo(self, P, t, d):
        c = t % 2.0
        if c < 1.3:                                         # hands over his eyes
            P["arm_l"] = P["arm_r"] = 0.6
            P["arm_lx"], P["arm_rx"] = 2.4, -2.4
            P["hide_eyes"] = True
        else:
            P["arm_l"] = P["arm_r"] = 0.0
            P["arm_lx"], P["arm_rx"] = -0.6, 0.6
            P["eyes"] = "^"

    def lift_peekaboo(self, t):
        c = t % 2.0
        return para((c - 1.3) / 0.4, 1.2) if 1.3 < c < 1.7 else 0

    def front_peekaboo(self, t, d, g):
        if (t % 2.0) >= 1.3:
            self.T(CX, g["bt"] - 2, "boo!", 8, "#FFFFFF")

    def pose_moonwalk(self, P, t, d):
        ph = int(t / 0.25) % 2
        P["legs"] = [2.0, 1.4, 2.0, 1.4] if ph else [1.4, 2.0, 1.4, 2.0]
        P["leg_dx"] = [0.5 * d, -0.5 * d, 0.5 * d, -0.5 * d] if ph else [-0.5 * d, 0.5 * d, -0.5 * d, 0.5 * d]
        P["eye_dx"] = 0.34 * d
        self.set_arm(P, -1, 2.4, -0.4)
        if t > 4.2:
            self.set_arm(P, 1, -1.2, 0.2)
            P["eyes"] = "^"

    def speed_moonwalk(self, t):
        return -75 if t < 4.2 else 0                         # glides backwards!

    def front_moonwalk(self, t, d, g):
        if int(t / 0.3) % 2 and t < 4.2:
            self.T(CX + 6 * d, FEET - 1, "*", 7, "#FFFFFF")

    def pose_hiccups(self, P, t, d):
        c = t % 1.1
        if c < 0.25:
            P.update(bh=6.5, bw=7.6)
            P["eye_h"] = 1.0
            P["eyes"] = "open"
            P["arm_l"] = P["arm_r"] = 1.4
        else:
            P["eye_dy"] = 0.2

    def lift_hiccups(self, t):
        c = t % 1.1
        return para(c / 0.25, 1.6) if c < 0.25 else 0

    def front_hiccups(self, t, d, g):
        if (t % 1.1) < 0.5:
            self.T(CX + 5 * d, g["bt"] - 1.5, "hic!", 7, "#FFFFFF")

    # ======================================================================
    # ============================ ACTIVITIES ==============================
    # ======================================================================
    # --- rock star with an electric guitar ---
    def pose_rockstar(self, P, t, d):
        P["leg_dx"] = [-0.7, -0.35, 0.35, 0.7]
        bang = int(t / 0.3) % 2
        P["lean"] = 0.45 if bang else -0.1
        P["eye_h"] = 0.3 if bang else 1.0
        strum = int(t / 0.08) % 2
        self.set_arm(P, -1, 3.3 if strum else 3.8, 3.0)
        self.set_arm(P, 1, 1.4, 1.4)
        if 6.0 < t < 6.8:
            P["legs"] = [1.0, 2.4, 2.4, 1.0]
            P["leg_dx"] = [-1.2, -0.6, 0.6, 1.2]
            P["eyes"] = "^"

    def lift_rockstar(self, t):
        return para((t - 6.0) / 0.8, 3.2) if 6.0 < t < 6.8 else 0

    def back_rockstar(self, t, d, g):
        ax = self.M(-11.0, 3.6)                              # amp
        self.R(ax, FEET - 4.6, 3.6, 4.6, "#1E1E1E")
        self.R(ax + 0.3, FEET - 3.8, 3.0, 3.0, "#3A3A3A")
        self.O(ax + 0.6, FEET - 3.5, 2.4, 2.4, fill="#2A2A2A", outline="#555555")
        self.R(ax + 0.4, FEET - 4.4, 0.4, 0.4, GOLD)
        self.R(ax + 1.2, FEET - 4.4, 0.4, 0.4, GOLD)

    def front_rockstar(self, t, d, g):
        bt = g["bt"]
        bx, by = CX - d * 0.8, bt + 4.2
        self.Pg([(bx - 2.6 * d, by - 1.4), (bx + 1.2 * d, by - 1.0), (bx + 1.6 * d, by + 0.4),
                 (bx - 0.2 * d, by + 1.6), (bx - 2.8 * d, by + 1.0)], "#C0392B", "#7A1F17")
        self.L([(bx + 1.2 * d, by - 0.4), (CX + d * 7.4, bt + 0.2)], "#2B2B2B", 4)
        self.Pg([(CX + d * 7.2, bt + 0.4), (CX + d * 8.6, bt - 0.8), (CX + d * 8.9, bt - 0.2)], "#2B2B2B")
        self.R(bx - 1.4 * d - 0.3, by - 0.3, 0.6, 0.6, "#EEEEEE")
        for i in range(3):
            p = (t * 0.9 + i / 3) % 1
            self.T(CX + d * (3 + 6 * p), bt - 1 - 6 * p, "♫" if i % 2 else "♪", 9,
                   ("#FFFFFF", GOLD, "#FF6B8B")[i], SYM)
        if 6.0 < t < 7.2:
            self.T(CX, 1.6, "ROCK!", 9, GOLD)

    # --- cooking: flips a pancake in a pan, chef hat ---
    def pose_cooking(self, P, t, d):
        flip = 1.0 < (t % 2.0) < 1.3
        self.set_arm(P, 1, 1.6 if flip else 2.4, 1.0)
        P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.4 if 1.0 < (t % 2.0) < 1.9 else 0.3
        if t > 8.0:
            P["eyes"] = "^"

    def upd_cooking(self, dt, t):
        if random.random() < dt * 3:
            hx, hy = self.g["hf"] if hasattr(self, "g") else (CX, FEET - 4)
            wx, wy = self.wp(hx + self.dir * 2.2, hy - 0.6)
            self.puff(wx, wy, 1, ("#DDDDDD",), 15, (40, 80), (0.5, 0.8), 0.6)

    def front_cooking(self, t, d, g):
        bl, bw, bt = g["bl"], g["bw"], g["bt"]
        self.R(bl + 0.8, bt - 2.6, bw - 1.6, 2.8, "#FFFFFF")            # chef hat
        self.O(bl + 0.2, bt - 3.6, bw - 0.4, 2.2, fill="#FFFFFF")
        hx, hy = g["hf"]
        px_ = hx + d * 2.2
        self.L([(hx, hy), (px_, hy - 0.2)], "#3A3A3A", 3)
        self.R(px_ - 1.6, hy - 0.5, 3.2, 0.6, "#2B2B2B")                 # pan
        c = t % 2.0
        py_ = hy - 1.0 - (para((c - 1.0) / 0.9, 5) if 1.0 < c < 1.9 else 0)
        self.O(px_ - 1.3, py_, 2.6, 0.7, fill="#E8B04A", outline="#B07A20")
        if t > 8.0:
            self.T(CX, 1.6, "chef's kiss", 6, GOLD)

    # --- gaming with a controller in front of a little screen ---
    def pose_gaming(self, P, t, d):
        P["legs"] = [1.0] * 4
        mash = int(t / 0.07) % 2
        P["arm_l"], P["arm_r"] = (3.4, 3.7) if mash else (3.7, 3.4)
        P["arm_lx"], P["arm_rx"] = 1.6, -1.6
        P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.2
        left = self.dur - t                                   # plays until the game / timer ends
        P["brows"] = 3 < t and left > 2
        if left < 1.5:
            P["eyes"] = "^" if self.sub_win else "x"

    def front_gaming(self, t, d, g):
        cx, cy = CX, g["bt"] + 3.8
        self.R(cx - 1.8, cy, 3.6, 1.4, "#2B2B2B")                       # controller
        self.R(cx - 1.4, cy + 0.4, 0.5, 0.5, "#888888")
        self.R(cx + 0.6, cy + 0.3, 0.4, 0.4, "#E5484D")
        self.R(cx + 1.1, cy + 0.7, 0.4, 0.4, "#8FD3FF")
        sx = self.M(8.0, 5.0)
        self.R(sx, FEET - 4.6, 5.0, 3.6, "#1E1E1E")                     # little screen
        self.R(sx + 0.3, FEET - 4.3, 4.4, 3.0, "#0F2A1A")
        self.R(sx + 2.1, FEET - 1.0, 0.8, 1.0, "#1E1E1E")
        if self.dur - t >= 1.5:
            px_ = sx + 0.6 + (math.sin(t * 3) * 0.5 + 0.5) * 3.4
            self.R(px_, FEET - 2.2, 0.6, 0.6, "#B5E48C")
            for i in range(3):
                ex = sx + 0.4 + ((t * 2 + i * 1.4) % 4.0)
                self.R(ex, FEET - 3.8 + i * 0.5, 0.4, 0.4, "#E5484D")
        else:
            self.T(sx + 2.5, FEET - 2.8, "WIN" if self.sub_win else "OVER", 5,
                   "#B5E48C" if self.sub_win else RED)

    # --- DJ at the turntables ---
    def pose_dj(self, P, t, d):
        scratch = math.sin(t * 9)
        self.set_arm(P, 1, 3.0, 0.8 + 0.6 * scratch)
        self.set_arm(P, -1, -0.4 if int(t / 1.5) % 2 else 1.0, 0.2)
        P["eye_h"] = 0.3 if int(t / 0.4) % 2 else 1.0

    def lift_dj(self, t):
        return 0.4 if int(t / 0.4) % 2 == 0 else 0

    def front_dj(self, t, d, g):
        self.R(CX - 8, FEET - 3.2, 16, 3.2, "#2B2B2B")                  # deck table
        self.R(CX - 8, FEET - 3.2, 16, 0.4, "#555555")
        for cx in (CX - 4.5, CX + 4.5):
            self.O(cx - 2, FEET - 3.6, 4, 1.2, fill="#111111", outline="#666666")
            a = t * 8
            self.L([(cx, FEET - 3.0), (cx + math.cos(a) * 1.8, FEET - 3.0 + math.sin(a) * 0.5)], "#CCCCCC", 1)
        for i in range(5):
            self.R(CX - 1.6 + i * 0.7, FEET - 2.4 - abs(math.sin(t * 6 + i)) * 1.2, 0.4,
                   abs(math.sin(t * 6 + i)) * 1.2 + 0.2, ("#B5E48C", GOLD, "#FF6B8B")[i % 3])
        self.front_headphones(t, d, g)

    # --- yoga: tree, warrior, balance ---
    def pose_yoga(self, P, t, d):
        pose = int(t / 3.0) % 3
        P["eye_h"] = 0.25
        if pose == 0:                                       # tree
            P["legs"] = [2.0, 2.0, 0.8, 0.8] if d > 0 else [0.8, 0.8, 2.0, 2.0]
            P["arm_l"] = P["arm_r"] = -1.4
            P["arm_lx"], P["arm_rx"] = 2.0, -2.0
        elif pose == 1:                                     # warrior
            P["leg_dx"] = [-1.4, -0.8, 0.8, 1.4]
            P["legs"] = [1.6] * 4
            P["arm_l"] = P["arm_r"] = 1.0
            P["arm_lx"], P["arm_rx"] = -2.0, 2.0
        else:                                               # wobbly balance
            P["legs"] = [2.4, 2.4, 0.5, 0.5]
            P["rot"] = 6 * math.sin(t * 3)
            P["arm_l"] = P["arm_r"] = 0.6
            P["arm_lx"], P["arm_rx"] = -1.2, 1.2

    def back_yoga(self, t, d, g):
        self.R(CX - 6, FEET - 0.3, 12, 0.3, "#7FA8C9")                  # mat

    # --- drawing on a sketch pad, then shows it off ---
    def pose_drawing(self, P, t, d):
        if t < 5.5:
            self.set_arm(P, -1, 2.4, 2.2)
            self.set_arm(P, 1, 2.6 + 0.4 * math.sin(t * 12), 0.6 + 0.4 * math.cos(t * 9))
            P["eye_dx"], P["eye_dy"] = 0.34 * d, 0.5
        else:
            P["arm_l"] = P["arm_r"] = 0.4
            P["eyes"] = "^"

    def front_drawing(self, t, d, g):
        if t < 5.5:
            x = CX + d * 1.0 - 1.8
            self.R(x, g["bt"] + 2.6, 3.6, 2.8, "#F5EBD7")
            hx, hy = g["hf"]
            self.L([(hx, hy), (hx - d * 1.2, hy + 0.8)], "#E5B400", 3)
        else:                                               # the masterpiece: a smiley
            x, y = CX - 3.0, g["bt"] - 4.6
            self.R(x, y, 6.0, 4.6, "#F5EBD7")
            self.O(x + 1.4, y + 0.6, 3.2, 3.2, outline="#333333", width=2)
            self.R(x + 2.3, y + 1.6, 0.4, 0.4, "#333333")
            self.R(x + 3.3, y + 1.6, 0.4, 0.4, "#333333")
            self.R(x + 2.3, y + 2.8, 1.4, 0.3, "#333333")
            self.T(CX, 1.0, "ta-da", 6, GOLD)

    # ======================================================================
    # ===================== REACTIONS + CURSOR GAMES =======================
    # ======================================================================
    def pose_ceiling(self, P, t, d):                         # monkey-bars along the top
        hand = int(t / 0.3) % 2
        P.update(legs=[2.6] * 4)
        P["arm_l"], P["arm_r"] = (-2.4, -1.6) if hand else (-1.6, -2.4)
        P["leg_dx"] = [0.5 * math.sin(t * 5)] * 4
        P["eye_dy"] = 0.45
        P["eyes"] = "^" if int(t / 2.5) % 3 == 2 else "open"

    def pose_petted(self, P, t, d):
        P["eyes"] = "^"
        P["shake"] = 0.2 * math.sin(t * 12)
        P["legs"] = [1.8] * 4

    def front_petted(self, t, d, g):
        for ex in (g["bl"] + 0.6, g["bl"] + g["bw"] - 1.8):
            self.R(ex, g["ey"] + 1.3, 1.2, 0.5, "#FF8FA8")             # blush
        for i in range(2):
            p = (t * 0.7 + i / 2) % 1
            self.T(CX + (i * 2 - 1) * 3, g["bt"] - 1 - 5 * p, "♥", 8, "#FF6B8B", SYM)

    def pose_startle(self, P, t, d):
        P["arm_l"] = P["arm_r"] = 0.0
        P["arm_lx"], P["arm_rx"] = -0.6, 0.6
        P["eye_dy"] = -0.2

    def lift_startle(self, t):
        return para(t / 0.5, 2.2) if t < 0.5 else 0

    def front_startle(self, t, d, g):
        self.T(CX, g["bt"] - 2.5, "!", 12, GOLD)

    def pose_welcome(self, P, t, d):
        up = int(t / 0.2) % 2
        P["arm_l"] = 0.0 if up else 0.8
        P["arm_r"] = 0.8 if up else 0.0
        P["eyes"] = "^"

    def lift_welcome(self, t):
        return abs(math.sin(t * 6)) * 1.0

    def front_welcome(self, t, d, g):
        self.T(CX, 1.4, "welcome back!", 6, GOLD)

    def pose_dizzy(self, P, t, d):
        P["shake"] = 0.9 * math.sin(t * 6)
        P["hide_eyes"] = True

    def front_dizzy(self, t, d, g):
        for ex in (g["bl"] + 1.5, g["bl"] + g["bw"] - 1.5):
            self.T(ex, g["ey"] + 0.5, "@", 8, EYE)
        self.T(CX, 1.6, "whoa...", 6, "#FFFFFF")

    def pose_flee(self, P, t, d):
        self.steps(P, t, d, 0.06, 0.8, 0.8, 0.3)
        P["lean"] = 0.7
        P["eye_dx"] = -0.34 * d                              # looks back at you
        P["eyes"] = "^"

    def front_flee(self, t, d, g):
        if int(t / 0.8) % 2 == 0:
            self.T(CX - 5 * d, g["bt"] - 1.5, "can't catch me!", 6, "#FFFFFF")

    def pose_throwball(self, P, t, d):
        P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.4
        if t < 0.6:
            self.set_arm(P, 1, 0.4, -0.8)
        elif t < 0.8:
            self.set_arm(P, 1, 1.0, 1.2)
        if 1.5 < t < 1.8:
            P["eye_h"] = 1.0
            P["eyes"] = "open"

    def front_throwball(self, t, d, g):
        if not (0.6 <= t < 1.8):
            return
        cx = (self.cursor[0] - self.wx) / PX
        cy = (self.cursor[1] - self.wy) / PX
        hx, hy = g["hf"]
        if t < 1.2:
            p = (t - 0.6) / 0.6
            bx, by = hx + (cx - hx) * p, hy + (cy - hy) * p - para(p, 3)
        else:
            p = (t - 1.2) / 0.6
            bx, by = cx + (CX - cx) * p, cy + (g["bt"] - cy) * p - para(p, 2)
        self.O(bx - 0.8, by - 0.8, 1.6, 1.6, fill="#FF6B8B", outline="#B03050")

    def pose_hiding(self, P, t, d):
        P["sink"] = min(t / 0.6, 1.0) * 5.6
        self.follow_cursor(P)

    def front_hiding(self, t, d, g):
        if t > 1.0 and int(t / 1.5) % 2:
            self.T(CX + 4, FEET - 3.5, "shh", 6, "#AAAAAA")

    def pose_found(self, P, t, d):
        P["eyes"] = "^"
        P["arm_l"] = P["arm_r"] = 0.0

    def lift_found(self, t):
        return para(t / 0.6, 3.0) if t < 0.6 else 0

    def front_found(self, t, d, g):
        self.T(CX, 1.4, "you found me!" if self.found_you else "you didn't find me!", 6, GOLD)

    def draw_popups(self, wx, wy):
        keep = []
        for txt, x, y, t0, col in self.popups:
            age = self.clock - t0
            if age < 0.9:
                self.T((x - wx) / PX, (y - wy) / PX - age * 4, txt, 9, col)
                keep.append((txt, x, y, t0, col))
        self.popups = keep

    # ======================================================================
    # ===================== FIXED / IMPROVED ANIMATIONS ====================
    # (these replace the earlier versions of the same names)
    # ======================================================================
    # --- Geometry-Dash style: he turns into a cube and hops spikes, 90 deg per jump ---




    # --- Slingshot: a much bigger slingshot ---
    def back_slingshot(self, t, d, g):
        # the slingshot stands IN FRONT of him; he pulls back away from it, then flies forward
        sx = self.M(6.8, 4.0)
        top = FEET - 12.0
        self.R(sx + 1.5, FEET - 7.0, 1.0, 7.0, "#7A4A20")                 # post
        self.L([(sx + 2.0, FEET - 6.6), (sx + 0.2, top)], "#7A4A20", 7)    # fork
        self.L([(sx + 2.0, FEET - 6.6), (sx + 3.8, top)], "#7A4A20", 7)
        self.R(sx + 1.2, FEET - 0.5, 1.6, 0.5, "#5C3A1E")
        front_x = g["bl"] + g["bw"] if d > 0 else g["bl"]
        for tip in (sx + 0.2, sx + 3.8):
            self.L([(tip, top + 0.3), (front_x, g["bt"] + 2.6)], "#3A2010", 3)
        self.R(front_x - (0.2 if d > 0 else 0.4), g["bt"] + 1.8, 0.6, 1.8, "#5C3A1E")   # pouch

    # --- reading: he actually holds the book ---
    def pose_read(self, P, t, d):
        P["legs"] = [1.2] * 4
        P["arm_l"] = P["arm_r"] = 2.6
        P["arm_lx"], P["arm_rx"] = 1.4, -1.4
        P["eye_dy"] = 0.6
        P["eye_dx"] = -0.34 + 0.68 * ((t % 0.9) / 0.9)

    def front_read(self, t, d, g):
        by = g["bt"] + 2.7
        self.R(CX - 3.4, by, 6.8, 2.8, "#7A3E1D")
        self.R(CX - 3.1, by + 0.15, 3.0, 2.4, "#F5EBD7")
        self.R(CX + 0.1, by + 0.15, 3.0, 2.4, "#F5EBD7")
        self.R(CX - 0.1, by, 0.2, 2.8, "#5A2C12")
        for i in range(3):
            self.R(CX - 2.8, by + 0.5 + i * 0.6, 2.3, 0.15, "#9A8F80")
            self.R(CX + 0.4, by + 0.5 + i * 0.6, 2.3, 0.15, "#9A8F80")
        c = t % 2.5
        if c > 2.0:
            k = (c - 2.0) / 0.5
            w = 3.0 * (1 - 2 * k)
            x0 = CX + 0.1 if w > 0 else CX + w
            self.R(x0, by + 0.05, abs(w), 2.5, "#FFFFFF")
        for hx in (CX - 3.9, CX + 3.0):                       # his hands holding the covers
            self.R(hx, by + 0.6, 0.9, 1.6)

    # --- coffee: the mug goes to his mouth, not his eye ---
    def pose_coffee(self, P, t, d):
        sip = self.coffee_sip(t)
        self.set_arm(P, 1, 3.0 if sip else 3.2, -1.2 if sip else 0.4)
        if sip:
            P["eye_h"] = 0.25
            P["eye_dy"] = 0.2
        elif 2.2 < (t % 2.4) or (t % 2.4) < 0.4:
            P["eyes"] = "^"

    def front_coffee(self, t, d, g):
        sip = self.coffee_sip(t)
        if sip:                                               # mug held up to his mouth
            mx = (g["bl"] + g["bw"] - 1.0) if d > 0 else (g["bl"] - 0.6)
            my = g["ey"] + 1.5
            self.R(CX - 0.5, g["ey"] + 1.9, 1.0, 0.5, "#3A1A10")
        else:
            hx, hy = g["hf"]
            mx, my = hx - 0.7 + d * 0.6, hy - 1.4
        self.R(mx, my, 1.6, 1.8, "#FFFFFF")
        self.R(mx + (1.6 if d > 0 else -0.4), my + 0.4, 0.4, 0.9, "#FFFFFF")
        self.R(mx + 0.1, my + 0.1, 1.4, 0.35, "#6B4423")
        if not sip:
            for k in range(2):
                p = (t * 0.8 + k * 0.5) % 1
                self.R(mx + 0.3 + k * 0.6 + 0.3 * math.sin(p * 6), my - 0.4 - p * 2.4, 0.3, 0.5, "#DDDDDD")

    # --- skateboard: pushes off, ollies and kickflips ---
    def skate_phase(self, t):
        c = t % 2.4
        if c < 0.9:
            return "push", c / 0.9
        if c < 1.4:
            return "cruise", 0
        if c < 2.0:
            return "flip", (c - 1.4) / 0.6
        return "cruise", 0

    def pose_skate(self, P, t, d):
        ph, k = self.skate_phase(t)
        P["rise"] = 0.9
        P["legs"] = [1.4] * 4
        P["arm_l"] = P["arm_r"] = 1.4
        P["arm_lx"], P["arm_rx"] = -0.6, 0.6
        P["eye_dx"] = 0.34 * d
        P["lean"] = 0.25
        if ph == "push":                                      # back foot pushes the ground
            back = (0, 2) if d > 0 else (2, 3)
            ext = math.sin(k * math.pi)
            for i in ((0, 1) if d > 0 else (2, 3)):
                P["legs"][i] = 1.4 + 0.9 * ext
                P["leg_dx"][i] = -d * 1.2 * ext
        elif ph == "flip":
            P["legs"] = [1.0] * 4
            P["arm_l"] = P["arm_r"] = 0.6
            P["eyes"] = "^" if k > 0.6 else "open"

    def speed_skate(self, t):
        ph, k = self.skate_phase(t)
        return 260 if ph != "push" else 200 + 120 * k

    def lift_skate(self, t):
        ph, k = self.skate_phase(t)
        return para(k, 3.0) if ph == "flip" else 0

    def front_skate(self, t, d, g):
        ph, k = self.skate_phase(t)
        y = FEET - 0.95 + (g["Lu"] * 0.35 if ph == "flip" else 0)
        if ph == "flip":                                       # kickflip: the board spins under him
            spin = math.cos(k * 2 * math.pi)
            h = 0.5 * abs(spin) + 0.15
            col = "#5A3A22" if spin > 0 else "#E5484D"
            self.R(CX - 4.5, y + (0.5 - h) / 2, 9, h, col)
            if abs(spin) > 0.4:
                self.R(CX - 3.5, y + 0.5, 0.9, 0.45, "#DDDDDD")
                self.R(CX + 2.6, y + 0.5, 0.9, 0.45, "#DDDDDD")
            if k > 0.75:
                self.T(CX + 6 * d, g["bt"] - 1.5, "kickflip!", 6, GOLD)
            return
        self.R(CX - 4.5, y, 9, 0.5, "#5A3A22")
        self.R(CX - 4.8, y - 0.2, 0.5, 0.4, "#5A3A22")
        self.R(CX + 4.3, y - 0.2, 0.5, 0.4, "#5A3A22")
        self.R(CX - 3.5, FEET - 0.45, 0.9, 0.45, "#DDDDDD")
        self.R(CX + 2.6, FEET - 0.45, 0.9, 0.45, "#DDDDDD")

    # --- painting: a much bigger canvas ---
    def back_paint(self, t, d, g):
        ex = self.M(5.6, 7.0)
        self.L([(ex + 0.6, FEET), (ex + 3.5, FEET - 11.0)], WOOD, 3)
        self.L([(ex + 6.4, FEET), (ex + 3.5, FEET - 11.0)], WOOD, 3)
        self.L([(ex + 3.5, FEET - 11.0), (ex + 3.5, FEET)], WOOD, 2)

    def front_paint(self, t, d, g):
        ex = self.M(5.6, 7.0)
        cy = FEET - 10.6
        self.R(ex - 0.2, cy - 0.2, 7.4, 6.4, "#C9B79C")
        self.R(ex, cy, 7.0, 6.0, "#FFFFFF")
        for i in range(min(int(t * 4.5), len(self.paint_dots))):
            px_, py_, col = self.paint_dots[i]
            self.R(ex + px_ * 1.9, cy + py_ * 1.9, 0.9, 0.9, col)
        self.R(ex + 1.0, FEET - 4.2, 5.0, 0.4, WOOD)          # ledge
        if t < 8:
            hx, hy = g["hf"]
            self.L([(hx, hy), (ex + (0.6 if d > 0 else 6.4), cy + 3.2)], "#C0A080", 2)

    # --- soccer: bigger ball, real keepy-uppies, a header, then a kick ---
    def soccer_ball(self, t, d, g):
        r = 1.35
        if t < 5.2:
            c = t % 0.7
            p = c / 0.7
            side = int(t / 0.7) % 2
            top = g["bt"] - 1.5 if int(t / 0.7) % 4 == 3 else FEET - 6.5
            bx = CX + d * (2.6 if side else 1.6)
            by = FEET - 1.6 - para(p, FEET - 1.6 - top)
            return bx, by, r
        p = (t - 5.2) / 1.3
        return CX + d * (2.0 + p * 16), FEET - 1.6 - para(min(p, 1), 8) + g["Lu"], r

    def pose_soccer(self, P, t, d):
        if t < 5.2:
            c = (t % 0.7) / 0.7
            side = int(t / 0.7) % 2
            header = int(t / 0.7) % 4 == 3
            P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.4
            if not header and (c < 0.15 or c > 0.85):         # foot kicks the ball up
                i = (2, 3) if (side and d > 0) or (not side and d < 0) else (0, 1)
                for k in i:
                    P["legs"][k] = 1.2
                    P["leg_dx"][k] = 0.6 * d
            P["arm_l"], P["arm_r"] = 1.8, 1.8
        elif t < 5.5:
            P["leg_dx"] = [0.0, 0.0, 1.4 * d, 1.4 * d]
            P["legs"] = [2, 2, 1.2, 1.2]
        else:
            P["arm_l"] = P["arm_r"] = 0.0
            P["eyes"] = "^"

    def speed_soccer(self, t):
        return 0

    def front_soccer(self, t, d, g):
        bx, by, r = self.soccer_ball(t, d, g)
        if t >= 6.5:
            self.T(CX, 2.4, "GOAL!", 9, GOLD)
            return
        self.O(bx - r, by - r, 2 * r, 2 * r, fill="#FFFFFF", outline="#222222", width=2)
        a = t * 9 * d
        for k in range(3):
            aa = a + k * 2.1
            self.R(bx + math.cos(aa) * 0.6 - 0.3, by + math.sin(aa) * 0.6 - 0.3, 0.6, 0.6, "#222222")
        if t < 5.2 and int(t / 0.7) % 4 == 3 and (t % 0.7) > 0.4:
            self.T(CX - 5 * d, g["bt"] - 1.5, "header!", 6, "#FFFFFF")

    # --- sneeze: the sneeze makes him jump ---
    def lift_sneeze(self, t):
        return para((t - 2.0) / 0.55, 3.2) if 2.0 <= t < 2.55 else 0

    # --- meditation: floats much higher ---
    def lift_meditate(self, t):
        rise = ease(min(t / 2.0, 1.0)) * 9.0
        if t > self.dur - 1.2:
            rise *= max(0.0, (self.dur - t) / 1.2)
        return rise + 0.8 * math.sin(t * 1.6)

    # --- balloon: way higher (up to near the top of the screen) ---
    def lift_balloon(self, t):
        if t < 1:
            return 0
        room = max(60.0, (self.fy - self.mon[1] - 180) / PX)
        k = ease((t - 1) / (self.BALLOON_POP - 1))
        return room * k * k + 1.2 * math.sin(t * 2)

    # --- paper plane: flies all the way to the edge of the screen ---
    def front_paperplane(self, t, d, g):
        bt = g["bt"]
        if t < 1.0:
            self.R(CX - 2, bt + 2.6, 4, 2.6, "#FFFFFF")
        elif t < 2.4:
            k = 1 - (t - 1.0) / 1.4 * 0.5
            self.Pg([(CX - 1.8 * k, bt + 3.6), (CX + 1.8 * k, bt + 3.6), (CX, bt + 2.4)], "#FFFFFF")

    def upd_paperplane(self, dt, t):
        if t < 2.4:
            return
        pl = getattr(self, "plane", None)
        if pl is None:
            if not self.once("plane_thrown"):              # only one plane per throw
                return
            hx, hy = self.g["hf"] if hasattr(self, "g") else (CX, FEET - 4)
            wx, wy = self.wp(hx, hy)
            self.plane = pl = {"x": wx, "y": wy, "y0": wy, "t0": self.clock, "d": self.dir}
        age = self.clock - pl["t0"]
        pl["x"] += pl["d"] * 420 * dt
        pl["y"] = pl["y0"] - age * 55 + math.sin(age * 3) * 22
        lo, hi = self.bounds()
        if pl["x"] < lo - 40 or pl["x"] > hi + 40:
            self.kill_sprite("plane")
            self.plane = None
            self.dur = t + 1.5
            return
        dd = pl["d"]

        def draw(p):
            p.Pg([(3 + dd * 2.6, 1.5), (3 - dd * 2.4, 0.2), (3 - dd * 1.4, 1.5), (3 - dd * 2.4, 2.8)],
                 "#FFFFFF", "#BBBBBB")
            p.L([(3 - dd * 1.4, 1.5), (3 + dd * 2.6, 1.5)], "#BBBBBB", 1)
        self.show_sprite("plane", 6, 3, pl["x"], pl["y"], draw)
        if t > self.dur - 0.5:
            self.dur = t + 1.0                                 # keep watching until it's gone

    def pose_paperplane(self, P, t, d):
        if t < 2.0:
            P["arm_l"] = P["arm_r"] = 3.0
            P["arm_lx"], P["arm_rx"] = 0.9, -0.9
            P["eye_dy"] = 0.5
        elif t < 2.4:
            self.set_arm(P, 1, 0.6, -0.6)
        else:
            P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.3
            self.set_arm(P, 1, -0.4, 0.6)                      # points after it
            if self.dur - t < 1.6:
                P["eyes"] = "^"

    # ======================================================================
    # ============================ TRANSPORT ===============================
    # ======================================================================
    # --- pogo stick ---
    def pogo_k(self, t):
        return (t % 0.42) / 0.42

    def lift_pogo(self, t):
        return para(self.pogo_k(t), 3.0)

    def pose_pogo(self, P, t, d):
        k = self.pogo_k(t)
        P["legs"] = [1.0] * 4
        P["rise"] = 1.2
        P["arm_l"] = P["arm_r"] = 3.2
        P["arm_lx"], P["arm_rx"] = 1.4, -1.4
        P["eye_dx"] = 0.34 * d
        if k < 0.12 or k > 0.88:                              # squash at the bottom
            P.update(bh=5.4, bw=8.6)
        P["eyes"] = "^" if int(t / 1.7) % 2 else "open"

    def speed_pogo(self, t):
        return 170

    def back_pogo(self, t, d, g):
        ground = FEET + g["Lu"]
        k = self.pogo_k(t)
        spring = 0.8 if (k < 0.12 or k > 0.88) else 1.4
        self.R(CX - 0.3, g["bt"] + 3.2, 0.6, ground - spring - g["bt"] - 3.2, "#9AA0A8")   # pole
        for i in range(4):
            self.R(CX - 0.6, ground - spring + i * spring / 4, 1.2, 0.2, "#555555")       # spring
        self.R(CX - 0.2, ground - 0.3, 0.4, 0.3, "#333333")

    def front_pogo(self, t, d, g):
        self.R(CX - 2.6, g["bt"] + 3.1, 5.2, 0.45, "#E5484D")          # handle bar
        self.R(CX - 2.6, FEET - 1.3 - 1.2 + 1.0, 5.2, 0.4, "#555555")  # foot pegs

    # --- flying rides: golden cloud / jetpack (movement is in the main program) ---
    def pose_fly(self, P, t, d):
        if self.ride == "cloud":
            P["legs"] = [0.8] * 4                             # sits cross-legged on it
            P["rise"] = 1.4
            P["eyes"] = "^" if int(t / 2) % 2 else "open"
            P["arm_l"], P["arm_r"] = (0.0, 2.0) if int(t / 3) % 3 == 0 else (2.0, 2.0)
        else:                                                 # jetpack
            P["legs"] = [2.5] * 4
            P["leg_dx"] = [0.4 * math.sin(t * 6)] * 4
            P["arm_l"] = P["arm_r"] = 1.2
            P["arm_lx"], P["arm_rx"] = -0.8, 0.8
            P["lean"] = 0.3
            P["eye_dx"] = 0.34 * d
        P["eye_dy"] = 0.3

    def back_fly(self, t, d, g):
        if self.ride == "cloud":
            y = FEET - 1.2
            for x, w, h in ((-6, 5, 2.6), (-2.5, 6, 3.0), (2, 5, 2.6), (-4, 4, 2), (1, 4, 2)):
                self.O(CX + x, y - h / 2 + 0.6, w, h, fill="#F5D76E")
            self.O(CX - 4, y - 0.6, 4, 1.4, fill="#FBE9A8")
            for i in range(3):                                # little trail
                self.O(CX - d * (7 + i * 1.6) - 0.6, y + 0.6 + i * 0.2, 1.4 - i * 0.3, 1.0 - i * 0.2,
                       fill="#F5D76E")
        else:
            x = g["bl"] - 1.6 if d > 0 else g["bl"] + g["bw"] - 0.2
            self.R(x, g["bt"] + 1.0, 1.8, 4.4, "#9AA0A8")
            self.R(x + 0.2, g["bt"] + 1.4, 1.4, 0.5, "#E5484D")
            fl = 1.5 + abs(math.sin(t * 25)) * 1.5
            self.Pg([(x + 0.2, g["bt"] + 5.4), (x + 1.6, g["bt"] + 5.4), (x + 0.9, g["bt"] + 5.4 + fl)],
                    "#FF8C1A")
            self.Pg([(x + 0.5, g["bt"] + 5.4), (x + 1.3, g["bt"] + 5.4), (x + 0.9, g["bt"] + 5.4 + fl * 0.6)],
                    GOLD)

    # --- portal gun (an original gadget) ---
    def pose_pgun(self, P, t, d):
        self.set_arm(P, 1, 2.0, 1.0)
        self.set_arm(P, -1, 2.3, 8.4)
        P["eye_dx"] = 0.34 * d
        P["brows"] = True

    def front_pgun(self, t, d, g):
        hx, hy = g["hf"]
        F = (lambda o, w: hx + o if d > 0 else hx - o - w)
        self.R(F(-0.6, 3.4), hy - 1.0, 3.4, 1.4, "#E8E8EE")
        self.R(F(2.6, 1.2), hy - 0.8, 1.2, 1.0, "#3A3A3A")
        self.O(F(3.6, 1.2), hy - 0.9, 1.2, 1.2, fill="#6CC6F0")
        self.R(F(0.2, 1.0), hy - 0.2, 1.0, 1.4, "#9AA0A8")
        if 0.45 < t < 0.75:
            self.L([(hx + d * 4.5, hy - 0.4), (hx + d * 14, hy - 1.5)], "#6CC6F0", 3)

    # --- ninja smoke bomb ---
    def pose_smoke(self, P, t, d):
        if t < 0.5:
            self.set_arm(P, 1, 0.4 + t * 6, 0.6)
            P["brows"] = True

    def front_smoke(self, t, d, g):
        if t < 0.5:
            hx, hy = g["hf"]
            self.O(hx + d * 0.6 - 0.6, hy - 0.6 + t * 8, 1.2, 1.2, fill="#2B2B2B")
            self.R(hx + d * 0.6 - 0.1, hy - 1.1 + t * 8, 0.2, 0.6, "#FF8C1A")

    # ======================================================================
    # ===================== DRAGON BOSS FIGHT (original dragon) ============
    # ======================================================================
    def dragon_pos(self, t):
        l, top, r, _ = self.mon
        w = r - l
        x = (l + r) / 2 + w * 0.34 * math.sin(t * 0.42)
        y = top + 230 + 120 * math.sin(t * 0.84)
        return x, y

    def upd_dragonfight(self, dt, t):
        D = getattr(self, "dragon", None)
        if D is None or D.get("start", 1e9) > self.clock or t < 0.05:
            self.dragon = D = {"hp": 6, "hit": -9.0, "dead": None, "arrows": [], "next": 2.0,
                               "start": self.clock, "n": 0, "fall": 0.0}
        x, y = self.dragon_pos(t)
        if D["dead"] is not None:
            D["fall"] += dt * 500
            y += D["fall"]
            if self.clock - D["dead"] > 1.4:
                self.kill_sprite("dragon")
                if self.clock - D["dead"] > 3.5:
                    self.dur = t + 0.1
        D["x"], D["y"] = x, y
        self.dir = 1 if x > self.x else -1
        # shoot arrows
        if D["dead"] is None and t >= D["next"]:
            D["next"] = t + 1.9
            hx, hy = self.wp(*self.g["hf"]) if hasattr(self, "g") else (self.x, self.fy - 20)
            lead = math.hypot(self.dragon_pos(t)[0] - hx, self.dragon_pos(t)[1] - hy) / 1100
            tx, ty = self.dragon_pos(t + lead)                 # aims where the dragon will be
            dist = max(1.0, math.hypot(tx - hx, ty - hy))
            D["n"] += 1
            D["arrows"].append({"x": hx, "y": hy, "vx": (tx - hx) / dist * 1100,
                                "vy": (ty - hy) / dist * 1100, "id": f"arrow{D['n']}"})
        keep = []
        for a in D["arrows"]:
            a["x"] += a["vx"] * dt
            a["y"] += a["vy"] * dt
            if D["dead"] is None and math.hypot(a["x"] - x, a["y"] - y) < 70:
                D["hp"] -= 1
                D["hit"] = self.clock
                self.popups.append(("hit!", self.x, self.fy - 11 * PX, self.clock, GOLD))
                self.kill_sprite(a["id"])
                if D["hp"] <= 0:
                    D["dead"] = self.clock
                    self.popups.append(("VICTORY!", self.x, self.fy - 12 * PX, self.clock, GOLD))
                continue
            lo, hi = self.bounds()
            if not (lo - 50 < a["x"] < hi + 50 and self.mon[1] - 80 < a["y"] < self.mon[3] + 50):
                self.kill_sprite(a["id"])
                continue
            ang = math.atan2(a["vy"], a["vx"])

            def draw_arrow(p, ang=ang):
                cx, cy = 3, 3
                dx, dy = math.cos(ang) * 2.6, math.sin(ang) * 2.6
                p.L([(cx - dx, cy - dy), (cx + dx, cy + dy)], "#8B5A2B", 2)
                p.Pg([(cx + dx * 1.15, cy + dy * 1.15), (cx + dx * 0.8 - dy * 0.25, cy + dy * 0.8 + dx * 0.25),
                      (cx + dx * 0.8 + dy * 0.25, cy + dy * 0.8 - dx * 0.25)], "#CCCCCC")
                p.L([(cx - dx, cy - dy), (cx - dx * 0.7, cy - dy * 0.7)], "#FFFFFF", 3)
            self.show_sprite(a["id"], 6, 6, a["x"], a["y"], draw_arrow)
            keep.append(a)
        D["arrows"] = keep
        if D["dead"] is None or self.clock - D["dead"] <= 1.4:
            hurt = self.clock - D["hit"] < 0.25
            face = 1 if math.cos(t * 0.42) > 0 else -1
            flap = math.sin(t * 7)
            hp = D["hp"]

            def draw_dragon(p, hurt=hurt, face=face, flap=flap, hp=hp):
                body = "#E5484D" if hurt else "#2FA878"
                dark = "#1F6F52"
                cx, cy = 14, 9
                p.R(cx - 5, 1.0, 10, 0.8, "#3A3A3A")                       # health bar
                p.R(cx - 5, 1.0, 10 * hp / 6, 0.8, "#E5484D")
                p.Pg([(cx - 1, cy - 1), (cx + 3, cy - 1), (cx + 1 - face * 4, cy - 6 - flap * 2)], dark)
                p.Pg([(cx - 3, cy - 1), (cx + 1, cy - 1), (cx - 1 - face * 6, cy - 5 - flap * 2.5)], dark)
                p.O(cx - 5, cy - 2, 10, 4.5, fill=body)                     # body
                p.Pg([(cx - face * 4.5, cy), (cx - face * 11, cy + 2.6), (cx - face * 4, cy + 2)], body)
                hx = cx + face * 6
                p.O(hx - 2.2, cy - 3.4, 4.4, 3.0, fill=body)               # head
                p.Pg([(hx + face * 1.6, cy - 2.4), (hx + face * 4.4, cy - 1.6), (hx + face * 1.6, cy - 0.8)], body)
                p.R(hx + face * 0.6 - 0.4, cy - 2.7, 0.8, 0.8, "#F2C94C")    # eye
                p.Pg([(hx - face * 1.0, cy - 3.2), (hx - face * 2.2, cy - 5.0), (hx - face * 0.2, cy - 3.4)], "#F5EBD7")
                for lx in (cx - 2.6, cx + 1.6):
                    p.R(lx, cy + 2.2, 0.8, 1.4, dark)
            self.show_sprite("dragon", 28, 14, x, y, draw_dragon)

    def pose_dragonfight(self, P, t, d):
        P["brows"] = True
        D = getattr(self, "dragon", None)
        self.set_arm(P, 1, 1.6, 0.6)
        self.set_arm(P, -1, 1.8, 6.0 if (t % 1.9) < 1.4 else 2.0)
        P["eye_dy"] = -0.45
        if D and D["dead"] is not None:
            P["eyes"] = "^"
            P["arm_l"] = P["arm_r"] = 0.0
            P["brows"] = False

    def lift_dragonfight(self, t):
        D = getattr(self, "dragon", None)
        if D and D["dead"] is not None:
            return abs(math.sin((self.clock - D["dead"]) * 6)) * 1.4
        return 0

    def front_dragonfight(self, t, d, g):
        D = getattr(self, "dragon", None)
        if D and D["dead"] is not None:
            return
        hx, hy = g["hf"]
        if D:
            ang = math.atan2(D.get("y", 0) - self.wp(hx, hy)[1], D.get("x", 0) - self.wp(hx, hy)[0])
        else:
            ang = -math.pi / 4 if d > 0 else -3 * math.pi / 4
        ca, sa = math.cos(ang), math.sin(ang)
        px_, py_ = -sa, ca                                    # perpendicular
        bx, by = hx + ca * 1.2, hy + sa * 1.2
        tip1 = (bx + px_ * 2.6 - ca * 0.8, by + py_ * 2.6 - sa * 0.8)
        tip2 = (bx - px_ * 2.6 - ca * 0.8, by - py_ * 2.6 - sa * 0.8)
        self.L([tip1, (bx + ca * 0.6, by + sa * 0.6), tip2], "#8B5A2B", 3)     # bow
        pull = 1.4 if (t % 1.9) < 1.4 else 0.2
        nock = (bx - ca * pull, by - sa * pull)
        self.L([tip1, nock, tip2], "#DDDDDD", 1)                                  # string
        if (t % 1.9) < 1.4:
            self.L([nock, (nock[0] + ca * 4.0, nock[1] + sa * 4.0)], "#8B5A2B", 2)  # arrow ready


# --------- regroup: headphones are a reaction, skate is transport, new acts ---------
ACT_GROUPS["Fun"] = [n for n in ACT_GROUPS["Fun"] if n not in ("headphones", "skate")]
ACT_GROUPS["Reactions"].append("headphones")
ACT_GROUPS["Games"].append("dragonfight")
ACT_GROUPS["Transport"] = ["skate", "pogo"]
ACTS.update({"pogo": (6, 6), "dragonfight": (60, 60), "skate": (8, 8), "meditate": (9, 9),
             "balloon": (10, 10), "soccer": (8, 8), "paperplane": (6, 6)})
Acts.BALLOON_POP = 8.4


# --------- movie scenes (costume + pose + prop + an original line in a caption) ---------
import pixbot_movies  # noqa: E402

pixbot_movies.install(Acts, ACTS, ACT_GROUPS)


# ---------------- relaxing in a deck chair (long calm idle) ----------------
def _pose_relax(self, P, t, d):
    k = min(t / 0.8, max(0.0, (self.dur - t) / 0.8), 1.0)
    P["rise"] = 1.4 * k
    P["lean"] = -0.5 * k                                   # leans back
    P["legs"] = [1.0, 1.0, 1.6, 1.6] if d > 0 else [1.6, 1.6, 1.0, 1.0]
    P["leg_dx"] = [0.0, 0.0, 0.8 * d, 0.8 * d] if d > 0 else [0.8 * d, 0.8 * d, 0.0, 0.0]
    P["arm_l"] = P["arm_r"] = -0.4 * k + 2.0 * (1 - k)     # hands behind his head
    P["arm_lx"], P["arm_rx"] = 1.0 * k, -1.0 * k
    c = t % 9.0
    P["eye_h"] = 0.25 if 2.0 < c < 6.5 else 1.0             # eyes closed, just chilling
    if 6.5 <= c < 7.5:
        self.follow_cursor(P)


def _back_relax(self, t, d, g):
    k = min(t / 0.8, max(0.0, (self.dur - t) / 0.8), 1.0)
    if k <= 0:
        return
    x = CX - d * (1 - k) * 12
    seat = FEET - 1.8
    self.L([(x - 5 * d, FEET), (x + 3 * d, seat)], "#8B5A2B", 3)          # frame
    self.L([(x + 4 * d, FEET), (x - 4 * d, seat - 5.5)], "#8B5A2B", 3)
    self.Pg([(x - 4.5 * d, seat - 5.0), (x - 3.4 * d, seat - 5.6), (x + 3.4 * d, seat + 0.2),
             (x + 2.4 * d, seat + 0.6)], "#4A90E2")                       # striped canvas
    for i in range(3):
        f = 0.2 + i * 0.3
        px_, py_ = x - 4.0 * d + (7.4 * d) * f, seat - 5.3 + 5.6 * f
        self.R(px_ - 0.4, py_ - 0.3, 0.8, 0.6, "#FFFFFF")


def _front_relax(self, t, d, g):
    c = t % 9.0
    if 2.5 < c < 6.0:
        self.T(CX + 5 * d, g["bt"] - 1 - (c - 2.5) * 0.6, "~", 9, "#AAAAAA")


Acts.pose_relax = _pose_relax
Acts.back_relax = _back_relax
Acts.front_relax = _front_relax
ACTS["relax"] = (20, 40)
ACT_GROUPS["Activities"].append("relax")


# ---------------- pogo stick stays under him while he bounces between places ----------------
def _pogo_air_stick(self, t, d, g):
    if not getattr(self, "on_pogo", False):
        return
    bot = FEET + 2.6
    self.R(CX - 0.3, g["bt"] + 3.2, 0.6, bot - g["bt"] - 3.2, "#9AA0A8")
    for i in range(4):
        self.R(CX - 0.6, bot - 1.4 + i * 0.35, 1.2, 0.2, "#555555")


def _pogo_air_front(self, t, d, g):
    if getattr(self, "on_pogo", False):
        self.R(CX - 2.6, g["bt"] + 3.1, 5.2, 0.45, "#E5484D")


_orig_pose = Acts.pose


def _pose_with_pogo(self):
    P = _orig_pose(self)
    if getattr(self, "on_pogo", False) and self.state in ("crouch", "leapto", "air"):
        P.update(legs=[1.0] * 4, rise=1.2, arm_l=3.2, arm_r=3.2, rot=0.0)
        P["arm_lx"], P["arm_rx"] = 1.4, -1.4
        P["eyes"] = "^"
    return P


Acts.pose = _pose_with_pogo
for _st in ("crouch", "leapto", "air"):
    setattr(Acts, "back_" + _st, _pogo_air_stick)
    setattr(Acts, "front_" + _st, _pogo_air_front)


# ---------------- relaxing on a beach lounger (redone) ----------------
def _relax_k(self, t):
    return max(0.0, min(t / 0.9, (self.dur - t) / 0.9, 1.0))


def _pose_relax2(self, P, t, d):
    k = ease(_relax_k(self, t))
    seat = 2.3                                            # seat height above the floor
    P["legs"] = [1.0] * 4
    P["rise"] = (seat - 1.0) * k
    P["rot"] = -24 * d * k                                # leans back into the backrest
    P["leg_dx"] = [1.2 * d * k] * 4                       # legs stretched out
    P["arm_l"] = P["arm_r"] = 2.0 - 2.6 * k               # hands behind his head
    P["arm_lx"], P["arm_rx"] = 1.2 * k, -1.2 * k
    c = t % 10.0
    if k >= 1.0 and 1.5 < c < 7.0:
        P["eye_h"] = 0.25                                 # eyes closed, soaking up the sun
    elif k >= 1.0 and 7.0 <= c < 8.5:
        self.follow_cursor(P)
        P["eye_dy"] = min(P["eye_dy"], 0.0)
    if k >= 1.0 and 8.5 <= c < 9.6:                       # sip of his drink
        self.set_arm(P, 1, 1.4, 1.0)


def _back_relax2(self, t, d, g):
    k = _relax_k(self, t)
    slide = (1 - ease(k)) * 14 * d                        # the set slides in / out
    # beach umbrella
    ux = CX - 7.5 * d - slide
    self.R(ux - 0.2, 2.6, 0.4, FEET - 2.6, "#E8E8E8")
    cols = ("#E5484D", "#FFFFFF")
    for i in range(6):
        self.A(ux - 7, 0.4, 14, 6.4, i * 30, 30, cols[i % 2])
    self.R(ux - 0.4, 2.3, 0.8, 0.6, "#E8E8E8")
    # the lounger: frame, seat, slanted backrest, foot end
    x0 = CX - slide
    seat_y = FEET - 2.3
    wood = "#B07A45"
    back_x = x0 - 4.6 * d
    self.L([(x0 - 4.0 * d, FEET), (x0 - 3.2 * d, seat_y + 0.5)], wood, 3)
    self.L([(x0 + 4.4 * d, FEET), (x0 + 3.8 * d, seat_y + 0.5)], wood, 3)
    self.Pg([(back_x - 0.4 * d, seat_y + 0.6), (back_x + 0.6 * d, seat_y + 0.6),
             (back_x - 2.6 * d, seat_y - 6.6), (back_x - 3.6 * d, seat_y - 6.4)], wood)
    # striped fabric on the backrest and seat
    for i in range(4):
        f0, f1 = i / 4, (i + 1) / 4
        p = lambda f, off: (back_x + off * d - 3.0 * d * f, seat_y + 0.5 - 7.0 * f)
        self.Pg([p(f0, 0.3), p(f0, 1.6), p(f1, 1.6), p(f1, 0.3)], "#4A90E2" if i % 2 == 0 else "#FFFFFF")
    self.R(min(back_x, x0 + 5.0 * d), seat_y, abs(x0 + 5.0 * d - back_x), 0.8, "#4A90E2")
    for i in range(5):
        self.R(min(back_x, x0 + 5.0 * d) + 0.8 + i * 1.9, seat_y, 0.8, 0.8, "#FFFFFF")


def _front_relax2(self, t, d, g):
    k = _relax_k(self, t)
    slide = (1 - ease(k)) * 14 * d
    # little side table with a cold drink
    tx = CX + 7.6 * d - slide
    self.R(tx - 1.6, FEET - 3.2, 3.2, 0.4, "#B07A45")
    self.R(tx - 0.2, FEET - 2.8, 0.4, 2.8, "#B07A45")
    self.Pg([(tx - 0.8, FEET - 5.2), (tx + 0.8, FEET - 5.2), (tx + 0.6, FEET - 3.2), (tx - 0.6, FEET - 3.2)],
            "#BFE8FF", "#8FBFD8")
    self.R(tx - 0.6, FEET - 4.6, 1.2, 1.3, "#F28C28")
    self.L([(tx + 0.3, FEET - 5.0), (tx + 0.9, FEET - 6.2)], "#E5484D", 2)
    self.O(tx - 1.1, FEET - 5.6, 0.9, 0.9, fill="#F2C94C")
    c = t % 10.0
    if k >= 1.0 and 2.0 < c < 6.5:
        self.T(CX + 4.5 * d, g["bt"] - 1.5 - ((c - 2.0) % 1.5) * 0.8, "~", 9, "#AAAAAA")


Acts.pose_relax = _pose_relax2
Acts.back_relax = _back_relax2
Acts.front_relax = _front_relax2
NO_HAT.add("relax")
NO_FACE.add("relax")
NO_BODY.add("relax")


def _pose_relax3(self, P, t, d):
    k = ease(_relax_k(self, t))
    # sits ON the seat (seat top is 2.3 above the floor), leans back, legs out along the lounger
    P["legs"] = [2.0 - 1.7 * k] * 4
    P["rise"] = 2.0 * k
    P["lean"] = -0.9 * k
    P["arm_l"] = P["arm_r"] = 2.0 - 2.5 * k               # hands behind his head
    P["arm_lx"], P["arm_rx"] = 0.9 * k, -0.9 * k
    c = t % 10.0
    if k >= 1.0 and 1.5 < c < 7.0:
        P["eye_h"] = 0.25                                 # eyes closed, soaking up the sun
    elif k >= 1.0 and 7.0 <= c < 8.5:
        self.follow_cursor(P)
        P["eye_dy"] = min(P["eye_dy"], 0.0)
    if k >= 1.0 and 8.5 <= c < 9.6:                       # a sip of his drink
        self.set_arm(P, 1, 2.0, 1.2)


def _front_relax3(self, t, d, g):
    _front_relax2(self, t, d, g)
    k = ease(_relax_k(self, t))
    if k < 0.3:
        return
    seat_y = FEET - 2.3
    front = g["bl"] + g["bw"] if d > 0 else g["bl"]
    col = self.body_color
    for i, off in enumerate((0.0, 1.5)):                   # two pairs of legs stretched out
        y = seat_y - 1.0 - off * 0.25
        x = front if d > 0 else front - 3.4 * k
        self.R(x, y + i * 0.05, 3.4 * k, 0.9, col)
        tip = front + d * 3.4 * k
        self.R(tip - (0 if d > 0 else 0.8), y - 0.5, 0.8, 0.9, col)   # little feet pointing up


Acts.pose_relax = _pose_relax3
Acts.front_relax = _front_relax3
