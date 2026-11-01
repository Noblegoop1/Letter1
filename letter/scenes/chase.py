"""The chase (SPEC §12, §13 step 1): the blank sheet became a little ASCII world on dark paper.

The game itself is `letter.art.chase` (fixed-step physics, the scripted course); this scene draws its glyphs
onto a 320 x 320 canvas at logical size and scales it up nearest-neighbour, so every cell stays crisp.
Space jumps and nothing else does anything. When the course ends the NO button is cornered at the wall,
trembling harder the closer the pointer comes, and only then can it be caught (click or Enter).
"""
import math

import pygame

from letter import config
from letter.art import chase, ending, sheet
from letter.engine import glyphs
from letter.engine.timeline import approach, clamp
from letter.scenes.base import Scene

S = config.CHASE_SIZE[0]
PAPER = sheet.WINDOW                 # the sheet's dark window the camera dived into
GLYPH_PX = 13                        # logical px: about one chase cell (8 x 12)
# per role: ground, horizon, obstacle, the red mouse pointer and its speed lines, NO, wall, stumble scatter,
# hint text (the core's sprite offsets are tuned to this font, drawn from each glyph's top-left)
RGB = {"g": (122, 108, 96), "h": (66, 58, 70), "o": (196, 168, 132), "m": (220, 60, 70), "r": (110, 40, 50),
       "n": config.NO, "w": (150, 132, 116), "x": (214, 120, 110), "t": (236, 224, 199)}
NEAR_TAU = 0.12                      # s: the pointer's distance is smoothed, so the tremble never jumps
FADE_IN = 0.6                        # s: the world draws itself in on the dark paper
GRAB = 6                             # logical px of slack around the NO button for the catching click


class ChaseScene(Scene):
    logical = config.CHASE_SIZE
    background = PAPER

    def __init__(self, app):
        super().__init__(app)
        self.game = chase.Chase()
        self.canvas = pygame.Surface((S, S))
        self.atlas = glyphs.Atlas("mono-bold", GLYPH_PX)   # logical size: the whole canvas is scaled up
        self.pointer = None
        self.near = 1e3                  # smoothed pointer distance to the NO button, logical px
        self.shake = (0.0, 0.0)
        self.resize(app.size)

    def resize(self, size):
        super().resize(size)
        self.bars_dirty = True

    # --- input -------------------------------------------------------------------------------------
    def _no_centre(self):
        x, y, w, h = self.game.no_rect()
        return x + w / 2, y + h / 2

    def on_event(self, ev, phase, e):
        if ev.type == pygame.KEYDOWN and ev.key == pygame.K_SPACE and phase == "chase":
            self.game.press()
        elif ev.type == pygame.MOUSEMOTION:
            self.pointer = self.view.to_logical(*ev.pos)
        elif ev.type == pygame.WINDOWLEAVE:
            self.pointer = None
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and phase == "cornered":
            x, y, w, h = self.game.no_rect()
            px, py = self.view.to_logical(*ev.pos)
            if x - GRAB <= px <= x + w + GRAB and y - GRAB <= py <= y + h + GRAB:
                self._catch()
        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and phase == "cornered":
            self._catch()

    def _catch(self):
        self.app.caught = self.game.picture(self.shake)   # the ending glitches this very frame
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
            far = 1e3 if self.pointer is None else math.dist(self.pointer, self._no_centre())
            if dt > 0:
                self.near = approach(self.near, far, dt, NEAR_TAU)
            dx, dy = ending.proximity_shake(self.near, t)
            self.shake = (dx * config.MOTION, dy * config.MOTION)

    def draw(self, screen, t, phase, e):
        c = self.canvas
        c.fill(PAPER)
        rgb = RGB
        if phase == "chase" and e < FADE_IN / config.SPEED:   # fade in from the paper: blend each colour toward it
            k = round(clamp(e * config.SPEED / FADE_IN) * 8) / 8   # 8 steps: each colour is a cached glyph
            rgb = {r: tuple(round(p + (v - p) * k) for v, p in zip(col, PAPER)) for r, col in RGB.items()}
        self.atlas.draw(c, ((ch, rgb[role], (round(x), round(y))) for ch, role, x, y in self.game.picture(self.shake)))
        if self.bars_dirty:   # the window keeps its pixels between frames: paint the bars once
            screen.fill(PAPER)
            self.bars_dirty = False
        pygame.transform.scale(c, self.view.size, screen.subsurface((*self.view.offset, *self.view.size)))
