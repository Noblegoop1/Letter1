"""Night sky for the night scene: the dark gradient, twinkling stars, a slowly rising moon, a violet
horizon glow and drifting moonlit clouds, drawn into the scene's 640 x 640 float canvas (display RGB).

Everything heavy is built once in Sky(): cloud density and shading textures (spectral noise that tiles
horizontally, so drifting is a slice), the moon sprite, the star list. A frame is a handful of array ops
on reused buffers. Clouds live only in rows [0, BAND); the horizon glow only below. Stars, clouds, glow
and the moon's halo fade out toward x = 0 and x = 639, so the edge columns are always exactly the plain
gradient (base_column()) that the scene's side bars continue. Pure NumPy; the scene owns the canvas.

Moon at 1 and clouds at 1 is the resting state; the scene ramps both in from the bloom. Clouds stay
dim (well under the scene's 0.42 glow threshold); only the moon and the cloud edges right by it bloom.
"""
import math

import numpy as np

from letter.engine.timeline import clamp, ease_out, smoothstep

S = 640
TOP = np.array((4, 5, 12), np.float32) / 255     # the scene's original gradient, kept as the base
LOW = np.array((16, 22, 44), np.float32) / 255
EDGE = 56.0                  # px over which everything but the gradient fades out at the side edges
BAND = 368                   # cloud rows; the clouds thin to nothing above this, the glow lives below

MOON_X, MOON_Y, MOON_R = 550, 82, 28       # final centre and radius: clear of the flower's head and bracts
RISE = 36.0                  # px the moon rises while it appears
HBOX = 84                    # moon sprite half-size (disc plus halo)
MOON_HI = np.array((0.80, 0.82, 0.86), np.float32)    # highlands: cool pale white (the glow pass adds more)
MOON_MARE = np.array((0.52, 0.56, 0.68), np.float32)  # maria: blue-grey
HALO = np.array((0.55, 0.64, 0.95), np.float32)

GLOW = np.array((0.13, 0.05, 0.20), np.float32)       # violet horizon glow at full moon (added)
GLOW_HI = np.array((0.05, 0.04, 0.14), np.float32)    # its colour higher up: bluer

CLOUD = np.array((0.62, 0.72, 1.00), np.float32)      # colour of light on the clouds (silver-blue)
AMB = (0.06, 0.20)           # light on the clouds away from the moon, without / with it
KF, RIMK, CORONA = 0.32, 0.28, 0.3       # moonlight on cloud bodies near the moon; silver rim brightness
RIM_W = 0.4                  # rims light the part of an edge where opacity is below this
MOON_SHOW = 0.3              # clouds over the moon are at most this much thinner, so it shows through
SUB = 4                      # sub-pixel phases of the main layer, so its edges glide instead of stepping
PERIOD, SPEED = 1024, 4.5    # cloud tile width (px, it repeats every 3.8 min) and drift (px/s)
ANISO, BETA = 1.9, 2.9       # noise stretch (wider than tall) and spectral slope (higher: smoother)
K, AMAX, COVER = 1.8, 0.86, 0.6   # opacity per unit density, max opacity, cover of the upper sky at clouds = 1
SLICES = 4                   # the cloud band is refreshed a quarter per frame (see _clouds)


def _edge(x, width=EDGE):
    """0 at the side edge columns, 1 from `width` px in."""
    d = np.clip(np.minimum(x, S - 1 - x) / width, 0.0, 1.0)
    return d * d * (3 - 2 * d)


