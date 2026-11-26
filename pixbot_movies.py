"""Movie-style scenes: Pixbot dresses up as a classic film type, strikes the pose,
and a line pops up in a caption bubble above his head.

All costumes are original designs and all lines are original (written for Pixbot),
they only nod to the genres.
"""
import math
import random

from pixbot_common import *  # noqa: F401,F403

SCENES = {
    # key: label, costume {hat, face, body}, body colour (None = his own), pose, prop, lines
    "movie_hero": ("Caped hero", {"face": "heromask", "body": "redcape"}, None, "heroic", "star", [
        "Every desktop needs a guardian.",
        "Fear not, citizen. Your files are safe.",
        "Up, up and... okay, maybe just up a bit."]),
    "movie_nightwatch": ("Night-watch hero", {"face": "nightmask", "body": "nightcape"}, None, "proud", "night", [
        "When the screen goes dark, I keep watch.",
        "Not all heroes wear capes. I do, though.",
        "I am the night shift."]),
    "movie_spaceknight": ("Space knight", {"body": "robe"}, None, "duel", "lasersword", [
        "The power is in the pixels.",
        "Trust your instincts, young coder.",
        "May your builds always pass."]),
    "movie_detective": ("Detective", {"hat": "deerstalker"}, None, "think", "magnifier", [
        "The clues never lie.",
        "Someone deleted a file... and I WILL find out who.",
        "Case closed."]),
    "movie_cowboy": ("Cowboy", {"hat": "cowboy", "face": "mustache", "body": "scarf"}, None, "lookout",
                     "tumbleweed", [
        "Howdy, partner.",
        "Saddle up. We ride at dawn.",
        "Fastest cursor in the West."]),
    "movie_pirate": ("Pirate", {"hat": "piratehat", "face": "eyepatch"}, None, "heroic", "chest", [
        "X marks the save file.",
        "Hoist the sails, we're downloading!",
        "Every captain needs a crew. You're hired."]),
    "movie_astronaut": ("Astronaut", {"hat": "spacehelmet", "body": "backpack"}, None, "proud", "flag", [
        "Next stop: the top of the screen.",
        "Space is big. So is this monitor.",
        "Mission control, all systems go."]),
    "movie_wizard": ("Wizard", {"hat": "wizard", "face": "beard"}, None, "heroic", "staff", [
        "Abraca-download!",
        "Magic is just code nobody explained.",
        "By the power of pixels!"]),
    "movie_boxer": ("Boxer", {"hat": "headband", "body": "boxrobe"}, None, "flex", "gloves", [
        "Every champion was once a beginner.",
        "One more round.",
        "Eyes on the prize."]),
    "movie_dino": ("Dinosaur", {"hat": "dinohood"}, "#5FB85A", "stomp", None, [
        "RAWR. (That means hello.)",
        "I'm a dinosaur now. Deal with it.",
        "Stomp. Stomp. Stomp."]),
    "movie_vampire": ("Vampire", {"face": "fangs", "body": "vampcape"}, "#C9C3D6", "cape", "moon", [
        "Good evening...",
        "I only come out when the brightness is low.",
        "Bleh! (Sorry, force of habit.)"]),
    "movie_robot": ("Robot", {"hat": "robotantenna"}, "#9AA0A8", "robot", None, [
        "Beep boop. Affection detected.",
        "Systems online.",
        "Rebooting cuteness..."]),
    "movie_agent": ("Secret agent", {"face": "sunglasses", "body": "jacket"}, None, "sneak", None, [
        "Agent C, reporting for duty.",
        "Nobody saw me. Nobody ever does.",
        "This message will not self-destruct. Relax."]),
    "movie_knight": ("Knight", {"hat": "knight", "body": "redcape"}, None, "duel", "swordshield", [
        "For the kingdom of Desktop!",
        "Honor. Courage. Snacks.",
        "Draw your sword!"]),
    "movie_zombie": ("Zombie", {}, "#7FA86A", "shamble", None, [
        "Braaains... I mean, bytes.",
        "Need... coffee...",
        "Mondays, am I right?"]),
    "movie_alien": ("Alien visitor", {"hat": "antennae"}, "#7CC86A", "wave", "saucer", [
        "Greetings, Earth cursor.",
        "We come in peace. Mostly.",
        "Your planet has excellent snacks."]),
    "movie_ninja": ("Ninja", {"hat": "headband", "face": "ninjamask"}, None, "sneak", None, [
        "Silent. Swift. Snacking.",
        "You never saw me.",
        "The way of the pixel."]),
    "movie_chef": ("Chef", {"hat": "chefhat", "face": "mustache", "body": "apron"}, None, "heroic", "pan", [
        "Order up!",
        "A pinch of salt, a pinch of code.",
        "Bon appetit!"]),
    "movie_viking": ("Viking", {"hat": "viking", "face": "beard"}, None, "heroic", "axe", [
        "To glory!",
        "The great hall awaits... after lunch.",
        "Shields up!"]),
    "movie_mummy": ("Mummy", {"body": "bandages"}, None, "shamble", None, [
        "I've been under wraps for a while.",
        "Three thousand years and still no Wi-Fi.",
        "Unravel the mystery!"]),
    "movie_explorer": ("Explorer", {"hat": "pith", "body": "backpack"}, None, "lookout", "map", [
        "Uncharted territory ahead.",
        "Every map has a missing corner.",
        "To the edge of the screen!"]),
}
DUR = 7.5


