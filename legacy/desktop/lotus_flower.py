"""SUPERSEDED 2026-10-31: the night flower became a sea holly (letter/art/flower.py). This is the
pointillist lotus it replaced, kept for reference only; nothing imports it.

Procedural pointillist flower for the night scene (SPEC 10.3-10.4).

A clean re-implementation of the techniques described in docs/flowers.md. The
iremcnar/Flowers reference has no licence, so none of its code is used here; only
the ideas (arc petals, layered noisy palettes, depth-ordered dot splats) carry over.

Every particle is generated once from one seeded RNG. A frame only evaluates
closed-form geometry for the animation state (grow, bloom, glow, bend, t) and splats
coloured dots into the shared canvas: float32 (640, 640, 3), indexed [y, x], display
RGB in 0..1 (the scene shows it as is), ground line at y = GROUND_Y. Palette colours
are written as hex and used directly.
"""
import math

import numpy as np

GROUND_Y = 500
ROOT = (320, 500)

_N = 640            # canvas side, px
STEM_LEN = 225.0    # root to head at full growth, px
PETAL_LEN = 138.0   # outer petal length at full bloom, px
RING_R = 1.27       # orbital ring radius, in petal lengths
BUD = 0.55          # size of the closed bud relative to the open head
HOOK = 2.75         # rad the stem tip turns over while the bud droops
BEND_TIP = 0.17     # rad the stem tip turns per unit of bend (wind plus pointer lean)
_M = 128            # stem centreline samples


def _rgb(*hexes):
    """Hex strings -> display RGB float32 colours in 0..1, shape (k, 3) (the canvas holds display values)."""
    c = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in hexes], np.float32)
    return c / 255


# The bloom wears the "sunrise glow" gradients the user chose: gold at the heart, through orange and
# coral, to pink tips. Stem, leaves and sepals are greens, so the warm head stands out in the night.
STEM_PAL = _rgb("1d5a44", "277250", "37905c", "56ac68")            # root -> head
STEM_ACCENT = _rgb("2c8c6a", "46ad86", "7ccb8c")
LEAF_PAL = _rgb("24704e", "33895c", "4ca068", "70b878", "9cd08a")   # midrib/base -> edge/tip
LEAF_RIB = _rgb("e9f8d6", "c9f0be")
LEAF_RIM = _rgb("c6f0ae", "def8c6", "a6e0b6")
PETAL_PALS = (                                                       # base -> tip, outer layer first
    _rgb("ff8a3a", "ff6045", "f4788a", "f0a0ac", "ffd6dc"),        # outer: orange -> coral -> pink tips
    _rgb("ffb42e", "ff9b3d", "ff7442", "ff5050"),                  # yellow -> orange -> coral
    _rgb("ffd23a", "fdc231", "f99a2c", "f37a2c"),                  # gold -> orange
    _rgb("ffe27a", "ffd100", "fbb514", "f7941d"),                  # inner: pale gold -> amber
    _rgb("2e7d52", "4a9a62", "76b874"),                             # sepals
)
PETAL_RIM = _rgb("ffd9b0", "ffdfe6", "ffc49a")
PETAL_HI = _rgb("fff4e2", "ffeaee")
GOLD = _rgb("ffd46c", "ffeaa6", "ffb658")
STAMEN_PAL = _rgb("fff6e6", "ffe9c6", "ffe08e", "ffbd55", "ff8a3e")  # base -> anther
CORE_PAL = _rgb("fff0d2", "ffd88a", "ffc04a", "ff9a3a")
HALO_IN, HALO_OUT = _rgb("ffa860", "e2507a")
RING = _rgb("ffc9a8", "ffb6c6")
NODE = _rgb("fff0e2")[0]
SPARK = _rgb("fff0c8", "ffb88a")

