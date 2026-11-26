"""Everything that can be switched on/off, shared by the pet and the control app."""
import json
import os

from pixbot_acts import ACT_GROUPS

from pixbot_paths import DATA_DIR as APPDIR, SETTINGS_FILE, COMMAND_FILE, PID_FILE  # noqa: E402

PRETTY = {
    "missioncomplete": "Mission complete", 
    "slingshot": "Slingshot launch",
    "saucers": "Saucer shooter",
    
    
    
    
    
    
    
    "paperplane": "Paper plane", "raincloud": "Rain cloud", "pullups": "Pull-ups",
    "bench": "Bench press", "curls": "Dumbbell curls", "guard": "PC security guard",
    "popcorn": "Popcorn chair", "listen": "Listening closely", "measure": "Sizing himself up",
    "stretchy": "Noodle stretch", "squish": "Pancake squish",
}

GROUPS = dict(ACT_GROUPS)
try:
    import pixbot_movies as _mv
    PRETTY.update({k: v[0] for k, v in _mv.SCENES.items()})
except Exception:
    pass
GROUPS["Transport"] = GROUPS.get("Transport", []) + ["cloud", "jetpack", "portalgun", "smokebomb",
                                                    "portal", "dig", "parachute"]
GROUPS["Moves"] = ["jump", "flip", "tricks", "slides", "explore", "point", "hang", "climb", "ceiling",
                   "hop", "tbhang", "edgehang", "mimic", "clock"]
GROUPS["Cursor games"] = ["reach", "grab", "jumparound", "slideunder", "kick", "bash", "chase",
                          "propose", "tag", "highfive", "throwball", "hideseek"]
GROUPS["Reacting to you"] = ["idlevisit", "typealong", "videoreact", "gamereact", "textbox", "hoverpet",
                             "clickstartle", "welcomeback", "fastmouse", "newwindow",
                             "closewindow", "clipboard", "battery", "greetings", "breakreminder",
                             "backspace", "capslock"]
PRETTY.update({
    "explore": "Hop onto windows & page content", "point": "Point at pictures / thumbnails",
    "hang": "Hang on the scrollbar", "climb": "Climb window borders", "parachute": "Climb out + parachute",
    "dig": "Dig + pop up", "portal": "Portals", "hop": "Change screens", "tbhang": "Hang off the taskbar",
    "edgehang": "Hang off small edges", "mimic": "Mimic logos", "clock": "Point at the clock late at night",
    "reach": "Reach for the cursor", "grab": "Grab & hang on the cursor", "jumparound": "Jump around the cursor",
    "slideunder": "Slide under the cursor", "kick": "Flying kick (and KO)", "bash": "Head bash (and KO)",
    "chase": "Chase the cursor", "propose": "Propose to the cursor",
    "newwindow": "Says 'ooh' when you open a window", "closewindow": "Waves bye when you close one",
    "clipboard": "Notices when you copy something", "battery": "Battery low / charging",
    "greetings": "Good morning & lunch time", "breakreminder": "Suggests a break after an hour",
    "backspace": "Facepalms at backspace mashing", "capslock": "Reacts to CAPS LOCK typing",
    "skate": "Skateboard (kickflips!)", "pogo": "Pogo stick", "cloud": "Golden flying cloud",
    "jetpack": "Jetpack", "portalgun": "Portal blaster", "smokebomb": "Ninja smoke bomb teleport",
    "portal": "Run through a portal", "dig": "Dig + pop up", "parachute": "Climb out + parachute",
    "dragonfight": "Dragon boss fight (bow & arrows)", "relax": "Relaxing in a deck chair",
    "tricks": "Tricks while jumping (flips, twists, splits...)",
    "slides": "Slides around (from runs and landings)",
    "gamereact": "Plays along when you're in a fullscreen game",
    "ceiling": "Monkey-bars along the top of the screen",
    "tag": "Tag - then runs away", "highfive": "High-five the cursor",
    "throwball": "Throw a ball at the cursor", "hideseek": "Hide and seek",
    "hoverpet": "Rest the cursor on him = pets", "clickstartle": "Jumps when you click near him",
    "welcomeback": "Welcomes you back", "fastmouse": "Gets blown away by a fast cursor",
    "dizzyspin": "Spin till dizzy", "trip": "Trips and faceplants", "peekaboo": "Peekaboo",
    "moonwalk": "Moonwalk", "hiccups": "Hiccups", "pushups": "Push-ups", "jumprope": "Jump rope",
    "boxing": "Punching bag", "deadlift": "Deadlift", "rockstar": "Rock guitar",
    "cooking": "Cooking pancakes", "gaming": "Playing video games", "dj": "DJ set",
    "yoga": "Yoga", "drawing": "Drawing",
    "idlevisit": "Come to the cursor when you're idle", "typealong": "Type along with you",
    "videoreact": "React to videos & music (until you pause)", "textbox": "Jump onto text boxes you click",
})

AVAILABILITY = [
    ("always", "Always", "He's always on screen, like now."),
    ("light", "When I'm not busy", "Leaves while you type a lot or are very active, comes back when things calm down."),
    ("idle", "Only when I'm idle", "Shows up after you've been away from mouse & keyboard for a while."),
    ("paused", "Paused", "Hidden until you change this."),
]