def install(Acts, ACTS, ACT_GROUPS):
    """Adds every scene as an animation to Pixbot's library."""
    ACT_GROUPS["Movie scenes"] = list(SCENES)
    for key in SCENES:
        ACTS[key] = (DUR, DUR)
        setattr(Acts, "pose_" + key, lambda self, P, t, d, k=key: _pose(self, P, t, d, k))
        setattr(Acts, "back_" + key, lambda self, t, d, g, k=key: _prop(self, t, d, g, k, "back"))
        setattr(Acts, "front_" + key, lambda self, t, d, g, k=key: _prop(self, t, d, g, k, "front"))
        setattr(Acts, "upd_" + key, lambda self, dt, t, k=key: _caption(self, t, k))
        style = SCENES[key][3]
        if style in ("sneak", "shamble", "stomp"):
            spd = {"sneak": 35, "shamble": 25, "stomp": 30}[style]
            setattr(Acts, "speed_" + key, lambda self, t, s=spd: s if t < DUR - 2.5 else 0)
        if style in ("stomp",):
            setattr(Acts, "lift_" + key, lambda self, t: 0.5 if int(t / 0.4) % 2 == 0 else 0)


def scene_outfit(state):
    s = SCENES.get(state)
    return s[1] if s else None


# ---------------- poses ----------------
def _pose(self, P, t, d, key):
    label, outfit, color, style, prop, lines = SCENES[key]
    if color:
        P["color"] = color
    if style == "proud":                     # chest out, hands on hips, looking up
        P.update(bw=8.4, bh=6.3)
        P["arm_l"] = P["arm_r"] = 3.2
        P["arm_lx"], P["arm_rx"] = 0.9, -0.9
        P["eye_dy"] = -0.5
        P["eye_dx"] = 0.34 * d if int(t / 2.5) % 2 else 0
    elif style == "heroic":                  # fist (or prop) raised high
        self.set_arm(P, 1, -1.6, 0.2)
        P["eye_dy"] = -0.3
        if t > 3:
            P["eyes"] = "^"
    elif style == "flex":
        P["arm_l"] = P["arm_r"] = 0.0 if int(t / 0.6) % 2 else 0.6
        P["eyes"] = "^"
    elif style == "lookout":                 # hand shading his eyes, scanning the horizon
        self.set_arm(P, 1, 0.4, -1.8)
        P["eye_dx"] = [0.34, 0.0, -0.34, 0.0][int(t / 1.0) % 4] * d
    elif style == "think":
        self.set_arm(P, 1, 2.6, 0.4)
        self.set_arm(P, -1, 1.2, 2.2)
        P["eye_dx"], P["eye_dy"] = 0.34 * d, -0.3
    elif style == "duel":                    # weapon forward, ready stance
        self.set_arm(P, 1, 2.0, 0.8)
        P["leg_dx"] = [-0.5, -0.25, 0.25, 0.5]
        P["brows"] = True
        P["eye_dx"] = 0.34 * d
    elif style == "sneak":
        self.steps(P, t, d, 0.22, 0.4, 0.4, 0.15)
        P.update(bh=5.5)
        P["eye_dx"] = [0.34, -0.34][int(t / 0.9) % 2] * d
    elif style == "shamble":                 # arms out in front, slow lurch
        self.steps(P, t, d, 0.35, 0.3, 0.6, 0.15)
        self.set_arm(P, 1, 2.0, 1.4)
        self.set_arm(P, -1, 2.2, 9.4)
        P["lean"] = 0.25
        P["eye_h"] = 0.6
    elif style == "stomp":
        self.steps(P, t, d, 0.4, 0.5, 0.8, 0.3)
        P["arm_l"] = P["arm_r"] = 1.0
        P["arm_lx"], P["arm_rx"] = 0.8, -0.8
        P["mouth"] = 0.8 if int(t / 0.8) % 2 else 0.0
    elif style == "cape":                    # holds the cape up dramatically
        P["arm_l"] = P["arm_r"] = 0.8
        P["arm_lx"], P["arm_rx"] = -0.8, 0.8
        P["eye_h"] = 0.6
    elif style == "robot":                   # stiff, jerky moves
        k = int(t / 0.5) % 4
        P["arm_l"] = (0.0, 2.0, 2.0, 0.0)[k]
        P["arm_r"] = (2.0, 0.0, 2.0, 0.0)[k]
        P["eye_h"] = 0.6
    elif style == "wave":
        self.set_arm(P, 1, 0.0 if int(t / 0.18) % 2 else 0.6)
        P["eyes"] = "^"


