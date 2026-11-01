"""Night meadow (SPEC 10.2): baked pointillist soil, grass blades, and the wind field shared with the flower
and fireflies.

Canvas contract: float32 (640, 640, 3) arrays indexed [y, x], RGB about 0..1, clipped later by the scene.
Draw order: sky -> render_back (soil + grass) -> flower -> render_front (near blades) -> fireflies -> glow.
"""
import math

import numpy as np

SIZE = 640
GROUND_Y = 500            # soil surface under the flower root (320, 500)
SOIL_TOP = 486            # first row of the baked soil band (crumbs sit a little above the surface)
SOIL_DEPTH = 150.0        # depth over which the soil darkens
EDGE = 170.0              # soil and grass fade out over this many px at x = 0 and x = 640
GAP = 11.0                # no back blades this close to the stem; shorter ones out to GAP_SOFT
GAP_SOFT = 50.0
GROW = 0.22               # emerge span over which one blade grows from nothing to full height
SPACING = 1.2             # px between samples along a blade
LIGHT_RADIUS = 175.0
TINT = np.array([0.42, 0.78, 1.0], np.float32)   # cool ocean cyan of the sea holly's bud and bloom light
SOIL_LIGHT, GRASS_LIGHT, GRASS_LIGHT_ADD = 1.1, 2.2, 0.06


def wind(x, t):
    """Lean in [-1, 1] (positive = rightwards) at logical x (0..640), time t seconds; x and t may be arrays.

    Two gust trains travel across the field, one rightwards and one leftwards, weighted by a slowly drifting
    direction, plus a short ripple; the overall strength drifts too. Incommensurate frequencies keep it from
    repeating, and the bound is 0.3 + 0.4 + 0.16 < 1 by construction, so no clipping is needed.
    """
    s = math.sin if isinstance(x, (int, float)) and isinstance(t, (int, float)) else np.sin   # scalars: ~20x faster
    d = 0.68 * s(0.041 * t + 1.0) + 0.32 * s(0.0157 * t + 4.0)                                # -1 left .. 1 right
    a = 0.6 + 0.2 * s(0.187 * t + 0.7) + 0.12 * s(0.067 * t + 2.9) + 0.08 * s(0.49 * t + 4.1)  # strength 0.2..1
    warp = 1.3 * s(0.0061 * x + 0.047 * t)                       # bends the gust fronts so they aren't straight
    gr = 0.5 + 0.5 * s(0.0145 * x - 1.7 * t + warp)
    gl = 0.5 + 0.5 * s(0.0109 * x + 1.31 * t + 2.0 - 0.8 * warp)
    rip = s(0.05 * x - 2.6 * t + 1.7 * s(0.019 * x + 0.31 * t))
    return a * (0.3 * d + 0.2 * ((1 + d) * gr * gr - (1 - d) * gl * gl) + 0.16 * rip)


def _ripple(x):
    return 1.2 * np.sin(0.043 * x) + 0.7 * np.sin(0.127 * x + 1.3)


def surface(x):
    """Soil surface y at logical x: a low crest under the flower that falls away toward the sides, with gentle
    ripples; surface(320) == GROUND_Y."""
    dx = np.abs(x - 320.0)
    return (GROUND_Y + 4.0 * (1.0 - np.exp(-(dx / 150.0) ** 2)) + 14.0 * _smooth((dx - 190.0) / 130.0)
            + _ripple(x) - _ripple(320.0))


def _smooth(e):
    e = np.clip(e, 0.0, 1.0)
    return e * e * (3.0 - 2.0 * e)


def _edge(x, depth=0.0):
    """Fade toward x = 0 and x = 640; deeper soil fades further in, so the band ends in rounded shoulders."""
    return _smooth((np.minimum(x, SIZE - x) - 0.45 * np.maximum(depth, 0.0)) / EDGE)


# --- soil, baked once --------------------------------------------------------------------------------------

_SOIL_PAL = np.array([
    (0.15, 0.115, 0.09), (0.21, 0.16, 0.12), (0.27, 0.21, 0.155), (0.33, 0.26, 0.19),
    (0.40, 0.32, 0.24), (0.26, 0.24, 0.21), (0.30, 0.20, 0.14)], np.float32)   # last two: grey, rust
_SOIL_P = np.array([0.16, 0.24, 0.22, 0.15, 0.07, 0.11, 0.05])

_R = 4
_OFF = np.array([(dx, dy) for dy in range(-_R, _R + 1) for dx in range(-_R, _R + 1)], np.int32)
_D2 = (_OFF ** 2).sum(1)