DEFAULTS = {               # (these defaults are your own setup, saved on 26 Nov 2026)
    "enabled": {},
    "frequency": 5.1,          # 1 = rarely ... 10 = constantly
    "availability": "always",
    "idle_seconds": 10,
    "screen_reading": True,
    "size": 4,
    # behaviour dials, all 0..10
    "home": 4.9,               # 0 = taskbar, 10 = top of the screen / up on things
    "energy": 0.0,             # 0 = calm, mostly sits and watches ... 10 = always on the move
    "cursor": 5.2,             # 0 = ignores your cursor ... 10 = obsessed with it
    "screenhop": 5.2,          # 0 = never changes screen ... 10 = changes screen often
    "color": "#7FA3C2",        # Pixbot's body colour
    "transport": 5.0,          # 0 = never uses transport ... 10 = rides around all the time
    "ride_length": 10.0,       # 0 = short rides ... 10 = rides for a long time
    "favorites": [],
    "dislikes": [],
    "fav_boost": 6,            # favourites come up this many times more often (1..10)
    "dislike_level": 2,        # disliked ones: 0 = never ... 10 = as often as the rest
    "outfit": {},              # {"hat": key, "face": key, "body": key}
    "text_size": 1.6,          # size of the words / captions above his head (1 = small ... 3 = huge)
}

COLOR_PRESETS = [
    ("Steel blue", "#7FA3C2"), ("Tangerine", "#D97757"), ("Sunset red", "#E0533D"), ("Bubblegum", "#F07EB0"),
    ("Grape", "#9B6BDF"), ("Ocean", "#4A90E2"), ("Sky", "#6CC6F0"), ("Mint", "#4FC79A"),
    ("Lime", "#9ACD32"), ("Banana", "#F2C94C"), ("Sand", "#D9B88F"), ("Snow", "#E8E8EE"),
    ("Charcoal", "#55575C"),
]


def shade(hex_color, f):
    """darker (f < 1) or lighter (f > 1) version of a colour"""
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    if f < 1:
        r, g, b = (int(v * f) for v in (r, g, b))
    else:
        r, g, b = (int(v + (255 - v) * (f - 1)) for v in (r, g, b))
    return "#%02x%02x%02x" % (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

BEHAVIOUR = [   # key, title, left label, right label
    ("home", "Where does he like to hang out?", "on the taskbar", "up top"),
    ("energy", "How much does he move around?", "calm", "hyper"),
    ("cursor", "How much does he play with your cursor?", "ignores it", "obsessed"),
    ("screenhop", "How often does he change screens?", "never", "often"),
]


def pretty(name):
    return PRETTY.get(name, name.capitalize())


def all_names():
    return [n for names in GROUPS.values() for n in names]


def load():
    s = json.loads(json.dumps(DEFAULTS))
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
        s.update({k: v for k, v in data.items() if k in DEFAULTS})
    except Exception:
        pass
    return s


def save(s):
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)
    os.replace(tmp, SETTINGS_FILE)


def special_gap(freq):
    """frequency dial 1..10 -> (min, max) seconds between special animations"""
    mid = 300 * (0.03 ** ((max(1, min(10, freq)) - 1) / 9))
    return mid * 0.6, mid * 1.4


# ---------------- tidy category layout (sidebar sections -> pages -> animations) ----------------
_LAYOUT = {
    "Everyday": ["wave", "dance", "think", "juggle", "happy", "error", "inspect", "build", "yawn",
                 "sneeze", "hiccups"],
    "Chill & hobbies": ["relax", "code", "gaming", "read", "coffee", "headphones", "meditate", "drawing",
                        "paint", "guitar", "rockstar", "dj", "cooking", "plant", "fish", "bubbles", "broom",
                        "camera", "pizza", "telescope", "paperplane", "raincloud", "balloon", "yoga"],
    "Sports & gym": ["train", "pullups", "bench", "curls", "pushups", "jumprope", "boxing", "deadlift",
                     "soccer"],
    "Silly": ["measure", "stretchy", "squish", "dizzyspin", "trip", "peekaboo", "moonwalk"],
    "Arcade fun": [
                  "saucers", "missioncomplete",
                  "slingshot", "dragonfight"],
    "Movie scenes": list(GROUPS.get("Movie scenes", [])),
    "Getting around": ["skate", "pogo", "cloud", "jetpack", "portalgun", "smokebomb", "portal", "dig",
                       "parachute"],
    "Moves & tricks": ["jump", "flip", "tricks", "slides", "explore", "point", "hang", "climb", "ceiling",
                       "hop", "tbhang", "edgehang", "mimic", "clock"],
    "Cursor games": list(GROUPS.get("Cursor games", [])),
    "Reacts to you": ["guard", "popcorn", "listen"] + list(GROUPS.get("Reacting to you", [])),
}
_all = [n for names in GROUPS.values() for n in names]
_seen = set()
for _g in _LAYOUT:                                   # drop duplicates / unknown names
    _LAYOUT[_g] = [n for n in _LAYOUT[_g] if n in _all and not (n in _seen or _seen.add(n))]
_LAYOUT["Everyday"] += [n for n in dict.fromkeys(_all) if n not in _seen]   # nothing gets lost
GROUPS = _LAYOUT

# sidebar: section header -> pages under it (pages that aren't animation lists are built by the app)
SECTIONS = [
    ("SETTINGS", ["General", "Behaviour", "Look", "Clothes"]),
    ("YOUR PICKS", ["Favourites ♥", "Disliked ✕"]),
    ("ANIMATIONS", ["Everyday", "Chill & hobbies", "Sports & gym", "Silly", "Arcade fun", "Movie scenes",
                    "Power forms"]),
    ("MOVING AROUND", ["Getting around", "Moves & tricks"]),
    ("INTERACTIVE", ["Cursor games", "Reacts to you"]),
    ("", ["Support / Donate"]),
]