# ---------------- props ----------------
def _prop(self, t, d, g, key, layer):
    prop = SCENES[key][4]
    bt, bl, bw = g["bt"], g["bl"], g["bw"]
    hx, hy = g["hf"]
    if layer == "back":
        if prop == "night":                  # moon and a city skyline behind him
            self.O(CX + 6.5 * d - 1.6, 1.0, 3.2, 3.2, fill="#F5EBD7")
            self.O(CX + 6.5 * d - 0.8, 0.6, 3.2, 3.2, fill=KEY_DARK)
            for i, (w, h) in enumerate(((2.2, 5), (1.8, 7), (2.6, 4), (1.6, 6), (2.2, 8), (2.0, 5))):
                x = 0.4 + sum(ww for ww, _ in ((2.2, 5), (1.8, 7), (2.6, 4), (1.6, 6), (2.2, 8), (2.0, 5))[:i]) * 2.3
                self.R(x, FEET - h, w * 1.9, h, "#2A2A3A")
                if i % 2 == 0:
                    self.R(x + 0.6, FEET - h + 1.0, 0.5, 0.5, "#F2C94C")
        elif prop == "moon":
            self.O(CX - 7 * d - 1.6, 0.8, 3.2, 3.2, fill="#F5EBD7")
        elif prop == "saucer":
            sx = CX - 8 * d
            y = 2.2 + 0.4 * math.sin(t * 3)
            self.O(sx - 3, y, 6, 1.6, fill="#9AA0A8")
            self.O(sx - 1.4, y - 1.1, 2.8, 2.0, fill="#BFE8FF")
            if int(t / 0.3) % 2:
                self.R(sx - 2.2, y + 0.6, 0.5, 0.4, "#7CFC00")
                self.R(sx + 1.6, y + 0.6, 0.5, 0.4, "#7CFC00")
        elif prop == "tumbleweed":
            x = (t * 6) % (COLS + 6) - 3
            x = x if d > 0 else COLS - x
            self.O(x - 1.2, FEET - 2.4 - abs(math.sin(t * 5)) * 0.8, 2.4, 2.4, outline="#A0703F", width=2)
        elif prop == "flag":
            fx = CX - 7.5 * d
            self.R(fx, FEET - 9, 0.4, 9, "#CCCCCC")
            wave = 0.3 * math.sin(t * 4)
            self.Pg([(fx + 0.4, FEET - 9), (fx + 0.4 + 4 * -d * -1, FEET - 8.4 + wave),
                     (fx + 0.4, FEET - 7)], "#D97757")
        elif prop == "chest":
            cx = self.M(6, 3.6)
            self.R(cx, FEET - 2.4, 3.6, 2.4, "#8B5A2B")
            self.R(cx, FEET - 2.4, 3.6, 0.6, "#6B4423")
            self.R(cx + 1.5, FEET - 2.0, 0.6, 0.8, "#F2C94C")
            if int(t / 0.4) % 2:
                self.T(cx + 1.8, FEET - 3.2, "*", 8, "#F2C94C")
        return
    # ---- front ----
    if prop == "star":
        self.T(CX, bt + 4.2, "★", 10, "#F2C94C", "Segoe UI Symbol")
    elif prop == "lasersword":
        tip = (hx + d * 1.6, hy - 6.0)
        glow = "#7CFC00" if int(t / 0.06) % 3 else "#C8FFB8"
        self.L([(hx + d * 0.4, hy), tip], glow, 4)
        self.L([(hx + d * 0.4, hy), tip], "#FFFFFF", 1)
        self.R(hx - 0.3, hy - 0.2, 0.8, 1.2, "#555555")
    elif prop == "magnifier":
        lx, ly = hx + d * 1.4, hy - 1.6
        self.L([(hx, hy), (lx, ly + 1.2)], "#5C3A1E", 3)
        self.O(lx - 1.4, ly - 1.4, 2.8, 2.8, fill="#DDF3FF", outline="#4A4A4A", width=3)
    elif prop == "staff":
        self.L([(hx, hy + 3), (hx, hy - 4)], "#6B4423", 3)
        self.O(hx - 0.9, hy - 5.4, 1.8, 1.8, fill="#9B6BDF")
        if int(t / 0.2) % 2:
            self.T(hx + d * 1.4, hy - 6.2, "*", 8, "#F2C94C")
    elif prop == "gloves":
        for gx, gy in (g["hl"], g["hr"]):
            self.R(gx - 1.2, gy - 1.2, 2.4, 2.4, "#C0392B")
    elif prop == "swordshield":
        self.L([(hx, hy), (hx + d * 1.0, hy - 5)], "#DDDDDD", 3)
        self.R(hx - 0.8, hy - 0.4, 1.6, 0.4, "#8B5A2B")
        sx, sy = g["hb"]
        self.Pg([(sx - 1.4, sy - 1.6), (sx + 1.4, sy - 1.6), (sx + 1.4, sy + 0.6), (sx, sy + 2.0),
                 (sx - 1.4, sy + 0.6)], "#2E6FD8", "#F2C94C")
    elif prop == "pan":
        self.L([(hx, hy), (hx + d * 1.8, hy - 1.4)], "#3A3A3A", 3)
        self.O(hx + d * 1.8 - 1.4, hy - 2.2, 2.8, 1.2, fill="#2B2B2B")
    elif prop == "axe":
        self.L([(hx, hy + 2), (hx, hy - 4)], "#6B4423", 3)
        self.Pg([(hx, hy - 4), (hx + d * 2.0, hy - 4.8), (hx + d * 2.0, hy - 2.4), (hx, hy - 3)], "#BBBBBB")
    elif prop == "map":
        mx = CX - 2.4
        self.R(mx, bt + 3.4, 4.8, 2.6, "#E9D8A6")
        self.L([(mx + 0.6, bt + 4.0), (mx + 2.0, bt + 5.0), (mx + 3.6, bt + 4.2)], "#C0392B", 1)
        self.T(mx + 3.8, bt + 4.3, "x", 6, "#C0392B")