# Petal rings, outer first, then the sepals. Closed angle and curl satisfy curl = -2*angle
# for the petals, so their tips meet on the axis (a pointed bud). Columns: count, closed
# angle, open angle (rad from the axis), closed curl, open curl (rad turned along the
# petal), length, closed/open half-width (fraction of length), dots each, azimuth offset,
# start of the opening window (bloom value; each window lasts 0.5, plus per-petal jitter).
LAYERS = (
    (8, 0.66, 1.42, -1.32, -0.30, 1.00, 0.21, 0.40, 920, 0.00, 0.10),
    (6, 0.60, 0.72, -1.20, -0.20, 0.95, 0.20, 0.40, 700, 0.39, 0.20),
    (5, 0.54, 0.42, -1.08, -0.12, 0.80, 0.18, 0.36, 440, 0.17, 0.30),
    (4, 0.46, 0.20, -0.92, -0.05, 0.62, 0.16, 0.30, 280, 0.71, 0.40),
    (4, 0.50, 1.45, -0.55, 0.20, 0.46, 0.17, 0.18, 150, 0.20, 0.02),   # sepals: hug the bud, then fold back
)
# Leaves: stem position (fraction), side (+1 right), length px, angle above horizontal,
# curl (negative droops), grow value where it starts to unfurl.
LEAVES = (
    (0.10, +1, 120.0, 0.44, -0.75, 0.16),
    (0.13, -1, 112.0, 0.40, -0.70, 0.25),
    (0.47, +1, 84.0, 0.66, -0.75, 0.38),
    (0.42, -1, 72.0, 0.62, -0.70, 0.47),
)
LEAF_W = 0.26       # leaf half-width, in leaf lengths

# Splat stamps as flat-index offsets, padded to 5 by repeating the centre:
# 1 px, plus (5 px), 2x2 (4 px).
_STAMP = np.array([[0, 0, 0, 0, 0], [0, -1, 1, -_N, _N], [0, 1, _N, _N + 1, 0]], np.int32)
_BOX = np.array([dy * _N + dx for dy in (-1, 0, 1) for dx in (-1, 0, 1)], np.int32)
_RGB = np.dtype((np.void, 12))   # one float32 RGB pixel, scattered as a single item


def _ss(x, a, b):
    """Smoothstep from a to b; a float for scalar x, else an array."""
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    t = t * t * (3.0 - 2.0 * t)
    return float(t) if np.ndim(t) == 0 else t


def _sinc(x):
    """sin(x)/x for |x| <= 1 (Taylor, error < 3e-6): safe at 0 and division-free."""
    x2 = x * x
    return 1 + x2 * (-1 / 6 + x2 * (1 / 120 - x2 / 5040))


def _rows(a, idx):
    """a[idx] for a C-contiguous 2-D array, gathering each row as one opaque item (~4x faster)."""
    v = a.view(np.dtype((np.void, a.itemsize * a.shape[1]))).ravel()
    return np.take(v, idx).view(a.dtype).reshape(-1, a.shape[1])


def _petal_width(u):
    return np.sin(np.pi * np.clip(u, 0, 1) ** 0.72) ** 0.9     # pinched base, widest ~38%, pointed tip


def _leaf_width(u):
    return np.sin(np.pi * np.clip(u, 0, 1) ** 0.75) ** 0.9      # ovate, pointed tip


def _along(rng, n, width):
    """n positions in [0, 1] with density proportional to width(u), so dots are even per area."""
    g = np.linspace(0, 1, 257)
    w = width(g)
    cdf = np.concatenate(([0], np.cumsum((w[1:] + w[:-1]) * 0.5)))
    return np.interp(rng.random(n) * cdf[-1], cdf, g).astype(np.float32)


def _across(rng, n, rim):
    """Lateral position in [-1, 1]; a `rim` fraction is pushed to the edges for an outline."""
    v = rng.uniform(-1, 1, n)
    edge = rng.random(n) < rim
    v[edge] = np.sign(v[edge]) * rng.uniform(0.86, 1.0, edge.sum())
    return v.astype(np.float32), edge


def _pick(rng, pal, g, spread=0.5, jitter=0.07):
    """Noisy gradient lookup: each dot snaps to one palette entry (no blending), then a
    small brightness jitter. The stippled mix of neighbours is the pointillist texture."""
    g = np.asarray(g, np.float64)
    i = np.rint(np.clip(g, 0, 1) * (len(pal) - 1) + rng.normal(0, spread, g.shape))
    i = np.clip(i, 0, len(pal) - 1).astype(int)
    return (pal[i] * (1 + rng.normal(0, jitter, (g.size, 1)))).astype(np.float32)


def _stamps(rng, n, p):
    return _STAMP[rng.choice(3, n, p=p)]


def _prefixes(start, take):
    """Indices of the first take[i] items of each block starting at start[i], in block order."""
    return np.concatenate([np.arange(a, a + k) for a, k in zip(start.tolist(), take.tolist())])