def _stamp(rgb, alpha, x, y, col, rad, a, soft=False):
    """Overwrite a disc of radius rad per dot into the band (later dots win); soft blends a rounded disc
    lit from the upper left instead (pebbles)."""
    m = _D2[None, :] <= (rad * rad)[:, None] + 0.01
    xs = np.rint(x).astype(np.int32)[:, None] + _OFF[None, :, 0]
    ys = np.rint(y).astype(np.int32)[:, None] + _OFF[None, :, 1] - SOIL_TOP
    m &= (xs >= 0) & (xs < rgb.shape[1]) & (ys >= 0) & (ys < rgb.shape[0])
    rows = np.nonzero(m)[0]
    ys, xs = ys[m], xs[m]
    if not soft:
        rgb[ys, xs] = col[rows] * a[rows, None]
        alpha[ys, xs] = a[rows]
        return
    r = np.sqrt(_D2)[None, :] / (rad[:, None] + 0.5)
    k = (np.clip(1.25 - r, 0, 1) * 0.8)[m] * a[rows]
    lit = (1.0 + 0.3 * (-_OFF[None, :, 0] - 1.3 * _OFF[None, :, 1]) / (2.2 * rad[:, None]))[m]
    rgb[ys, xs] = rgb[ys, xs] * (1 - k)[:, None] + col[rows] * (k * lit)[:, None]
    alpha[ys, xs] = alpha[ys, xs] * (1 - k) + k


def _bake_soil(rng, quality):
    """-> (premultiplied rgb, 1 - alpha) for rows SOIL_TOP..SIZE: dark earth under fine brown dots."""
    px = np.arange(SIZE) + 0.5
    depth = (np.arange(SOIL_TOP, SIZE) + 0.5)[:, None] - surface(px)[None, :]
    alpha = (_smooth((depth + 1.0) / 3.0) * _edge(px[None, :], depth) ** 1.6).astype(np.float32)
    dk = np.clip(depth / SOIL_DEPTH, 0.0, 1.0)[..., None]
    base = np.array([0.055, 0.042, 0.033], np.float32) * (1 - dk) + np.array([0.016, 0.013, 0.011]) * dk
    rgb = (base * alpha[..., None]).astype(np.float32)

    ph = rng.uniform(0, 2 * np.pi, 4)

    def clump(x, y):   # cheap low-frequency lumps, 0..1
        return 0.5 + 0.25 * (np.sin(0.061 * x + 0.083 * y + ph[0]) * np.sin(0.097 * y - 0.041 * x + ph[1])
                             + np.sin(0.023 * x + ph[2]) * np.sin(0.15 * y + 0.03 * x + ph[3]))

    n = int(80000 * quality)
    x = rng.uniform(-3, SIZE + 3, n)
    d = rng.random(n) ** 1.35 * (SOIL_DEPTH - 4) - 0.5
    crumb = rng.random(n) < 0.02
    d[crumb] = -rng.random(crumb.sum()) * 3.0            # a few crumbs above the line: an uneven surface
    y = surface(x) + d
    c = clump(x, y)
    e = _edge(x, d)
    keep = rng.random(n) < (0.45 + 0.55 * c) * e ** 0.7   # denser in the lumps, thinning toward the sides
    x, y, d, c, e = x[keep], y[keep], d[keep], c[keep], e[keep]
    n = len(x)
    dn = np.clip(d / SOIL_DEPTH, 0, 1)
    bright = (1 - 0.82 * dn) ** 1.6 * (0.5 + 0.35 * c + 0.3 * rng.random(n))
    col = _SOIL_PAL[rng.choice(len(_SOIL_PAL), n, p=_SOIL_P)] * (bright * (1 + 0.12 * rng.standard_normal(n)))[:, None]
    rad = rng.choice(np.array([0.5, 1.0, 1.5]), n, p=[0.6, 0.32, 0.08])
    order = np.argsort(-d)                                 # deep first, so surface dots sit on top
    _stamp(rgb, alpha, x[order], y[order], col[order], rad[order], e[order] ** 0.8)

    m = int(160 * quality)                                 # pebbles: soft, lighter grey-brown discs
    x = rng.uniform(0, SIZE, m)
    d = rng.random(m) ** 1.3 * 120 + 2.0
    rad = rng.uniform(1.2, 2.8, m)
    tone = np.array([0.43, 0.38, 0.32], np.float32) * (0.6 + 0.4 * rng.random(m))[:, None]
    tone *= ((1 - 0.8 * d / SOIL_DEPTH) ** 1.5)[:, None] * (1 + 0.08 * rng.standard_normal((m, 3)))
    _stamp(rgb, alpha, x, surface(x) + d, tone.astype(np.float32), rad, _edge(x, d), soft=True)
    return rgb, np.repeat((1.0 - alpha)[..., None], 3, axis=2)    # full shape: no broadcast in the frame loop