KEY_DARK = "#010203"     # cuts a crescent out of the moon (transparent colour)


# ---------------- caption bubble above his head ----------------
def _caption(self, t, key):
    lines = SCENES[key][5]
    if "line" not in getattr(self, "scene_pick", {}) or self.scene_pick.get("key") != key \
            or self.scene_pick.get("start", -1) > self.clock or t < 0.05:
        self.scene_pick = {"key": key, "line": random.choice(lines), "start": self.clock}
    if not (0.5 < t < DUR - 0.3):
        self.kill_sprite("caption")
        return
    text = self.scene_pick["line"]
    shown = text[:max(1, int((t - 0.5) * 28))]           # typed out letter by letter
    col = self.body_color
    sc = getattr(self, "text_scale", 1.0)
    wu, hu = int(64 * sc), int(9 * sc) + 2               # bubble grows with the text size
    bx = self.x
    by = self.fy - 13 * PX - self.lift() - hu * PX / 2 - 4

    def draw(p, shown=shown, col=col):
        cv, u = p.cv, p.u
        w, h = wu * u, hu * u
        tail = 2 * u
        cv.create_rectangle(2, 2, w - 2, h - tail, fill="#1E1E1E", outline=col, width=2)
        cv.create_polygon(w / 2 - 6, h - tail - 1, w / 2 + 6, h - tail - 1, w / 2, h - 2,
                          fill="#1E1E1E", outline=col)
        cv.create_rectangle(w / 2 - 5, h - tail - 3, w / 2 + 5, h - tail, fill="#1E1E1E", outline="")
        cv.create_text(w / 2, (h - tail) / 2 + 1, text=shown, fill="#FFFFFF", width=w - 16,
                       font=("Segoe UI", max(8, round(9 * sc)), "bold"), justify="center")
    self.show_sprite("caption", wu, hu, bx, by, draw)
