"""The endings (SPEC §13, §10.7).

- Caught (NO route): the chase world freezes, glitches and dissolves into black.
- face / black: a melancholic kaomoji fades in alone, one tear runs down, the face fades, black stays.
  The invitation's NO arrives here too, straight from the night (no glitch).
- joy / exit (the invitation's YES): on black a smiling kaomoji fades in, changes to love eyes, fades, and
  the app closes.

Coordinates are the chase's 320 x 320 logical canvas; everything is drawn crisp at window resolution through
the viewport. The effects are `letter.art.ending`; this scene only times and draws them. No input does
anything here (E4), apart from closing the window.
"""
import pygame

from letter import config
from letter.art import ending
from letter.engine import glyphs
from letter.engine.timeline import clamp, hash32, span
from letter.scenes.base import Scene
from letter.scenes.chase import GLYPH_PX, PAPER, RGB

S = config.CHASE_SIZE[0]
# beats, seconds at SPEED 1: glitch 4.9 s, face 11.8 s, joy 7.5 s (config.T)
GLITCH = {"freeze": (0.0, 0.4), "glitch": (0.4, 2.4), "dissolve": (2.4, 4.9)}
FACE = {"in": (0.8, 2.8), "tear": 3.8, "out": (9.3, 11.8)}
JOY = {"smile_in": (0.6, 1.4), "smile_out": (2.8, 3.1), "love_in": (3.2, 3.5), "pulse": (4.6, 5.3),
       "love_out": (5.8, 7.0)}
FACE_PX, TEAR_PX = 46, 24             # logical px of the face's and the tear's glyphs (drawn at window size)
FACE_RAISE = 14                      # logical px above centre, leaving room below for the tear to run
FACE_RGB, TEAR_RGB, FLASH_RGB = (176, 172, 206), (186, 214, 255), (226, 220, 240)
JOY_RGB, HEART_RGB = (246, 228, 236), (255, 118, 158)
# the joy faces need glyphs JetBrains Mono lacks. Windows' own Cambria and Segoe UI Symbol have them between
# them (not bundled; on every Windows 10/11 PC): each character uses the first font that has it. If any is
# missing everywhere, ASCII-safe faces in the bundled font are used instead.
SMILE, LOVE, HEART = "(˶ᵔ ᵕ ᵔ˶)", "(♡‿♡)", "♡"
FALLBACK = ("(^‿^)", "(*^ω^*)")
SYSTEM_FONTS = ("cambria", "segoeuisymbol")


def _beat(e, window):
    return span(e, [w / config.SPEED for w in window])


def _blend(rgb, a, under):
    """rgb at alpha a over `under`, in 16 steps so each faded colour is one cached glyph."""
    a = round(clamp(a) * 16) / 16
    return tuple(round(u + (v - u) * a) for v, u in zip(rgb, under))


def _img(font, c):
    try:
        return pygame.image.tobytes(font.render(c, True, (255, 255, 255), (0, 0, 0)), "RGB")
    except pygame.error:
        return None


def _draws(font, ch, missing=None):
    """True if font has a real glyph for ch (not the empty box it shows for unassigned code points)."""
    missing = missing if missing is not None else {_img(font, "\u0378"), _img(font, "\u0379")}
    return _img(font, ch) not in missing


def joy_faces(px):
    """[(smile, love)] as lists of (font, char) at px: each character in the first font that draws it."""
    chain = [pygame.font.Font(path, round(px)) for path in map(pygame.font.match_font, SYSTEM_FONTS) if path]
    chain.append(glyphs.font("mono-bold", px))
    missing = [{_img(f, "\u0378"), _img(f, "\u0379")} for f in chain]   # each font's empty box, once
    faces = []
    for text in (SMILE, LOVE):
        picks = [next((f for f, m in zip(chain, missing) if ch == " " or _draws(f, ch, m)), None) for ch in text]
        if None in picks:
            return [[(chain[-1], ch) for ch in text] for text in FALLBACK]
        faces.append(list(zip(picks, text)))
    return faces


