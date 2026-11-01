"""Logical canvas -> window: uniform scale, centred, letterboxed. One transform for drawing AND input."""


class Viewport:
    def __init__(self, logical, window):
        self.logical = logical
        self.resize(window)

    def resize(self, window):
        lw, lh = self.logical
        self.window = window
        self.scale = min(window[0] / lw, window[1] / lh)
        self.size = (round(lw * self.scale), round(lh * self.scale))
        self.offset = ((window[0] - self.size[0]) // 2, (window[1] - self.size[1]) // 2)

    def to_window(self, x, y):
        return self.offset[0] + x * self.scale, self.offset[1] + y * self.scale

    def to_logical(self, wx, wy):
        return (wx - self.offset[0]) / self.scale, (wy - self.offset[1]) / self.scale

    def rect(self, x, y, w, h):
        """Logical rect -> integer window rect (x, y, w, h)."""
        wx, wy = self.to_window(x, y)
        return round(wx), round(wy), round(w * self.scale), round(h * self.scale)

    def px(self, n):
        """Logical length -> window pixels (at least 1)."""
        return max(1, round(n * self.scale))
