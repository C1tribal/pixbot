"""Pixbot - control app.

Turn every animation on/off, choose how often he does special things, when he's
around, start him with Windows, preview any animation, start/stop him.
Changes are saved instantly and Pixbot picks them up within a second.
"""
import ctypes
import json
import os
import subprocess
import sys
import time
import tkinter as tk
import winreg
from tkinter import ttk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixbot_catalog as cat  # noqa: E402

import pixbot_paths  # noqa: E402
ICON = pixbot_paths.ICON_FILE
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "Pixbot"

BG, CARD, CARD2 = "#1A1A1A", "#242424", "#2E2E2E"
FG, MUTED, ACCENT = "#ECECEC", "#9A9A9A", "#D97757"


# ---------------- pet process helpers ----------------
def pet_pid():
    try:
        pid = int(open(cat.PID_FILE).read().strip())
    except Exception:
        return None
    k32 = ctypes.windll.kernel32
    h = k32.OpenProcess(0x1000, False, pid)
    if not h:
        return None
    code = ctypes.c_ulong()
    k32.GetExitCodeProcess(h, ctypes.byref(code))
    k32.CloseHandle(h)
    return pid if code.value == 259 else None


def start_pet():
    if not pet_pid():
        subprocess.Popen(pixbot_paths.launch_cmd(), cwd=pixbot_paths.DATA_DIR, creationflags=0x00000008)


def send(cmd):
    cmd["t"] = time.time()
    with open(cat.COMMAND_FILE, "w", encoding="utf-8") as f:
        json.dump(cmd, f)


def stop_pet():
    pid = pet_pid()
    if not pid:
        return
    send({"quit": True})
    for _ in range(20):
        time.sleep(0.1)
        if not pet_pid():
            return
    subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)


# ---------------- start with Windows ----------------
def startup_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
            return True
    except OSError:
        return False


def set_startup(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ,
                              " ".join(f'"{a}"' for a in pixbot_paths.launch_cmd()))
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except OSError:
                pass


