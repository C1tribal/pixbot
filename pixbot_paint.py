"""A tiny 'painter' with the same drawing calls Pixbot's animations use (R, O, Pg, L, T),
for drawing onto any tkinter canvas in grid units. Used by the app's previews and by the
little effect windows (paper plane, dragon, arrows...)."""


class Painter:
    def __init__(self, canvas, unit, ox=0.0, oy=0.0):
        self.cv, self.u, self.ox, self.oy = canvas, unit, ox, oy

    def _p(self, x, y):
        return self.ox + x * self.u, self.oy + y * self.u

    def R(self, x, y, w, h, color="#D97757"):
        x0, y0 = self._p(x, y)
        x1, y1 = self._p(x + w, y + h)
        if x1 > x0 and y1 > y0:
            self.cv.create_rectangle(round(x0), round(y0), round(x1), round(y1), fill=color, outline="")

    def O(self, x, y, w, h, fill="", outline="", width=1):
        x0, y0 = self._p(x, y)
        x1, y1 = self._p(x + w, y + h)
        self.cv.create_oval(x0, y0, x1, y1, fill=fill, outline=outline, width=width)

    def Pg(self, pts, fill, outline=""):
        flat = [v for p in pts for v in self._p(*p)]
        self.cv.create_polygon(flat, fill=fill, outline=outline)

    def L(self, pts, color, width=2):
        flat = [v for p in pts for v in self._p(*p)]
        self.cv.create_line(flat, fill=color, width=width)

    def T(self, x, y, s, size, color="#D97757", font="Consolas"):
        self.cv.create_text(*self._p(x, y), text=s, fill=color, font=(font, size, "bold"))
