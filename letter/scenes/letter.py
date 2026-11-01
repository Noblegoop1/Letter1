"""The letter scene (SPEC §9): an ASCII envelope under a lamp, dedication, question banner, YES / NO.

Everything is glyphs, drawn at the window's real pixel size (never upscaled). Static layers are cached
per window size; per frame only the float, the question's wave and glints, and the buttons change.
"""
import numpy as np
import pygame

from letter import config
from letter.art import banner, buttons, dissolve, envelope as env, sheet
from letter.engine import asciigrid, glyphs, story
from letter.engine.timeline import clamp, drift, ease, ease_out, hash32, quake, span
from letter.scenes import night, no_route
from letter.scenes.base import Scene

CELL = (9.0, 14.4)                          # logical envelope cell: 67 x 27 cells ~ 600 x 390
BODY_TOP = 220                               # logical y of the envelope's top edge
ENV_LEFT = 640 - env.ENV_W * CELL[0] / 2
GRID_TOP = BODY_TOP - env.HEAD * CELL[1]     # the layers include flap headroom above the body
QUESTION_BOX = (50, 14, 1180, 192)           # logical area the banner must fit in
DEDICATION = ("To Esther", 520)              # text, logical y on the bottom flap
SLOT_CENTRES = {"left": (470, 708), "right": (810, 708)}
BTN_PX = 10.5                                # logical font size of the button glyphs
GRADIENT = ((255, 236, 228), (214, 84, 132))  # question letters: lit top -> deep rose bottom
SHADOW_RGB, VINE_RGB, SIDE_RGB = (52, 24, 46), (162, 95, 126), (150, 62, 104)
STRIP = 2                                    # banner columns per wave strip
WAVE = (2.2, 46.0, 4.6)                      # banner wave: logical px, columns per wavelength, s per cycle
HOVER = 2.5                                  # logical px the banner and buttons drift up and down
GLINTS, GLINT_S = 3, 0.9                     # glints on the banner at once, seconds each
# NO route, first three clicks (SPEC §11): the question each phase asks, then the beats
ASK = "Will you open?"
QUESTIONS = {"no-1": "Are You Sure?", "no-2": "Is This What You Really Want?"}   # other phases ask ASK
XFADE = 0.6                                  # s for one question to give way to the next
QUAKE = (0.9, 12.0)                          # no-2 earthquake: s, logical px peak
SWAP_ARC = 46.0                              # no-3: logical px one button arcs over (the other under)
INK = (255, 196, 212)
# YES reveal beats, seconds at SPEED 1 (the phase lasts config.T["yes-reveal"])
REVEAL = {"fade": (0.0, 0.4), "dissolve": (0.0, 1.0), "flap": (0.1, 0.9), "sheet": (0.4, 1.6), "zoom": (1.5, 3.0)}
SHEET_X, SHEET_Y0, SHEET_RISE = (env.ENV_W - sheet.W) // 2, env.TOP + 3, sheet.H - 3  # cells


