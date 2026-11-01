"""The ending (SPEC §13 steps 2-5): caught, the chase world freezes, glitches and dissolves into black;
a small, melancholic ASCII face fades in alone, one tear runs down, the face fades and black stays.

Drawn on the chase's 320 x 320 canvas, scaled up nearest-neighbour. The effects are `letter.art.ending`;
this scene only times and draws them. No input does anything here (E4), apart from closing the window.
"""
import pygame

from letter import config
from letter.art import ending
from letter.engine import glyphs
from letter.engine.timeline import clamp, hash32, span
from letter.scenes.base import Scene
from letter.scenes.chase import GLYPH_PX, PAPER, RGB

S = config.CHASE_SIZE[0]
# beats, seconds at SPEED 1: glitch phase 4.9 s, face phase 11.8 s (config.T)
GLITCH = {"freeze": (0.0, 0.4), "glitch": (0.4, 2.4), "dissolve": (2.4, 4.9)}
FACE = {"in": (0.8, 2.8), "tear": 3.8, "out": (9.3, 11.8)}
FACE_PX, TEAR_PX = 46, 24             # logical px of the face's and the tear's glyphs (drawn at window size)
FACE_RAISE = 14                      # logical px above centre, leaving room below for the tear to run
FACE_RGB, TEAR_RGB, FLASH_RGB = (176, 172, 206), (186, 214, 255), (226, 220, 240)


def _beat(e, window):
    return span(e, [w / config.SPEED for w in window])


def _blend(rgb, a, under):
    """rgb at alpha a over `under`, in 16 steps so each faded colour is one cached glyph."""
    a = round(clamp(a) * 16) / 16
    return tuple(round(u + (v - u) * a) for v, u in zip(rgb, under))


class EndingScene(Scene):
    logical = config.CHASE_SIZE
    background = (0, 0, 0)

    def __init__(self, app):
        super().__init__(app)
        self.frozen = [tuple(i) for i in getattr(app, "caught", None) or []]   # the chase's last frame
        # the dissolve starts from the glitch's last frame, so the world never snaps back clean
        self.broken = ending.glitch(self.frozen, ending.GLITCH_LEN - 1e-3, calm=config.CALM)[0]
        self.canvas = pygame.Surface((S, S))
        self.atlas = glyphs.Atlas("mono-bold", GLYPH_PX)
        self.resize(app.size)

    def resize(self, size):
        super().resize(size)
        self.bars = None   # the colour the side bars were last painted

    def on_event(self, ev, phase, e):
        pass   # E4: nothing responds any more

    def _items(self, c, items, under):
        self.atlas.draw(c, ((ch, _blend(RGB.get(role, RGB["g"]), a, under), (round(x), round(y)))
                            for ch, role, x, y, a in items))

    def draw(self, screen, t, phase, e):
        c, paper = self.canvas, (0, 0, 0)
        if phase == "glitch":
            p = _beat(e, GLITCH["dissolve"])
            paper = tuple(round(v * (1 - p)) for v in PAPER)   # the paper darkens to black as the world goes
            c.fill(paper)
            if p > 0:
                self._items(c, ending.dissolve(self.broken, p), paper)
            elif _beat(e, GLITCH["glitch"]) > 0:
                g = (e - GLITCH["glitch"][0] / config.SPEED) * config.SPEED
                items, flash = ending.glitch(self.frozen, g, calm=config.CALM)
                if flash > 0:   # a character flash: half the cells fill with pale noise glyphs
                    rgb, tick = _blend(FLASH_RGB, 0.4 * flash, paper), int(g * 60)
                    self.atlas.draw(c, ((ending.NOISE[h % len(ending.NOISE)], rgb, (col * 8, row * 12))
                                        for row in range(27) for col in range(40)
                                        for h in (hash32(col, row, tick),) if h & 0x100))
                self._items(c, [(*i, 1.0) for i in items], paper)
            else:
                self._items(c, [(*i, 1.0) for i in self.frozen], paper)
        else:
            c.fill(paper)
        if self.bars != paper:   # the window keeps its pixels: repaint the bars only when their colour changes
            screen.fill(paper)
            self.bars = paper
        pygame.transform.scale(c, self.view.size, screen.subsurface((*self.view.offset, *self.view.size)))
        if phase == "face":   # alone on black, so drawn crisp at the window's own size, not scaled up
            self._draw_face(screen, e)

    def _draw_face(self, screen, e):
        a = _beat(e, FACE["in"]) * (1 - _beat(e, FACE["out"]))
        if a <= 0:
            return
        v = self.view
        big, small = glyphs.font("mono-bold", FACE_PX * v.scale), glyphs.font("mono-bold", TEAR_PX * v.scale)
        text = ending.FACE[0]
        adv, line = big.size("M")[0], big.get_height()
        cx, cy = v.to_window(S / 2, S / 2 - FACE_RAISE)
        x0, y0 = cx - adv * len(text) / 2, cy - line / 2
        screen.blit(big.render(text, True, _blend(FACE_RGB, a, (0, 0, 0))), (round(x0), round(y0)))
        tear_e = e - FACE["tear"] / config.SPEED
        if tear_e >= 0:
            for g, col, row, ta in ending.tear(tear_e * config.SPEED):
                drop = small.render(g, True, _blend(TEAR_RGB, ta * a, (0, 0, 0)))
                screen.blit(drop, drop.get_rect(center=(round(x0 + (col + 0.5) * adv), round(y0 + row * line))))