# --- grass ---------------------------------------------------------------------------------------------------

# (base colour, tip colour, weight): muted night greens and teals, some blue-violet tips to answer the flower
_FAMILIES = [
    ((0.030, 0.068, 0.046), (0.14, 0.27, 0.17), 0.34),
    ((0.024, 0.062, 0.066), (0.10, 0.25, 0.25), 0.22),
    ((0.048, 0.062, 0.042), (0.20, 0.26, 0.18), 0.14),
    ((0.024, 0.048, 0.066), (0.11, 0.18, 0.27), 0.12),
    ((0.030, 0.058, 0.054), (0.15, 0.17, 0.36), 0.18),
]


class _Blades:
    """A set of blades: per-blade parameters and flattened per-sample arrays, built once."""

    def __init__(self, rng, x, y0, length, lean, depth, width):
        n = len(x)
        self.x = x.astype(np.float32)
        self.length = length.astype(np.float32)
        self.lean = lean.astype(np.float32)
        self.curl = rng.normal(0, 0.3, n).astype(np.float32)                 # rest curvature (total turn, rad)
        stiff = rng.random(n)
        self.flex = ((0.45 + 0.6 * (1 - stiff)) * np.clip(length / 38.0, 0.45, 1.5)).astype(np.float32)
        self.lag = (0.06 + 0.4 * (1 - stiff) + 0.12 * rng.random(n)).astype(np.float32)  # spring-like lag (s)
        self.fw = rng.uniform(2 * np.pi * 0.55, 2 * np.pi * 1.6, n).astype(np.float32)
        self.fph = rng.uniform(0, 2 * np.pi, n).astype(np.float32)
        self.famp = rng.uniform(0.025, 0.07, n).astype(np.float32)
        # emergence: random, short and far-back blades a little earlier
        self.th = ((1 - GROW) * np.clip(0.75 * rng.random(n) + 0.25 * length / max(length.max(), 1)
                                        - 0.1 * (1 - depth), 0, 1)).astype(np.float32)
        self.alpha = (_edge(x) ** 0.6).astype(np.float32)

        fam = rng.choice(len(_FAMILIES), n, p=[f[2] for f in _FAMILIES])
        base = np.array([f[0] for f in _FAMILIES], np.float32)[fam]
        tip = np.array([f[1] for f in _FAMILIES], np.float32)[fam]
        bright = ((0.85 + 0.6 * rng.random(n)) * (0.62 + 0.45 * depth) * (0.35 + 0.65 * _edge(x)))[:, None]

        cnt = np.ceil(length / SPACING).astype(np.int64) + 2
        bi = np.repeat(np.arange(n), cnt)
        start = np.concatenate([[0], np.cumsum(cnt)[:-1]])
        u = (np.arange(len(bi)) - start[bi]) / (cnt[bi] - 1.0)
        # region a bent blade can reach; samples are kept relative to its corner (x0, top)
        reach = length.max() + 3
        self.top = max(0, int(y0.min() - reach - 3))
        self.rows = min(SIZE, int(np.ceil(y0.max() + 2))) - self.top
        self.x0 = max(0, int(x.min() - reach))
        self.w = min(SIZE, int(np.ceil(x.max() + reach))) - self.x0
        self.xr, self.yr = (x - self.x0).astype(np.float32), (y0 - self.top).astype(np.float32)
        self.bi = bi
        self.c1 = (2 * u * (1 - u)).astype(np.float32)                         # quadratic Bezier weights
        self.c2 = (u * u).astype(np.float32)
        self.c0x = ((1 - u) ** 2 * self.xr[bi]).astype(np.float32)
        self.c0y = ((1 - u) ** 2 * self.yr[bi]).astype(np.float32)
        self.wt = ((width[bi] * (1 - u) ** 0.85 + 0.2) * SPACING / 0.8).astype(np.float32)
        grain = 1 + 0.1 * rng.standard_normal(len(bi))
        self.col = np.ascontiguousarray(((base[bi] + (tip - base)[bi] * (u ** 1.3)[:, None])
                                         * (bright[bi] * grain[:, None])).T.astype(np.float32))   # (3, samples)

        self.col_lit = GRASS_LIGHT * self.col + GRASS_LIGHT_ADD
        self.wt_full = self.wt * self.alpha[bi]
        self.pb = np.empty((4, n), np.float32)
        npx = self.rows * self.w
        self.taps = np.array([0, 1, self.w, self.w + 1], np.int64)[:, None]
        self.buf = np.zeros((4, npx), np.float32)          # coverage, then premultiplied r, g, b
        self.ra, self.rk = np.empty(npx, np.float32), np.empty(npx, np.float32)
        self.w4 = np.empty((4, len(bi)), np.float32)       # per-frame scratch, reused: no big temporaries
        self.tmp = np.empty((4, len(bi)), np.float32)
        self.idx4 = np.empty((4, len(bi)), np.int64)

    def draw(self, canvas, t, emerge, light):
        if emerge >= 1.0:
            g, wgt = 1.0, self.wt_full
        else:
            g = _smooth((emerge - self.th) / GROW)
            if not g.any():
                return
            wgt = self.wt * (self.alpha * g)[self.bi]               # weight ~ sample spacing ~ g
        w = wind(self.x, t - self.lag)
        turn = self.curl + self.flex * w + self.famp * np.sin(self.fw * t + self.fph) * (0.4 + np.abs(w))
        turn = np.clip(turn, -1.6, 1.6)
        lean = np.clip(self.lean + 0.3 * self.flex * w, -0.6, 0.6)     # so a tip never dips below its root
        half = 0.5 * turn
        chord = self.length * g * np.sinc(half / np.pi)              # circular arc of the blade's length
        mid = lean + half
        h = chord / (2.0 * np.cos(half))                             # tangent intersection = Bezier control
        pb = self.pb                                                 # per blade: control and tip points
        pb[0] = self.xr + h * np.sin(lean)
        pb[1] = self.xr + chord * np.sin(mid)
        pb[2] = self.yr - h * np.cos(lean)
        pb[3] = self.yr - chord * np.cos(mid)
        bi = self.bi
        lit = light is not None and light[2] > 0
        if lit:                                                      # light per blade, at its middle
            lx, ly, s = light
            dx, dy = (pb[0] + pb[1]) * 0.5 - (lx - self.x0), (pb[2] + pb[3]) * 0.5 - (ly - self.top)
            f = np.clip(1.0 - (dx * dx + dy * dy) * (1.0 / LIGHT_RADIUS ** 2), 0.0, None)
            fs = (f * f * s)[bi]
        X = self.c0x + self.c1 * pb[0][bi] + self.c2 * pb[1][bi]
        Y = self.c0y + self.c1 * pb[2][bi] + self.c2 * pb[3][bi]

        # bilinear splat; off-canvas x only happens for edge blades, which are faded to nothing
        np.clip(X, 0, self.w - 1.001, out=X)
        np.clip(Y, 0, self.rows - 1.001, out=Y)
        fx0, fy0 = np.floor(X), np.floor(Y)
        fx, fy = X - fx0, Y - fy0
        fx1 = 1.0 - fx
        np.add((fy0 * self.w + fx0).astype(np.int64), self.taps, out=self.idx4)
        idx = self.idx4.ravel()
        wy0, wy1 = wgt * (1.0 - fy), wgt * fy
        w4, tmp, buf = self.w4, self.tmp, self.buf
        np.multiply(wy0, fx1, out=w4[0])
        np.multiply(wy0, fx, out=w4[1])
        np.multiply(wy1, fx1, out=w4[2])
        np.multiply(wy1, fx, out=w4[3])
        buf.fill(0.0)
        np.add.at(buf[0], idx, w4.ravel())
        for c in range(3):
            cc = self.col[c]
            if lit:                                                  # col * (1 + gain * tint) + add * tint
                cc = cc + (TINT[c] * fs) * self.col_lit[c]
            np.multiply(w4, cc, out=tmp)
            np.add.at(buf[1 + c], idx, tmp.ravel())

        # coverage-weighted "over", order-independent: canvas * (1 - a) + mean colour * a, a = min(coverage, 1)
        acc, a, k = buf[0], self.ra, self.rk
        np.minimum(acc, 1.0, out=a)
        np.maximum(acc, 1e-12, out=k)
        np.divide(a, k, out=k)
        np.subtract(1.0, a, out=a)
        shape = (self.rows, self.w)
        a, k = a.reshape(shape), k.reshape(shape)
        for c in range(3):
            v = canvas[self.top:self.top + self.rows, self.x0:self.x0 + self.w, c]
            v *= a
            p = buf[1 + c].reshape(shape)
            p *= k
            v += p