def _splat(canvas, x, y, col, offs, add=False):
    """Stamp dots in array order (later dots overwrite earlier ones: painter's order), or
    add them (glow particles; a pixel hit twice in one call counts once)."""
    xi = (x + 0.5).astype(np.int32)
    yi = (y + 0.5).astype(np.int32)
    if len(xi) and (xi.min() < 1 or yi.min() < 1 or xi.max() > _N - 2 or yi.max() > _N - 2):
        keep = np.flatnonzero((xi >= 1) & (xi < _N - 1) & (yi >= 1) & (yi < _N - 1))
        xi, yi, col = xi[keep], yi[keep], _rows(col, keep)
        offs = _rows(offs, keep) if offs.ndim == 2 else offs
    idx = (yi * _N + xi)[:, None] + offs
    if add:
        canvas.reshape(-1, 3)[idx] += col[:, None, :]
    else:
        canvas.reshape(-1).view(_RGB)[idx] = np.ascontiguousarray(col, np.float32).view(_RGB)


class Flower:
    """The flower's particles, built once; `render` splats one animation state."""

    def __init__(self, seed=5, quality=1.0):
        rng = np.random.default_rng(seed)
        q = max(0.05, float(quality))

        def cnt(n):
            return max(16, int(round(n * q)))

        self._grid = np.linspace(0, STEM_LEN, _M).astype(np.float32)
        self._cache = {}                                        # part -> (state key, shapes); see _memo
        self._build_stem(rng, cnt(2500))
        self._build_leaves(rng, cnt(820))
        self._build_head(rng, cnt)
        self._build_aura(rng, cnt)
        self.counts = {
            "stem": len(self._st_s), "leaves": self._lf_uvw.shape[1], "petals": self._pt_uvw.shape[1],
            "stamens": len(self._sm_t), "core": len(self._co_x), "halo": len(self._ha_x),
            "rings": len(self._rg_a), "sparks": len(self._sp_a), "nodes": 6,
        }
        self.counts["total"] = sum(self.counts.values())

    # ---- build (once) -------------------------------------------------------------
    def _build_stem(self, rng, n):
        s = np.sort(rng.random(n)).astype(np.float32)          # sorted: the grown part is a prefix
        lat, rim = _across(rng, n, 0.18)
        col = _pick(rng, STEM_PAL, s * 0.8 + rng.random(n) * 0.2, 0.6)
        accent = rng.random(n) < 0.42 - 0.32 * s                # teal/blue flecks, densest near the root
        col[accent] = _pick(rng, STEM_ACCENT, rng.random(accent.sum()), 0.9)
        col *= (0.78 + 0.32 * (0.5 - 0.5 * lat))[:, None]       # lit from the left: reads as round
        col[rim] *= 1.15
        self._st_s, self._st_lat, self._st_col = s * STEM_LEN, lat, col
        self._st_offs = _stamps(rng, n, (0.25, 0.5, 0.25))

    def _build_leaves(self, rng, per_leaf):
        parts = []
        for _ in LEAVES:
            u = _along(rng, per_leaf, _leaf_width)
            v, rim = _across(rng, per_leaf, 0.12)
            rib = rng.random(per_leaf) < 0.08
            v[rib] = rng.normal(0, 0.03, rib.sum())
            # deep green along the midrib and base, fresh green toward the edges and tip
            col = _pick(rng, LEAF_PAL, 0.55 * u + 0.45 * np.abs(v) + rng.normal(0, 0.08, per_leaf), 0.55)
            col[rib] = _pick(rng, LEAF_RIB, rng.random(rib.sum()), 0.6) * 1.1
            edge = rim & (rng.random(per_leaf) < 0.6)
            col[edge] = _pick(rng, LEAF_RIM, rng.random(edge.sum()), 0.7)
            col *= (0.82 + 0.18 * v)[:, None]                    # one half of the blade lighter: a fold
            offs = _stamps(rng, per_leaf, (0.15, 0.6, 0.25))
            offs[rib] = _STAMP[1]
            parts.append((u, v, col, offs))                      # random order: any prefix is an even subset
        u, v, col, offs = (np.concatenate(p) for p in zip(*parts))
        self._lf_uvw = np.stack((u, v, _leaf_width(u).astype(np.float32)))
        self._lf_col, self._lf_offs = col, offs
        self._lf_start = np.arange(len(LEAVES)) * per_leaf
        self._lf_n = per_leaf
        L = np.array(LEAVES, np.float32)
        self._lf_s, self._lf_m, self._lf_len = L[:, 0] * STEM_LEN, L[:, 1], L[:, 2]
        self._lf_a0, self._lf_c, self._lf_t0 = L[:, 3], L[:, 4], L[:, 5]

    def _build_head(self, rng, cnt):
        layer = np.concatenate([np.full(row[0], i) for i, row in enumerate(LAYERS)])
        P = len(layer)
        tab = np.array(LAYERS, np.float32)[layer]               # each petal's copy of its layer row
        az = np.concatenate([2 * np.pi * np.arange(row[0]) / row[0] + row[9] for row in LAYERS])
        az = az + rng.normal(0, 0.09, P)
        self._p_ac, self._p_ao, self._p_kc, self._p_ko = tab[:, 1], tab[:, 2], tab[:, 3], tab[:, 4]
        self._p_len = tab[:, 5] * rng.uniform(0.92, 1.08, P).astype(np.float32)
        self._p_wc, self._p_wo = tab[:, 6], tab[:, 7]
        self._p_aj = rng.normal(0, 0.05, P).astype(np.float32)
        self._p_ws = tab[:, 10] + rng.uniform(0, 0.08, P).astype(np.float32)
        self._p_ct, self._p_st = np.cos(az).astype(np.float32), np.sin(az).astype(np.float32)
        self._p_outer = (layer == 0) | (layer == len(LAYERS) - 1)

        parts = []
        for p in range(P):
            d, petal = cnt(LAYERS[layer[p]][8]), layer[p] < len(LAYERS) - 1      # last layer: sepals
            u = _along(rng, d, _petal_width)
            v, _ = _across(rng, d, 0.14)
            col = _pick(rng, PETAL_PALS[layer[p]], u + rng.normal(0, 0.1, d), 0.5)
            r = rng.random(d)
            rim = (np.abs(v) > 0.86) & (r < 0.55)
            hi = (r > 0.96) & (layer[p] < 2)
            gold = (r > 0.96 - 0.025 * (1 + layer[p])) & (r <= 0.96) & (u < 0.55) & petal
            if petal:
                col[rim] = _pick(rng, PETAL_RIM, rng.random(rim.sum()), 0.8)
            col[hi] = _pick(rng, PETAL_HI, rng.random(hi.sum()), 0.6)
            col[gold] = _pick(rng, GOLD, rng.random(gold.sum()), 0.8) * 1.3
            offs = _stamps(rng, d, (0.1, 0.65, 0.25))
            offs[rim | hi] = _STAMP[1]
            parts.append((u, v, col, offs))                      # random order within a petal
        u, v, col, offs = (np.concatenate(x) for x in zip(*parts))
        self._pt_uvw = np.stack((u, v, _petal_width(u).astype(np.float32)))
        self._pt_col, self._pt_offs = col, offs
        self._pt_n = np.array([len(x[0]) for x in parts])
        self._pt_start = np.concatenate(([0], np.cumsum(self._pt_n)[:-1]))

        # stamens: filaments splaying from the centre, denser toward the anther tips
        n, nf = cnt(600), 60
        fid = rng.integers(0, nf, n)
        faz, ftilt, flen = rng.uniform(0, 2 * np.pi, nf), rng.uniform(0.25, 0.9, nf), rng.uniform(0.26, 0.48, nf)
        t = (1 - rng.random(n) ** 1.6).astype(np.float32)
        self._sm_t = t
        self._sm_ca, self._sm_sa = np.cos(faz[fid]).astype(np.float32), np.sin(faz[fid]).astype(np.float32)
        self._sm_tilt, self._sm_len = ftilt[fid].astype(np.float32), flen[fid].astype(np.float32)
        self._sm_col = _pick(rng, STAMEN_PAL, t, 0.35)
        self._sm_offs = np.where((t > 0.86)[:, None], _STAMP[1], _stamps(rng, n, (0.5, 0.3, 0.2)))

        # glowing core: a squashed ball of warm dots at the base of the inner petals
        n = cnt(350)
        a = rng.uniform(0, 2 * np.pi, n)
        r = np.sqrt(rng.random(n))
        self._co_x, self._co_z = (r * np.cos(a)).astype(np.float32), (r * np.sin(a)).astype(np.float32)
        self._co_h = rng.normal(0, 0.35, n).astype(np.float32)
        self._co_col = _pick(rng, CORE_PAL, r + rng.normal(0, 0.15, n), 0.6)
        self._co_offs = _stamps(rng, n, (0.2, 0.6, 0.2))

    def _build_aura(self, rng, cnt):
        n = cnt(1400)                                            # halo: dense in the middle
        a = rng.uniform(0, 2 * np.pi, n)
        r = np.minimum(np.abs(rng.normal(0, 0.55, n)), 1.6) / 1.6
        self._ha_x, self._ha_y = (r * np.cos(a)).astype(np.float32), (r * np.sin(a)).astype(np.float32)
        self._ha_b = ((1 - r) ** 1.5).astype(np.float32)
        self._ha_ph = rng.uniform(0, 2 * np.pi, n).astype(np.float32)
        self._ha_col = (HALO_IN + (HALO_OUT - HALO_IN) * r[:, None] ** 0.6).astype(np.float32)

        big, small = cnt(560), cnt(130)                          # one big ring + six touching it inside
        ring = np.concatenate([np.full(big, -1)] + [np.full(small, j) for j in range(6)])
        k = np.concatenate([np.arange(big)] + [np.arange(small)] * 6)
        n = len(ring)
        self._rg_j = ring.astype(np.float32)
        self._rg_small = (ring >= 0).astype(np.float32)
        # evenly spaced with a little jitter, so each ring reads as a clean dotted line
        self._rg_a = (2 * np.pi * (k + rng.uniform(-0.3, 0.3, n)) / np.where(ring < 0, big, small)).astype(np.float32)
        self._rg_jit = rng.normal(0, 0.004, n).astype(np.float32)
        self._rg_rank = rng.random(n).astype(np.float32)
        col = _pick(rng, RING, rng.random(n), 0.6, 0.15) * rng.uniform(0.5, 1.0, (n, 1)).astype(np.float32)
        self._rg_col = col * np.where(ring < 0, 1.0, 0.6).astype(np.float32)[:, None]
        self._rg_offs = _stamps(rng, n, (0.6, 0.15, 0.25))

        n = cnt(300)                                             # sparks: drift out and up, then respawn
        self._sp_a = rng.uniform(0, 2 * np.pi, n).astype(np.float32)
        self._sp_ca, self._sp_sa = np.cos(self._sp_a), np.sin(self._sp_a)
        self._sp_r = rng.uniform(0.1, 1.2, n).astype(np.float32)
        self._sp_speed = rng.uniform(0.6, 1.4, n).astype(np.float32)
        self._sp_ph = rng.random(n).astype(np.float32)
        self._sp_col = SPARK[(rng.random(n) < 0.35).astype(int)] * rng.uniform(0.5, 1.0, (n, 1)).astype(np.float32)
        self._sp_offs = _stamps(rng, n, (0.65, 0.35, 0.0))

    # ---- pose ---------------------------------------------------------------------
    def _pose(self, grow, bloom, bend):
        """Stem centreline on the sample grid and the head frame for one state."""
        g = self._grid
        length = STEM_LEN * (1 - (1 - min(grow / 0.85, 1.0)) ** 2)          # fast rise, easing in
        rel = np.minimum(g / max(length, 1.0), 1.0)
        droop = (0.25 * _ss(grow, 0.05, 0.35) + 0.75 * _ss(grow, 0.5, 1.0)) * (1 - _ss(bloom, 0.0, 0.55))
        hook_len = max(min(62.0, 0.5 * length), 1.0)
        hook = _ss(g, length - hook_len, length)                            # 0 below the hook, 1 at the tip
        a = g / STEM_LEN
        # tangent angle, clockwise from straight up: a gentle S at rest, a lean that grows
        # toward the tip, and the hooked tip. The hanging bud swings with the wind like a
        # pendulum (its hook opens against the lean), so it too moves the way bend points.
        theta = (-0.075 + 0.17 * a - 0.08 * a * a + 0.025 * np.sin(9 * a + 1)
                 + bend * BEND_TIP * rel + droop * hook * (HOOK - 0.6 * bend))
        half = (theta[1:] + theta[:-1]) * 0.5
        ds = STEM_LEN / (_M - 1)
        x = ROOT[0] + np.concatenate(([0], np.cumsum(np.sin(half)) * ds)).astype(np.float32)
        y = ROOT[1] - np.concatenate(([0], np.cumsum(np.cos(half)) * ds)).astype(np.float32)
        size = BUD * _ss(grow, 0.45, 1.0) + (1 - BUD) * _ss(bloom, 0.05, 0.85)
        return {"x": x, "y": y, "theta": theta, "len": length, "size": size,
                "phi": float(np.interp(length, g, theta)),
                "tip": (float(np.interp(length, g, x)), float(np.interp(length, g, y)))}

    def head(self, grow, bloom, bend):
        """(x, y) of the head centre in logical px."""
        p = self._pose(float(grow), float(bloom), float(bend))
        c = (0.38 - 0.12 * float(bloom)) * PETAL_LEN * p["size"]
        return p["tip"][0] + math.sin(p["phi"]) * c, p["tip"][1] - math.cos(p["phi"]) * c

    def hit(self, x, y, grow, bloom, bend):
        """True when (x, y) is on the bud or flower head (generous, for click-to-bloom)."""
        if grow <= 0:
            return False
        hx, hy = self.head(grow, bloom, bend)
        size = self._pose(float(grow), float(bloom), float(bend))["size"]
        return math.hypot(x - hx, y - hy) <= max(30.0, 0.8 * PETAL_LEN * size)

    # ---- render -------------------------------------------------------------------
    # Shapes, colours, stamps and draw order depend only on grow and bloom, so each part
    # caches them on just the values it depends on; bend, t and glow only move dots or scale
    # a few colours. The bud waiting for its click and the open flower are cheap frames.
    def _memo(self, name, key, make):
        hit = self._cache.get(name)
        if hit is None or hit[0] != key:
            hit = self._cache[name] = (key, make())
        return hit[1]

    def render(self, canvas, grow, bloom, glow, bend, t):
        """Splat the flower for one state into `canvas` (float32 (640, 640, 3), C-contiguous)."""
        grow, bloom, glow, bend, t = float(grow), float(bloom), float(glow), float(bend), float(t)
        if grow <= 0:
            return
        if canvas.shape != (_N, _N, 3) or canvas.dtype != np.float32 or not canvas.flags.c_contiguous:
            raise ValueError("canvas must be a C-contiguous float32 (640, 640, 3) array")
        p = self._pose(grow, bloom, bend)
        aura = _ss(bloom, 0.6, 1.0) * glow
        self._halo(canvas, p, bloom, glow, t)
        # painter's order: rings (behind), stem, leaves, head (depth-sorted per petal)
        for part in (self._rings(p, bloom, aura, t), self._stem(p, grow), self._leaves(p, grow, bend, t),
                     self._head(p, grow, bloom, glow)):
            if part is not None:
                _splat(canvas, *part)
        self._sparks(canvas, p, aura, t)

    # Each part returns (x, y, colours, stamps) or None.
    def _stem(self, p, grow):
        def make():
            n = int(np.searchsorted(self._st_s, p["len"], side="right"))
            s = self._st_s[:n]
            return s, self._st_lat[:n] * 6.0 * (1 - 0.35 * s / STEM_LEN) * np.clip((p["len"] - s) / 14 + 0.45, 0.45, 1.0)
        s, off = self._memo("stem", grow, make)
        n = len(s)
        if n == 0:
            return None
        g = self._grid
        x, y, th = (np.interp(s, g, p[k]).astype(np.float32) for k in ("x", "y", "theta"))
        return x + np.cos(th) * off, y + np.sin(th) * off, self._st_col[:n], self._st_offs[:n]

    def _leaves(self, p, grow, bend, t):
        reached = np.clip((p["len"] - self._lf_s) / 10, 0, 1)            # stem front has passed it
        lf = (_ss(grow, self._lf_t0, self._lf_t0 + 0.3) * reached).astype(np.float32)

        def make():
            take = (self._lf_n * (0.15 + 0.85 * lf) * (lf > 0)).astype(np.int64)
            idx = _prefixes(self._lf_start, take)
            return (np.repeat(np.arange(len(LEAVES)), take), *np.take(self._lf_uvw, idx, axis=1),
                    _rows(self._lf_col, idx), _rows(self._lf_offs, idx))
        lid, u, v, w, col, offs = self._memo("leaves", grow, make)
        if len(lid) == 0:
            return None
        g = self._grid
        ax = np.interp(self._lf_s, g, p["x"]).astype(np.float32)
        ay = np.interp(self._lf_s, g, p["y"]).astype(np.float32)
        th = np.interp(self._lf_s, g, p["theta"]).astype(np.float32)
        m = self._lf_m
        # direction (clockwise from up): young leaves hug the stem, then open to their angle;
        # they ride the stem's local tilt, lean a little extra with the wind and flutter.
        psi0 = (m * (np.pi / 2 - (self._lf_a0 + (1 - lf) * 1.1)) + th + 0.1 * bend
                + 0.03 * (0.4 + 0.6 * abs(bend)) * np.sin(1.3 * t + 2.1 * np.arange(4, dtype=np.float32)))
        curl = -m * self._lf_c * lf
        length = self._lf_len * (1 - (1 - lf) ** 2)
        width = LEAF_W * length * (0.3 + 0.7 * lf)
        turn = curl[lid] * u
        dist = length[lid] * u * _sinc(turn * 0.5)
        mid, tan = psi0[lid] + turn * 0.5, psi0[lid] + turn
        lat = v * w * width[lid]
        x = ax[lid] + dist * np.sin(mid) + lat * np.cos(tan)
        y = ay[lid] - dist * np.cos(mid) + lat * np.sin(tan)
        return x, y, col, offs

    @staticmethod
    def _tilt(X, h, Z, tilt):
        """Head-local (X right, h up the axis, Z toward the viewer) tilted toward the viewer
        about X: returns X, height on screen along the axis, depth (bigger = nearer)."""
        s, c = math.sin(tilt), math.cos(tilt)
        return X, h * c - Z * s, h * s + Z * c

    def _petal_table(self, open_p, Lh):
        """Per-petal shape for this frame: angle, curl, length, half-width, wrap, cos/sin azimuth."""
        L = self._p_len * Lh
        return np.stack((self._p_ac + (self._p_ao - self._p_ac) * open_p + self._p_aj,
                         self._p_kc + (self._p_ko - self._p_kc) * open_p,
                         L, (self._p_wc + (self._p_wo - self._p_wc) * open_p) * L,
                         1 - 0.8 * open_p, self._p_ct, self._p_st))

    @staticmethod
    def _petal_xyz(T, u, v, w, Lh):
        """Petal points as head-local X, h, Z. The centreline is an arc of constant curvature:
        angle A from the axis at the base, turning by K over the petal (closed form via sinc)."""
        A, K, L, half, wrap, ct, st = T
        x = K * u * 0.5
        s = L * u * _sinc(x)
        r = s * np.sin(A + x)
        h = s * np.cos(A + x)
        lat = v * w * half
        r = r + 0.03 * Lh - wrap * lat * lat / (2 * (r + 0.06 * Lh))     # closed petals wrap the bud
        h = h + 0.25 * (1 - wrap) * lat * lat / L                          # open petals cup upward
        return ct * r - st * lat, h, st * r + ct * lat

    def _head(self, p, grow, bloom, glow):
        if p["size"] <= 0.02:
            return None
        X, up, col, offs, a, b, centre = self._memo("head", (grow, bloom), lambda: self._head_shape(p["size"], bloom))
        np.multiply(centre, 0.5 + 0.6 * glow, out=col[a:b])                # the heart brightens with glow
        sp, cp = math.sin(p["phi"]), math.cos(p["phi"])
        hx, hy = p["tip"]
        # the head is rigid: roll it in the screen plane to the stem tip's angle
        return hx + X * cp + up * sp, hy + X * sp - up * cp, col, offs

    def _head_shape(self, size, bloom):
        """Head-local dots in paint order: X, up, colours, stamps, and the slice [a:b] holding
        the centre (core and stamens) with its unscaled colours."""
        Lh = PETAL_LEN * size
        tilt = 0.10 + 0.32 * _ss(bloom, 0.2, 0.9)
        open_p = _ss(bloom, self._p_ws, self._p_ws + 0.5).astype(np.float32)
        T = self._petal_table(open_p, Lh)

        # painter's order per petal: sort the petals by the depth of their middle
        key = self._tilt(*self._petal_xyz(T, 0.45, 0.0, 1.0, Lh), tilt)[2]
        order = np.argsort(key)
        # the bud shows only its outer petals and sepals (densely, so it reads as closed);
        # inner petals appear as each starts to open
        vis = np.where(self._p_outer, 1.0, np.clip(open_p * 4, 0, 1)) * min(1.0, 3 * size)
        take = (self._pt_n * vis)[order].astype(np.int64)

        def select():                              # changes rarely while blooming: only on reorders
            idx = _prefixes(self._pt_start[order], take)
            return np.take(self._pt_uvw, idx, axis=1), _rows(self._pt_col, idx), _rows(self._pt_offs, idx)
        (u, v, w), col, offs = self._memo("petals", (order.tobytes(), take.tobytes()), select)
        X, h, Z = self._petal_xyz(np.repeat(T[:, order], take, axis=1), u, v, w, Lh)
        X, up, depth = self._tilt(X, h, Z, tilt)
        shade = np.clip(0.72 + 0.3 * np.clip(0.5 + 0.5 * depth / Lh, 0, 1) + 0.12 * h / Lh, 0.55, 1.12)
        col = col * shade[:, None]

        # centre: glowing core plus stamens, one group drawn at the centre's depth
        ss = _ss(bloom, 0.35, 0.85)
        cr = 0.1 * Lh * (0.6 + 0.4 * ss)
        cX, cH, cZ = self._co_x * cr, 0.05 * Lh + self._co_h * cr * 0.6, self._co_z * cr
        n = int(len(self._sm_t) * ss)
        if n:
            tl = self._sm_tilt[:n] * (0.6 + 0.4 * bloom)
            ell = Lh * ss * self._sm_len[:n] * self._sm_t[:n]
            r = ell * np.sin(tl) + 0.02 * Lh
            cX = np.concatenate((cX, r * self._sm_ca[:n]))
            cH = np.concatenate((cH, 0.05 * Lh + ell * np.cos(tl)))
            cZ = np.concatenate((cZ, r * self._sm_sa[:n]))
        cX, cup, _ = self._tilt(cX, cH, cZ, tilt)
        mcol = np.concatenate((self._co_col, self._sm_col[:n]))
        moffs = np.concatenate((self._co_offs, self._sm_offs[:n]))
        k = int(np.searchsorted(key[order], self._tilt(0.0, 0.08 * Lh, 0.0, tilt)[2]))
        a = int(take[:k].sum())
        return (np.concatenate((X[:a], cX, X[a:])), np.concatenate((up[:a], cup, up[a:])),
                np.concatenate((col[:a], mcol, col[a:])), np.concatenate((offs[:a], moffs, offs[a:])),
                a, a + len(cX), mcol)

    def _centres(self, p):
        """Halo centre (the flower's heart), ring centre (higher up the axis), head scale."""
        Lh = PETAL_LEN * p["size"]
        sp, cp = math.sin(p["phi"]), math.cos(p["phi"])
        hx, hy = p["tip"]
        return (hx + sp * 0.3 * Lh, hy - cp * 0.3 * Lh), (hx + sp * 0.58 * Lh, hy - cp * 0.58 * Lh), Lh

    def _halo(self, canvas, p, bloom, glow, t):
        """A soft twinkling cloud of light behind the head: faint for the bud, wide when open."""
        if glow <= 0.01 or p["size"] <= 0.02:
            return
        (hx, hy), _, Lh = self._centres(p)
        R = Lh * (0.9 + 0.5 * bloom)
        b = self._ha_b * (0.75 + 0.25 * np.sin(1.3 * t + self._ha_ph)) * (0.16 * glow * (0.5 + 0.5 * bloom))
        _splat(canvas, hx + self._ha_x * R, hy + self._ha_y * R, self._ha_col * b[:, None], _STAMP[0, :1], add=True)

    def _rings(self, p, bloom, aura, t):
        """Orbital rings: a big circle and six half-size circles through its centre, slowly
        turning. Dots appear as the bloom ends and brighten with glow."""
        if aura <= 0.01:
            return None

        def make():
            idx = np.flatnonzero(self._rg_rank < min(1.0, 1.4 * _ss(bloom, 0.6, 1.0)))
            return (self._rg_j[idx], self._rg_small[idx], self._rg_a[idx], self._rg_jit[idx],
                    _rows(self._rg_col, idx), _rows(self._rg_offs, idx))
        j, small, a0, jit, col, offs = self._memo("rings", bloom, make)
        _, (rx, ry), Lh = self._centres(p)
        Rs = RING_R * Lh
        ca = 2 * np.pi * j / 6 + 0.1 * t
        a = a0 + 0.04 * t
        rad = Rs * (1 - 0.5 * small + jit)
        x = rx + 0.5 * Rs * small * np.cos(ca) + rad * np.cos(a)
        y = ry + 0.5 * Rs * small * np.sin(ca) + rad * np.sin(a)
        return x, y, col * (0.35 + 0.65 * aura), offs

    def _sparks(self, canvas, p, aura, t):
        """Sparks drifting out and up, and bright nodes on the big ring, added as light."""
        if aura <= 0.01:
            return
        _, (rx, ry), Lh = self._centres(p)
        Rs = RING_R * Lh
        na = 2 * np.pi * np.arange(6) / 6 + 0.1 * t
        tw = 0.8 + 0.2 * np.sin(2.6 * t + np.arange(6) * 1.7)
        _splat(canvas, rx + Rs * np.cos(na), ry + Rs * np.sin(na), (NODE * (1.3 * aura * tw)[:, None]).astype(np.float32),
               _BOX, add=True)
        life = (0.08 * t * self._sp_speed + self._sp_ph) % 1.0
        rho = self._sp_r * Rs * (0.6 + 0.5 * life)
        x = rx + self._sp_ca * rho
        y = ry + self._sp_sa * rho - life * 0.3 * Lh
        fade = np.sin(np.pi * life) * (aura * (0.7 + 0.3 * np.sin(5 * t + 6 * self._sp_ph)))
        _splat(canvas, x, y, self._sp_col * fade[:, None], self._sp_offs, add=True)
