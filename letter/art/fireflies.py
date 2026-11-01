"""Fireflies for the night scene (SPEC 10.5): waypoint wanderers over the whole 640 x 640 night.

Each firefly flies toward its own list of waypoints with a limited turn rate and acceleration, slows
near each one, sometimes hovers, then moves on. A share of waypoints sit near the flower head, so a few
drift close now and then; ordinary waypoints keep clear of it, so the flower stays the focal point.
They wait in the grass until `arrival` reaches their turn, then glow up and fade in as they lift off.

Rhythms: quick flashes (fast rise, slower fade), double flashes and slow soft glows, each with its own
period and phase, and no two flashes alike. Light is added to the scene's float canvas (display RGB):
one baked stamp per firefly (warm yellow-green core, a greener exponential halo), a white-hot centre at
a flash peak, and a faint trail that keeps the light it had a moment ago, so a flash in flight leaves a
short fading streak. Three depth bands (far: small, dim, slow, cooler, drawn behind the grass; near:
larger, brighter, warmer) plus a few big out-of-focus "bokeh" discs close to the camera. `lights()`
hands the scene each one's position and strength for its wide bloom halo. Pure NumPy.
"""
import numpy as np

SIZE = 640                      # night canvas is SIZE x SIZE, indexed [y, x]
_M = 24                         # positions stay _M px inside the canvas (the largest stamp radius): no cropping
_SUB = 4                        # quarter-pixel stamp offsets, so slow drift glides instead of stepping
_K = 128                        # waypoints per firefly before its list repeats (about 25 min)
_BOX = (28.0, 612.0, 24.0, 492.0)    # x0, x1, y0, y1 for waypoints; y > 440 dips into the grass tops
_PERCH = (130.0, 510.0, 462.0, 494.0)   # where they wait in the grass on the island before arriving
_REACH, _TIMEOUT = 8.0, 14.0    # px that counts as reached; s before giving up on a target
_CLEAR = 125.0                  # ordinary waypoints are pushed this far from the flower
_TRAIL = np.arange(1, 7)        # trail points, each _LAG s further back along the motion
_LAG = 0.07
_BACK = (_LAG * np.arange(_TRAIL.size + 1))[:, None]   # now, then each trail point's moment
_FADE = 0.12                    # share of the arrival range one firefly takes to fade in
_WAKE = 0.25                    # ... and to glow up and settle into its rhythm as it lifts off
_LIT = 1e-4                     # brightness below which a firefly is not drawn (nor reported by lights)

# Per depth band (0 far, 1 mid, 2 near).
_SHARE = (0.34, 0.36, 0.30)
_CRUISE = np.array([[9.0, 15.0], [15.0, 25.0], [24.0, 36.0]])   # px/s
_TURN = np.array([1.1, 1.5, 1.9])                                 # rad/s
_ACC = np.array([9.0, 14.0, 20.0])                                # px/s^2
_WIND_PX = np.array([3.0, 5.0, 7.0])                              # px/s drift at full lean (parallax)
_RAD = (9, 15, 24)                                                # stamp radius
_CORE_SIGMA = ((0.75, 0.85), (1.05, 1.25), (1.45, 1.75))          # (small, big) per band
_HALO_LEN = ((1.8, 2.1), (3.0, 3.6), (4.5, 5.5))                # exponential glow length
_CORE_HEX = (("#c0f090", "#d4ea86"), ("#e0ff80", "#f4f57a"), ("#f0ff9a", "#fff59a"))   # (lime, gold)
_HALO_HEX = (("#4fb868", "#6cb85a"), ("#94d84c", "#b8d646"), ("#b0e446", "#d4e03e"))
_CORE_GAIN = np.array([0.55, 0.8, 0.95])     # core peak at full brightness, on top of the halo's
_HALO_GAIN = np.array([0.5, 0.85, 1.1])
_HOT_GAIN = np.array([0.2, 0.4, 0.5])        # white centre at a flash peak
_HOT_RGB = np.array([1.0, 1.0, 0.9])
_TRAIL_GAIN = np.array([0.08, 0.15, 0.24])
_LIGHT_GAIN = np.array([0.35, 0.7, 1.0])     # strength reported by lights()
_LAYERS = {None: (0, 1, 2), "far": (0,), "near": (1, 2), "bokeh": ()}