# ---------------- UI ----------------
class App:
    def __init__(self):
        self.s = cat.load()
        self.root = tk.Tk()
        self.root.title("Pixbot")
        self.root.configure(bg=BG)
        self.root.geometry("1060x800")
        self.root.minsize(780, 480)
        self.scrollers = []
        self.root.bind_all("<MouseWheel>", self.on_wheel)
        if os.path.exists(ICON):
            try:
                self.root.iconbitmap(ICON)
            except Exception:
                pass
        self.save_job = None
        self.style()
        self.build()
        self.status_loop()

    def style(self):
        st = ttk.Style(self.root)
        st.theme_use("clam")
        st.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
        st.configure("Card.TFrame", background=CARD)
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background=CARD, foreground=MUTED, padding=(12, 6),
                     borderwidth=0, font=("Segoe UI", 10))
        st.map("TNotebook.Tab", background=[("selected", CARD2)], foreground=[("selected", FG)])
        st.configure("TCheckbutton", background=CARD, foreground=FG, indicatorbackground=CARD2,
                     indicatorforeground=ACCENT, focuscolor=CARD)
        st.map("TCheckbutton", background=[("active", CARD)],
               indicatorbackground=[("selected", ACCENT), ("active", CARD2)])
        st.configure("TRadiobutton", background=CARD, foreground=FG, indicatorbackground=CARD2,
                     focuscolor=CARD)
        st.map("TRadiobutton", background=[("active", CARD)],
               indicatorbackground=[("selected", ACCENT)])
        st.configure("Horizontal.TScale", background=CARD, troughcolor=CARD2)
        st.configure("Vertical.TScrollbar", background=CARD2, troughcolor=CARD, borderwidth=0,
                     arrowcolor=MUTED, bordercolor=CARD, lightcolor=CARD2, darkcolor=CARD2,
                     gripcount=0)
        st.map("Vertical.TScrollbar", background=[("active", "#3A3A3A")])

    def label(self, parent, text, size=10, color=FG, bold=False, bg=CARD, wrap=0):
        return tk.Label(parent, text=text, bg=bg, fg=color, justify="left", anchor="w",
                        font=("Segoe UI", size, "bold" if bold else "normal"), wraplength=wrap)

    def button(self, parent, text, cmd, primary=False, bg=CARD):
        b = tk.Label(parent, text=text, bg=ACCENT if primary else CARD2,
                     fg="#1A1A1A" if primary else FG, padx=12, pady=5, cursor="hand2",
                     font=("Segoe UI", 10, "bold" if primary else "normal"))
        b.bind("<Button-1>", lambda e: cmd())
        return b

    def build(self):
        r = self.root
        # ----- header -----
        head = tk.Frame(r, bg=BG)
        head.pack(fill="x", padx=18, pady=(14, 8))
        self.logo = tk.Canvas(head, width=64, height=52, bg=BG, highlightthickness=0)
        self.logo.pack(side="left")
        self.draw_logo()
        t = tk.Frame(head, bg=BG)
        t.pack(side="left", padx=12)
        self.label(t, "Pixbot", 20, bold=True, bg=BG).pack(anchor="w")
        self.label(t, "your little desktop buddy - settings", 10, MUTED, bg=BG).pack(anchor="w")
        right = tk.Frame(head, bg=BG)
        right.pack(side="right")
        self.status = self.label(right, "", 10, MUTED, bg=BG)
        self.status.pack(side="left", padx=10)
        self.toggle_btn = self.button(right, "Start Pixbot", self.toggle_pet, primary=True)
        self.toggle_btn.pack(side="left", padx=4)
        self.button(right, "Restart", self.restart_pet).pack(side="left", padx=4)

        body = tk.Frame(r, bg=BG)
        body.pack(fill="both", expand=True, padx=18, pady=(4, 16))


        # ----- right: animations -----
        rightc = tk.Frame(body, bg=BG)
        rightc.pack(side="left", fill="both", expand=True)
        top = tk.Frame(rightc, bg=BG)
        top.pack(fill="x")
        self.label(top, "Settings & animations", 12, bold=True, bg=BG).pack(side="left")
        self.count_lbl = self.label(top, "", 9, MUTED, bg=BG)
        self.count_lbl.pack(side="left", padx=10)
        self.button(top, "Everything off", lambda: self.set_all(False), bg=BG).pack(side="right", padx=3)
        self.button(top, "Everything on", lambda: self.set_all(True), bg=BG).pack(side="right", padx=3)
        self.label(rightc, "Settings on the left, animations below. ▶ plays one right now.", 9, MUTED,
                   bg=BG).pack(anchor="w", pady=(2, 6))

        panel = tk.Frame(rightc, bg=CARD)
        panel.pack(fill="both", expand=True)
        side_outer = tk.Frame(panel, bg=CARD2, width=190)
        side_outer.pack(side="left", fill="y")
        side_outer.pack_propagate(False)
        side = self.scroll_area(side_outer, pad=False, bg=CARD2, bar=False)   # wheel-scrolls
        self.content = tk.Frame(panel, bg=CARD)
        self.content.pack(side="left", fill="both", expand=True)
        self.vars, self.pages, self.tabs = {}, {}, {}
        self.fav_btns, self.dis_btns = {}, {}
        # build every page first ...
        gen_outer = tk.Frame(self.content, bg=CARD)
        self.build_general(self.scroll_area(gen_outer, pad=False))
        self.pages["General"] = gen_outer
        for title, maker in (("Behaviour", self.make_behaviour_page), ("Look", self.make_look_page),
                             ("Clothes", self.make_clothes_page), ("Favourites ♥", self.make_fav_page),
                             ("Disliked ✕", self.make_dis_page), ("Support / Donate", self.make_support_page)):
            self.pages[title] = maker()
        for group, names in cat.GROUPS.items():
            self.pages[group] = self.make_tab(group, names)
        # ... then the sidebar, grouped under small section headers
        for i, (header, titles) in enumerate(cat.SECTIONS):
            if header:
                tk.Label(side, text=header, bg=CARD2, fg="#7A7A7A", anchor="w", padx=14,
                         pady=(2), font=("Segoe UI", 8, "bold")).pack(fill="x", pady=(10 if i else 6, 0))
            else:
                tk.Frame(side, bg="#3A3A3A", height=1).pack(fill="x", pady=(10, 2))
            for title in titles:
                if title not in self.pages:
                    continue
                count = len(cat.GROUPS[title]) if title in cat.GROUPS else None
                text = f"{title}  ({count})" if count else title
                b = tk.Label(side, text=text, bg=CARD2, fg=MUTED, anchor="w", padx=20, pady=6,
                             cursor="hand2", font=("Segoe UI", 10))
                b.pack(fill="x")
                b.bind("<Button-1>", lambda e, t_=title: self.show_page(t_))
                self.tabs[title] = b
        self.show_page("General")
        self.update_count()
        self.refresh_marks()

    # ---------- scrollable areas (mouse wheel works on whatever is under the pointer) ----------
    def scroll_area(self, parent, pad=True, bg=CARD, bar=True):
        canvas = tk.Canvas(parent, bg=bg, highlightthickness=0, yscrollincrement=20)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=bg)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.configure(yscrollcommand=sb.set)
        if bar:
            sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=(10, 0) if pad else 0,
                    pady=6 if pad else 0)
        self.scrollers.append(canvas)
        return inner

    def on_wheel(self, e):
        w = self.root.winfo_containing(e.x_root, e.y_root)
        while w is not None:
            if w in self.scrollers:
                bbox = w.bbox("all")
                if bbox and bbox[3] - bbox[1] > w.winfo_height():   # only if there's more to see
                    w.yview_scroll(int(-e.delta / 120) * 2, "units")
                return
            w = w.master

    def slider_row(self, parent, key, lo_txt, hi_txt, lo, hi, on_change):
        row = tk.Frame(parent, bg=CARD)
        self.label(row, lo_txt, 9, MUTED).pack(side="left")
        v = tk.DoubleVar(value=self.s.get(key, cat.DEFAULTS[key]))
        ttk.Scale(row, from_=lo, to=hi, variable=v, length=220,
                  command=lambda _=None: on_change(v)).pack(side="left", padx=8)
        self.label(row, hi_txt, 9, MUTED).pack(side="left")

        def reset():
            v.set(cat.DEFAULTS[key])
            on_change(v)
        self.button(row, "Default", reset).pack(side="left", padx=10)
        return row, v

    # ---------- favourites & dislikes ----------
    def make_fav_page(self):
        outer = tk.Frame(self.content, bg=CARD)
        page = self.scroll_area(outer, pad=False)
        self.label(page, "Favourites ♥", 12, bold=True).pack(anchor="w", padx=18, pady=(14, 2))
        self.label(page, "Tap ♥ next to any animation to add it here. He does these more often.",
                   9, MUTED, wrap=560).pack(anchor="w", padx=18)
        row, self.fav_var = self.slider_row(page, "fav_boost", "a bit more", "a LOT more", 1, 10,
                                            self.on_fav_boost)
        row.pack(anchor="w", padx=18, pady=(12, 0))
        self.fav_lbl = self.label(page, "", 9, ACCENT)
        self.fav_lbl.pack(anchor="w", padx=18)
        self.fav_list = tk.Frame(page, bg=CARD)
        self.fav_list.pack(fill="x", padx=12, pady=(8, 0))
        self.on_fav_boost(self.fav_var, save=False)
        return outer

    def make_dis_page(self):
        outer = tk.Frame(self.content, bg=CARD)
        page = self.scroll_area(outer, pad=False)
        self.label(page, "Disliked ✕", 12, bold=True).pack(anchor="w", padx=18, pady=(14, 2))
        self.label(page, "Tap ✕ next to any animation to add it here. He does these less often "
                         "(or never).", 9, MUTED, wrap=560).pack(anchor="w", padx=18)
        row, self.dis_var = self.slider_row(page, "dislike_level", "never", "as often as others",
                                            0, 10, self.on_dis_level)
        row.pack(anchor="w", padx=18, pady=(12, 0))
        self.dis_lbl = self.label(page, "", 9, ACCENT)
        self.dis_lbl.pack(anchor="w", padx=18)
        self.dis_list = tk.Frame(page, bg=CARD)
        self.dis_list.pack(fill="x", padx=12, pady=(8, 0))
        self.on_dis_level(self.dis_var, save=False)
        return outer

    # ---------- support / donate ----------
    LINKS_FILE = pixbot_paths.LINKS_FILE

    def load_links(self):
        try:
            with open(pixbot_paths.links_path(), encoding="utf-8") as f:
                data = json.load(f)
            return [(k, v.strip()) for k, v in data.items() if not k.startswith("_") and str(v).strip()]
        except Exception:
            return []

    def make_support_page(self):
        outer = tk.Frame(self.content, bg=CARD)
        page = self.scroll_area(outer, pad=False)
        self.label(page, "Support Pixbot ♥", 12, bold=True).pack(anchor="w", padx=18, pady=(14, 2))
        self.label(page, "Enjoying your little desktop buddy? Pixbot is free. If he makes your day a bit "
                         "better, you can help keep new animations coming:", 10, FG, wrap=520
                   ).pack(anchor="w", padx=18, pady=(4, 10))
        self.links_box = tk.Frame(page, bg=CARD)
        self.links_box.pack(anchor="w", padx=18)
        self.fill_links()
        row = tk.Frame(page, bg=CARD)
        row.pack(anchor="w", padx=18, pady=(14, 0))
        self.button(row, "Edit links...", self.edit_links).pack(side="left")
        self.button(row, "Reload", self.fill_links).pack(side="left", padx=8)
        self.label(page, "Other ways to help: share Pixbot with a friend, or tell me which animation "
                         "you want next!", 9, MUTED, wrap=520).pack(anchor="w", padx=18, pady=(16, 0))
        self.label(page, "Pixbot is an independent, original project: all of its art, animations and text "
                         "were made for Pixbot.", 8, MUTED, wrap=520
                   ).pack(anchor="w", padx=18, pady=(18, 10))
        return outer

    def fill_links(self):
        for w in self.links_box.winfo_children():
            w.destroy()
        links = self.load_links()
        if not links:
            self.label(self.links_box, "No donation links yet - press 'Edit links...' and paste yours "
                                       "into the file, then 'Reload'.", 9, MUTED, wrap=500).pack(anchor="w")
            return
        import webbrowser
        for i, (name, url) in enumerate(links):
            b = self.button(self.links_box, f"♥  {name}", lambda u=url: webbrowser.open(u), primary=(i == 0))
            b.grid(row=i // 3, column=i % 3, padx=(0, 8), pady=4, sticky="w")

    def edit_links(self):
        if not os.path.exists(self.LINKS_FILE):          # make your own editable copy first
            import shutil
            shutil.copyfile(pixbot_paths.DEFAULT_LINKS_FILE, self.LINKS_FILE)
        os.startfile(self.LINKS_FILE)

    def on_fav_boost(self, v, save=True):
        n = max(1, int(round(v.get())))
        self.s["fav_boost"] = n
        self.fav_lbl.config(text=f"favourites come up about {n}× as often"
                            + ("  (default)" if n == cat.DEFAULTS["fav_boost"] else ""))
        if save:
            self.save_soon()

    def on_dis_level(self, v, save=True):
        n = int(round(v.get()))
        self.s["dislike_level"] = n
        txt = "never" if n == 0 else ("as often as everything else" if n >= 10
                                      else f"only {n * 10}% as often as the others")
        self.dis_lbl.config(text=txt + ("  (default)" if n == cat.DEFAULTS["dislike_level"] else ""))
        if save:
            self.save_soon()

    def toggle_mark(self, name, kind):
        favs = self.s.setdefault("favorites", [])
        dis = self.s.setdefault("dislikes", [])
        mine, other = (favs, dis) if kind == "fav" else (dis, favs)
        if name in mine:
            mine.remove(name)
        else:
            mine.append(name)
            if name in other:
                other.remove(name)
        self.refresh_marks()
        self.save_soon()

    def refresh_marks(self):
        favs = set(self.s.get("favorites", []))
        dis = set(self.s.get("dislikes", []))
        for n, b in self.fav_btns.items():
            b.config(fg="#FF6B8B" if n in favs else "#666666")
        for n, b in self.dis_btns.items():
            b.config(fg="#E5484D" if n in dis else "#666666")
        for holder, names, kind in ((self.fav_list, favs, "fav"), (self.dis_list, dis, "dis")):
            for w in holder.winfo_children():
                w.destroy()
            if not names:
                self.label(holder, "Nothing here yet.", 9, MUTED).pack(anchor="w", padx=8, pady=6)
            for n in sorted(names, key=cat.pretty):
                row = tk.Frame(holder, bg=CARD)
                row.pack(anchor="w", pady=2)
                play = tk.Label(row, text="▶", bg=CARD2, fg=ACCENT, width=2, cursor="hand2",
                                font=("Segoe UI Symbol", 9))
                play.pack(side="left", padx=(0, 6))
                play.bind("<Button-1>", lambda e, nn=n: self.preview(nn))
                self.label(row, cat.pretty(n), 10).pack(side="left")
                rm = tk.Label(row, text="remove", bg=CARD2, fg=MUTED, padx=8, cursor="hand2",
                              font=("Segoe UI", 8))
                rm.pack(side="left", padx=10)
                rm.bind("<Button-1>", lambda e, nn=n, k=kind: self.toggle_mark(nn, k))

    # ---------- clothes ----------
    def make_clothes_page(self):
        import pixbot_outfits as wardrobe
        from pixbot_paint import Painter
        self.wardrobe, self.PainterCls = wardrobe, Painter
        page = tk.Frame(self.content, bg=CARD)
        top = tk.Frame(page, bg=CARD)
        top.pack(fill="x", padx=18, pady=(14, 0))
        self.clothes_prev = tk.Canvas(top, width=190, height=150, bg=CARD2, highlightthickness=0)
        self.clothes_prev.pack(side="left")
        info = tk.Frame(top, bg=CARD)
        info.pack(side="left", padx=14, fill="y")
        self.label(info, "Clothes", 12, bold=True).pack(anchor="w")
        self.label(info, "Pick a hat, something for his face and something to wear. "
                         "Some animations bring their own outfit and swap these off for a moment.",
                   9, MUTED, wrap=250).pack(anchor="w")
        self.clothes_lbl = self.label(info, "", 9, ACCENT, wrap=250)
        self.clothes_lbl.pack(anchor="w", pady=(6, 0))
        self.button(info, "Take everything off", self.clear_outfit).pack(anchor="w", pady=(8, 0))
        holder = tk.Frame(page, bg=CARD)
        holder.pack(fill="both", expand=True, pady=(6, 0))
        inner = self.scroll_area(holder)
        self.label(inner, "Ready-made looks", 10, bold=True).pack(anchor="w", padx=6, pady=(4, 2))
        sets = tk.Frame(inner, bg=CARD)
        sets.pack(anchor="w", padx=6)
        for i, (name, (h, f, b)) in enumerate(wardrobe.SETS.items()):
            bt_ = self.button(sets, name, lambda hh=h, ff=f, bb=b: self.set_outfit(hh, ff, bb))
            bt_.grid(row=i // 3, column=i % 3, padx=3, pady=3, sticky="w")
        self.outfit_btns = {}
        for slot, title in wardrobe.SLOTS:
            self.label(inner, title, 10, bold=True).pack(anchor="w", padx=6, pady=(12, 2))
            grid = tk.Frame(inner, bg=CARD)
            grid.pack(anchor="w", padx=6)
            items = [(None, "None")] + [(k, v[1]) for k, v in wardrobe.OUTFITS.items() if v[0] == slot]
            for i, (key, label) in enumerate(items):
                b = tk.Label(grid, text=label, bg=CARD2, fg=FG, padx=10, pady=4, cursor="hand2",
                             font=("Segoe UI", 9))
                b.grid(row=i // 2, column=i % 2, padx=3, pady=3, sticky="w")
                b.bind("<Button-1>", lambda e, s_=slot, k=key: self.pick_piece(s_, k))
                self.outfit_btns[(slot, key)] = b
        self.update_clothes()
        return page

    def outfit(self):
        return dict(self.s.get("outfit") or {})

    def pick_piece(self, slot, key):
        o = self.outfit()
        o[slot] = key
        self.s["outfit"] = o
        self.update_clothes()
        self.save_soon()

    def set_outfit(self, h, f, b):
        self.s["outfit"] = {"hat": h, "face": f, "body": b}
        self.update_clothes()
        self.save_soon()

    def clear_outfit(self):
        self.set_outfit(None, None, None)

    def update_clothes(self):
        o = self.outfit()
        for (slot, key), b in self.outfit_btns.items():
            on = o.get(slot) == key
            b.config(bg=ACCENT if on else CARD2, fg="#1A1A1A" if on else FG)
        names = [self.wardrobe.OUTFITS[o[s]][1] for s in ("hat", "face", "body")
                 if o.get(s) in self.wardrobe.OUTFITS]
        self.clothes_lbl.config(text="Wearing: " + (", ".join(names) if names else "nothing"))
        c = self.clothes_prev
        c.delete("all")
        u = 7
        p = self.PainterCls(c, u, (190 - 12 * u) / 2, 150 - 9.0 * u)
        col = self.body_col()
        g = {"bl": 2, "bw": 8, "bt": 0, "bh": 6, "ey": 1, "d": 1}
        self.wardrobe.draw(p, o, g, "back")
        p.R(3, 6, 1.6, 1.4, cat.shade(col, 0.75))
        p.R(7.4, 6, 1.6, 1.4, cat.shade(col, 0.75))
        p.R(2.7, 7.4, 2.2, 0.6, "#2B3440")
        p.R(7.1, 7.4, 2.2, 0.6, "#2B3440")
        p.R(0.2, 2.2, 1.6, 1.6, col)
        p.R(10.2, 2.2, 1.6, 1.6, col)
        p.R(1.8, 2.8, 0.4, 0.4, "#4A5562")
        p.R(9.8, 2.8, 0.4, 0.4, "#4A5562")
        p.R(5.85, -1.2, 0.3, 1.2, "#4A5562")
        p.R(5.55, -1.9, 0.9, 0.9, "#FF5A5A")
        p.R(2, 0, 8, 6, col)
        p.R(2, 0, 8, 0.35, cat.shade(col, 0.75))
        p.R(2.3, 4.9, 0.4, 0.4, "#2B3440")
        p.R(9.3, 4.9, 0.4, 0.4, "#2B3440")
        p.R(2.9, 0.6, 6.2, 2.6, "#1B2430")
        p.R(3.6, 1.4 + (1 - 1), 1, 1, "#7CF3FF")
        p.R(7.4, 1.4 + (1 - 1), 1, 1, "#7CF3FF")
        self.wardrobe.draw(p, o, g, "front")

    def build_general(self, left):
        pad = dict(padx=16, anchor="w")

        self.label(left, "General", 12, bold=True).pack(pady=(14, 6), **pad)
        self.startup_var = tk.BooleanVar(value=startup_enabled())
        ttk.Checkbutton(left, text="Start Pixbot when Windows starts", variable=self.startup_var,
                        command=self.on_startup).pack(pady=2, **pad)
        self.vision_var = tk.BooleanVar(value=self.s["screen_reading"])
        ttk.Checkbutton(left, text="Let him look at the screen", variable=self.vision_var,
                        command=self.on_vision).pack(pady=2, **pad)
        self.label(left, "Screenshots stay in memory for a split second and are never saved.",
                   8, MUTED, wrap=320).pack(**pad)

        self.label(left, "How often does he do something special?", 11, bold=True).pack(pady=(16, 2), **pad)
        self.freq_var = tk.DoubleVar(value=self.s["frequency"])
        row = tk.Frame(left, bg=CARD)
        row.pack(fill="x", padx=16)
        self.label(row, "rarely", 8, MUTED).pack(side="left")
        ttk.Scale(row, from_=1, to=10, variable=self.freq_var, command=self.on_freq,
                  length=220).pack(side="left", padx=6)
        self.label(row, "a lot", 8, MUTED).pack(side="left")
        row = tk.Frame(left, bg=CARD)
        row.pack(fill="x", padx=16)
        self.freq_lbl = self.label(row, "", 9, ACCENT)
        self.freq_lbl.pack(side="left")
        self.button(row, "Default", self.default_freq).pack(side="right")
        self.update_freq_label()

        self.label(left, "When is Pixbot around?", 11, bold=True).pack(pady=(16, 4), **pad)
        self.avail_var = tk.StringVar(value=self.s["availability"])
        for key, title, desc in cat.AVAILABILITY:
            ttk.Radiobutton(left, text=title, value=key, variable=self.avail_var,
                            command=self.on_avail).pack(pady=(4, 0), **pad)
            self.label(left, desc, 8, MUTED, wrap=270).pack(padx=40, anchor="w")
        self.idle_row = tk.Frame(left, bg=CARD)
        self.idle_var = tk.DoubleVar(value=self.s["idle_seconds"])
        self.label(self.idle_row, "idle for", 9, MUTED).pack(side="left")
        ttk.Scale(self.idle_row, from_=10, to=600, variable=self.idle_var, command=self.on_idle,
                  length=170).pack(side="left", padx=6)
        self.idle_lbl = self.label(self.idle_row, "", 9, ACCENT)
        self.idle_lbl.pack(side="left")
        self.update_idle_row()

        self.label(left, "Size", 11, bold=True).pack(pady=(16, 2), **pad)
        row = tk.Frame(left, bg=CARD)
        row.pack(fill="x", padx=16)
        self.size_var = tk.DoubleVar(value=self.s["size"])
        self.label(row, "small", 8, MUTED).pack(side="left")
        ttk.Scale(row, from_=2, to=8, variable=self.size_var, command=self.on_size,
                  length=220).pack(side="left", padx=6)
        self.label(row, "big", 8, MUTED).pack(side="left")
        row = tk.Frame(left, bg=CARD)
        row.pack(fill="x", padx=16, pady=(4, 0))
        self.size_preview = tk.Canvas(row, width=8 * 13, height=8 * 11, bg=CARD2,
                                      highlightthickness=0)
        self.size_preview.pack(side="left")
        info = tk.Frame(row, bg=CARD)
        info.pack(side="left", padx=10, fill="y")
        self.size_lbl = self.label(info, "", 9, ACCENT)
        self.size_lbl.pack(anchor="w")
        self.size_note = self.label(info, "", 8, MUTED, wrap=150)
        self.size_note.pack(anchor="w")
        self.button(info, "Default", self.default_size).pack(anchor="w", pady=(4, 0))
        self.update_size_info()

        self.label(left, "Text above his head", 11, bold=True).pack(pady=(16, 2), **pad)
        row = tk.Frame(left, bg=CARD)
        row.pack(fill="x", padx=16)
        self.text_var = tk.DoubleVar(value=self.s.get("text_size", cat.DEFAULTS["text_size"]))
        self.label(row, "smaller", 8, MUTED).pack(side="left")
        ttk.Scale(row, from_=0.8, to=3.0, variable=self.text_var, command=self.on_text_size,
                  length=200).pack(side="left", padx=6)
        self.label(row, "bigger", 8, MUTED).pack(side="left")
        row = tk.Frame(left, bg=CARD)
        row.pack(fill="x", padx=16, pady=(4, 14))
        self.text_prev = tk.Label(row, text="it's late!", bg=CARD2, fg="#F2C94C", padx=10, pady=4,
                                  font=("Consolas", 10, "bold"))
        self.text_prev.pack(side="left")
        self.text_lbl = self.label(row, "", 9, ACCENT)
        self.text_lbl.pack(side="left", padx=10)
        self.button(row, "Default", self.default_text_size).pack(side="right")
        self.on_text_size(save=False)

    def on_text_size(self, _=None, save=True):
        v = round(self.text_var.get(), 1)
        self.s["text_size"] = v
        self.text_prev.config(font=("Consolas", max(6, round(8 * v)), "bold"))
        self.text_lbl.config(text=f"{v:.1f}×" + ("  (default)" if abs(v - cat.DEFAULTS["text_size"]) < 0.05 else ""))
        if save:
            self.save_soon()

    def default_text_size(self):
        self.text_var.set(cat.DEFAULTS["text_size"])
        self.on_text_size()


    def make_behaviour_page(self):
        outer = tk.Frame(self.content, bg=CARD)
        page = self.scroll_area(outer, pad=False)
        self.label(page, "How Pixbot behaves", 12, bold=True).pack(anchor="w", padx=18, pady=(14, 2))
        self.label(page, "These change his personality, not which animations he knows. "
                         "Changes apply within a second.", 9, MUTED, wrap=560).pack(anchor="w", padx=18)
        self.dial_vars, self.dial_lbls = {}, {}
        for key, title, lo, hi in cat.BEHAVIOUR:
            box = tk.Frame(page, bg=CARD)
            box.pack(fill="x", padx=18, pady=(16, 0))
            self.label(box, title, 11, bold=True).pack(anchor="w")
            row = tk.Frame(box, bg=CARD)
            row.pack(fill="x", pady=(4, 0))
            self.label(row, lo, 9, MUTED).pack(side="left")
            v = tk.DoubleVar(value=self.s.get(key, cat.DEFAULTS[key]))
            self.dial_vars[key] = v
            ttk.Scale(row, from_=0, to=10, variable=v, length=230,
                      command=lambda _=None, k=key: self.on_dial(k)).pack(side="left", padx=8)
            self.label(row, hi, 9, MUTED).pack(side="left")
            self.button(row, "Default", lambda k=key: self.default_dial(k)).pack(side="right")
            lbl = self.label(box, "", 9, ACCENT)
            lbl.pack(anchor="w", pady=(2, 0))
            self.dial_lbls[key] = lbl
            self.update_dial_label(key)
        self.button(page, "Reset all behaviour to defaults", self.reset_dials).pack(
            anchor="w", padx=18, pady=(22, 0))
        return outer

    # ---------- Look page: Pixbot's colour ----------
    def make_look_page(self):
        outer = tk.Frame(self.content, bg=CARD)
        page = self.scroll_area(outer, pad=False)
        self.label(page, "Pixbot's colour", 12, bold=True).pack(anchor="w", padx=18, pady=(14, 2))
        self.label(page, "Pick a colour - he changes straight away.", 9, MUTED).pack(anchor="w", padx=18)
        self.look_preview = tk.Canvas(page, width=200, height=130, bg=CARD2, highlightthickness=0)
        self.look_preview.pack(anchor="w", padx=18, pady=(12, 4))
        self.look_lbl = self.label(page, "", 9, ACCENT)
        self.look_lbl.pack(anchor="w", padx=18)
        grid = tk.Frame(page, bg=CARD)
        grid.pack(anchor="w", padx=18, pady=(12, 0))
        self.swatches = {}
        for i, (name, col) in enumerate(cat.COLOR_PRESETS):
            cell = tk.Frame(grid, bg=CARD)
            cell.grid(row=i // 3, column=i % 3, padx=(0, 18), pady=6, sticky="w")
            sw = tk.Canvas(cell, width=30, height=30, bg=CARD, highlightthickness=2,
                           highlightbackground=CARD, cursor="hand2")
            sw.create_rectangle(3, 3, 28, 28, fill=col, outline="")
            sw.pack(side="left")
            sw.bind("<Button-1>", lambda e, c=col: self.set_color(c))
            lb = self.label(cell, name, 9, FG)
            lb.pack(side="left", padx=6)
            lb.bind("<Button-1>", lambda e, c=col: self.set_color(c))
            self.swatches[col.lower()] = sw
        row = tk.Frame(page, bg=CARD)
        row.pack(anchor="w", padx=18, pady=(16, 0))
        self.button(row, "Custom colour...", self.pick_custom).pack(side="left")
        self.button(row, "Default", lambda: self.set_color(cat.DEFAULTS["color"])).pack(side="left", padx=8)
        self.update_look()
        return outer

    def set_color(self, col):
        self.s["color"] = col
        self.update_look()
        self.save_soon()

    def pick_custom(self):
        from tkinter import colorchooser
        res = colorchooser.askcolor(color=self.s.get("color", cat.DEFAULTS["color"]),
                                    title="Pixbot's colour", parent=self.root)
        if res and res[1]:
            self.set_color(res[1])

    def body_col(self):
        return self.s.get("color") or cat.DEFAULTS["color"]

    def update_look(self):
        col = self.body_col()
        for c, sw in self.swatches.items():
            sw.config(highlightbackground=FG if c == col.lower() else CARD)
        name = next((n for n, c in cat.COLOR_PRESETS if c.lower() == col.lower()), col.upper())
        self.look_lbl.config(text=name + ("  (default)" if col.lower() == cat.DEFAULTS["color"].lower() else ""))
        c = self.look_preview
        c.delete("all")
        u = 12
        ox, oy = (200 - 12 * u) / 2, (130 - 8 * u) / 2 + u

        def px(x, y, w, h, fill):
            c.create_rectangle(ox + x * u, oy + y * u, ox + (x + w) * u, oy + (y + h) * u, fill=fill, outline="")
        px(3, 6, 1.6, 1.4, cat.shade(col, 0.75))
        px(7.4, 6, 1.6, 1.4, cat.shade(col, 0.75))
        px(2.7, 7.4, 2.2, 0.6, "#2B3440")
        px(7.1, 7.4, 2.2, 0.6, "#2B3440")
        px(0.2, 2.2, 1.6, 1.6, col)
        px(10.2, 2.2, 1.6, 1.6, col)
        px(1.8, 2.8, 0.4, 0.4, "#4A5562")
        px(9.8, 2.8, 0.4, 0.4, "#4A5562")
        px(5.85, -1.2, 0.3, 1.2, "#4A5562")
        px(5.55, -1.9, 0.9, 0.9, "#FF5A5A")
        px(2, 0, 8, 6, col)
        px(2, 0, 8, 0.35, cat.shade(col, 0.75))
        px(2.3, 4.9, 0.4, 0.4, "#2B3440")
        px(9.3, 4.9, 0.4, 0.4, "#2B3440")
        px(2.9, 0.6, 6.2, 2.6, "#1B2430")
        px(3.6, 1.4 + (1 - 1), 1, 1, "#7CF3FF")
        px(7.4, 1.4 + (1 - 1), 1, 1, "#7CF3FF")
        if hasattr(self, "size_preview"):
            self.update_size_info()

    DIAL_WORDS = {
        "home": ["sticks to the taskbar", "mostly on the taskbar", "a bit of both",
                 "mostly up on things", "lives up top"],
        "energy": ["very calm - mostly sits and watches", "calm", "a normal amount",
                   "lively", "hyper - always on the move"],
        "cursor": ["ignores your cursor", "plays with it now and then", "likes it",
                   "loves playing with it", "obsessed with your cursor"],
        "screenhop": ["never changes screens", "rarely", "now and then", "often", "very often"],
    }

    def update_dial_label(self, key):
        v = self.dial_vars[key].get()
        words = self.DIAL_WORDS[key]
        if key == "screenhop" and v < 0.5:
            txt = words[0]
        else:
            txt = words[min(4, int(v / 10 * 5 - 1e-9) if v < 10 else 4)]
        if abs(v - cat.DEFAULTS[key]) < 0.25:
            txt += "  (default)"
        self.dial_lbls[key].config(text=txt)

    def on_dial(self, key):
        self.s[key] = round(self.dial_vars[key].get(), 1)
        self.update_dial_label(key)
        self.save_soon()

    def default_dial(self, key):
        self.dial_vars[key].set(cat.DEFAULTS[key])
        self.on_dial(key)

    def reset_dials(self):
        for key, *_ in cat.BEHAVIOUR:
            self.default_dial(key)

    def show_page(self, group):
        for g, f in self.pages.items():
            f.pack_forget()
            self.tabs[g].config(bg=CARD2, fg=MUTED, font=("Segoe UI", 10))
        self.pages[group].pack(fill="both", expand=True)
        self.tabs[group].config(bg=CARD, fg=FG, font=("Segoe UI", 10, "bold"))

    def make_tab(self, group, names):
        outer = tk.Frame(self.content, bg=CARD)
        bar = tk.Frame(outer, bg=CARD)
        bar.pack(fill="x", padx=10, pady=(8, 2))
        self.button(bar, "All on", lambda n=names: self.set_group(n, True)).pack(side="left", padx=(0, 4))
        self.button(bar, "All off", lambda n=names: self.set_group(n, False)).pack(side="left")
        if group == "Getting around":                       # how much he gets around on these
            tbox = tk.Frame(outer, bg=CARD)
            tbox.pack(fill="x", padx=10, pady=(8, 0))
            self.label(tbox, "How much should he use transport?", 10, bold=True).pack(anchor="w")
            row, self.tr_var = self.slider_row(tbox, "transport", "never", "all the time", 0, 10,
                                               self.on_transport)
            row.pack(anchor="w", pady=(4, 0))
            self.tr_lbl = self.label(tbox, "", 9, ACCENT)
            self.tr_lbl.pack(anchor="w")
            self.on_transport(self.tr_var, save=False)
            self.label(tbox, "How long does each ride last?", 10, bold=True).pack(anchor="w", pady=(10, 0))
            row, self.rl_var = self.slider_row(tbox, "ride_length", "short hops", "long trips", 0, 10,
                                               self.on_ride_length)
            row.pack(anchor="w", pady=(4, 0))
            self.rl_lbl = self.label(tbox, "", 9, ACCENT)
            self.rl_lbl.pack(anchor="w")
            self.on_ride_length(self.rl_var, save=False)
        inner = self.scroll_area(outer)
        cols = 2
        for i, n in enumerate(names):
            cell = tk.Frame(inner, bg=CARD)
            cell.grid(row=i // cols, column=i % cols, sticky="w", padx=(0, 24), pady=3)
            v = tk.BooleanVar(value=self.s["enabled"].get(n, True))
            self.vars[n] = v
            play = tk.Label(cell, text="▶", bg=CARD2, fg=ACCENT, width=2, cursor="hand2",
                            font=("Segoe UI Symbol", 9))
            play.pack(side="left", padx=(0, 6))
            play.bind("<Button-1>", lambda e, nn=n: self.preview(nn))
            ttk.Checkbutton(cell, text=cat.pretty(n), variable=v,
                            command=lambda nn=n: self.on_toggle(nn)).pack(side="left")
            fav = tk.Label(cell, text="♥", bg=CARD, fg="#666666", cursor="hand2",
                           font=("Segoe UI Symbol", 10))
            fav.pack(side="left", padx=(6, 0))
            fav.bind("<Button-1>", lambda e, nn=n: self.toggle_mark(nn, "fav"))
            dis = tk.Label(cell, text="✕", bg=CARD, fg="#666666", cursor="hand2",
                           font=("Segoe UI Symbol", 9))
            dis.pack(side="left", padx=(4, 0))
            dis.bind("<Button-1>", lambda e, nn=n: self.toggle_mark(nn, "dis"))
            self.fav_btns[n], self.dis_btns[n] = fav, dis
        return outer

    def on_ride_length(self, v, save=True):
        n = round(v.get(), 1)
        self.s["ride_length"] = n
        secs = 5 + 55 * (n / 10) ** 1.3
        txt = f"skateboard / pogo rides last about {int(secs)} s, flights make {2 + int(n / 10 * 12)} stops"
        self.rl_lbl.config(text=txt + ("  (default)" if abs(n - cat.DEFAULTS["ride_length"]) < 0.25 else ""))
        if save:
            self.save_soon()

    def on_transport(self, v, save=True):
        n = round(v.get(), 1)
        self.s["transport"] = n
        words = ["never", "once in a while", "now and then", "a lot", "all the time"]
        txt = words[min(4, int(n / 10 * 5 - 1e-9) if n < 10 else 4)] if n > 0.4 else "never"
        self.tr_lbl.config(text=txt + ("  (default)" if abs(n - cat.DEFAULTS["transport"]) < 0.25 else ""))
        if save:
            self.save_soon()

    # ---------- logo: little pixel Pixbot ----------
    def draw_logo(self, blink=False):
        c, u = self.logo, 4
        c.delete("all")
        ox, oy = 8, 10
        eh = 0.3 if blink else 1

        def px(x, y, w, h, col=None):
            col = col or self.body_col()
            c.create_rectangle(ox + x * u, oy + y * u, ox + (x + w) * u, oy + (y + h) * u, fill=col, outline="")
        px(3, 6, 1.6, 1.4, cat.shade(self.body_col(), 0.75))
        px(7.4, 6, 1.6, 1.4, cat.shade(self.body_col(), 0.75))
        px(2.7, 7.4, 2.2, 0.6, "#2B3440")
        px(7.1, 7.4, 2.2, 0.6, "#2B3440")
        px(0.2, 2.2, 1.6, 1.6, self.body_col())
        px(10.2, 2.2, 1.6, 1.6, self.body_col())
        px(1.8, 2.8, 0.4, 0.4, "#4A5562")
        px(9.8, 2.8, 0.4, 0.4, "#4A5562")
        px(5.85, -1.2, 0.3, 1.2, "#4A5562")
        px(5.55, -1.9, 0.9, 0.9, "#FF5A5A")
        px(2, 0, 8, 6, self.body_col())
        px(2, 0, 8, 0.35, cat.shade(self.body_col(), 0.75))
        px(2.3, 4.9, 0.4, 0.4, "#2B3440")
        px(9.3, 4.9, 0.4, 0.4, "#2B3440")
        px(2.9, 0.6, 6.2, 2.6, "#1B2430")
        px(3.6, 1.4 + (1 - eh), 1, eh, "#7CF3FF")
        px(7.4, 1.4 + (1 - eh), 1, eh, "#7CF3FF")
        self.root.after(150 if blink else 3200, lambda: self.draw_logo(not blink))

    # ---------- saving ----------
    def save_soon(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(250, self.save_now)

    def save_now(self):
        self.save_job = None
        cat.save(self.s)

    def on_toggle(self, n):
        self.s["enabled"][n] = self.vars[n].get()
        self.update_count()
        self.save_soon()

    def set_group(self, names, on):
        for n in names:
            self.vars[n].set(on)
            self.s["enabled"][n] = on
        self.update_count()
        self.save_soon()

    def set_all(self, on):
        self.set_group(cat.all_names(), on)

    def update_count(self):
        names = cat.all_names()
        on = sum(1 for n in names if self.vars[n].get())
        self.count_lbl.config(text=f"{on} of {len(names)} on")

    def on_freq(self, _=None):
        self.s["frequency"] = round(self.freq_var.get(), 1)
        self.update_freq_label()
        self.save_soon()

    def update_freq_label(self):
        lo, hi = cat.special_gap(self.s["frequency"])
        mid = (lo + hi) / 2
        txt = f"about every {int(mid)} seconds" if mid < 90 else f"about every {mid / 60:.0f} minutes"
        if abs(self.s["frequency"] - cat.DEFAULTS["frequency"]) < 0.15:
            txt += "  (default)"
        self.freq_lbl.config(text=txt)

    def on_avail(self):
        self.s["availability"] = self.avail_var.get()
        self.update_idle_row()
        self.save_soon()

    def update_idle_row(self):
        if self.avail_var.get() == "idle":
            self.idle_row.pack(fill="x", padx=40, pady=4)
        else:
            self.idle_row.pack_forget()
        secs = int(self.idle_var.get())
        self.idle_lbl.config(text=f"{secs} s" if secs < 120 else f"{secs // 60} min")

    def on_idle(self, _=None):
        self.s["idle_seconds"] = int(self.idle_var.get())
        self.update_idle_row()
        self.save_soon()

    def on_size(self, _=None):
        v = int(round(self.size_var.get()))
        if v != self.s["size"]:
            self.s["size"] = v
            self.save_soon()
            self.size_changed = True
        self.update_size_info()

    def update_size_info(self):
        v = int(self.s["size"])
        w, h = 12 * v, 8 * v                       # Pixbot is 12 x 8 blocks (arms + legs included)
        tag = "  (default)" if v == cat.DEFAULTS["size"] else ""
        self.size_lbl.config(text=f"{w} × {h} px{tag}")
        note = "shown at real size on the left"
        if getattr(self, "size_changed", False):
            note += " - press Restart to apply"
        self.size_note.config(text=note)
        c = self.size_preview
        c.delete("all")
        ox = (int(c["width"]) - w) / 2
        oy = (int(c["height"]) - h) / 2 + v

        def px(x, y, ww, hh, col=None):
            col = col or self.body_col()
            c.create_rectangle(ox + x * v, oy + y * v, ox + (x + ww) * v, oy + (y + hh) * v,
                               fill=col, outline="")
        px(3, 6, 1.6, 1.4, cat.shade(self.body_col(), 0.75))
        px(7.4, 6, 1.6, 1.4, cat.shade(self.body_col(), 0.75))
        px(2.7, 7.4, 2.2, 0.6, "#2B3440")
        px(7.1, 7.4, 2.2, 0.6, "#2B3440")
        px(0.2, 2.2, 1.6, 1.6, self.body_col())
        px(10.2, 2.2, 1.6, 1.6, self.body_col())
        px(1.8, 2.8, 0.4, 0.4, "#4A5562")
        px(9.8, 2.8, 0.4, 0.4, "#4A5562")
        px(5.85, -1.2, 0.3, 1.2, "#4A5562")
        px(5.55, -1.9, 0.9, 0.9, "#FF5A5A")
        px(2, 0, 8, 6, self.body_col())
        px(2, 0, 8, 0.35, cat.shade(self.body_col(), 0.75))
        px(2.3, 4.9, 0.4, 0.4, "#2B3440")
        px(9.3, 4.9, 0.4, 0.4, "#2B3440")
        px(2.9, 0.6, 6.2, 2.6, "#1B2430")
        px(3.6, 1.4 + (1 - 1), 1, 1, "#7CF3FF")
        px(7.4, 1.4 + (1 - 1), 1, 1, "#7CF3FF")

    def default_size(self):
        self.size_var.set(cat.DEFAULTS["size"])
        self.on_size()

    def default_freq(self):
        self.freq_var.set(cat.DEFAULTS["frequency"])
        self.on_freq()

    def on_vision(self):
        self.s["screen_reading"] = self.vision_var.get()
        self.save_soon()

    def on_startup(self):
        try:
            set_startup(self.startup_var.get())
        except OSError:
            self.startup_var.set(startup_enabled())

    # ---------- pet control ----------
    def preview(self, name):
        if not pet_pid():
            start_pet()
            self.root.after(2500, lambda: send({"play": name}))
        else:
            send({"play": name})
        self.refresh_status()

    def toggle_pet(self):
        if pet_pid():
            stop_pet()
        else:
            start_pet()
        self.root.after(600, self.refresh_status)

    def restart_pet(self):
        self.save_now()
        stop_pet()
        start_pet()
        self.root.after(800, self.refresh_status)

    def refresh_status(self):
        running = bool(pet_pid())
        self.status.config(text="● running" if running else "○ stopped",
                           fg="#7BD88F" if running else MUTED)
        self.toggle_btn.config(text="Stop Pixbot" if running else "Start Pixbot")

    def status_loop(self):
        self.refresh_status()
        self.root.after(1500, self.status_loop)


if __name__ == "__main__":
    App().root.mainloop()