def _spectral(rng, h, w, beta, aniso):
    """Noise (h, w) with unit std that tiles horizontally, stretched horizontally by aniso, and its
    smoothed slope toward the moon (up and a little right): the side of a cloud facing the light."""
    rows, h = h, 1 << (h - 1).bit_length()   # FFT at a power-of-two height (fast), then keep `rows`
    ky = np.fft.fftfreq(h).astype(np.float32)[:, None]
    kx = np.fft.rfftfreq(w).astype(np.float32)[None, :]
    k = np.sqrt((kx * aniso) ** 2 + ky ** 2)
    k0 = 1.0 / 240   # longer waves are damped, so the cloud amount stays even across the tile
    amp = np.maximum(k, k0) ** (-beta / 2) * np.minimum(k / k0, 1) ** 2 * np.exp(-(k / 0.16) ** 2)
    amp[0, 0] = 0.0
    spec = np.fft.rfft2(rng.standard_normal((h, w), np.float32)) * amp
    d = np.fft.irfft2(spec, s=(h, w))[:rows]
    d = (d / d.std()).astype(np.float32)
    ux, uy = 0.3 / 1.0466, -1.0 / 1.0466
    slope = np.fft.irfft2(spec * (-2j * np.pi) * (kx * ux + ky * uy) * np.exp(-(k / 0.05) ** 2), s=(h, w))[:rows]
    return d, (slope / slope.std()).astype(np.float32)


def _wrap(a):
    """Append the first S columns, so any S wide slice of the tile is one plain slice."""
    return np.ascontiguousarray(np.concatenate([a, a[:, :S]], axis=1))


