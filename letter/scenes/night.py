"""The night (SPEC §10.2–§10.6): the sheet's dark becomes a meadow, a seed falls, the flower grows,
blooms on a click, fireflies arrive, and clouds and the moon fill the sky. Pointillist particles on a
640 x 640 logical canvas.

Each frame: sky -> far fireflies -> meadow back -> seed -> flower -> meadow front -> near fireflies and
bokeh -> glow -> window.
"""
import math
import threading

import numpy as np
import pygame

from letter import config
from letter.art import fireflies, flower, invitation, meadow, sky
from letter.engine import glyphs, story
from letter.engine.timeline import approach, bayer, clamp, ease, ease_in, lean_target, lerp, smoothstep, span
from letter.scenes.base import Scene

S = config.NIGHT_SIZE[0]
GROUND_Y = meadow.GROUND_Y
# beats inside each phase, seconds at SPEED 1
NIGHT = {"sky": (0.0, 1.0), "emerge": (0.3, 1.9)}
SEED = {"fall": (0.4, 1.2), "puff": (1.2, 1.5), "grow": (2.0, 6.5)}
ARRIVE = (0.3, 6.3)          # bloomed: fireflies fade in over this window
SKY = {"moon": (0.0, 9.0), "clouds": (1.0, 10.0)}   # s after the bloom starts: the moon leads the clouds
# the invitation (SPEC §10.7): phases with fireflies, and the beats of its two endings (s at SPEED 1)
FLYING = ("bloomed", "gather", "invite", "letgo", "farewell")
FAREWELL = {"scatter": 3.0, "bright": (1.0, 3.5), "dim": (4.5, 8.0), "fade": (5.5, 8.0)}
LETGO = {"scatter": 2.0, "fade": (0.4, 2.5)}
BRIGHTER = 1.15              # extra flower glow at its brightest, on YES
BUTTONS_OUT = 0.5            # s: the invitation's buttons fade once a choice is made
HOVER_TAU = 0.12
CHOICES = {"yes": "date-yes", "no": "date-no"}
BUD_GLOW = 0.25
LEAN_CAP = math.radians(6) / flower.BEND_TIP   # in bend units: the pointer turns the head 6 degrees at most
LEAN_TAU, LEAN_RADIUS = 0.35, 220.0
WIND_BEND = 1.2     # wind -> bend: a breeze sways the head 1-2 degrees, gusts up to about 7
GRAIN_STEP = 16              # logical px between paper-grain glyphs during the dissolve
FLY_GLOW = 220 * np.array([0.7, 1.0, 0.3], np.float32)   # 8-bit bloom each firefly lends at full strength


def _build(out=None):
    q = config.QUALITY
    parts = (meadow.Meadow(quality=q), flower.Flower(quality=q), fireflies.Fireflies(count=max(10, int(40 * q))),
             sky.Sky(quality=q))
    if out is not None:
        out.append(parts)
    return parts


_early, _worker = [], None


def prepare():
    """Start building the night's art (about 200 ms, pure NumPy) on a worker thread, so entering the night
    never stalls a frame. Called while the reader looks at the letter; harmless if the night never comes."""
    global _worker
    if _worker is None or (not _worker.is_alive() and not _early):   # none yet, or the last one was used
        _worker = threading.Thread(target=_build, args=(_early,), daemon=True)
        _worker.start()


