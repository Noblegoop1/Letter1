"""The NO route's last beat on the letter (SPEC §11 no-4).

The heart trembles, cracks and bursts into ASCII fragments; "If you really feel that way, prove it." is
written where it was, character by character, in the dedication's ink; the envelope opens on its own and
the blank sheet rises; the NO button leaves its slot and hops onto the sheet; then the letter scene's camera
dives in and the sheet becomes the chase. A mixin of LetterScene: it draws with that scene's atlases, layout
and caches. (The first three NO beats, questions, earthquake and swap, live in letter.py.)
"""
import math

import pygame

from letter import config
from letter.art import envelope as env, heart
from letter.engine import glyphs
from letter.engine.timeline import clamp, ease, ease_out, hash32, lerp, span

# beats inside no-4, seconds at SPEED 1 (the phase lasts config.T["no-4"] = 8.1)
NO4 = {"tremble": (0.0, 0.4), "crack": (0.4, 0.8), "shatter": (0.8, 2.4), "message": (2.4, 3.9),
       "open": (4.5, 5.7), "rise": (4.8, 5.9), "hop": (5.7, 6.5), "zoom": (6.5, 8.1)}
MESSAGE = "If you really feel that way, prove it."
MESSAGE_PX = 22                    # logical px of the message's italic ink
CHAR_IN = 0.15                     # s each character takes to write itself in
SEAL_RGB = {"h": (226, 52, 70), "H": (120, 30, 44), "c": (46, 12, 20)}   # wax, seal edge, crack
LANDING = (0.6, 0.68)              # where the NO button lands, as fractions of the sheet's window: the dive
                                   # crops the window's sides, so right of centre, not near the edge
LANDED_SCALE, HOP_ARC = 0.24, 80.0   # its size once on the sheet; logical px of the hop's arc


def beat(e, name):
    """0..1 progress through one of the no-4 beats, e seconds into the phase."""
    return span(e, [w / config.SPEED for w in NO4[name]])


def ink(e):
    """How far each character of the message has written itself in (0..1), e seconds into no-4."""
    start = NO4["message"][0] / config.SPEED
    per = (NO4["message"][1] - NO4["message"][0] - CHAR_IN) / len(MESSAGE) / config.SPEED
    return [clamp((e - start - i * per) / (CHAR_IN / config.SPEED)) for i in range(len(MESSAGE))]


def hop(p, start, target, arc):
    """(x, y, tumble degrees, scale) of the NO button p of the way through its hop from start to target."""
    k = ease(p)
    return (lerp(start[0], target[0], k), lerp(start[1], target[1], k) - arc * math.sin(math.pi * p),
            14 * math.sin(2 * math.pi * p) * (1 - p), lerp(1.0, LANDED_SCALE, k))


def _scene():
    from letter.scenes import letter   # the letter scene's layout (it imports this module, so import late)
    return letter