class Sky:
    def __init__(self, seed=11, quality=1.0):
        rng = np.random.default_rng(seed)
        f32 = np.float32
        y = np.linspace(0, 1, S, dtype=f32)
        self._col = TOP + (LOW - TOP) * y[:, None] ** 1.6          # same values as the old night._sky()
        self.base = np.ascontiguousarray(np.broadcast_to(self._col[:, None, :], (S, S, 3)), dtype=f32)
        self._grad = [np.ascontiguousarray(self._col[:BAND, c:c + 1]) for c in range(3)]
        xs = np.arange(S, dtype=f32)
        edge = _edge(xs)

        # horizon glow under the band: from nothing at BAND, strongest around the island's top
        yy = np.arange(BAND, S, dtype=f32)
        ramp = np.clip((yy - BAND) / (490 - BAND), 0, 1)
        ramp = ramp * ramp * (3 - 2 * ramp) * (1 - 0.4 * np.clip((yy - 490) / (S - 490), 0, 1))
        hue = GLOW_HI + (GLOW - GLOW_HI) * np.clip((yy - BAND) / (500 - BAND), 0, 1)[:, None]
        wide = np.clip(np.minimum(xs, S - 1 - xs) / 150, 0, 1)
        gx = np.exp(-((xs - 320) / 220) ** 2) * wide * wide * (3 - 2 * wide)   # no box: gone well before the edges
        self._glow = np.ascontiguousarray(ramp[:, None, None] * hue[:, None, :] * gx[None, :, None], dtype=f32)
        self._low = np.empty_like(self._glow)
        self._low_key = None

        self._build_moon(rng, edge)
        self._build_stars(rng, quality, edge)
        self._build_clouds(rng, edge)

    # --- building -------------------------------------------------------------------------------
    def _build_moon(self, rng, edge):
        n = 2 * HBOX + 1
        d = np.arange(n, dtype=np.float32) - HBOX
        yy, xx = np.meshgrid(d, d, indexing="ij")
        r = np.hypot(xx, yy)
        out = np.maximum(r - MOON_R, 0)
        fade = np.clip(1 - (r / HBOX) ** 2, 0, 1) ** 2                 # nothing left at the box edge
        halo = 0.10 * np.exp(-out / 5.0) + 0.06 * np.exp(-out / 22.0) + 0.03 * np.exp(-out / 55.0)
        # a sparse stipple of faint dots around it, like the flower's dotted aura
        dots = (rng.random(r.shape) < 0.16 * np.exp(-out / 22.0)) * rng.uniform(0.05, 0.20, r.shape)
        halo = (halo + dots * (out > 3)) * fade * edge[MOON_X - HBOX:MOON_X + HBOX + 1][None, :]
        halo = halo[..., None] * HALO

        # the disc: limb darkening, maria, a fine stippled grain, a stippled rim instead of a hard edge
        u, v = xx / MOON_R, yy / MOON_R
        mu = np.sqrt(np.clip(1 - u * u - v * v, 0, 1))
        # maria roughly where the real ones are (Procellarum, Imbrium, Serenitatis, Tranquillitatis, ...),
        # with ragged edges from a few random waves, so they read as the moon and not as round blots
        maria = np.zeros_like(r)
        for cx, cy, sx, sy, w in ((-0.56, 0.02, 0.20, 0.34, 0.9), (-0.30, -0.42, 0.20, 0.17, 1.0),
                                  (0.17, -0.36, 0.13, 0.12, 1.0), (0.32, -0.06, 0.15, 0.17, 0.9),
                                  (0.68, -0.28, 0.07, 0.09, 1.0), (0.50, 0.20, 0.09, 0.12, 0.8),
                                  (-0.20, 0.40, 0.14, 0.10, 0.7), (-0.48, 0.44, 0.07, 0.07, 0.8)):
            maria += w * np.exp(-((u - cx) ** 2 / (2 * sx * sx) + (v - cy) ** 2 / (2 * sy * sy)))
        ang, fr, ph = rng.uniform(0, np.pi, 7), rng.uniform(5, 13, 7), rng.uniform(0, 2 * np.pi, 7)
        rag = sum(np.cos(f * (u * np.cos(a) + v * np.sin(a)) + p) for a, f, p in zip(ang, fr, ph)) / 7
        m = np.clip((maria + 0.5 * rag - 0.3) * 1.4, 0, 1)
        grain = np.where(rng.random(r.shape) < 0.08, 0.80, 1.0) * rng.uniform(0.93, 1.05, r.shape)
        light = (0.82 + 0.18 * mu ** 0.5) * grain
        disc = (MOON_HI * (1 - m[..., None]) + MOON_MARE * m[..., None]) * light[..., None]
        for cx, cy in ((-0.20, 0.64), (-0.30, -0.06), (0.08, 0.22)):   # a few bright young craters
            disc += 0.18 * np.exp(-((u - cx) ** 2 + (v - cy) ** 2) / (2 * 0.045 ** 2))[..., None]
        keep = np.clip((MOON_R + 0.6 - r) / 1.8, 0, 1)
        alpha = (rng.random(r.shape) < keep).astype(np.float32)
        alpha[r < MOON_R - 1.5] = 1.0
        a3 = alpha[..., None]
        self._spr = np.ascontiguousarray(disc * a3 + halo * (1 - a3), dtype=np.float32)
        self._mb = np.zeros((n + 1, n, 3), np.float32)     # the sprite spread over two rows, scaled
        self._mt = np.empty((n, n, 3), np.float32)
        self._mT = np.empty((n + 1, n, 3), np.float32)

    def _build_stars(self, rng, quality, edge):
        want = int(480 * quality)
        bokeh_n = int(round(6 * quality))
        occupied = np.zeros((S + 16, S + 16), bool)
        palette = np.array([(0.88, 0.92, 1.0), (0.70, 0.80, 1.0), (1.0, 0.88, 0.72)], np.float32)
        cand = rng.uniform((6, 3), (S - 6, S - 4), (want * 3, 2)).astype(int)
        u = rng.random(want * 3)
        pick = rng.choice(3, want * 3, p=(0.6, 0.27, 0.13))
        sig = rng.uniform(1.8, 2.6, want * 3)
        px, py, pid, pw, base, sx, sy = [], [], [], [], [], [], []
        disc = [(dx, dy) for dy in range(-6, 7) for dx in range(-6, 7) if dx * dx + dy * dy <= 36]
        for j in range(want * 3):
            if len(base) >= want:
                break
            x, y = cand[j]
            bokeh = len(base) < bokeh_n and y < 420
            b = bright = 0.10 + 0.62 * u[j] ** 5
            foot = [(0, 0, 1.0)]
            if bokeh:   # a soft out-of-focus glow round a small core, like the photo's few big stars
                b = 0.28 + 0.2 * u[j]
                s2 = 2 * sig[j] ** 2
                foot = [(dx, dy, (dx == dy == 0) * 0.8 + 0.22 * math.exp(-(dx * dx + dy * dy) / s2)) for dx, dy in disc]
            elif bright > 0.30:   # a tiny glint
                foot += [(1, 0, 0.32), (-1, 0, 0.32), (0, 1, 0.32), (0, -1, 0.32)]
                if bright > 0.45:
                    foot += [(2, 0, 0.1), (-2, 0, 0.1), (0, 2, 0.1), (0, -2, 0.1)]
            span = max(max(abs(dx), abs(dy)) for dx, dy, _ in foot) + 1
            box = occupied[y - span + 8:y + span + 9, x - span + 8:x + span + 9]
            if box.any():
                continue
            box[:] = True
            sid = len(base)
            base.append(b * edge[x] * (1.0 - 0.5 * smoothstep(320, 620, y)))   # fainter low and at the edges
            sx.append(x)
            sy.append(y)
            col = palette[0] if bokeh else palette[pick[j]]
            for dx, dy, w in foot:
                px.append(x + dx)
                py.append(y + dy)
                pid.append(sid)
                pw.append(col * w)
        n = len(base)
        self._sb = np.array(base, np.float32)
        self._stw = rng.uniform(0.2, 0.65, n).astype(np.float32)                    # twinkle depth
        self._sw = rng.uniform((0.6, 1.7), (2.4, 4.3), (n, 2)).astype(np.float32)   # two rates, rad/s
        self._sp = rng.uniform(0, 2 * np.pi, (n, 2)).astype(np.float32)
        dm = np.maximum(np.hypot(np.array(sx) - MOON_X, np.array(sy) - MOON_Y) - MOON_R, 0)
        self._sglare = np.clip(1.15 * np.exp(-dm / 60), 0, 1).astype(np.float32)   # washed out near the moon
        self._px, self._py = np.array(px, np.intp), np.array(py, np.intp)
        self._pid = np.array(pid, np.intp)
        self._pw = np.array(pw, np.float32)
        self._pin = np.nonzero(self._py < BAND)[0]

    def _build_clouds(self, rng, edge):
        f32 = np.float32
        ys = np.arange(BAND, dtype=f32)
        # denser high up, thinning toward the horizon, and certainly gone by the end of the band
        vb = -2.0 * np.clip((ys - 40) / (BAND - 40), 0, 1) ** 1.4 - 9 * np.clip((ys - BAND + 50) / 49, 0, 1) ** 2
        d, slope = _spectral(rng, BAND, PERIOD, BETA, ANISO)
        d += vb[:, None]
        # density thresholds for clouds 0..1: the cover of the upper half grows linearly
        self._thr = np.quantile(d[: BAND // 2: 3, ::3], 1.0 - np.linspace(0.0, COVER, 33)).astype(f32)
        self._thr[0] = d.max() + 1.0
        self._steps = np.linspace(0, 1, len(self._thr))
        dk = _wrap(d * K)
        step = dk[:, 1:] - dk[:, :-1]
        self._dk = [dk] + [np.ascontiguousarray(dk[:, :-1] + step * (q / SUB)) for q in range(1, SUB)]
        # lit tops facing the moon, darker undersides, the thickest cores a little darker
        shade = 0.70 + 0.42 * slope - 0.08 * np.clip(d - self._thr[-1], 0.0, 3.0)
        self._shade = _wrap(np.clip(shade, 0.25, 1.35).astype(f32))
        fade = _edge(np.arange(S, dtype=f32), 100.0)        # clouds fade over more px: they are big
        self._lift = ((1 - fade) * 1.5 * K).astype(f32)     # thinner toward the side edges...
        self._cap = (AMAX * fade).astype(f32)               # ...and gone at them
        self._row = np.empty(S, f32)
        # moonlight on the clouds (for the final moon position): a bright corona where they cross the
        # disc, a soft wide falloff around it
        yb, xb = np.mgrid[0:BAND, 0:S].astype(f32)
        dm = np.maximum(np.hypot(xb - MOON_X, yb - MOON_Y) - MOON_R, 0)
        self._F = (CORONA * np.exp(-dm / 10) + KF * (0.7 * np.exp(-dm / 45) + 0.3 * np.exp(-dm / 170))).astype(f32)
        # clouds crossing the moon are thinned a little (scaled, so their texture still shows over it)
        reach = MOON_R + 40
        self._show_box = (int(MOON_Y + RISE) + reach, MOON_X - reach, min(S, MOON_X + reach))
        sy1, sx0, sx1 = self._show_box
        self._show = np.ascontiguousarray(1 - MOON_SHOW * np.exp(-(dm[:sy1, sx0:sx1] / 30) ** 2), dtype=f32)
        # silver rims: where they can show
        g = np.exp(-dm / 30) * edge
        rows, cols = np.nonzero(g > 0.02)
        self._rim_box = (int(rows.max()) + 1, int(cols.min()))
        ry1, rx0 = self._rim_box
        self._G = np.ascontiguousarray(g[:ry1, rx0:] * RIMK * 4 / RIM_W ** 2, dtype=f32)
        self._a, self._T, self._L, self._lf, self._t1, self._t2 = (np.empty((BAND, S), f32) for _ in range(6))
        self._band = np.empty((BAND, S, 3), f32)     # the composited cloud band, refreshed in slices
        self._lf_key = self._last = None
        self._slice = 0

    # --- per frame ------------------------------------------------------------------------------
    def base_column(self):
        """(S, 3) float32: the plain gradient the side edges always show, for the scene's side bars."""
        return self._col.copy()

    @staticmethod
    def moon_pos(moon):
        """(x, y, radius) of the moon disc in canvas px for a moon amount 0..1."""
        return float(MOON_X), MOON_Y + RISE * (1 - ease_out(clamp(moon))), float(MOON_R)

    def render(self, canvas, t, dark=1.0, moon=0.0, clouds=0.0):
        """Overwrite canvas (S, S, 3) float32 with the sky at story time t."""
        c = canvas
        dark, moon, clouds = clamp(dark), clamp(moon), clamp(clouds)
        vis = smoothstep(0.0, 1.0, moon)
        lit = round(vis * 64) / 64   # glow and cloud light step in 1/64ths (under 1/255 each): far less work
        self._below(c[BAND:], dark, lit)
        T = None
        if clouds > 0:
            T = self._clouds(c, t, clouds, lit, dark)
        else:
            self._last = None
            np.multiply(self.base[:BAND], dark, out=c[:BAND])
        if vis > 0 and dark > 0:
            self._moon(c, moon, vis * dark, T)
        self._stars(c, t, dark, vis, T)
        return c

    def _below(self, low, dark, vis):
        """Rows below the band: the gradient plus the horizon glow (cached while dark and moon hold)."""
        key = (dark, vis)
        if key != self._low_key:
            np.multiply(self._glow, vis, out=self._low)
            np.add(self._low, self.base[BAND:], out=self._low)
            if dark < 1:
                np.multiply(self._low, dark, out=self._low)
            self._low_key = key
        np.copyto(low, self._low)

    def _clouds(self, c, t, clouds, vis, dark):
        """Clouds over the gradient in rows [0, BAND) of c; returns their transmission (for the moon and
        stars). They drift 0.08 px per frame and their texture moves in 1/4 px steps, so while time and
        the inputs move smoothly only a quarter of the band is recomputed each frame (the rest is at most
        three frames old, which cannot show); any jump redraws it all."""
        key = (t, clouds, vis, dark)
        last, self._last = self._last, key
        if last is None or abs(t - last[0]) > 0.25 or max(abs(x - y) for x, y in zip(key[1:], last[1:])) > 0.02:
            ranges = ((0, BAND),)
        else:
            self._slice = (self._slice + 1) % SLICES
            ranges = ((BAND * self._slice // SLICES, BAND * (self._slice + 1) // SLICES),)
        off = (t * SPEED) % PERIOD
        i = int(off)
        dk = self._dk[int((off - i) * SUB)]
        np.add(self._lift, np.interp(clouds, self._steps, self._thr) * K, out=self._row)
        if self._lf_key != vis:   # light on the clouds: ambient plus moonlight falling off from the moon
            np.multiply(self._F, vis, out=self._lf)
            np.add(self._lf, AMB[0] + (AMB[1] - AMB[0]) * vis, out=self._lf)
            self._lf_key = vis
        grad = [g * dark for g in self._grad] if dark < 1 else self._grad
        k = CLOUD * dark
        sy1, sx0, sx1 = self._show_box
        ry1, rx0 = self._rim_box
        for r0, r1 in ranges:
            a, T, L = self._a[r0:r1], self._T[r0:r1], self._L[r0:r1]
            t1, t2 = self._t1[r0:r1], self._t2[r0:r1]
            np.subtract(dk[r0:r1, i:i + S], self._row, out=a)
            np.maximum(a, 0.0, out=a)
            np.minimum(a, self._cap, out=a)   # (np.clip with an array bound is ~10x slower)
            if r0 < sy1:
                ab = a[:sy1 - r0, sx0:sx1]
                np.multiply(ab, self._show[r0:r1], out=ab)
            np.subtract(1.0, a, out=T)
            np.multiply(a, self._shade[r0:r1, i:i + S], out=L)
            np.multiply(L, self._lf[r0:r1], out=L)
            if vis > 0 and r0 < ry1:   # thin silver edges on the clouds near the moon
                n = min(r1, ry1) - r0
                ar, r = a[:n, rx0:], t1[:n, rx0:]
                np.subtract(RIM_W, ar, out=r)     # a(w - a): only the thin outer part of each edge
                np.maximum(r, 0.0, out=r)
                np.multiply(r, ar, out=r)
                np.multiply(r, self._G[r0:r0 + n], out=r)
                if vis < 1:
                    np.multiply(r, vis, out=r)
                np.add(L[:n, rx0:], r, out=L[:n, rx0:])
            for ch in range(3):   # per channel: broadcasting a mask over a trailing axis of 3 is ~10x slower
                np.multiply(T, grad[ch][r0:r1], out=t1)
                np.multiply(L, k[ch], out=t2)
                np.add(t1, t2, out=self._band[r0:r1, :, ch])
        np.copyto(c[:BAND], self._band)
        return self._T

    def _moon(self, c, moon, k, T):
        x, y, _ = self.moon_pos(moon)
        top = y - HBOX
        iy = math.floor(top)
        f = top - iy
        n = 2 * HBOX + 1
        if f > 1e-4:   # sub-pixel rise: spread over two rows
            mb = self._mb
            np.multiply(self._spr, (1 - f) * k, out=mb[:n])
            mb[n] = 0
            np.multiply(self._spr, f * k, out=self._mt)
            np.add(mb[1:], self._mt, out=mb[1:])
        elif k < 1:
            mb = self._mb[:n]
            np.multiply(self._spr, k, out=mb)
        else:
            mb = self._spr
        ix = MOON_X - HBOX
        y0, y1 = max(iy, 0), min(iy + len(mb), S)
        src = mb[y0 - iy:y1 - iy]
        dst = c[y0:y1, ix:ix + n]
        if T is not None:   # behind the clouds
            Tb = T[y0:y1, ix:ix + n]
            tb = self._mT[:y1 - y0]
            np.stack((Tb, Tb, Tb), axis=-1, out=tb)
            np.multiply(src, tb, out=tb)
            src = tb
        np.add(dst, src, out=dst)

    def _stars(self, c, t, dark, vis, T):
        s = np.sin(self._sw * t + self._sp)
        b = self._sb * (1 - self._stw * (0.5 + 0.25 * s[:, 0] + 0.25 * s[:, 1]))
        if vis > 0:
            b *= 1 - vis * self._sglare
        v = b[self._pid] * dark
        if T is not None:
            p = self._pin
            v[p] *= T[self._py[p], self._px[p]]
        c[self._py, self._px] += self._pw * v[:, None]
