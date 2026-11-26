"""Pixbot's wardrobe: 50+ original clothing pieces in three slots (hat / face / body),
plus ready-made outfit sets. Every piece is a small drawing function:

    fn(p, g, layer)   p = painter with R/O/Pg/L/T (grid units)
                      g = body geometry: bl (left), bw (width), bt (top), bh (height),
                          ey (eye row), d (facing +1/-1)
                      layer = "back" (behind his body) or "front"
"""


def _cx(g):
    return g["bl"] + g["bw"] / 2


# ----------------------------- HATS -----------------------------
def top_hat(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.R(cx - 3.6, bt - 0.6, 7.2, 0.7, "#1A1A1A")
    p.R(cx - 2.4, bt - 4.6, 4.8, 4.1, "#1A1A1A")
    p.R(cx - 2.4, bt - 1.6, 4.8, 0.6, "#B0101A")


def baseball_cap(color, back=False):
    def fn(p, g, layer):
        if layer != "front":
            return
        cx, bt, d = _cx(g), g["bt"], -g["d"] if back else g["d"]
        p.O(cx - 3.4, bt - 2.4, 6.8, 3.6, fill=color)
        p.R(cx - 3.4, bt - 0.6, 6.8, 0.8, color)
        brim_x = cx + 2.4 if d > 0 else cx - 5.6
        p.R(brim_x, bt - 0.1, 3.2, 0.5, color)
        p.R(cx - 0.3, bt - 2.6, 0.6, 0.4, "#FFFFFF")
    return fn


def beanie(color, pom="#FFFFFF"):
    def fn(p, g, layer):
        if layer != "front":
            return
        cx, bt = _cx(g), g["bt"]
        p.O(cx - 3.6, bt - 2.8, 7.2, 4.4, fill=color)
        p.R(cx - 3.8, bt - 0.4, 7.6, 1.0, pom if pom != "#FFFFFF" else color)
        for i in range(5):
            p.R(cx - 3.4 + i * 1.5, bt - 0.4, 0.6, 1.0, _darker(color))
        p.O(cx - 0.8, bt - 3.8, 1.6, 1.6, fill=pom)
    return fn




def crown(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.Pg([(cx - 3, bt + 0.2), (cx + 3, bt + 0.2), (cx + 3, bt - 2.6), (cx + 1.5, bt - 1.2),
          (cx, bt - 3.0), (cx - 1.5, bt - 1.2), (cx - 3, bt - 2.6)], "#F2C94C", "#B8913A")
    p.R(cx - 0.4, bt - 1.0, 0.8, 0.8, "#E5484D")


def party_hat(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.Pg([(cx - 2.2, bt + 0.3), (cx + 2.2, bt + 0.3), (cx + 0.4, bt - 4.4)], "#9B6BDF")
    p.R(cx - 1.4, bt - 1.4, 0.6, 0.6, "#F2C94C")
    p.R(cx + 0.4, bt - 2.6, 0.6, 0.6, "#6CC6F0")
    p.O(cx - 0.4, bt - 5.2, 1.4, 1.4, fill="#F07EB0")


def cowboy_hat(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.Pg([(cx - 6, bt - 0.4), (cx - 4.5, bt + 0.4), (cx + 4.5, bt + 0.4), (cx + 6, bt - 0.4),
          (cx + 4.5, bt - 0.2), (cx - 4.5, bt - 0.2)], "#8B5A2B")
    p.Pg([(cx - 3, bt - 0.2), (cx + 3, bt - 0.2), (cx + 2.6, bt - 3.2), (cx, bt - 2.6),
          (cx - 2.6, bt - 3.2)], "#9C6A38")
    p.R(cx - 3, bt - 1.0, 6, 0.5, "#5C3A1E")


def wizard_hat(p, g, layer):
    if layer != "front":
        return
    cx, bt, d = _cx(g), g["bt"], g["d"]
    p.O(cx - 5, bt - 0.8, 10, 1.6, fill="#2E3A87")
    p.Pg([(cx - 3, bt - 0.2), (cx + 3, bt - 0.2), (cx - d * 2.5, bt - 6.5)], "#2E3A87")
    p.T(cx, bt - 2.4, "★", 8, "#F2C94C", "Segoe UI Symbol")


def chef_hat(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.R(cx - 3, bt - 2.4, 6, 2.6, "#FFFFFF")
    p.O(cx - 3.8, bt - 4.6, 7.6, 3.2, fill="#FFFFFF")


def viking_helmet(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.O(cx - 3.6, bt - 2.8, 7.2, 4.4, fill="#9AA0A8")
    p.R(cx - 3.8, bt - 0.4, 7.6, 0.9, "#7E848C")
    p.Pg([(cx - 3.4, bt - 1.2), (cx - 5.6, bt - 4.4), (cx - 3.8, bt - 2.2)], "#F5EBD7")
    p.Pg([(cx + 3.4, bt - 1.2), (cx + 5.6, bt - 4.4), (cx + 3.8, bt - 2.2)], "#F5EBD7")


def pirate_hat(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.Pg([(cx - 5.4, bt + 0.2), (cx + 5.4, bt + 0.2), (cx + 3.4, bt - 3.0), (cx, bt - 2.2),
          (cx - 3.4, bt - 3.0)], "#1A1A1A")
    p.R(cx - 0.9, bt - 1.8, 1.8, 1.2, "#FFFFFF")
    p.R(cx - 0.4, bt - 1.6, 0.3, 0.3, "#1A1A1A")
    p.R(cx + 0.1, bt - 1.6, 0.3, 0.3, "#1A1A1A")


def santa_hat(p, g, layer):
    if layer != "front":
        return
    cx, bt, d = _cx(g), g["bt"], g["d"]
    p.Pg([(cx - 3.4, bt + 0.2), (cx + 3.4, bt + 0.2), (cx - d * 4.2, bt - 3.4)], "#D7263D")
    p.R(cx - 3.8, bt - 0.4, 7.6, 1.0, "#FFFFFF")
    p.O(cx - d * 4.2 - 0.8, bt - 4.2, 1.6, 1.6, fill="#FFFFFF")


def grad_cap(p, g, layer):
    if layer != "front":
        return
    cx, bt, d = _cx(g), g["bt"], g["d"]
    p.R(cx - 2.6, bt - 1.2, 5.2, 1.4, "#1A1A1A")
    p.Pg([(cx - 4.6, bt - 1.4), (cx, bt - 2.6), (cx + 4.6, bt - 1.4), (cx, bt - 0.6)], "#1A1A1A")
    p.L([(cx, bt - 1.6), (cx + d * 3.6, bt - 1.2), (cx + d * 3.8, bt + 1.2)], "#F2C94C", 2)


def beret(p, g, layer):
    if layer != "front":
        return
    cx, bt, d = _cx(g), g["bt"], g["d"]
    p.O(cx - 3.8 - d * 0.6, bt - 2.0, 7.6, 2.6, fill="#C0392B")
    p.R(cx - 0.2, bt - 2.6, 0.4, 0.7, "#C0392B")


def sombrero(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.O(cx - 7, bt - 1.0, 14, 2.0, fill="#E9C46A", outline="#B8913A")
    p.Pg([(cx - 2.6, bt - 0.2), (cx + 2.6, bt - 0.2), (cx + 1.6, bt - 3.8), (cx - 1.6, bt - 3.8)], "#E9C46A")
    p.R(cx - 2.4, bt - 1.2, 4.8, 0.5, "#2FA84F")
    p.R(cx - 6, bt - 0.4, 12, 0.3, "#E5484D")


def propeller_cap(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.O(cx - 3.2, bt - 2.4, 6.4, 3.4, fill="#4A90E2")
    p.Pg([(cx, bt - 2.4), (cx - 0.9, bt - 0.8), (cx, bt - 0.8)], "#E5484D")
    p.Pg([(cx, bt - 2.4), (cx + 0.9, bt - 0.8), (cx, bt - 0.8)], "#F2C94C")
    p.R(cx - 0.15, bt - 3.4, 0.3, 1.0, "#555555")
    p.R(cx - 2.4, bt - 3.6, 4.8, 0.4, "#E5484D")


def bunny_ears(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    for sx in (-1.8, 1.8):
        p.O(cx + sx - 0.9, bt - 4.8, 1.8, 5.0, fill="#FFFFFF")
        p.O(cx + sx - 0.4, bt - 4.0, 0.8, 3.6, fill="#F7B8CF")


def cat_ears(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    for sx in (-2.6, 2.6):
        p.Pg([(cx + sx - 1.4, bt + 0.2), (cx + sx + 1.4, bt + 0.2), (cx + sx, bt - 2.4)], "#333333")
        p.Pg([(cx + sx - 0.6, bt), (cx + sx + 0.6, bt), (cx + sx, bt - 1.3)], "#F7B8CF")


def halo(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.O(cx - 3, bt - 2.6, 6, 1.4, outline="#F2C94C", width=3)


def devil_horns(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    for sx in (-2.6, 2.6):
        p.Pg([(cx + sx - 0.9, bt + 0.3), (cx + sx + 0.9, bt + 0.3), (cx + sx * 1.25, bt - 2.0)], "#C0392B")


def flower(p, g, layer):
    if layer != "front":
        return
    x, y = g["bl"] + g["bw"] - 1.6, g["bt"] - 0.4
    for dx, dy in ((-0.8, 0), (0.8, 0), (0, -0.8), (0, 0.8)):
        p.O(x + dx - 0.7, y + dy - 0.7, 1.4, 1.4, fill="#F07EB0")
    p.O(x - 0.5, y - 0.5, 1.0, 1.0, fill="#F2C94C")


def ribbon_bow(p, g, layer):
    if layer != "front":
        return
    x, y = g["bl"] + g["bw"] - 2.0, g["bt"] - 0.4
    p.Pg([(x, y), (x - 1.8, y - 1.1), (x - 1.8, y + 1.1)], "#E5484D")
    p.Pg([(x, y), (x + 1.8, y - 1.1), (x + 1.8, y + 1.1)], "#E5484D")
    p.R(x - 0.4, y - 0.4, 0.8, 0.8, "#B0101A")


def knight_helmet(p, g, layer):
    if layer != "front":
        return
    bl, bw, bt, ey = g["bl"], g["bw"], g["bt"], g["ey"]
    p.R(bl - 0.2, bt - 1.4, bw + 0.4, 3.4, "#9AA0A8")
    p.O(bl - 0.2, bt - 2.8, bw + 0.4, 3.0, fill="#9AA0A8")
    p.R(bl + 0.6, ey + 0.3, bw - 1.2, 0.35, "#2B2B2B")
    p.Pg([(_cx(g), bt - 2.8), (_cx(g) + 1.2, bt - 5.0), (_cx(g) + 2.2, bt - 4.6)], "#C0392B")


def space_helmet(p, g, layer):
    if layer == "back":
        return
    cx = _cx(g)
    p.O(cx - g["bw"] / 2 - 1.0, g["bt"] - 1.4, g["bw"] + 2.0, 6.0, outline="#CFE8F8", width=3)
    p.O(cx + 1.4, g["bt"] - 0.6, 1.4, 0.8, fill="#FFFFFF")






def headband(p, g, layer):
    if layer != "front":
        return
    bl, bw, bt, d = g["bl"], g["bw"], g["bt"], g["d"]
    p.R(bl - 0.1, bt + 0.25, bw + 0.2, 0.7, "#E5484D")
    kx = bl if d > 0 else bl + bw
    p.Pg([(kx, bt + 0.5), (kx - d * 2.4, bt + 0.1), (kx - d * 2.2, bt + 0.8)], "#E5484D")


# ----------------------------- FACE -----------------------------
def _eyes(g):
    sx = g["bw"] / 8
    return g["bl"] + 1 * sx, g["bl"] + g["bw"] - 1 * sx - 1


def sunglasses(p, g, layer):
    if layer != "front":
        return
    e1, e2 = _eyes(g)
    ey = g["ey"]
    for ex in (e1, e2):
        p.Pg([(ex - 0.6, ey - 0.25), (ex + 1.6, ey - 0.25), (ex + 1.3, ey + 1.1), (ex - 0.3, ey + 1.1)], "#0A0A0A")
        p.L([(ex - 0.2, ey + 0.1), (ex + 0.4, ey - 0.05)], "#7A7A7A", 2)
    p.R(e1 + 1.6, ey - 0.15, e2 - e1 - 2.2, 0.3, "#0A0A0A")
    p.R(g["bl"] - 0.1, ey - 0.15, e1 - g["bl"] - 0.4, 0.25, "#0A0A0A")
    p.R(e2 + 1.6, ey - 0.15, g["bl"] + g["bw"] - e2 - 1.4, 0.25, "#0A0A0A")


def nerd_glasses(p, g, layer):
    if layer != "front":
        return
    e1, e2 = _eyes(g)
    ey = g["ey"]
    for ex in (e1, e2):
        p.O(ex - 0.7, ey - 0.6, 2.4, 2.2, outline="#1A1A1A", width=2)
    p.R(e1 + 1.7, ey + 0.2, e2 - e1 - 2.4, 0.25, "#1A1A1A")


def monocle(p, g, layer):
    if layer != "front":
        return
    e1, e2 = _eyes(g)
    ey = g["ey"]
    p.O(e2 - 0.7, ey - 0.6, 2.4, 2.4, outline="#F2C94C", width=2)
    p.L([(e2 + 1.4, ey + 1.6), (e2 + 1.8, ey + 3.6)], "#F2C94C", 1)


def eyepatch(p, g, layer):
    if layer != "front":
        return
    e1, e2 = _eyes(g)
    ey = g["ey"]
    p.O(e1 - 0.5, ey - 0.5, 2.0, 2.0, fill="#1A1A1A")
    p.L([(g["bl"], ey - 1.2), (g["bl"] + g["bw"], ey + 1.6)], "#1A1A1A", 2)


def mustache(p, g, layer):
    if layer != "front":
        return
    cx, y = _cx(g), g["ey"] + 1.8
    p.Pg([(cx, y), (cx - 2.6, y + 0.9), (cx - 1.4, y - 0.2)], "#3B2314")
    p.Pg([(cx, y), (cx + 2.6, y + 0.9), (cx + 1.4, y - 0.2)], "#3B2314")


def beard(p, g, layer):
    if layer != "front":
        return
    bl, bw, ey = g["bl"], g["bw"], g["ey"]
    p.Pg([(bl + 0.4, ey + 1.8), (bl + bw - 0.4, ey + 1.8), (bl + bw - 1.6, ey + 4.6),
          (_cx(g), ey + 5.4), (bl + 1.6, ey + 4.6)], "#8B5A2B")


def clown_nose(p, g, layer):
    if layer != "front":
        return
    cx, y = _cx(g), g["ey"] + 1.2
    p.O(cx - 0.9, y, 1.8, 1.8, fill="#E5484D")
    p.O(cx - 0.4, y + 0.2, 0.6, 0.5, fill="#FF9A9E")


def glasses_3d(p, g, layer):
    if layer != "front":
        return
    e1, e2 = _eyes(g)
    ey = g["ey"]
    p.R(g["bl"] + 0.3, ey - 0.4, g["bw"] - 0.6, 1.8, "#F5F5F5")
    p.R(e1 - 0.4, ey - 0.2, 1.8, 1.4, "#E5484D")
    p.R(e2 - 0.4, ey - 0.2, 1.8, 1.4, "#4AA8E2")


def star_glasses(p, g, layer):
    if layer != "front":
        return
    e1, e2 = _eyes(g)
    for ex in (e1, e2):
        p.T(ex + 0.5, g["ey"] + 0.5, "★", 13, "#F07EB0", "Segoe UI Symbol")


def ninja_mask(p, g, layer):
    if layer != "front":
        return
    bl, bw, ey = g["bl"], g["bw"], g["ey"]
    p.R(bl, ey + 1.4, bw, g["bt"] + g["bh"] - ey - 2.2, "#2B2B2B")


def blush(p, g, layer):
    if layer != "front":
        return
    e1, e2 = _eyes(g)
    for ex in (e1, e2):
        p.R(ex - 0.4, g["ey"] + 1.3, 1.6, 0.5, "#FF8FA8")




def _darker(hex_color, f=0.75):
    h = hex_color.lstrip("#")
    r, gg, b = (int(int(h[i:i + 2], 16) * f) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (r, gg, b)


# ----------------------------- BODY -----------------------------
def bow_tie(p, g, layer):
    if layer != "front":
        return
    cx, y = _cx(g), g["bt"] + g["bh"] * 0.62
    p.Pg([(cx, y), (cx - 1.8, y - 0.9), (cx - 1.8, y + 0.9)], "#B0101A")
    p.Pg([(cx, y), (cx + 1.8, y - 0.9), (cx + 1.8, y + 0.9)], "#B0101A")
    p.R(cx - 0.4, y - 0.4, 0.8, 0.8, "#7A0A12")


def neck_tie(p, g, layer):
    if layer != "front":
        return
    cx, y = _cx(g), g["bt"] + g["bh"] * 0.55
    p.Pg([(cx - 0.5, y), (cx + 0.5, y), (cx + 0.8, y + 2.2), (cx, y + 2.8), (cx - 0.8, y + 2.2)], "#2E3A87")


def scarf(p, g, layer):
    if layer != "front":
        return
    bl, bw, y, d = g["bl"], g["bw"], g["bt"] + g["bh"] * 0.5, g["d"]
    p.R(bl - 0.2, y, bw + 0.4, 1.0, "#E5484D")
    for i in range(4):
        p.R(bl + 0.4 + i * 2.0, y, 0.7, 1.0, "#FFFFFF")
    x = bl + 1 if d < 0 else bl + bw - 2
    p.R(x, y + 0.9, 1.1, 2.6, "#E5484D")


def cape(color, inner):
    def fn(p, g, layer):
        if layer != "back":
            return
        bl, bw, bt, bh = g["bl"], g["bw"], g["bt"], g["bh"]
        p.Pg([(bl + 0.4, bt + 1.0), (bl + bw - 0.4, bt + 1.0), (bl + bw + 1.6, bt + bh + 2.0),
              (bl - 1.6, bt + bh + 2.0)], color)
        p.R(bl - 0.2, bt + 0.9, bw + 0.4, 0.6, inner)
    return fn


def gold_chain(p, g, layer):
    if layer != "front":
        return
    bl, bw, y = g["bl"], g["bw"], g["bt"] + g["bh"] * 0.5
    p.L([(bl + 1.0, y), (_cx(g), y + 1.6), (bl + bw - 1.0, y)], "#F2C94C", 3)
    p.O(_cx(g) - 0.6, y + 1.3, 1.2, 1.2, fill="#F2C94C")


def medal(p, g, layer):
    if layer != "front":
        return
    cx, y = _cx(g), g["bt"] + g["bh"] * 0.5
    p.Pg([(cx - 1.2, y), (cx - 0.2, y), (cx, y + 1.6), (cx - 1.0, y + 1.6)], "#4A90E2")
    p.Pg([(cx + 1.2, y), (cx + 0.2, y), (cx, y + 1.6), (cx + 1.0, y + 1.6)], "#E5484D")
    p.O(cx - 0.8, y + 1.4, 1.6, 1.6, fill="#F2C94C", outline="#B8913A")


def backpack(p, g, layer):
    if layer != "back":
        return
    bl, bw, bt, d = g["bl"], g["bw"], g["bt"], g["d"]
    x = bl - 1.6 if d > 0 else bl + bw
    p.R(x, bt + 1.2, 1.8, 3.8, "#2FA84F")
    p.R(x, bt + 2.8, 1.8, 0.4, "#1F7A3A")


def tutu(p, g, layer):
    if layer != "front":
        return
    bl, bw, y = g["bl"], g["bw"], g["bt"] + g["bh"] - 1.4
    p.Pg([(bl - 1.2, y + 1.4), (bl + 0.6, y), (bl + bw - 0.6, y), (bl + bw + 1.2, y + 1.4)], "#F7B8CF")
    for i in range(5):
        p.R(bl - 0.6 + i * (bw + 1.2) / 5, y + 1.0, 0.4, 0.4, "#FFFFFF")


def apron(p, g, layer):
    if layer != "front":
        return
    cx, bt, bh = _cx(g), g["bt"], g["bh"]
    p.R(cx - 2.4, bt + bh * 0.45, 4.8, bh * 0.55 + 0.2, "#FFFFFF")
    p.R(cx - 1.2, bt + bh * 0.62, 2.4, 1.0, "#E5E5E5")


def angel_wings(p, g, layer):
    if layer != "back":
        return
    bl, bw, bt = g["bl"], g["bw"], g["bt"]
    p.O(bl - 4.2, bt - 0.4, 5.0, 4.4, fill="#FFFFFF", outline="#DADADA")
    p.O(bl + bw - 0.8, bt - 0.4, 5.0, 4.4, fill="#FFFFFF", outline="#DADADA")


def suit_jacket(p, g, layer):
    if layer != "front":
        return
    bl, bw, bt, bh = g["bl"], g["bw"], g["bt"], g["bh"]
    st = bt + bh * 0.47
    p.R(bl, st, bw, bt + bh - st, "#1A1A1A")
    cx = _cx(g)
    p.Pg([(cx - 1.1, st), (cx + 1.1, st), (cx, st + 1.8)], "#FFFFFF")


def superhero_belt(p, g, layer):
    if layer != "front":
        return
    bl, bw, y = g["bl"], g["bw"], g["bt"] + g["bh"] - 1.4
    p.R(bl, y, bw, 0.8, "#F2C94C")
    p.R(_cx(g) - 0.8, y - 0.2, 1.6, 1.2, "#B8913A")


def life_vest(p, g, layer):
    if layer != "front":
        return
    bl, bw, bt, bh = g["bl"], g["bw"], g["bt"], g["bh"]
    p.R(bl + 0.2, bt + bh * 0.45, 2.2, bh * 0.5, "#F28C28")
    p.R(bl + bw - 2.4, bt + bh * 0.45, 2.2, bh * 0.5, "#F28C28")


# ----------------------------- movie-look pieces (original designs) -----------------------------
def domino_mask(color):
    def fn(p, g, layer):
        if layer != "front":
            return
        bl, bw, ey = g["bl"], g["bw"], g["ey"]
        p.Pg([(bl + 0.2, ey - 0.5), (bl + bw - 0.2, ey - 0.5), (bl + bw - 0.6, ey + 1.4),
              (_cx(g) + 0.5, ey + 1.0), (_cx(g) - 0.5, ey + 1.0), (bl + 0.6, ey + 1.4)], color)
        e1, e2 = _eyes(g)
        for ex in (e1, e2):
            p.R(ex, ey, 1, 1, "#FFFFFF")
    return fn


def deerstalker(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.O(cx - 3.4, bt - 2.6, 6.8, 3.6, fill="#8A6E4B")
    for i in range(4):
        p.R(cx - 3.0 + i * 1.6, bt - 2.0, 0.3, 2.2, "#6E5638")
    p.R(cx - 5.0, bt - 0.4, 2.2, 0.6, "#8A6E4B")
    p.R(cx + 2.8, bt - 0.4, 2.2, 0.6, "#8A6E4B")


def dino_hood(p, g, layer):
    if layer != "front":
        return
    bl, bw, bt = g["bl"], g["bw"], g["bt"]
    p.R(bl - 0.2, bt - 1.0, bw + 0.4, 1.4, "#4FA34D")
    for i in range(4):
        x = bl + 0.6 + i * 2.0
        p.Pg([(x, bt - 0.9), (x + 1.4, bt - 0.9), (x + 0.7, bt - 2.4)], "#F2C94C")


def vamp_cape(p, g, layer):
    bl, bw, bt, bh = g["bl"], g["bw"], g["bt"], g["bh"]
    if layer == "back":
        p.Pg([(bl, bt + 0.6), (bl + bw, bt + 0.6), (bl + bw + 2.2, bt + bh + 2.0),
              (bl - 2.2, bt + bh + 2.0)], "#1A1A1A")
        p.Pg([(bl - 0.6, bt + 0.6), (bl - 2.4, bt - 2.6), (bl + 1.4, bt + 0.6)], "#8E1B2E")
        p.Pg([(bl + bw + 0.6, bt + 0.6), (bl + bw + 2.4, bt - 2.6), (bl + bw - 1.4, bt + 0.6)], "#8E1B2E")


def fangs(p, g, layer):
    if layer != "front":
        return
    cx, y = _cx(g), g["ey"] + 1.8
    p.Pg([(cx - 1.2, y), (cx - 0.4, y), (cx - 0.8, y + 1.0)], "#FFFFFF")
    p.Pg([(cx + 0.4, y), (cx + 1.2, y), (cx + 0.8, y + 1.0)], "#FFFFFF")


def antenna(color):
    def fn(p, g, layer):
        if layer != "front":
            return
        cx, bt = _cx(g), g["bt"]
        for sx in (-2.0, 2.0):
            p.L([(cx + sx, bt + 0.2), (cx + sx * 1.3, bt - 2.6)], "#555555", 2)
            p.O(cx + sx * 1.3 - 0.6, bt - 3.2, 1.2, 1.2, fill=color)
    return fn


def bandages(p, g, layer):
    if layer != "front":
        return
    bl, bw, bt, bh = g["bl"], g["bw"], g["bt"], g["bh"]
    for i in range(5):
        y = bt + 0.3 + i * bh / 5
        if abs(y - g["ey"]) < 1.0:
            continue
        p.R(bl - 0.1, y, bw + 0.2, 0.55, "#EDE6D6")
    p.L([(bl, bt + 0.8), (bl + bw, bt + bh - 0.8)], "#D8CFBA", 2)


def pith_helmet(p, g, layer):
    if layer != "front":
        return
    cx, bt = _cx(g), g["bt"]
    p.O(cx - 5, bt - 0.8, 10, 1.6, fill="#D9C28F")
    p.O(cx - 3.2, bt - 3.4, 6.4, 3.6, fill="#D9C28F")
    p.R(cx - 3.1, bt - 0.9, 6.2, 0.5, "#8A6E4B")


def hooded_robe(p, g, layer):
    bl, bw, bt, bh = g["bl"], g["bw"], g["bt"], g["bh"]
    if layer == "back":
        p.O(bl - 0.8, bt - 1.6, bw + 1.6, 4.0, fill="#6B4A2E")
    else:
        p.R(bl, bt + bh * 0.45, bw, bh * 0.55 + 0.2, "#7A5A3A")
        p.R(_cx(g) - 0.3, bt + bh * 0.45, 0.6, bh * 0.55, "#4E3620")


def boxing_robe(p, g, layer):
    if layer != "front":
        return
    bl, bw, bt, bh = g["bl"], g["bw"], g["bt"], g["bh"]
    p.R(bl, bt + bh * 0.45, bw, bh * 0.55 + 0.2, "#C0392B")
    p.Pg([(_cx(g) - 1.4, bt + bh * 0.45), (_cx(g) + 1.4, bt + bh * 0.45), (_cx(g), bt + bh * 0.75)], "#F2C94C")


def chest_star(p, g, layer):
    if layer != "front":
        return
    p.T(_cx(g), g["bt"] + g["bh"] * 0.68, "★", 10, "#F2C94C", "Segoe UI Symbol")


# ----------------------------- catalogue -----------------------------
OUTFITS = {
    # hats
    "tophat": ("hat", "Top hat", top_hat),
    "redcap": ("hat", "Red baseball cap", baseball_cap("#D7263D")),
    "bluecap": ("hat", "Blue baseball cap", baseball_cap("#2E6FD8")),
    "backcap": ("hat", "Backwards cap", baseball_cap("#2B2B2B", back=True)),
    "beanie": ("hat", "Beanie", beanie("#4A90E2", "#FFFFFF")),
    "crown": ("hat", "Crown", crown),
    "partyhat": ("hat", "Party hat", party_hat),
    "cowboy": ("hat", "Cowboy hat", cowboy_hat),
    "wizard": ("hat", "Wizard hat", wizard_hat),
    "chefhat": ("hat", "Chef hat", chef_hat),
    "viking": ("hat", "Viking helmet", viking_helmet),
    "piratehat": ("hat", "Pirate hat", pirate_hat),
    "santa": ("hat", "Santa hat", santa_hat),
    "gradcap": ("hat", "Graduation cap", grad_cap),
    "beret": ("hat", "Beret", beret),
    "sombrero": ("hat", "Sombrero", sombrero),
    "propeller": ("hat", "Propeller cap", propeller_cap),
    "bunny": ("hat", "Bunny ears", bunny_ears),
    "catears": ("hat", "Cat ears", cat_ears),
    "halo": ("hat", "Halo", halo),
    "horns": ("hat", "Devil horns", devil_horns),
    "flower": ("hat", "Flower", flower),
    "ribbon": ("hat", "Ribbon bow", ribbon_bow),
    "knight": ("hat", "Knight helmet", knight_helmet),
    "spacehelmet": ("hat", "Space helmet", space_helmet),
    "headband": ("hat", "Red headband", headband),
    # face
    "sunglasses": ("face", "Sunglasses", sunglasses),
    "nerdglasses": ("face", "Round glasses", nerd_glasses),
    "monocle": ("face", "Monocle", monocle),
    "eyepatch": ("face", "Eyepatch", eyepatch),
    "mustache": ("face", "Mustache", mustache),
    "beard": ("face", "Beard", beard),
    "clownnose": ("face", "Clown nose", clown_nose),
    "glasses3d": ("face", "3D glasses", glasses_3d),
    "starglasses": ("face", "Star glasses", star_glasses),
    "ninjamask": ("face", "Ninja mask", ninja_mask),
    "blush": ("face", "Blushing cheeks", blush),
    # body
    "bowtie": ("body", "Bow tie", bow_tie),
    "tie": ("body", "Tie", neck_tie),
    "scarf": ("body", "Striped scarf", scarf),
    "redcape": ("body", "Hero cape", cape("#D7263D", "#B0101A")),
    "royalcape": ("body", "Royal cape", cape("#6A2C91", "#F2C94C")),
    "goldchain": ("body", "Gold chain", gold_chain),
    "medal": ("body", "Medal", medal),
    "backpack": ("body", "Backpack", backpack),
    "tutu": ("body", "Tutu", tutu),
    "apron": ("body", "Apron", apron),
    "wings": ("body", "Angel wings", angel_wings),
    "jacket": ("body", "Suit jacket", suit_jacket),
    "herobelt": ("body", "Hero belt", superhero_belt),
    "lifevest": ("body", "Life vest", life_vest),
    # movie-look pieces
    "deerstalker": ("hat", "Detective hat", deerstalker),
    "dinohood": ("hat", "Dino hood", dino_hood),
    "antennae": ("hat", "Alien antennae", antenna("#7CFC00")),
    "robotantenna": ("hat", "Robot antennae", antenna("#E5484D")),
    "pith": ("hat", "Explorer helmet", pith_helmet),
    "heromask": ("face", "Hero mask (blue)", domino_mask("#2E6FD8")),
    "nightmask": ("face", "Night-watch mask", domino_mask("#1A1A1A")),
    "fangs": ("face", "Vampire fangs", fangs),
    "nightcape": ("body", "Night-watch cape", cape("#1A1A1A", "#3A3A3A")),
    "vampcape": ("body", "Vampire cape", vamp_cape),
    "bandages": ("body", "Mummy wraps", bandages),
    "robe": ("body", "Hooded robe", hooded_robe),
    "boxrobe": ("body", "Boxing robe", boxing_robe),
    "chest_star": ("body", "Hero star emblem", chest_star),
}

SLOTS = [("hat", "Hats"), ("face", "Face"), ("body", "Body")]

SETS = {   # name: (hat, face, body)
    "King": ("crown", None, "royalcape"),
    "Pirate captain": ("piratehat", None, "redcape"),
    "Old-school pirate": ("piratehat", "eyepatch", None),
    "Wizard": ("wizard", "beard", None),
    "Chef": ("chefhat", "mustache", "apron"),
    "Cowboy": ("cowboy", "mustache", "scarf"),
    "Knight": ("knight", None, "redcape"),
    "Astronaut": ("spacehelmet", None, "backpack"),
    "Secret agent": (None, "sunglasses", "jacket"),
    "Party animal": ("partyhat", "starglasses", "bowtie"),
    "Viking": ("viking", "beard", None),
    "Ninja": ("headband", "ninjamask", None),
    "Superhero": (None, None, "redcape"),
    "Graduate": ("gradcap", "nerdglasses", "medal"),
    "Fighter": ("headband", None, "herobelt"),
}


def draw(p, outfit, g, layer, skip=()):
    """outfit = {"hat": key|None, "face": ..., "body": ...}"""
    for slot in ("body", "face", "hat") if layer == "front" else ("body", "hat", "face"):
        if slot in skip:
            continue
        key = (outfit or {}).get(slot)
        if key and key in OUTFITS:
            try:
                OUTFITS[key][2](p, g, layer)
            except Exception:
                pass
