"""Fonts and ASCII glyph drawing. Text is rendered at the window's real pixel size, never upscaled."""
import pygame

from letter.engine import assets

FILES = {
    "mono": "JetBrainsMono-Regular.ttf",
    "mono-bold": "JetBrainsMono-Bold.ttf",
    "mono-italic": "JetBrainsMono-Italic.ttf",
}
_fonts = {}


def font(name, px):
    key = (name, max(4, round(px)))
    if key not in _fonts:
        _fonts[key] = pygame.font.Font(assets.path("fonts", FILES[name]), key[1])
    return _fonts[key]


class Atlas:
    """One cached surface per (character, colour) at one pixel size; draws grids in a single fblits call."""

    def __init__(self, name, px):
        self.font = font(name, px)
        self.cell = self.font.size("M")
        self._cache = {}

    def glyph(self, ch, rgb):
        key = (ch, rgb)
        if key not in self._cache:
            self._cache[key] = self.font.render(ch, True, rgb)
        return self._cache[key]

    def draw(self, surface, items):
        """items: iterable of (char, rgb, (x, y)) in window pixels; spaces are skipped."""
        surface.fblits([(self.glyph(ch, rgb), pos) for ch, rgb, pos in items if ch != " "])

    def draw_rows(self, surface, rows, rgb_of, x, y):
        """Draw rows of text as a grid at (x, y); rgb_of(row, col, ch) picks each colour."""
        cw, ch_ = self.cell
        self.draw(surface, ((c, rgb_of(r, i, c), (x + i * cw, y + r * ch_))
                            for r, row in enumerate(rows) for i, c in enumerate(row)))
