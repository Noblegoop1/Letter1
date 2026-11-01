"""The chase (SPEC §12, §13 step 1): the reader's mouse pointer chases the big floating NO button through a
side-scrolling runner on the sheet's dark paper, jumping over walls.

The game itself is `letter.art.chase` (fixed-step physics, the scripted course). This scene feeds it the
real mouse (the system cursor is hidden: the red pointer in the game *is* the cursor) and Space, and
draws it crisp at window resolution through the viewport (320 x 320 logical). The NO button is the
envelope's own NO button art, drawn into the rectangle the game moves. When the course ends the button is
cornered, trembling harder the closer the pointer comes, and only then can it be caught (click or Enter).
"""
import math

import pygame

from letter import config
from letter.art import buttons, chase, ending, sheet
from letter.engine import glyphs
from letter.engine.timeline import approach, clamp
from letter.scenes.base import Scene

S = config.CHASE_SIZE[0]
PAPER = sheet.WINDOW                 # the sheet's dark window the camera dived into
GLYPH_PX = 13                        # logical px of the world's glyphs (one 8 x 12 cell)
# per role: ground, horizon, obstacle, the red mouse pointer and its speed lines, NO, wall, stumble scatter,
# hint text (the core's sprite offsets are tuned to this font, drawn from each glyph's top-left)
RGB = {"g": (122, 108, 96), "h": (66, 58, 70), "o": (196, 168, 132), "m": (220, 60, 70), "r": (110, 40, 50),
       "n": config.NO, "w": (150, 132, 116), "x": (214, 120, 110), "t": (236, 224, 199)}
FADE_IN = 0.6                        # s: the world draws itself in on the dark paper
NEAR_TAU = 0.12                      # s: the pointer's distance is smoothed, so the tremble never jumps
NO_ART = buttons.frame("NO")         # (rows, roles) of the envelope's NO button at rest


def _no_glyph_px(rect):
    """Logical font px that fits the NO button's art (40 x 11 cells of 0.6 x 1.1 em) into rect."""
    rows, _ = NO_ART
    return min(rect[2] / (len(rows[0]) * 0.6), rect[3] / (len(rows) * 1.1))


def no_items(rect):
    """The NO button's art as glyph items (ch, "n", x, y) in logical px, laid out in rect."""
    rows, _ = NO_ART
    px = _no_glyph_px(rect)
    x0 = rect[0] + (rect[2] - len(rows[0]) * 0.6 * px) / 2
    y0 = rect[1] + (rect[3] - len(rows) * 1.1 * px) / 2
    return [(c, "n", x0 + i * 0.6 * px, y0 + r * 1.1 * px)
            for r, row in enumerate(rows) for i, c in enumerate(row) if c != " "]


class ChaseScene(Scene):
    logical = config.CHASE_SIZE
    background = PAPER

    def __init__(self, app):
        super().__init__(app)
        self.game = chase.Chase()
        self.pointer = None
        self.near = 1e3                  # smoothed pointer distance to the NO button, logical px
        self.shake = (0.0, 0.0)
        pygame.mouse.set_visible(False)  # one pointer on screen: the game's
        self.resize(app.size)

    def resize(self, size):
        super().resize(size)
        self.atlas = glyphs.Atlas("mono-bold", GLYPH_PX * self.view.scale)
        self._button = None              # the NO button picture, rebuilt for this window size

    # --- input -------------------------------------------------------------------------------------
    def _no_centre(self):
        x, y, w, h = self.game.no_rect()
        return x + w / 2, y + h / 2

    def on_event(self, ev, phase, e):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE and phase == "chase":
            self.game.press()
        elif ev.type == pygame.MOUSEMOTION:
            self.pointer = self.view.to_logical(*ev.pos)
            self.game.aim(*self.pointer)
        elif ev.type == pygame.WINDOWLEAVE:
            self.pointer = None
            self.game.aim(None)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and phase == "cornered":
            x, y, w, h = self.game.no_rect()
            px, py = self.view.to_logical(*ev.pos)
            sx, sy = self.shake
            if x + sx <= px <= x + sx + w and y + sy <= py <= y + sy + h:
                self._catch()
        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and phase == "cornered":
            self._catch()

    def _catch(self):
        """Freeze this frame (world, pointer and the NO button's glyphs) for the ending to glitch and dissolve."""
        x, y, w, h = self.game.no_rect()
        rect = (x + self.shake[0], y + self.shake[1], w, h)
        self.app.caught = self.game.picture() + no_items(rect)
        self.app.caught_no_px = _no_glyph_px(rect)
        self.app.emit("catch")

    def target(self, name):
        if name == "no":
            return self.view.to_window(*self._no_centre())
        raise KeyError(name)

    # --- animation ---------------------------------------------------------------------------------
    def update(self, dt, t, phase, e):
        if phase == "chase":
            self.game.update(dt)
            if self.game.cornered:
                self.app.emit("course-end")
        elif phase == "cornered":
            self.game.update(dt)   # the button still hovers, the pointer still follows the mouse
            far = 1e3 if self.pointer is None else math.dist(self.pointer, self._no_centre())
            if dt > 0:
                self.near = approach(self.near, far, dt, NEAR_TAU)
            dx, dy = ending.proximity_shake(self.near, t)
            self.shake = (dx * config.MOTION, dy * config.MOTION)

    def _button_picture(self, rect):
        """The envelope's NO button art at the size the game gives it, for this window (cached)."""
        size = (round(rect[2] * self.view.scale), round(rect[3] * self.view.scale))
        if self._button is None or self._button[0] != size:
            px = _no_glyph_px(rect) * self.view.scale
            atlas = glyphs.Atlas("mono-bold", px)
            rows, roles = NO_ART
            surf = pygame.Surface(size, pygame.SRCALPHA)
            cw, ch = 0.6 * px, 1.1 * px
            x0, y0 = (size[0] - len(rows[0]) * cw) / 2, (size[1] - len(rows) * ch) / 2
            atlas.draw(surf, ((c, config.CREAM if role == "f" else config.NO, (x0 + i * cw, y0 + r * ch))
                              for r, (row, rr) in enumerate(zip(rows, roles)) for i, (c, role) in enumerate(zip(row, rr))))
            self._button = (size, surf)
        return self._button[1]

    def draw(self, screen, t, phase, e):
        screen.fill(PAPER)
        fade = clamp(e * config.SPEED / FADE_IN) if phase == "chase" else 1.0
        k = round(fade * 8) / 8                      # 8 steps: each faded colour is one cached glyph
        rgb = {r: tuple(round(p + (v - p) * k) for v, p in zip(col, PAPER)) for r, col in RGB.items()}
        v = self.view
        items = self.game.picture()
        front = [i for i in items if i[1] in ("r", "m", "x")]   # the pointer (and its trail, its stumble) on top
        self.atlas.draw(screen, ((ch, rgb[role], v.to_window(x, y)) for ch, role, x, y in items if role not in "rmx"))
        x, y, w, h = self.game.no_rect()
        sx, sy = self.shake if phase == "cornered" else (0.0, 0.0)
        pic = self._button_picture((x, y, w, h))
        pic.set_alpha(round(255 * fade) if fade < 1 else None)
        screen.blit(pic, v.to_window(x + sx, y + sy))
        self.atlas.draw(screen, ((ch, rgb[role], v.to_window(x, y)) for ch, role, x, y in front))