class NightScene(Scene):
    logical = config.NIGHT_SIZE
    background = config.NIGHT_BG

    def __init__(self, app):
        super().__init__(app)
        if _worker is not None:
            _worker.join()
        self.meadow, self.flower, self.flies, self.sky = _early.pop() if _early else _build()
        self.canvas = np.zeros((S, S, 3), np.float32)
        self.bytes = np.zeros((S, S, 3), np.uint8)                       # reused every frame
        self.surf = pygame.image.frombuffer(self.bytes, (S, S), "RGB")   # shares self.bytes: no copy
        self.glow_bytes = np.zeros((S // 8, S // 8, 3), np.uint8)   # a soft halo: 80 x 80 is plenty
        self.glow_surf = pygame.image.frombuffer(self.glow_bytes, (S // 8, S // 8), "RGB")
        self.lean, self.pointer = 0.0, None
        self.hover = {name: 0.0 for name in CHOICES}   # the invitation's buttons, smoothed 0..1
        self.focus = None
        self.over = None                    # the invitation's button under the pointer or focus, for its tick
        self.state = (0.0, 0.0, 0.0, 0.0)   # grow, bloom, glow, bend
        self.resize(app.size)

    def resize(self, size):
        super().resize(size)
        self.grain_atlas = glyphs.Atlas("mono", 13 * self.view.scale)
        # the side bars carry on the square's sky gradient, so the square has no visible edge
        W, H = size
        ys = np.clip((np.arange(H) - self.view.offset[1]) / max(1, self.view.size[1]), 0, 1)
        col = (self.sky.base_column()[np.minimum((ys * (S - 1)).astype(int), S - 1)] * 255).astype(np.uint8)
        bars = pygame.Surface((1, H))
        pygame.surfarray.pixels3d(bars)[0] = col
        self.bars = pygame.transform.scale(bars, (W, H)).convert()
        self.bars_dirty = True
        self.frame32 = self.surf.convert()   # the canvas in the window's format, refilled every frame
        self._halo = None

    # --- input -------------------------------------------------------------------------------------
    def _choice_at(self, pos):
        x, y = pos
        for name, (bx, by, bw, bh) in invitation.BUTTONS.items():
            if bx <= x <= bx + bw and by <= y <= by + bh:
                return name
        return None

    def on_event(self, ev, phase, e):
        if ev.type == pygame.MOUSEMOTION:
            self.pointer = self.view.to_logical(*ev.pos)
        elif ev.type == pygame.WINDOWLEAVE:
            self.pointer = None
        elif phase == "invite":   # the invitation's own decision: its own buttons and events (SPEC §8)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                name = self._choice_at(self.view.to_logical(*ev.pos))
                if name:
                    self.app.emit(CHOICES[name])
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.focus = "yes" if ev.key == pygame.K_LEFT else "no"
            elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.focus:
                self.app.emit(CHOICES[self.focus])
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and phase == "grown":
            x, y = self.view.to_logical(*ev.pos)
            grow, bloom, _, bend = self.state
            if self.flower.hit(x, y, grow, bloom, bend):
                self.app.emit("flower")
        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and phase == "grown":
            self.app.emit("flower")

    def target(self, name):
        if name == "flower":
            grow, bloom, _, bend = self.state
            return self.view.to_window(*self.flower.head(grow, bloom, bend))
        for choice, event in CHOICES.items():
            if name == event:
                x, y, w, h = invitation.BUTTONS[choice]
                return self.view.to_window(x + w / 2, y + h / 2)
        raise KeyError(name)

    def enter(self, phase, t):
        if phase == "gather":
            self.flies.gather(invitation.cells(), t, duration=story.duration("gather"))
        elif phase == "farewell":   # YES: the message breaks back into fireflies that scatter and fade
            self.flies.scatter(t, duration=FAREWELL["scatter"] / config.SPEED)
        elif phase == "letgo":      # NO: it disperses quietly
            self.flies.scatter(t, duration=LETGO["scatter"] / config.SPEED, gentle=True)

    # --- animation ---------------------------------------------------------------------------------
    def _beats(self, t, phase, e):
        """(emerge, grow, bloom, glow) for the current moment."""
        k = 1 / config.SPEED
        w = lambda name, table: [x * k for x in table[name]]  # noqa: E731
        pulse = 0.85 + 0.15 * math.sin(t * 2 * math.pi / 3.0)
        if phase == "night":
            return span(e, w("emerge", NIGHT)), 0.0, 0.0, 0.0
        if phase == "seed":
            g = ease(span(e, w("grow", SEED)))
            return 1.0, g, 0.0, BUD_GLOW * g * pulse
        if phase == "grown":
            return 1.0, 1.0, 0.0, BUD_GLOW * pulse
        if phase == "bloom":
            b = ease(clamp(e / story.duration("bloom")))
            return 1.0, 1.0, b, lerp(BUD_GLOW, 1.0, b) * lerp(pulse, 1.0, b)
        glow = 0.92 + 0.08 * pulse
        if phase == "farewell":   # a last warm answer: brighter than it has been, then slowly dimmer
            glow = (glow + BRIGHTER * ease(span(e, w("bright", FAREWELL)))) * (1 - 0.85 * ease(span(e, w("dim", FAREWELL))))
        return 1.0, 1.0, 1.0, glow

    def update(self, dt, t, phase, e):
        grow, bloom, _, bend = self.state
        target = 0.0
        if self.pointer is not None and phase in ("grown", "bloom", "bloomed"):
            hx, hy = self.flower.head(grow, bloom, bend)
            target = lean_target(self.pointer[0] - hx, self.pointer[1] - hy, LEAN_RADIUS, LEAN_CAP)
        if dt > 0:
            self.lean = approach(self.lean, target, dt, LEAN_TAU)
        if phase in FLYING and dt > 0:
            self.flies.update(dt, t, wind=meadow.wind, attract=self.flower.head(grow, bloom, bend))
        lit = None
        for name in CHOICES:   # the invitation's buttons light up under the pointer (or keyboard focus)
            over = phase == "invite" and (self.focus == name or (self.pointer is not None and
                                                                 self._choice_at(self.pointer) == name))
            lit = name if over else lit
            if dt > 0:
                self.hover[name] = approach(self.hover[name], 1.0 if over else 0.0, dt, HOVER_TAU)
        if lit is not None and lit != self.over:
            self.app.audio.play("hover")
        self.over = lit

    # --- drawing -----------------------------------------------------------------------------------
    def _seed(self, c, e, t):
        k = 1 / config.SPEED
        f = span(e, [x * k for x in SEED["fall"]])
        if 0 < f < 1:
            x = 320 + meadow.wind(320.0, t) * 10 * f
            y = int(lerp(-6, GROUND_Y - 3, ease_in(f)))
            c[max(0, y - 2):y + 2, int(x) - 1:int(x) + 2] = (1.4, 1.25, 0.9)   # a small glowing seed
        p = span(e, [x * k for x in SEED["puff"]])
        if 0 < p < 1:
            for i in range(7):  # a few soil specks hop out and settle
                ang = math.pi * (0.15 + 0.7 * i / 6)
                x = int(320 + math.cos(ang) * 14 * p)
                y = int(GROUND_Y - 2 - math.sin(ang) * 10 * math.sin(math.pi * p))
                c[y:y + 2, x:x + 2] = (0.42, 0.33, 0.25)

    def _glow(self, c, strength, lights=None):
        """Bloom: the brightest parts, sampled at 1/8 size, blurred in C and added onto the canvas frame.
        (A NumPy blur on the full canvas measured 18 ms; this costs about 1 ms.) lights: the fireflies'
        (x, y, strength); their tiny cores fall between the samples, so each is splatted in directly."""
        self._tick = getattr(self, "_tick", 0) + 1
        if self._tick % 2 or self._halo is None:
            small = (c[2::8, 2::8] + c[6::8, 6::8]) * 0.5   # glow changes slowly: rebuild every other frame
            g = np.clip((small - 0.42) * (255 * strength), 0, None)
            if lights is not None and len(lights[0]):
                gx, gy = lights[0] / 8 - 0.5, lights[1] / 8 - 0.5
                x0, y0 = np.floor(gx).astype(np.intp), np.floor(gy).astype(np.intp)
                fx, fy, n = gx - x0, gy - y0, S // 8
                for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
                    np.add.at(g, (np.clip(y0 + dy, 0, n - 1), np.clip(x0 + dx, 0, n - 1)), (lights[2] * w)[:, None] * FLY_GLOW)
            np.copyto(self.glow_bytes, np.minimum(g, 255), casting="unsafe")
            halo = pygame.transform.gaussian_blur(self.glow_surf, 2)
            self._halo = pygame.transform.smoothscale(halo, (S, S)).convert()
        self.frame32.blit(self._halo, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _invitation(self, c, t, phase, e):
        """The invitation's YES / NO buttons: dot outlines and dot-matrix labels, fading in, then out on a choice."""
        if phase == "invite":
            a = clamp(e / story.duration("invite"))
        elif phase in ("letgo", "farewell"):
            a = 1 - clamp(e * config.SPEED / BUTTONS_OUT)
        else:
            return
        if a <= 0:
            return
        for name in CHOICES:
            invitation.draw(c, name, self.hover[name], t, a)

    def _grain(self, screen, emerge):
        """Paper grain glyphs over the night that dither away as the ground comes up."""
        v, rgb = self.view, (64, 56, 46)
        items = []
        for gy in range(0, S, GRAIN_STEP):
            for gx in range(0, S, GRAIN_STEP):
                cx, cy = gx // GRAIN_STEP, gy // GRAIN_STEP
                if bayer(cx, cy) * 0.9 + 0.05 > emerge:
                    items.append((".'"[(cx * 7 + cy * 3) % 2], rgb, v.to_window(gx + 4, gy + 4)))
        self.grain_atlas.draw(screen, items)

    def draw(self, screen, t, phase, e):
        emerge, grow, bloom, glow = self._beats(t, phase, e)
        bend = clamp(WIND_BEND * config.MOTION * meadow.wind(320.0, t) + self.lean, -1.0, 1.0)
        self.state = (grow, bloom, glow, bend)
        c = self.canvas
        dark = smoothstep(0, NIGHT["sky"][1] / config.SPEED, e) if phase == "night" else 1.0
        k = 1 / config.SPEED
        since_bloom = {"bloom": e, "bloomed": story.duration("bloom") + e}.get(phase, -1.0 if phase in
                                                                              ("night", "seed", "grown") else 1e3)
        moon, clouds = (ease(span(since_bloom, [w * k for w in SKY[n]])) for n in ("moon", "clouds"))
        self.sky.render(c, t, dark, moon, clouds)
        # the endings fade the whole night (bars too) to black
        fade = {"letgo": 1 - smoothstep(LETGO["fade"][0] * k, LETGO["fade"][1] * k, e),
                "farewell": 1 - smoothstep(FAREWELL["fade"][0] * k, FAREWELL["fade"][1] * k, e)}.get(phase, 1.0)
        light = (320, GROUND_Y - 8, glow) if glow > 0 else None
        arrival = span(e, [x / config.SPEED for x in ARRIVE]) if phase == "bloomed" else 1.0
        if phase in FLYING:   # from the first bloomed frame: rendering is what lifts them out of the grass
            self.flies.render(c, t, arrival, layer="far")   # the far band passes behind the grass and the flower
        self.meadow.render_back(c, t, emerge, light)
        if phase == "seed":
            self._seed(c, e, t)
        if grow > 0:
            self.flower.render(c, grow, bloom, glow, bend, t)
        self.meadow.render_front(c, t, emerge, light)
        if phase in FLYING:
            self.flies.render(c, t, arrival, layer="near")
            self.flies.render(c, t, arrival, layer="bokeh")   # a few soft, out-of-focus ones close to us
        self._invitation(c, t, phase, e)
        if fade < 1:
            np.multiply(c, fade, out=c)
            dark = fade
        # side bars: only the strips outside the square, and only when they change (the window keeps its
        # pixels between frames); alpha (slow) only while the night fades up
        if dark < 1 or self.bars_dirty:
            self.bars.set_alpha(round(255 * dark) if dark < 1 else None)
            if dark < 1:
                screen.fill((0, 0, 0))
            ox, sw = self.view.offset[0], self.view.size[0]
            for x, w in ((0, ox), (ox + sw, screen.get_width() - ox - sw)):
                if w > 0:
                    screen.blit(self.bars, (x, 0), (x, 0, w, screen.get_height()))
            self.bars_dirty = dark < 1
        np.clip(c, 0, 1, out=c)
        np.multiply(c, 255.0, out=self.bytes, casting="unsafe")   # one pass, straight into the shared buffer
        self.frame32.blit(self.surf, (0, 0))   # 24 -> 32 bit: scaling 32-bit is about twice as fast
        lights = self.flies.lights(t, arrival) if phase in FLYING else None
        if lights is not None and fade < 1:   # the halos fade with the night
            lights = (lights[0], lights[1], lights[2] * fade)
        self._glow(c, (0.6 + 0.6 * min(glow, 1.9)) * fade, lights)
        # nearest (not smooth) keeps the dots crisp; scaling straight into the window skips a full-size blit
        pygame.transform.scale(self.frame32, self.view.size, screen.subsurface((*self.view.offset, *self.view.size)))
        if phase == "night" and emerge < 1:
            self._grain(screen, emerge)