class NoRoute:
    def _no4_envelope(self, e):
        """(comp, rise): the envelope without its seal; later it opens on its own and the sheet rises."""
        p = beat(e, "open")
        if p <= 0:
            return self._resting(1.0, seal=False), 0.0
        rise = ease_out(beat(e, "rise")) * _scene().SHEET_RISE
        comp = self._opened(env.flap_depth(180 * ease(p)), rise, seal=False)
        self._write_dedication(comp, 1.0)
        return comp, rise

    def _draw_no4(self, screen, t, e, envelope, box):
        left, top, width = envelope
        self._draw_heart(screen, e, left, top)
        self._draw_message(screen, e, left + width / 2, top)
        self._draw_buttons(screen, t, 1 - beat(e, "open"), names=["yes"])   # YES fades as the envelope opens
        self._draw_hop(screen, t, e, box)

    def _faded(self, font, ch, rgb, alpha):
        """A glyph at one of 8 alpha levels (cached), so hundreds of fading fragments are one fblits."""
        level = round(clamp(alpha) * 8)
        key = ("fade", id(font), ch, rgb, level)
        if key not in self._cache:
            g = font.render(ch, True, rgb)
            g.set_alpha(round(255 * level / 8))
            self._cache[key] = g
        return self._cache[key]

    def _draw_heart(self, screen, e, left, top):
        cw, ch = self.cell
        s, font = self.view.scale, self.env_atlas.font
        x0 = left + (env.CX - heart.SIZE[0] // 2) * cw
        y0 = top + (env.TIP - heart.SIZE[1] // 2) * ch
        burst = e - NO4["shatter"][0] / config.SPEED
        if burst >= 0:
            items = [(self._faded(font, g, SEAL_RGB[k], a), (x0 + x * s, y0 + y * s))
                     for x, y, g, a, k in heart.shatter(burst * config.SPEED, _scene().CELL) if a > 0.06]
        else:   # trembling, harder as the crack grows; the halves part a little
            amp = (0.8 + 1.6 * beat(e, "crack")) * beat(e, "tremble") * s * config.MOTION
            tick = int(e * 30)
            items = []
            for c, r, g, k, dx in heart.cracked(beat(e, "crack")):
                h = hash32(c, r, tick)
                jx, jy = ((h & 255) / 127.5 - 1) * amp, (((h >> 8) & 255) / 127.5 - 1) * amp
                items.append((self._faded(font, g, SEAL_RGB[k], 1.0), (x0 + (c + dx) * cw + jx, y0 + r * ch + jy)))
        screen.fblits(items)

    def _draw_message(self, screen, e, cx, top):
        """Where the heart was, the message writes itself in, one character after another."""
        p = beat(e, "message")
        if p <= 0:
            return
        L, s = _scene(), self.view.scale
        if "message" not in self._cache:
            f = glyphs.font("mono-italic", MESSAGE_PX * s)
            glow, pad = L._blurred(f.render(MESSAGE, True, (255, 120, 160)), max(2, round(4 * s)), 255)
            self._cache["message"] = (f, glow, pad)
        f, glow, pad = self._cache["message"]
        adv, h = f.size("M")[0], f.get_height()
        x0, y = cx - adv * len(MESSAGE) / 2, top + env.TIP * self.cell[1] - h / 2
        glow.set_alpha(round(110 * p))
        screen.blit(glow, (x0 - pad, y - pad))
        screen.fblits([(self._faded(f, c, L.INK, a), (x0 + i * adv, y + (1 - a) * 3 * s))
                       for i, (c, a) in enumerate(zip(MESSAGE, ink(e))) if a > 0 and c != " "])

    def _button_picture(self, name):
        """The button at rest on its own surface, for the hop's scaling and tumble."""
        key = ("button", name)
        if key not in self._cache:
            L, b = _scene(), self.buttons[name]
            rows, roles = L.buttons.frame(b.word)
            cw, ch = self.btn_atlas.cell[0], L.BTN_PX * 1.1 * self.view.scale
            surf = pygame.Surface((round(len(rows[0]) * cw) + 2, round((len(rows) + 1) * ch)), pygame.SRCALPHA)
            self.btn_atlas.draw(surf, ((c, config.CREAM if role == "f" else b.colour, (i * cw, r * ch))
                                       for r, (row, rr) in enumerate(zip(rows, roles))
                                       for i, (c, role) in enumerate(zip(row, rr))))
            self._cache[key] = surf
        return self._cache[key]

    def _draw_hop(self, screen, t, e, box):
        """NO leaves its slot, hops in an arc onto the sheet, shrinking, and rides it into the dive."""
        p = beat(e, "hop")
        if p <= 0:
            self._draw_buttons(screen, t, 1.0, names=["no"])
            return
        x, y, w, h = self.hitbox("no")
        start = self.view.to_window(x + w / 2, y + h / 2)
        target = lerp(box[0], box[2], LANDING[0]), lerp(box[1], box[3], LANDING[1])
        px, py, tumble, scale = hop(p, start, target, HOP_ARC * self.view.scale)
        pic = pygame.transform.rotozoom(self._button_picture("no"), tumble, scale)
        screen.blit(pic, pic.get_rect(center=(round(px), round(py))))