# Bokeh: big soft discs close to the camera.
_BK_RGB = np.array([1.0, 0.95, 0.45])     # warm, so they read as out-of-focus fireflies, not lens dust
_BK_GAIN = 0.21                 # at radius 14; larger discs spread the same light thinner
_BK_FADE = 0.2


def _rgb(hexstr):
    """"#rrggbb" -> display RGB in 0..1 (the canvas holds display values)."""
    return np.array([int(hexstr[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0


def _offsets(r):
    """(_SUB, _SUB, w, w) squared distance from each pixel to a centre at quarter-pixel offset (fy, fx)."""
    d = np.arange(2 * r + 1)[None, :] - r - np.arange(_SUB)[:, None] / _SUB    # (_SUB, w) pixel - centre
    return d[:, None, :, None] ** 2 + d[None, :, None, :] ** 2


def _gauss(r2, s):
    """Gaussian with the same total light at every offset, so a moving dot never twinkles from sampling."""
    g = np.exp(-r2 / (2 * s * s))
    return g * (2 * np.pi * s * s) / g.sum(axis=(2, 3), keepdims=True)


def _glow_stamps(band):
    """(4, _SUB, _SUB, w, w, 3) float32: core + halo in colour, for (small, big) x (lime, gold).

    Colour and the halo's share are baked in, so a frame scales whole stamps once: broadcasting a
    per-firefly colour over a trailing axis of 3 was the slowest step of the render."""
    r = _RAD[band]
    r2 = _offsets(r)
    window = np.clip(1.0 - (r2 / (r * r)) ** 1.5, 0.0, 1.0)   # halo falls to zero at the stamp edge
    out = np.empty((4, _SUB, _SUB, 2 * r + 1, 2 * r + 1, 3), np.float32)
    for big in (0, 1):
        core = _gauss(r2, _CORE_SIGMA[band][big])
        halo = np.exp(-np.sqrt(r2) / _HALO_LEN[band][big]) * window   # a long soft tail reads as glow
        for hue in (0, 1):
            out[2 * big + hue] = (core[..., None] * _rgb(_CORE_HEX[band][hue]) * _CORE_GAIN[band]
                                  + halo[..., None] * _rgb(_HALO_HEX[band][hue]) * _HALO_GAIN[band])
    return out


def _disc(r):
    """(_SUB, _SUB, w, w, 3) float32 bokeh: a soft disc of radius r with a faint brighter rim."""
    R = int(np.ceil(r + 3))
    d = np.sqrt(_offsets(R))
    edge = 1.0 - np.clip((d - (r - 2.0)) / 3.0, 0.0, 1.0)
    edge = edge * edge * (3 - 2 * edge)
    prof = edge * (0.45 + 0.3 * (d / r) ** 2 + 0.5 * np.exp(-((d - (r - 1.6)) / 1.3) ** 2))
    grain = np.random.default_rng(int(r * 100)).uniform(0.75, 1.25, prof.shape[-2:])   # a pointillist speckle
    return (prof[..., None] * grain[..., None] * _BK_RGB).astype(np.float32)


class Fireflies:
    def __init__(self, count=40, seed=7):
        n = self.count = int(count)
        rng = np.random.default_rng(seed)
        u = lambda lo, hi, size=n: rng.uniform(lo, hi, size)   # noqa: E731

        band = self._band = rng.choice(3, n, p=_SHARE)
        self._members = [np.flatnonzero(band == b) for b in range(3)]
        self._var = 2 * (rng.random(n) < 0.5) + (rng.random(n) < 0.4)   # stamp: 2 * big + gold
        self._cruise = _CRUISE[band, 0] + (_CRUISE[band, 1] - _CRUISE[band, 0]) * rng.random(n)
        self._turn, self._acc, self._wind_px = _TURN[band], _ACC[band], _WIND_PX[band]
        self._slow_r = 2.5 * self._cruise / self._turn     # slowing radius that always captures the target
        self._hover_speed = u(2.0, 6.0)
        # Heading wobble (two sines) and a slow speed swell, so paths meander and sometimes slacken.
        self._wob = np.stack([u(0.3, 0.6), u(0.5, 1.4), u(0, 6.3), u(0.12, 0.3), u(1.6, 3.4), u(0, 6.3)])
        self._swell = np.stack([2 * np.pi / u(8, 20), u(0, 6.3)])

        # They start perched in the grass; the first waypoint lifts each one up into the night.
        px0, px1, py0, py1 = _PERCH
        perch = np.stack([u(px0, px1), u(py0, py1)], axis=-1)
        stem = np.abs(perch[:, 0] - 320.0) < 24.0
        perch[stem, 0] += np.where(perch[stem, 0] < 320.0, -48.0, 48.0)   # not on the flower's stem
        self._perch = perch
        x0, x1, y0, y1 = _BOX
        lo, span = np.array([x0, y0]), np.array([x1 - x0, y1 - y0])
        lift = np.clip(perch + np.stack([u(-130, 130), -u(150, 340)], axis=-1), lo, lo + span)
        # Then out toward the sides of the night, so they fan out from the island instead of lingering by
        # the flower, and from there a random walk of 90-260 px hops folded back into the box. Independent
        # random points would crowd the paths into the middle; the folded walk spreads them evenly.
        side = np.where(perch[:, 0] < 320.0, -1.0, 1.0) * np.where(rng.random(n) < 0.75, 1.0, -1.0)
        spread = np.stack([320.0 + side * u(150, 292), u(y0, 420)], axis=-1)
        a, r = rng.uniform(0, 2 * np.pi, (n, _K - 2)), rng.uniform(90, 260, (n, _K - 2))
        walk = (spread[:, None, :] - lo + np.cumsum(np.stack([r * np.cos(a), r * np.sin(a)], -1), 1)) % (2 * span)
        walk = lo + np.where(walk > span, 2 * span - walk, walk)
        self._wp = np.concatenate([lift[:, None], spread[:, None], walk], 1)
        # About 12% of waypoints are instead offsets around the flower head (never the lift-off).
        self._bias = rng.random((n, _K)) < 0.12
        self._bias[:, 0] = False
        a, r = rng.uniform(0, 2 * np.pi, (n, _K)), rng.uniform(30, 100, (n, _K))
        self._bias_off = np.stack([r * np.cos(a), r * np.sin(a)], axis=-1)
        self._hover_dur = np.where(rng.random((n, _K)) < 0.35, 0.0, rng.uniform(0.4, 3.0, (n, _K)))
        self._hover_dur[self._bias] += 0.5                 # linger a moment by the flower

        # Pulse: stratified periods with golden-ratio phases, so neighbouring periods never start together.
        rank = rng.permutation(n)
        self._period = 1.2 + 2.8 * (rank + u(0.2, 0.8)) / n
        self._phase = (rank * 0.6180339887 + u(0, 0.05)) % 1.0
        self._jit = np.stack([u(0.03, 0.08), 2 * np.pi / u(5, 12), u(0, 6.3)])
        # Kinds: a quick flash (fast rise, slower fade), a double flash, or a slow soft glow. Short periods
        # are glows, so the flashers keep a dark gap between flashes.
        kind = np.where(self._period < 1.9, 2, rng.choice(3, n, p=(0.55, 0.25, 0.2)))
        self._glow = kind == 2
        dbl = kind == 1   # a double flash is two short blinks with a dark dip between them
        self._rise = np.where(dbl, u(0.07, 0.11), u(0.1, 0.18))
        self._decay = np.where(dbl, u(0.1, 0.16), u(0.4, 0.75))
        self._gap = u(0.36, 0.5)
        self._echo = np.where(dbl, u(0.6, 0.85), 0.0)
        self._peak = np.where(self._glow, u(0.65, 0.9), u(0.8, 1.0))
        self._base = np.where(self._glow, u(0.2, 0.3), u(0.1, 0.16))   # flashers keep a faint ember
        self._vary = np.stack([np.where(self._glow, u(0.05, 0.2), u(0.1, 0.35)), 2 * np.pi / u(6, 14), u(0, 6.3)])
        self._wing = np.stack([2 * np.pi * u(9, 15), u(0, 6.3)])
        self._thresh = rng.permutation(n) / n * (1.0 - _WAKE)
        self._released = None   # None: no arrival seen yet, so all fly (tests, tools)
        self._memo_key, self._memo = None, None

        self._glow_st = [_glow_stamps(b) for b in range(3)]
        hot = _gauss(_offsets(3), 0.6)
        self._hot_st = (hot[..., None] * _HOT_RGB).astype(np.float32)
        self._trail_rgb = np.array([[_rgb(h) for h in hs] for hs in _HALO_HEX], np.float32)[band, self._var % 2]
        self._trail_rgb *= _TRAIL_GAIN[band][:, None].astype(np.float32)

        # Bokeh: slow Lissajous drifts over the night, each its own radius, pulse and turn to arrive.
        nb = int(np.clip(n // 10, 3, 6))
        self._bk_r = rng.permutation(np.linspace(10.0, 24.0, nb)) + u(-1.0, 1.0, nb)
        self._bk_R = np.ceil(self._bk_r + 3).astype(int)
        self._bk_st = [_disc(r) for r in self._bk_r]
        k = rng.permutation(nb)   # stratified phases, so they start spread apart, not in a clump
        px, py = 2 * np.pi * (k + u(0.2, 0.8, nb)) / nb, 2 * np.pi * ((k * 0.618 + u(0, 0.08, nb)) % 1.0)
        self._bk_path = np.stack([2 * np.pi / u(150, 260, nb), 2 * np.pi / u(70, 120, nb), px, u(0, 6.3, nb),
                                  2 * np.pi / u(150, 260, nb), 2 * np.pi / u(70, 120, nb), py, u(0, 6.3, nb)])
        self._bk_beat = np.stack([2 * np.pi / u(3.5, 6.5, nb), u(0, 6.3, nb),
                                  u(0.8, 1.1, nb) * (14.0 / self._bk_r) ** 0.6])   # gain: bigger is fainter
        self._bk_thresh = np.linspace(0.3, 0.7, nb)   # they drift in late in the arrival

        # Motion state.
        self._pos = perch.copy()
        self._th = -np.pi / 2 + u(-0.5, 0.5)
        self._sp = 0.7 * self._cruise
        self._vel = np.stack([self._sp * np.cos(self._th), self._sp * np.sin(self._th)], axis=-1)
        self._th0, self._sp0 = self._th.copy(), self._sp.copy()
        self._k = np.zeros(n, np.intp)
        self._hov = np.zeros(n, bool)
        self._hover_left = np.zeros(n)
        self._seek_t = np.zeros(n)
        self._attract = None
        self._target = self._pick(np.arange(n))

    @property
    def positions(self):
        """(count, 2) current x, y in night-canvas px (a copy)."""
        return self._pos.copy()

    def _pick(self, idx):
        """Current waypoint for fireflies idx, resolved against the latest flower position."""
        k = self._k[idx] % _K
        tgt = self._wp[idx, k]
        if self._attract is not None:
            a = np.asarray(self._attract, float)
            d = tgt - a
            r = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-6)
            near = (r < _CLEAR) & (k > 0)   # mirror into the ring outside the clear zone (not the lift-off)
            tgt[near] = a + d[near] * ((2 * _CLEAR - r[near]) / r[near])[:, None]
            b = self._bias[idx, k]
            tgt[b] = a + self._bias_off[idx[b], k[b]]
        x0, x1, y0, y1 = _BOX
        return np.clip(tgt, (x0, y0), (x1, y1))

    def _release(self, arrival):
        """Let fireflies whose turn has come leave the grass (latched: they never go back)."""
        go = self._thresh < arrival
        self._released = go if self._released is None else self._released | go

    def update(self, dt, t, wind=None, attract=None):
        """Advance by dt seconds. wind(x_array, t) -> lean in [-1, 1]; attract = flower head (x, y).
        Fireflies whose arrival turn has not come (see render) stay perched in the grass."""
        if dt <= 0:
            return
        if attract is not None:
            self._attract = (float(attract[0]), float(attract[1]))
        pos = self._pos
        d = self._target - pos
        dist = np.hypot(d[:, 0], d[:, 1])
        self._seek_t += dt
        arrived = ~self._hov & ((dist < _REACH) | (self._seek_t > _TIMEOUT))
        if arrived.any():
            i = np.flatnonzero(arrived)
            self._hov[i] = True
            self._hover_left[i] = self._hover_dur[i, self._k[i] % _K]
        self._hover_left[self._hov] -= dt
        done = self._hov & (self._hover_left <= 0)
        if done.any():
            i = np.flatnonzero(done)
            self._k[i] += 1
            self._hov[i] = False
            self._seek_t[i] = 0.0
            self._target[i] = self._pick(i)
            d[i] = self._target[i] - pos[i]
            dist[i] = np.hypot(d[i, 0], d[i, 1])

        w = self._wob
        wobble = w[0] * np.sin(w[1] * t + w[2]) + w[3] * np.sin(w[4] * t + w[5])
        phi = np.arctan2(d[:, 1], d[:, 0]) + wobble * np.where(self._hov, 2.0, 1.0)
        swell = np.clip(0.85 + 0.45 * np.sin(self._swell[0] * t + self._swell[1]), 0.35, 1.15)
        swell[self._k == 0] = 1.0   # lift off steadily
        want = np.where(self._hov, self._hover_speed,
                        self._cruise * swell * np.clip(dist / self._slow_r, 0.2, 1.0))
        turn = (phi - self._th + np.pi) % (2 * np.pi) - np.pi
        lim = self._turn * dt
        self._th += np.clip(turn * (1.0 - np.exp(-3.0 * dt)), -lim, lim)
        lim = self._acc * dt
        self._sp += np.clip(want - self._sp, -lim, lim)

        vel = self._vel
        vel[:, 0] = self._sp * np.cos(self._th)
        vel[:, 1] = self._sp * np.sin(self._th)
        if wind is not None:
            vel[:, 0] += np.clip(np.asarray(wind(pos[:, 0], t), float), -1.0, 1.0) * self._wind_px
        pos += vel * dt
        np.clip(pos, _M, SIZE - 1 - _M, out=pos)

        if self._released is not None and not self._released.all():
            i = np.flatnonzero(~self._released)   # still waiting: back on the perch, ready to lift off
            pos[i], vel[i] = self._perch[i], 0.0
            self._th[i], self._sp[i] = self._th0[i], self._sp0[i]
            self._k[i], self._hov[i], self._seek_t[i] = 0, False, 0.0

    def pulse(self, t):
        """Brightness 0..1 of each firefly at time t (t may be an array of shape (T, 1) -> (T, count))."""
        j = self._jit
        u = (t / self._period + self._phase + j[0] * np.sin(j[1] * t + j[2])) % 1.0
        s = u * self._period                      # seconds since this cycle's flash began
        flash = self._blink(s) + self._echo * self._blink(s - self._gap)
        soft = (0.5 - 0.5 * np.cos(2 * np.pi * u)) ** 1.5
        v = self._vary
        peak = self._peak * (1.0 - v[0] * (0.5 + 0.5 * np.sin(v[1] * t + v[2])))   # no two flashes alike
        return self._base + (peak - self._base) * np.where(self._glow, soft, np.minimum(flash, 1.0))

    def _blink(self, s):
        """One flash, s seconds after it starts: a quick smooth rise, then an exponential fade."""
        x = np.clip(s / self._rise, 0.0, 1.0)
        return x * x * (3.0 - 2.0 * x) * np.exp(-np.maximum(s - self._rise, 0.0) / self._decay)

    def _bright(self, t, arrival):
        """(1 + trail points, count) brightness now and at each trail point's moment, computed once per
        frame for all layers and lights(). Each firefly fades in as it lifts off, glowing up once before
        it settles into its own rhythm."""
        if self._memo_key != (t, arrival):
            self._release(arrival)
            x = (arrival - self._thresh) / _WAKE
            wake = 0.65 * np.sin(np.pi * np.clip(x, 0.0, 1.0)) ** 2
            fade = np.clip(x * (_WAKE / _FADE), 0.0, 1.0)
            self._memo = np.maximum(self.pulse(t - _BACK), wake) ** 0.7 * fade   # ** 0.7 lifts the dim states
            self._memo_key = (t, arrival)
        return self._memo

    def lights(self, t, arrival=1.0):
        """(x, y, strength) float arrays for the fireflies visible now (canvas px; strength 0..1 is the
        current brightness, larger for nearer bands), for the scene's wide bloom halo. Bokeh not included."""
        b = self._bright(t, arrival)[0]
        i = np.flatnonzero(b > _LIT)
        return self._pos[i, 0].copy(), self._pos[i, 1].copy(), b[i] * _LIGHT_GAIN[self._band[i]]

    def render(self, canvas, t, arrival=1.0, layer=None):
        """Add light into canvas ((640, 640, 3) float, in place). arrival 0..1 brings them in one by one,
        rising out of the grass. layer: None everything; "far" the far band (the scene draws it behind
        the grass and the flower); "near" the mid and near bands; "bokeh" the out-of-focus foreground."""
        if layer not in _LAYERS:
            raise ValueError(f"layer must be None, 'far', 'near' or 'bokeh', not {layer!r}")
        lv = self._bright(t, arrival)
        if layer in (None, "bokeh"):
            self._render_bokeh(canvas, t, arrival)
            if layer:
                return
        b = lv[0] * (1.0 + 0.06 * np.sin(self._wing[0] * t + self._wing[1]))   # wing flicker
        p = self._pos
        xi, yi = np.floor(p[:, 0]).astype(np.intp), np.floor(p[:, 1]).astype(np.intp)
        fx = ((p[:, 0] - xi) * _SUB).astype(np.intp)
        fy = ((p[:, 1] - yi) * _SUB).astype(np.intp)
        drawn = []
        for band in _LAYERS[layer]:
            i = self._members[band]
            i = i[lv[0, i] > _LIT]
            if i.size == 0:
                continue
            drawn.append(i)
            r, w = _RAD[band], 2 * _RAD[band] + 1
            imgs = self._glow_st[band][self._var[i], fy[i], fx[i]]
            imgs *= b[i].astype(np.float32)[:, None, None, None]
            for img, y, x in zip(imgs, (yi[i] - r).tolist(), (xi[i] - r).tolist()):
                canvas[y:y + w, x:x + w] += img
            hot = np.clip((b[i] - 0.62) / 0.38, 0.0, 1.0) ** 2 * _HOT_GAIN[band]
            for h, j in zip(hot.tolist(), i.tolist()):
                if h > 0.0:
                    canvas[yi[j] - 3:yi[j] + 4, xi[j] - 3:xi[j] + 4] += self._hot_st[fy[j], fx[j]] * np.float32(h)
        if drawn:
            self._render_trail(canvas, lv[1:], np.concatenate(drawn))

    def _render_trail(self, canvas, lv, i):
        """Fading points back along the motion, each with the light the firefly had then (lv: trail
        brightness), splatted bilinearly. Hovering fireflies leave none."""
        b = lv[:, i] * (1.0 - _TRAIL[:, None] / (_TRAIL.size + 1.0)) ** 2   # (trail, m)
        v = self._vel[i]
        b *= np.clip(np.hypot(v[:, 0], v[:, 1]) / 8.0, 0.0, 1.0)
        tp = (self._pos[i][None] - v[None] * _BACK[1:, :, None]).reshape(-1, 2)
        np.clip(tp, 0, SIZE - 2, out=tp)
        rgb = (b[..., None] * self._trail_rgb[i][None]).reshape(-1, 3)
        ti = np.floor(tp).astype(np.intp)
        f = tp - ti
        for dy in (0, 1):
            for dx in (0, 1):
                wgt = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1])
                np.add.at(canvas, (ti[:, 1] + dy, ti[:, 0] + dx), (rgb * wgt[:, None]).astype(canvas.dtype))

    def _bokeh(self, t, arrival):
        """Bokeh centres (nb, 2) and brightness (nb,) at time t; dimmed near the flower head."""
        q = self._bk_path
        R = self._bk_R
        x = SIZE / 2 + (SIZE / 2 - R - 1) * (0.72 * np.sin(q[0] * t + q[2]) + 0.28 * np.sin(q[1] * t + q[3]))
        y = 290.0 + (290.0 - R - 1) * (0.72 * np.sin(q[4] * t + q[6]) + 0.28 * np.sin(q[5] * t + q[7]))   # mostly sky
        hx, hy = self._attract if self._attract is not None else (320.0, 250.0)
        dist = np.hypot(x - hx, y - hy)
        clear = 0.25 + 0.75 * np.clip((dist - 100.0) / 110.0, 0.0, 1.0)
        k = self._bk_beat
        beat = 0.6 + 0.4 * (0.5 - 0.5 * np.cos(k[0] * t + k[1])) ** 1.3
        fade = np.clip((arrival - self._bk_thresh) / _BK_FADE, 0.0, 1.0)
        return np.stack([x, y], -1), _BK_GAIN * k[2] * beat * clear * fade

    def _render_bokeh(self, canvas, t, arrival):
        pos, g = self._bokeh(t, arrival)
        for st, R, (x, y), gain in zip(self._bk_st, self._bk_R.tolist(), pos.tolist(), g.tolist()):
            if gain <= _LIT:
                continue
            xi, yi = int(x), int(y)
            fx, fy = int((x - xi) * _SUB), int((y - yi) * _SUB)
            canvas[yi - R:yi + R + 1, xi - R:xi + R + 1] += st[fy, fx] * np.float32(gain)