def _back_blades(rng, quality):
    """Tufts of 1-5 blades fanned out, across the width, thinning toward the edges, with a gap at the stem."""
    nt = int(165 * quality)
    tx = rng.uniform(2, SIZE - 2, nt * 3)
    tx = tx[(rng.random(len(tx)) < _edge(tx) ** 0.6) & (np.abs(tx - 320) > GAP + 2)][:nt]
    k = rng.integers(1, 6, len(tx))
    tid = np.repeat(np.arange(len(tx)), k)
    i = np.arange(len(tid)) - np.repeat(np.cumsum(k) - k, k)
    x = tx[tid] + rng.normal(0, 2.0, len(tid))
    side = np.where(x < 320, -1.0, 1.0)
    x = np.where(np.abs(x - 320) < GAP, 320 + side * (GAP + rng.random(len(x)) * 4), x)
    lean = (i - (k[tid] - 1) / 2) * 0.17 + rng.normal(0, 0.07, len(x))
    depth = np.clip(rng.random(len(tx))[tid] + rng.normal(0, 0.08, len(x)), 0, 1)   # 0 back .. 1 near
    y0 = surface(x) + 0.5 + 6.0 * depth
    length = (14 + 40 * rng.random(len(x)) ** 1.4) * (0.78 + 0.32 * depth) * (0.55 + 0.45 * _edge(x))
    length = np.minimum(length * np.where(rng.random(len(x)) < 0.05, 1.3, 1.0), 62.0)
    length *= 0.3 + 0.7 * _smooth((np.abs(x - 320) - GAP) / (GAP_SOFT - GAP))       # keep the stem readable
    width = rng.uniform(1.15, 2.1, len(x)) * (0.85 + 0.3 * depth)
    order = np.argsort(depth)
    return _Blades(rng, x[order], y0[order], length[order], lean[order], depth[order], width[order])