class EndingScene(Scene):
    logical = config.CHASE_SIZE
    background = (0, 0, 0)

    def __init__(self, app):
        super().__init__(app)
        self.frozen = [tuple(i) for i in getattr(app, "caught", None) or []]   # the chase's last frame
        # the dissolve starts from the glitch's last frame, so the world never snaps back clean
        self.broken = ending.glitch(self.frozen, ending.GLITCH_LEN - 1e-3, calm=config.CALM)[0]
        self.no_px = getattr(app, "caught_no_px", GLYPH_PX)   # the NO button's glyph size in that frame
        pygame.mouse.set_visible(True)   # the chase hid the system cursor
        self.resize(app.size)

    def resize(self, size):
        super().resize(size)
        s = self.view.scale
        self.atlas = glyphs.Atlas("mono-bold", GLYPH_PX * s)
        self.no_atlas = glyphs.Atlas("mono-bold", self.no_px * s)
        self._joy = None   # the joy faces load Windows fonts: only when that ending plays (on black)

    def on_event(self, ev, phase, e):
        pass   # E4: nothing responds any more

    def _items(self, screen, items, under):
        v, world, no = self.view, [], []
        for ch, role, x, y, a in items:
            (no if role == "n" else world).append((ch, _blend(RGB.get(role, RGB["g"]), a, under), v.to_window(x, y)))
        self.atlas.draw(screen, world)
        self.no_atlas.draw(screen, no)

    def draw(self, screen, t, phase, e):
        paper = (0, 0, 0)
        if phase == "glitch":
            p = _beat(e, GLITCH["dissolve"])
            paper = tuple(round(v * (1 - p)) for v in PAPER)   # the paper darkens to black as the world goes
        screen.fill(paper)
        if phase == "glitch":
            self._draw_glitch(screen, e, paper)
        elif phase == "face":
            self._draw_face(screen, e)
        elif phase == "joy":
            self._draw_joy(screen, e)

    def _draw_glitch(self, screen, e, paper):
        p = _beat(e, GLITCH["dissolve"])
        if p > 0:
            self._items(screen, ending.dissolve(self.broken, p), paper)
        elif _beat(e, GLITCH["glitch"]) > 0:
            g = (e - GLITCH["glitch"][0] / config.SPEED) * config.SPEED
            items, flash = ending.glitch(self.frozen, g, calm=config.CALM)
            if flash > 0:   # a character flash: half the cells fill with pale noise glyphs
                rgb, tick, v = _blend(FLASH_RGB, 0.4 * flash, paper), int(g * 60), self.view
                self.atlas.draw(screen, ((ending.NOISE[h % len(ending.NOISE)], rgb, v.to_window(col * 8, row * 12))
                                         for row in range(27) for col in range(40)
                                         for h in (hash32(col, row, tick),) if h & 0x100))
            self._items(screen, [(*i, 1.0) for i in items], paper)
        else:
            self._items(screen, [(*i, 1.0) for i in self.frozen], paper)

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

    def _draw_joy(self, screen, e):
        """A smile, then love eyes (never both at once), a faint pulse, then it fades."""
        if self._joy is None:
            self._joy = joy_faces(FACE_PX * self.view.scale)
        smile, love = self._joy
        a_smile = _beat(e, JOY["smile_in"]) * (1 - _beat(e, JOY["smile_out"]))
        a_love = _beat(e, JOY["love_in"]) * (1 - _beat(e, JOY["love_out"]))
        chars, a = (smile, a_smile) if a_smile > 0 else (love, a_love)
        if a <= 0:
            return
        pulse = _beat(e, JOY["pulse"])
        scale = 1 + 0.045 * (4 * pulse * (1 - pulse)) if chars is love else 1.0   # one soft heartbeat
        parts = [(f.render(ch, True, _blend(HEART_RGB if ch == HEART else JOY_RGB, a, (0, 0, 0))), f.get_ascent())
                 for f, ch in chars]
        top = max(asc for _, asc in parts)   # fonts differ: line every glyph up on one baseline
        w = sum(p.get_width() for p, _ in parts)
        face = pygame.Surface((w, max(top - asc + p.get_height() for p, asc in parts)), pygame.SRCALPHA)
        x = 0
        for p, asc in parts:   # character by character, so the hearts can be their own colour
            face.blit(p, (x, top - asc))
            x += p.get_width()
        if scale != 1.0:
            face = pygame.transform.smoothscale(face, (round(face.get_width() * scale), round(face.get_height() * scale)))
        screen.blit(face, face.get_rect(center=self.view.to_window(S / 2, S / 2)))