def _blurred(surf, radius, alpha):
    """surf blurred by radius px, padded so the blur isn't clipped. Wide blurs run at reduced size: a soft
    glow loses nothing, and a full-size gaussian blur of the banner took over 100 ms at 1080p."""
    pad = radius * 3
    big = pygame.Surface((surf.get_width() + pad * 2, surf.get_height() + pad * 2), pygame.SRCALPHA)
    big.blit(surf, (pad, pad))
    k = 4 if radius >= 8 else 2 if radius >= 4 else 1
    small = pygame.transform.smoothscale(big, (big.get_width() // k, big.get_height() // k)) if k > 1 else big
    small = pygame.transform.gaussian_blur(small, max(1, round(radius / k)))
    big = pygame.transform.smoothscale(small, big.get_size()) if k > 1 else small
    big.set_alpha(alpha)
    return big, pad


class Button:
    def __init__(self, word, colour, slot):
        self.word, self.colour, self.slot = word, colour, slot
        self.hover_since = None
        self.hovered = False
        self.swap = None        # (old slot, start time) while trading places


class LetterScene(no_route.NoRoute, Scene):
    logical = config.LETTER_SIZE
    background = config.BG

    def __init__(self, app):
        self.buttons = {"yes": Button("YES", config.YES, "left"), "no": Button("NO", config.NO, "right")}
        self.focus = None
        self.question, self.previous, self.asked_at = ASK, None, 0.0   # the question, and the one it replaced
        self.frozen = None      # float pose held still once the reveal starts
        self.zoom = None        # (scale, origin) of the camera dive, measured when it begins
        super().__init__(app)
        self.resize(app.size)

    # --- layout and caches ------------------------------------------------------------------------
    def resize(self, size):
        super().resize(size)
        s = self.view.scale
        self._cache = {}
        self._tilt = None
        self.cell = (CELL[0] * s, CELL[1] * s)
        self.env_atlas = glyphs.Atlas("mono", CELL[0] / 0.6 * s)
        self.btn_atlas = glyphs.Atlas("mono-bold", BTN_PX * s)
        self.bg = self._background()
        for q in {ASK, *QUESTIONS.values()}:   # ~80 ms each: build them now (behind the launch veil), not mid-scene
            self._banner(q)

    def _background(self):
        """Night-dark room with a warm pool of lamplight falling from above onto the envelope."""
        W, H = self.app.size
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        cx, cy = self.view.to_window(640, 330)
        r = np.hypot((x - cx) / (0.55 * W), (y - cy) / (0.75 * H))
        glow = np.clip(1 - r, 0, 1) ** 2
        rgb = np.array(config.BG, np.float32) + np.array((58, 38, 46), np.float32) * glow[..., None] * 0.9
        surf = pygame.Surface((W, H))
        pygame.surfarray.pixels3d(surf)[...] = np.clip(rgb, 0, 255).astype(np.uint8).swapaxes(0, 1)
        return surf

    def _layer(self, rows, roles):
        fg, bg = env.colours(rows, roles)
        return asciigrid.render(self.env_atlas, rows, fg, bg, self.cell)

    def envelope_layers(self, d, seal=True):
        """(back, front) surfaces for flap depth d, cached."""
        return self._env_layer(d, seal, "back"), self._env_layer(d, seal, "front")

    def _env_layer(self, d, seal, part):
        key = ("env", d, seal and d > 0, part)   # the seal only shows while the flap faces us
        if key not in self._cache:
            self._cache[key] = self._layer(*env.envelope(d, seal)[part])
        return self._cache[key]

    def _dedication(self):
        if "ded" not in self._cache:
            f = glyphs.font("mono-italic", 30 * self.view.scale)
            text = f.render(DEDICATION[0], True, INK)
            glow, pad = _blurred(f.render(DEDICATION[0], True, (255, 120, 160)), max(2, round(4 * self.view.scale)), 120)
            self._cache["ded"] = (text, glow, pad)
        return self._cache["ded"]

    def _sheet(self):
        if "sheet" not in self._cache:
            rows, fg, bg = sheet.build()
            self._cache["sheet"] = asciigrid.render(self.env_atlas, rows, fg, bg, self.cell)
        return self._cache["sheet"]

    def _draw_dissolve(self, comp, p):
        """'To Esther' crumbling letter by letter into rising ASCII specks."""
        f = glyphs.font("mono-italic", 30 * self.view.scale)
        small = glyphs.font("mono", 18 * self.view.scale)
        adv, lh = f.size("M")[0], f.get_height()
        text = DEDICATION[0]
        x0 = comp.get_width() / 2 - adv * len(text) / 2
        y0 = (DEDICATION[1] - GRID_TOP) * self.view.scale - lh / 2
        for i, g in dissolve.letters(text, p):
            if g is not None:
                comp.blit(f.render(g, True, INK), (x0 + i * adv, y0))
        for i, dx, dy, g, alpha in dissolve.specks(text, p):
            s = small.render(g, True, INK)
            s.set_alpha(round(255 * alpha))
            comp.blit(s, (x0 + (i + 0.3 + dx) * adv, y0 + lh * 0.4 + dy * lh))

    def _opened(self, d, rise, seal=True):
        """Envelope composite while it opens: back, the sheet risen `rise` cells, front with the flap at d."""
        back, front = self.envelope_layers(d, seal)
        comp = back.copy()
        comp.blit(self._sheet(), (round(SHEET_X * self.cell[0]), round((SHEET_Y0 - rise) * self.cell[1])))
        comp.blit(front, (0, 0))
        return comp

    def _reveal(self, e):
        """The YES reveal: the flap folds back, the sheet rises, the dedication crumbles."""
        k = 1 / config.SPEED
        d = env.flap_depth(180 * ease(span(e, [w * k for w in REVEAL["flap"]])))
        rise = ease_out(span(e, [w * k for w in REVEAL["sheet"]])) * SHEET_RISE
        comp = self._opened(d, rise)
        self._draw_dissolve(comp, span(e, [w * k for w in REVEAL["dissolve"]]))
        return comp, rise

    def _write_dedication(self, comp, writing):
        text, glow, pad = self._dedication()
        y = (DEDICATION[1] - GRID_TOP) * self.view.scale - 3 * self.view.scale * (1 - writing)
        rect = text.get_rect(center=(comp.get_width() / 2, y))
        glow.set_alpha(round(120 * writing))
        comp.blit(glow, (rect.x - pad, rect.y - pad))
        t2 = text.copy()
        t2.set_alpha(round(255 * writing))
        comp.blit(t2, rect)

    def _resting(self, writing, seal=True):
        """Closed envelope with the dedication at the given fade (rebuilt only when that changes)."""
        key = ("rest", round(writing, 2), seal)
        if key not in self._cache:
            back, front = self.envelope_layers(env.CY, seal)
            comp = back.copy()
            comp.blit(front, (0, 0))
            if writing > 0:
                self._write_dedication(comp, writing)
            self._cache = {k: v for k, v in self._cache.items() if k[0] != "rest"}
            self._cache[key] = comp
        return self._cache[key]

    def _tilted(self, comp, angle):
        """comp rotated by angle degrees. Rotation is the costliest step of a letter frame (3-9 ms), so a
        still composite reuses its last tilt until the angle moves 0.04 degrees (under half a px at the corners)."""
        if angle == 0:
            return comp
        q = round(angle / 0.04)
        if self._tilt is None or self._tilt[0] is not comp or self._tilt[1] != q:
            self._tilt = (comp, q, pygame.transform.rotozoom(comp, q * 0.04, 1.0))
        return self._tilt[2]

    def _banner(self, text):
        """The question's layers (shadow, glow, face) cut into thin column strips so they can wave, and the
        well-lit cells where glints may appear. Built once per question and window size."""
        key = ("q", text)
        if key not in self._cache:
            art = banner.banner(text, QUESTION_BOX[2], QUESTION_BOX[3])
            s = self.view.scale
            cell = (art["cell"][0] * s, art["cell"][1] * s)
            atlas = glyphs.Atlas("mono-bold", art["glyph_px"] * s)
            kind, light, band = art["kind"], art["light"], art["band"]
            top, bottom = (np.array(c, np.float32) for c in GRADIENT)
            # lit from above (the gradient) and from the top left (the bevel), with a near-white sheen
            fg = (top + (bottom - top) * band[..., None] ** 1.2) * (0.62 + 0.7 * light[..., None])
            fg += 240 * np.clip(light - 0.75, 0, 1)[..., None]
            fg[kind == 2] = SIDE_RGB
            fg[kind == 3] = VINE_RGB
            fg = np.clip(fg, 0, 255).astype(np.uint8)
            face = asciigrid.render(atlas, art["rows"], fg, cell=cell)
            glow, gpad = _blurred(face, max(2, round(8 * s)), 255)
            shadow, spad = _blurred(asciigrid.render(atlas, art["rows"], np.full_like(fg, SHADOW_RGB), cell=cell),
                                    max(2, round(3.5 * s)), 255)
            off = 5 * s
            sw = max(2, round(STRIP * cell[0]))
            cuts = []   # per layer: (x, y offset from the face's top-left, strip)
            for surf, (ox, oy) in ((shadow, (0.6 * off - spad, off - spad)), (glow, (-gpad, -gpad)), (face, (0, 0))):
                w = surf.get_width()
                cuts.append([(ox + x, oy, surf.subsurface((x, 0, min(sw, w - x), surf.get_height())))
                             for x in range(0, w, sw)])
            spots = [((c + 0.5) * cell[0], (r + 0.4) * cell[1]) for r, c in zip(*np.nonzero((kind == 1) & (light > 0.7)))]
            sparkle = glyphs.font("mono-bold", art["glyph_px"] * 1.5 * s)   # on black: it is added, not blended
            self._cache[key] = {"size": face.get_size(), "cuts": cuts, "spots": spots, "alpha": None, "cell_w": cell[0],
                                "sparkle": [sparkle.render("+", True, (g, g, round(g * 0.9)), (0, 0, 0))
                                            for g in (60, 120, 190, 255)]}
        return self._cache[key]

    def _draw_questions(self, screen, t, k, fade):
        """The question, crossfading from the one it replaced (NO route)."""
        x = clamp((t - self.asked_at) / (XFADE / config.SPEED)) if self.previous else 1.0
        if x < 1:
            self._draw_question(screen, self.previous, t, k * fade * (1 - x))
        self._draw_question(screen, self.question, t, k * fade * x, glints=x >= 1)

    def _draw_question(self, screen, text, t, vis, glints=True):
        """A question: rises and fades in, then hovers and waves gently, with glints on its lit strokes."""
        if vis <= 0:
            return
        k = ease_out(span(t, (1.0, 2.0)))
        v, q = self.view, self._banner(text)
        bx, by, bw, bh = QUESTION_BOX
        cx, cy = v.to_window(bx + bw / 2, by + bh / 2 + 12 * (1 - k) + HOVER * config.MOTION * drift(t, (5.3, 8.9)))
        x0, y0 = cx - q["size"][0] / 2, cy - q["size"][1] / 2
        if q["alpha"] != vis:
            for strips, a in zip(q["cuts"], (200, 115, 255)):
                for *_, sub in strips:
                    sub.set_alpha(round(a * vis))
            q["alpha"] = vis
        amp, lam = WAVE[0] * config.MOTION * v.scale * k, WAVE[1] * q["cell_w"]
        ph = 2 * np.pi * t / WAVE[2]
        dy = lambda x: amp * np.sin(2 * np.pi * x / lam - ph)  # noqa: E731
        half = STRIP * q["cell_w"] / 2
        screen.fblits([(sub, (round(x0 + x), round(y0 + y + dy(x + half)))) for strips in q["cuts"] for x, y, sub in strips])
        if vis < 1 or not glints or not q["spots"] or config.CALM:   # A11: no flashes
            return
        for j in range(GLINTS):   # each glint flares and fades over GLINT_S on a lit cell picked by a hash
            u = t / GLINT_S + j / GLINTS
            x, y = q["spots"][hash32(int(u), j) % len(q["spots"])]
            g = q["sparkle"][min(3, int(4 * np.sin(np.pi * (u % 1.0)) ** 2))]
            screen.blit(g, g.get_rect(center=(round(x0 + x), round(y0 + y + dy(x)))), special_flags=pygame.BLEND_RGB_ADD)

    # --- buttons -----------------------------------------------------------------------------------
    def hitbox(self, name):
        """Fixed logical rect of a button's slot: hover never moves it."""
        cx, cy = SLOT_CENTRES[self.buttons[name].slot]
        w, h = buttons.SIZE[0] * BTN_PX * 0.6, buttons.SIZE[1] * BTN_PX * 1.1
        return cx - w / 2, cy - h / 2, w, h

    def _button_at(self, pos):
        lx, ly = self.view.to_logical(*pos)
        for name in self.buttons:
            x, y, w, h = self.hitbox(name)
            if x <= lx <= x + w and y <= ly <= y + h:
                return name
        return None

    def _draw_button(self, screen, name, t):
        b = self.buttons[name]
        e = None if b.hover_since is None else t - b.hover_since
        rows, roles = buttons.frame(b.word, hover_e=e)
        lit = b.hovered or self.focus == name
        frame_rgb = (255, 248, 236) if lit else config.CREAM
        x, y, w, h = self.hitbox(name)
        # the picture drifts, the hitbox doesn't: an idle bob (each button its own), plus a lift when lit
        bob = 0.6 * HOVER * config.MOTION * drift(t + 2.1 * (b.word == "NO"), (3.7, 5.9))
        sx, sy = self._swap_offset(b, t)
        dx = ((2.0 * np.sin(t * 2.3) if lit else 0.0) + sx) * self.view.scale
        dy = (bob - (1.5 if lit else 0.0) + sy) * self.view.scale
        wx, wy = self.view.to_window(x, y)
        cw, ch = self.btn_atlas.cell[0], BTN_PX * 1.1 * self.view.scale
        self.btn_atlas.draw(screen, ((c, frame_rgb if role == "f" else b.colour, (wx + dx + i * cw, wy + dy + r * ch))
                                     for r, (row, rr) in enumerate(zip(rows, roles))
                                     for i, (c, role) in enumerate(zip(row, rr))))

    def _swap_offset(self, b, t):
        """Logical offset of a button's picture from its (new) slot while the two trade places."""
        if b.swap is None:
            return 0.0, 0.0
        old, since = b.swap
        p = ease(clamp((t - since) / config.T["no-3"] * config.SPEED))
        if p >= 1:
            b.swap = None
            return 0.0, 0.0
        (fx, fy), (tx, ty) = SLOT_CENTRES[old], SLOT_CENTRES[b.slot]
        arc = SWAP_ARC * np.sin(np.pi * p) * (-1 if old == "left" else 1)   # left-to-right goes over the top
        return (fx - tx) * (1 - p), (fy - ty) * (1 - p) + arc

    def _draw_buttons(self, screen, t, fade, names=None):
        names = names or list(self.buttons)
        if fade <= 0:
            return
        if fade >= 1:
            for name in names:
                self._draw_button(screen, name, t)
            return
        # fading: draw into a kept alpha layer and blit only the buttons' area (a full-screen layer per
        # frame cost several ms at 1080p)
        if getattr(self, "_fade_layer", None) is None or self._fade_layer.get_size() != screen.get_size():
            self._fade_layer = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        area = pygame.Rect(self.view.rect(*self.hitbox(names[0])))
        for name in names:
            area.union_ip(self.view.rect(*self.hitbox(name)))
        area = area.inflate(self.view.px(24), self.view.px(24)).clip(self._fade_layer.get_rect())
        self._fade_layer.fill((0, 0, 0, 0), area)
        for name in names:
            self._draw_button(self._fade_layer, name, t)
        self._fade_layer.set_alpha(round(255 * fade))
        screen.blit(self._fade_layer, area, area)

    # --- story hooks -------------------------------------------------------------------------------
    def on_event(self, ev, phase, e):
        if ev.type == pygame.MOUSEMOTION:
            over = self._button_at(ev.pos)
            for name, b in self.buttons.items():
                if name == over and not b.hovered and phase in ("letter", "no-1", "no-2", "no-3"):
                    b.hover_since = self.app.t
                b.hovered = name == over
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            name = self._button_at(ev.pos)
            if name and not story.locked(phase, self.app.since, self.app.t):
                self.app.emit(name)
        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_LEFT, pygame.K_RIGHT):
            by_x = sorted(self.buttons, key=lambda n: SLOT_CENTRES[self.buttons[n].slot][0])
            self.focus = by_x[0] if ev.key == pygame.K_LEFT else by_x[-1]
            self.buttons[self.focus].hover_since = self.app.t
        elif ev.type == pygame.KEYDOWN and ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and self.focus:
            if not story.locked(phase, self.app.since, self.app.t):
                self.app.emit(self.focus)

    def target(self, name):
        x, y, w, h = self.hitbox(name)
        return self.view.to_window(x + w / 2, y + h / 2)

    def enter(self, phase, t):
        question = QUESTIONS.get(phase, ASK)
        if question != self.question:
            self.previous, self.question, self.asked_at = self.question, question, t
        if phase == "no-3":   # YES and NO trade slots; each keeps its colour and action, its hitbox goes with it
            for b in self.buttons.values():
                b.swap, b.slot = (b.slot, t), "right" if b.slot == "left" else "left"
                b.hovered = False
            self.focus = None
        if phase in ("yes-reveal", "no-4"):
            self.frozen = self.float_offset(t)
            self.focus = None
            for b in self.buttons.values():
                b.hovered = False

    def update(self, dt, t, phase, e):
        # build the flap's frames during the intro and while the reader looks at the letter, so the opening
        # never stalls; one layer (about 6 ms) per frame keeps every frame inside 60 fps
        if phase in ("intro", "letter", "no-1", "no-2", "no-3", "no-4"):
            # the NO route opens the envelope too, without its seal: build those frames after the others
            for seal in (True, False) if phase.startswith("no-") else (True,):
                for d in range(env.CY, -env.CY - 1, -1):
                    for part in ("back", "front"):
                        if ("env", d, seal and d > 0, part) not in self._cache:
                            self._env_layer(d, seal, part)
                            return
            if phase == "letter":
                night.prepare()   # the flap is ready; YES leads to the night, so build its art meanwhile

    # --- drawing -----------------------------------------------------------------------------------
    def float_offset(self, t):
        """Gentle drift and tilt: sums of sines with unrelated periods, so it never visibly loops."""
        m = config.MOTION
        return 7.0 * m * drift(t, (7.3, 11.9, 17.3)), 1.1 * m * drift(t + 5.0, (9.1, 13.7, 23.3))

    def _draw_shadow(self, screen, dy):
        """An ASCII shadow under the envelope: tighter and darker when it sinks, softer when it rises."""
        v = self.view
        rows = [" " * 8 + "." * 51, "  ..:" + ":" * 59 + ":..", " " * 8 + "." * 51]
        k = max(0.25, 0.75 - 0.04 * dy)
        rgb = (round(48 * k), round(30 * k), round(46 * k))
        x0, y0 = v.to_window(ENV_LEFT, BODY_TOP + env.ENV_H * CELL[1] + 4)
        self.env_atlas.draw_rows(screen, rows, lambda r, c, ch: rgb, x0, y0)

    def _camera(self, screen):
        if getattr(self, "_cam", None) is None or self._cam.get_size() != screen.get_size():
            self._cam = pygame.Surface(screen.get_size())
        return self._cam

    def draw(self, screen, t, phase, e):
        dx, dy = quake(e, QUAKE[0] / config.SPEED, QUAKE[1] * config.MOTION) if phase == "no-2" else (0, 0)
        if dx or dy:   # the earthquake: the whole letter shakes; the lamplit room behind barely shows it
            cam = self._camera(screen)
            self._draw_scene(cam, t, phase, e)
            screen.blit(self.bg, (0, 0))
            screen.blit(cam, (round(dx * self.view.scale), round(dy * self.view.scale)))
            return
        dive = {"yes-reveal": REVEAL["zoom"], "no-4": no_route.NO4["zoom"]}.get(phase)
        if dive is None or e < dive[0] / config.SPEED:
            self._draw_scene(screen, t, phase, e)
            return
        # camera dive: draw the frame off-screen, then scale it about the centre of the sheet's window
        W, H = screen.get_size()
        box = self._draw_scene(self._camera(screen), t, phase, e)
        if self.zoom is None:
            self.zoom = (sheet.cover_scale(box, W, H), ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2))
        scale, (ox, oy) = self.zoom
        z = scale ** ease(span(e, [w / config.SPEED for w in dive]))
        src = pygame.Rect(round(ox - ox / z), round(oy - oy / z), max(1, round(W / z)), max(1, round(H / z)))
        src = src.clip(self._cam.get_rect())
        screen.fill(sheet.WINDOW)
        if src.width and src.height:
            part = pygame.transform.smoothscale(self._cam.subsurface(src), (round(src.width * z), round(src.height * z)))
            screen.blit(part, (round(ox + (src.x - ox) * z), round(oy + (src.y - oy) * z)))

    def _draw_scene(self, screen, t, phase, e):
        """Draw the letter; returns the sheet window's rect in window px (for the camera dive)."""
        v = self.view
        screen.blit(self.bg, (0, 0))
        revealing, refusing = phase == "yes-reveal", phase == "no-4"
        fade = 1 - span(e, [w / config.SPEED for w in REVEAL["fade"]]) if revealing else 1.0
        if refusing:
            fade = 1 - no_route.beat(e, "crack")   # the question gives way as the heart cracks
        dy, angle = self.frozen if (revealing or refusing) and self.frozen else self.float_offset(t)
        # both openings level the envelope first (then no rotation is needed)
        angle *= (1 - no_route.beat(e, "tremble")) if refusing else fade
        self._draw_shadow(screen, dy)
        if revealing:
            comp, rise = self._reveal(e)
        elif refusing:
            comp, rise = self._no4_envelope(e)
        else:
            comp, rise = self._resting(ease_out(span(t, (0.4, 1.6)))), 0.0
        rot = self._tilted(comp, angle)
        cx, cy = v.to_window(640, GRID_TOP + env.ROWS * CELL[1] / 2 + dy)
        screen.blit(rot, rot.get_rect(center=(round(cx), round(cy))))
        left, top = cx - comp.get_width() / 2, cy - comp.get_height() / 2
        x0, y0, x1, y1 = sheet.INSIDE
        box = (left + (SHEET_X + x0) * self.cell[0], top + (SHEET_Y0 - rise + y0) * self.cell[1],
               left + (SHEET_X + x1) * self.cell[0], top + (SHEET_Y0 - rise + y1) * self.cell[1])
        self._draw_questions(screen, t, ease_out(span(t, (1.0, 2.0))), fade)
        if refusing:
            self._draw_no4(screen, t, e, (left, top, comp.get_width()), box)
        elif t > 1.2 and fade > 0:
            self._draw_buttons(screen, t, fade)
        if t < 0.6:  # launch: fade up from black
            veil = pygame.Surface(screen.get_size())
            veil.set_alpha(round(255 * (1 - t / 0.6)))
            screen.blit(veil, (0, 0))
        return box