def _front_blades(rng, quality):
    """A few short near blades either side of the stem base, leaning outward so the stem stays clear."""
    n = max(6, int(12 * quality))
    side = np.where(np.arange(n) % 2 == 0, -1.0, 1.0)
    x = 320 + side * rng.uniform(5, 32, n)
    y0 = surface(x) + rng.uniform(5, 10, n)
    length = rng.uniform(8, 19, n) * (0.6 + 0.4 * np.clip(np.abs(x - 320) / 20, 0, 1))
    lean = side * rng.uniform(0.08, 0.45, n)
    return _Blades(rng, x, y0, length, lean, np.ones(n), rng.uniform(1.4, 2.2, n))


class Meadow:
    def __init__(self, seed=3, quality=1.0):
        rng = np.random.default_rng(seed)
        self.soil_rgb, self.soil_keep = _bake_soil(rng, quality)
        self.soil_lit = self.soil_rgb * (SOIL_LIGHT * TINT)
        self.kr = r = int(0.85 * LIGHT_RADIUS)          # the cubed falloff is negligible beyond this
        d2 = ((np.arange(-r, r + 1, dtype=np.float32) / LIGHT_RADIUS) ** 2)
        k = np.clip(1.0 - d2[:, None] - d2[None, :], 0.0, None) ** 3
        self.kernel = np.repeat(k[..., None], 3, axis=2)     # full shape: no broadcast in the frame loop
        self.back = _back_blades(rng, quality)
        self.front = _front_blades(rng, quality)

    def render_back(self, canvas, t, emerge, light=None):
        """Soil and most of the grass, in place. emerge 0..1 grows the grass; light is None or (x, y, 0..1)."""
        band = canvas[SOIL_TOP:]
        np.multiply(band, self.soil_keep, out=band)
        band += self.soil_rgb
        if light is not None and light[2] > 0:
            self._light_soil(canvas, *light)
        if emerge > 0:
            self.back.draw(canvas, t, emerge, light)

    def render_front(self, canvas, t, emerge, light=None):
        """The few near blades in front of the stem base, in place."""
        if emerge > 0:
            self.front.draw(canvas, t, emerge, light)

    def _light_soil(self, canvas, lx, ly, s):
        """Add the tinted, lit soil around (lx, ly): slices of a precomputed falloff, no per-pixel maths."""
        r = self.kr
        cx, cy = int(round(lx)), int(round(ly))
        x0, x1 = max(0, cx - r), min(SIZE, cx + r + 1)
        y0, y1 = max(SOIL_TOP, cy - r), min(SIZE, cy + r + 1)
        if x0 >= x1 or y0 >= y1:
            return
        k = self.kernel[y0 - cy + r:y1 - cy + r, x0 - cx + r:x1 - cx + r] * s
        k *= self.soil_lit[y0 - SOIL_TOP:y1 - SOIL_TOP, x0:x1]
        canvas[y0:y1, x0:x1] += k
