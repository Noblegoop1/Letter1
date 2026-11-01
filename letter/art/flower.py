"""Procedural pointillist sea holly (Eryngium) for the night scene (SPEC 10.3-10.4).

A tall ribbed stem with spiny lobed leaves carries an egg-shaped cone of tiny florets set in
phyllotaxis spirals, ringed by a star of long, narrow, spiny bracts. It grows as a closed bud hanging
from a hooked stem tip; on the click the head lifts, the bracts open into the star one by one and a
wave of light climbs the cone. Colours come from the user's blue gradients
(reference/sea-holly/blue-gradients.png): an ocean glow under moonlight.

Every particle is generated once from one seeded RNG. A frame only evaluates closed-form geometry for
the animation state (grow, bloom, glow, bend, t) and splats coloured dots into the shared canvas:
float32 (640, 640, 3), indexed [y, x], display RGB in 0..1 (the scene shows it as is), ground line at
y = GROUND_Y. The techniques (arc-shaped blades, noisy palettes, depth-ordered dot splats) are the ones
described in docs/flowers.md; no reference code is used.
"""
import math

import numpy as np

GROUND_Y = 500
ROOT = (320, 500)

_N = 640            # canvas side, px
STEM_LEN = 236.0    # root to head at full growth, px
CONE_H = 90.0       # flower cone height at full bloom, px
CONE_R = 30.0       # its widest radius
BRACT_LEN = 116.0   # outer bract length at full bloom, px
BUD = 0.62          # size of the closed bud relative to the open head
HOOK = 2.75         # rad the stem tip turns over while the bud droops
BEND_TIP = 0.17     # rad the stem tip turns per unit of bend (wind plus pointer lean)
FLORETS = 240       # florets on the cone
_M = 128            # stem centreline samples
_GOLDEN = math.pi * (3 - math.sqrt(5))


def _rgb(*hexes):
    """Hex strings -> display RGB float32 colours in 0..1, shape (k, 3) (the canvas holds display values)."""
    c = np.array([[int(h[i:i + 2], 16) for i in (0, 2, 4)] for h in hexes], np.float32)
    return c / 255


# The user's seven blue gradients, top -> bottom: 4a55c8->0a1a8c, 3478f6->0b3fb8, 0ea5e0->1a1a5e,
# 6a44ff->1e1650, 2e5fd8->1c1a5a, 046a9a->1e1e5e, 0a5a8a->0a2448. "Ocean glow under the moonlight":
# a cyan-to-royal-blue cone deepening to indigo at its base, violet-periwinkle bracts with silver-blue
# edges, an indigo stem and teal leaves.
CONE_PAL = _rgb("1b1464", "1c229a", "2b39ae", "2459cf", "3478f6", "0ea5e0", "4cc4f0", "a6e6ff")  # groove/base -> lit tip
SPECK = _rgb("eefaff", "d2f0ff", "b4e0ff")                                   # pollen and moonlit spine tips
BRACT_PAL = _rgb("1e1650", "2f2087", "4a3cc8", "6060e8", "7a8cf2", "a8bcfc")  # base -> tip
COLLAR_PAL = _rgb("1e1650", "2a1e7c", "3f2bad", "5036cc", "6a5cf0")
BRACT_RIM = _rgb("b0c6f4", "cddcff", "90b2ee")                               # silver-blue sheen on the edges
BRACT_RIB = _rgb("a0b6f4", "c2d2ff")
STEM_PAL = _rgb("1b1464", "211a72", "2f2087", "3a2aa6", "4547bc")            # root -> head
STEM_RIB = _rgb("5258d8", "6470ea", "4a55c8")
LEAF_PAL = _rgb("0a2448", "0b3a5e", "0a5a8a", "176c96", "3684a8", "6aa4c2")  # midrib/base -> edge/tip
LEAF_RIB = _rgb("9cc0d6", "bcd6e6")
LEAF_RIM = _rgb("86b4ce", "acd0e2", "74a4c4")
HALO_IN, HALO_OUT = _rgb("0ea5e0", "6a44ff")
SPARK = _rgb("c4f2ff", "6cc6ff", "a89cff")

# Bract rings, outer star first, then the short spiny collar under the cone. Columns: count, closed
# angle, open angle (rad from the axis), closed curl, open curl (rad turned along the bract), length
# (in BRACT_LEN), half-width (fraction of length), dots each, azimuth offset, start of the opening
# window (bloom value; each bract's window lasts 0.45 and starts up to 0.33 later), teeth per edge,
# base radius (in CONE_R), base height (in CONE_H). Closed bracts hug the bud and curl in over it.
BRACTS = (
    (12, 0.52, 1.34, -0.75, 0.18, 1.00, 0.13, 560, 0.00, 0.04, 6, 0.62, 0.05),
    (9, 0.45, 0.92, -0.50, 0.12, 0.42, 0.14, 160, 0.35, 0.20, 3, 0.55, 0.09),
)
# Leaves: stem position (fraction), side (+1 right), length px, angle above horizontal,
# curl (negative droops), grow value where it starts to unfurl, lobes per edge.
LEAVES = (
    (0.04, +1, 98.0, 0.50, -0.65, 0.14, 5),
    (0.06, -1, 92.0, 0.44, -0.60, 0.22, 5),
    (0.36, -1, 70.0, 0.55, -0.55, 0.34, 4),
    (0.50, +1, 70.0, 0.68, -0.50, 0.44, 4),
)
LEAF_W = 0.30       # leaf half-width at a lobe tip, in leaf lengths
# Side branches from the leaf axils, each carrying a small copy of the main head (it opens with it):
# stem position (fraction), side (+1 right), length px, head scale, grow value where it starts.
BRANCHES = ((0.36, -1, 104.0, 0.40, 0.38),)
SIDE_EVERY = 6      # a side head draws every 6th dot of the main head (about even density at scale 0.4)
_RIBS = np.array([-0.82, -0.42, 0.0, 0.42, 0.82])   # stem ribs, lateral positions
_DIM = np.array([0.6, 0.62, 0.9], np.float32)   # unlit florets: the cyan sinks to royal blue
_LIGHT = np.array([0.45, 0.70, 0.55]) / np.linalg.norm([0.45, 0.70, 0.55])   # moonlight, head-local

# Splat stamps as flat-index offsets, padded to 5 by repeating the centre:
# 1 px, plus (5 px), 2x2 (4 px).
_STAMP = np.array([[0, 0, 0, 0, 0], [0, -1, 1, -_N, _N], [0, 1, _N, _N + 1, 0]], np.int32)
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


def _cone_r(h):
    """Cone radius (in CONE_R) at height h (0 base .. 1 apex): an egg, widest low, a rounded point on top."""
    return np.sin(np.pi * (0.1 + 0.9 * np.clip(h, 0, 1)) ** 0.78) ** 0.75


def _bract_env(u):
    return np.sin(np.pi * np.clip(u, 0, 1) ** 0.55)            # narrow base, widest at ~30%, long sharp point


def _leaf_env(u):
    return np.sin(np.pi * np.clip(u, 0, 1) ** 0.7) ** 0.8


def _teeth(rng, u, v, n, depth):
    """Width factor for spiny edges: n sawteeth per edge that point toward the tip, offset per edge."""
    f = (n * u + rng.random() + 0.5 * (v > 0)) % 1.0
    return 1 - depth + depth * f * f


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


def _head_tilt(bloom):
    """Rad the head tips toward the viewer: a little for the bud, more open so the star shows."""
    return 0.12 + 0.28 * _ss(bloom, 0.2, 0.9)


class Flower:
    """The sea holly's particles, built once; `render` splats one animation state."""

    def __init__(self, seed=5, quality=1.0):
        rng = np.random.default_rng(seed)
        q = max(0.05, float(quality))

        def cnt(n):
            return max(16, int(round(n * q)))

        self._grid = np.linspace(0, STEM_LEN, _M).astype(np.float32)
        self._cache = {}                                        # part -> (state key, shapes); see _memo
        self._build_stem(rng, cnt(2200))
        self._build_leaves(rng, cnt(800))
        self._build_bracts(rng, cnt)
        self._build_cone(rng, max(6, int(round(30 * q))))
        self._build_aura(rng, cnt)
        self._build_branches(rng, cnt(240))
        self.counts = {
            "stem": len(self._st_s), "leaves": self._lf_uvw.shape[1], "bracts": self._bt_uvw.shape[1],
            "florets": self._cn_X.size, "halo": len(self._ha_x), "sparks": len(self._sp_a),
            "branches": len(BRANCHES) * (len(self._br_u) + (self._bt_uvw.shape[1] + self._cn_X.size // 2) // SIDE_EVERY),
        }   # a side head reuses the main head's particles; counted as the dots it draws (half the florets face us)
        self.counts["total"] = sum(self.counts.values())

    # ---- build (once) -------------------------------------------------------------
    def _build_stem(self, rng, n):
        s = np.sort(rng.random(n)).astype(np.float32)          # sorted: the grown part is a prefix
        lat = rng.uniform(-1, 1, n)
        rib = rng.random(n) < 0.55                               # most dots line the ribs: a fluted stem
        lat[rib] = rng.choice(_RIBS, rib.sum()) + rng.normal(0, 0.05, rib.sum())
        lat = np.clip(lat, -1, 1).astype(np.float32)
        col = _pick(rng, STEM_PAL, s * 0.8 + rng.random(n) * 0.2, 0.6)
        col[rib] = _pick(rng, STEM_RIB, rng.random(rib.sum()), 0.8) * (0.6 + 0.25 * s[rib, None])
        col *= (0.66 + 0.42 * (0.5 + 0.5 * lat))[:, None]       # moonlit from the right: reads as round
        self._st_s, self._st_lat, self._st_col = s * STEM_LEN, lat, col
        self._st_offs = np.where(rib[:, None], _stamps(rng, n, (0.55, 0.3, 0.15)), _stamps(rng, n, (0.15, 0.5, 0.35)))

    def _build_leaves(self, rng, per_leaf):
        parts = []
        for leaf in LEAVES:
            u = _along(rng, per_leaf, _leaf_env)
            v, rim = _across(rng, per_leaf, 0.16)
            rib = rng.random(per_leaf) < 0.07
            v[rib] = rng.normal(0, 0.03, rib.sum())
            w = _leaf_env(u) * _teeth(rng, u, v, leaf[6], 0.7)  # deep, spine-tipped lobes
            # deep teal along the midrib and base, silvery blue-green toward the edges and tip
            col = _pick(rng, LEAF_PAL, 0.5 * u + 0.5 * np.abs(v) + rng.normal(0, 0.08, per_leaf), 0.55)
            col[rib] = _pick(rng, LEAF_RIB, rng.random(rib.sum()), 0.6)
            edge = rim & (rng.random(per_leaf) < 0.6)
            col[edge] = _pick(rng, LEAF_RIM, rng.random(edge.sum()), 0.7)
            col *= (0.8 + 0.2 * v)[:, None]                      # one half of the blade lighter: a fold
            offs = _stamps(rng, per_leaf, (0.2, 0.55, 0.25))
            offs[rib | edge] = _STAMP[0]
            parts.append((u, v, w.astype(np.float32), col, offs))   # random order: any prefix is an even subset
        u, v, w, col, offs = (np.concatenate(p) for p in zip(*parts))
        self._lf_uvw = np.stack((u, v, w))
        self._lf_col, self._lf_offs = col, offs
        self._lf_start = np.arange(len(LEAVES)) * per_leaf
        self._lf_n = per_leaf
        L = np.array(LEAVES, np.float32)
        self._lf_s, self._lf_m, self._lf_len = L[:, 0] * STEM_LEN, L[:, 1], L[:, 2]
        self._lf_a0, self._lf_c, self._lf_t0 = L[:, 3], L[:, 4], L[:, 5]

    def _build_bracts(self, rng, cnt):
        ring = np.concatenate([np.full(row[0], i) for i, row in enumerate(BRACTS)])
        P = len(ring)
        tab = np.array(BRACTS, np.float32)[ring]               # each bract's copy of its ring row
        az = np.concatenate([2 * np.pi * np.arange(row[0]) / row[0] + row[8] for row in BRACTS])
        az = az + rng.normal(0, 0.06, P)
        self._b_ac, self._b_ao, self._b_kc, self._b_ko = tab[:, 1], tab[:, 2], tab[:, 3], tab[:, 4]
        self._b_len = tab[:, 5] * rng.uniform(0.82, 1.08, P).astype(np.float32)
        self._b_hw = tab[:, 6]
        self._b_aj = rng.normal(0, 0.14, P).astype(np.float32)   # open bracts splay up and down a little
        order = np.concatenate([rng.permutation(row[0]) / row[0] for row in BRACTS])
        self._b_ws = (tab[:, 9] + 0.3 * order + rng.uniform(0, 0.03, P)).astype(np.float32)
        self._b_r0, self._b_h0 = tab[:, 11] * CONE_R, tab[:, 12] * CONE_H
        self._b_ct, self._b_st = np.cos(az).astype(np.float32), np.sin(az).astype(np.float32)

        parts = []
        for p in range(P):
            row = BRACTS[ring[p]]
            d = cnt(row[7])
            u = _along(rng, d, _bract_env)
            v, _ = _across(rng, d, 0.22)
            w = _bract_env(u) * _teeth(rng, u, v, row[10], 0.6)
            col = _pick(rng, BRACT_PAL if ring[p] == 0 else COLLAR_PAL, u + rng.normal(0, 0.08, d), 0.35)
            r = rng.random(d)
            rim = (np.abs(v) > 0.86) & (r < 0.85)
            rib = (np.abs(v) < 0.1) & (r < 0.35) & (u > 0.1)     # a pale midvein
            col[rim] = _pick(rng, BRACT_RIM, rng.random(rim.sum()), 0.8) * (0.35 + 0.75 * u[rim, None])
            col[rib] = _pick(rng, BRACT_RIB, rng.random(rib.sum()), 0.6) * (0.3 + 0.7 * u[rib, None])
            offs = _stamps(rng, d, (0.2, 0.55, 0.25))
            offs[rim | rib] = _STAMP[0]
            parts.append((u, v, w.astype(np.float32), col, offs))   # random order within a bract
        u, v, w, col, offs = (np.concatenate(x) for x in zip(*parts))
        self._bt_uvw = np.stack((u, v, w))
        self._bt_col, self._bt_offs = col, offs
        self._bt_n = np.array([len(x[0]) for x in parts])
        self._bt_start = np.concatenate(([0], np.cumsum(self._bt_n)[:-1]))

    def _build_cone(self, rng, k):
        """FLORETS bumps of k dots on an egg-shaped surface of revolution, in golden-angle spirals.
        Stored per floret (F, k) at full size in head-local px: X right, H up the axis, Z toward us.
        Within a floret the dots run rim first, crown last, then the pale spine tip, so the crowns sit on
        dark grooves; florets are painted far to near, so near ones overlap far ones like a pinecone's."""
        F = FLORETS
        hh = np.linspace(0, 1, 513)
        rr = _cone_r(hh) * CONE_R
        sl = np.gradient(rr, hh * CONE_H)                       # dr/dh
        dA = 2 * np.pi * rr * np.sqrt(1 + sl * sl)              # surface per px of height
        A = np.concatenate(([0], np.cumsum((dA[1:] + dA[:-1]) * 0.5 * np.diff(hh * CONE_H))))
        hf = np.interp((np.arange(F) + 0.5) / F * A[-1], A, hh)   # even per area: the florets tile it
        d = math.sqrt(A[-1] / F)                                 # floret spacing, px
        az = np.arange(F) * _GOLDEN + rng.uniform(0, 2 * np.pi)
        rf, s = np.interp(hf, hh, rr), np.interp(hf, hh, sl)
        nn = np.sqrt(1 + s * s)
        ca, sa = np.cos(az), np.sin(az)
        N = np.stack((ca / nn, -s / nn, sa / nn))                # outward normal
        Tm = np.stack((ca * s / nn, 1 / nn, sa * s / nn))        # along the surface toward the apex
        Ta = np.stack((-sa, 0 * sa, ca))                         # around the axis
        Pc = np.stack((ca * rf, hf * CONE_H, sa * rf))
        # one template for every floret: a little sunflower of dots, rim first; turned per floret
        j = np.arange(k - 1)
        rho = 0.56 * np.sqrt((k - 1.5 - j) / (k - 1)) + rng.normal(0, 0.03, (F, k - 1))
        ang = j * _GOLDEN + rng.uniform(0, 2 * np.pi, (F, 1))
        a, b = rho * np.cos(ang), rho * np.sin(ang) * 1.15 + 0.06    # a teardrop leaning to the apex
        lift = 0.45 * (1 - np.clip(rho / 0.56, 0, 1) ** 2)
        a, b = np.c_[a, np.zeros(F)], np.c_[b, np.full(F, 0.3)]
        lift, rho = np.c_[lift, np.full(F, 0.75)], np.c_[rho, np.zeros(F)]   # last: the spine tip
        pos = Pc[:, :, None] + d * (a * Ta[:, :, None] + b * Tm[:, :, None] + lift * N[:, :, None])
        self._cn_X, self._cn_H, self._cn_Z = pos.astype(np.float32)
        self._cn_N, self._cn_P, self._cn_h = N.astype(np.float32), Pc.astype(np.float32), hf.astype(np.float32)

        # bright crowns over dark grooves; crowns royal blue low on the cone, cyan toward the top
        shape = 1 - np.clip(rho / 0.56, 0, 1) ** 1.5
        g = (0.2 + 0.8 * shape) * (0.4 + 0.6 * hf[:, None]) + rng.normal(0, 0.04, (F, k))
        col = _pick(rng, CONE_PAL, g.ravel(), 0.35).reshape(F, k, 3)
        col *= (0.62 + 0.5 * np.clip(_LIGHT @ N, 0, 1))[:, None, None].astype(np.float32)
        speck = (rng.random((F, k)) < 0.04) & (shape > 0.5)
        speck[:, -1] = rng.random(F) < 0.75
        col[speck] = _pick(rng, SPECK, rng.random(speck.sum()), 0.6) * (0.7 + 0.35 * hf[np.nonzero(speck)[0], None])
        self._cn_col = col
        offs = np.where((shape > 0.45)[..., None], _stamps(rng, F * k, (0.1, 0.6, 0.3)).reshape(F, k, 5),
                        _stamps(rng, F * k, (0.5, 0.45, 0.05)).reshape(F, k, 5))
        offs[speck] = _STAMP[0]
        self._cn_offs = offs
        # shimmer: a slow ripple of light climbing the cone; the specks twinkle on their own
        self._cn_ph = np.where(speck, rng.uniform(0, 2 * np.pi, (F, k)), 6.5 * hf[:, None]).astype(np.float32)
        self._cn_w = np.where(speck, rng.uniform(1.4, 3.6, (F, k)), 1.3).astype(np.float32)
        self._cn_amp = np.where(speck, 0.4, 0.09).astype(np.float32)

    def _build_aura(self, rng, cnt):
        n = cnt(1400)                                            # halo: dense in the middle
        a = rng.uniform(0, 2 * np.pi, n)
        r = np.minimum(np.abs(rng.normal(0, 0.55, n)), 1.6) / 1.6
        self._ha_x, self._ha_y = (r * np.cos(a)).astype(np.float32), (r * np.sin(a)).astype(np.float32)
        self._ha_b = ((1 - r) ** 1.5).astype(np.float32)
        self._ha_ph = rng.uniform(0, 2 * np.pi, n).astype(np.float32)
        self._ha_col = (HALO_IN + (HALO_OUT - HALO_IN) * r[:, None] ** 0.6).astype(np.float32)

        n = cnt(300)                                             # motes rising off the head like bubbles
        self._sp_a = rng.uniform(0, 2 * np.pi, n).astype(np.float32)
        self._sp_ca, self._sp_sa = np.cos(self._sp_a), np.sin(self._sp_a)
        self._sp_r = rng.uniform(0.1, 1.0, n).astype(np.float32)
        self._sp_speed = rng.uniform(0.6, 1.4, n).astype(np.float32)
        self._sp_ph = rng.random(n).astype(np.float32)
        self._sp_col = SPARK[rng.choice(3, n, p=(0.45, 0.4, 0.15))] * rng.uniform(0.5, 1.0, (n, 1)).astype(np.float32)
        self._sp_offs = _stamps(rng, n, (0.7, 0.3, 0.0))

    def _build_branches(self, rng, n):
        self._br_u = np.sort(rng.random(n)).astype(np.float32)  # shared by the branches: the grown part is a prefix
        self._br_lat = rng.uniform(-1, 1, n).astype(np.float32)
        self._br_col = _pick(rng, STEM_PAL, 0.35 + 0.65 * self._br_u, 0.6) * (0.66 + 0.42 * (0.5 + 0.5 * self._br_lat))[:, None]
        self._br_offs = _stamps(rng, n, (0.3, 0.5, 0.2))
        self._br_grid = np.linspace(0, 1, 24).astype(np.float32)

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
        # tangent angle, clockwise from straight up: nearly straight with a faint S, a lean that grows
        # toward the tip, and the hooked tip. The hanging bud swings with the wind like a pendulum
        # (its hook opens against the lean), so it too moves the way bend points.
        theta = (-0.05 + 0.1 * a - 0.05 * a * a + 0.015 * np.sin(8 * a + 1)
                 + bend * BEND_TIP * rel + droop * hook * (HOOK - 0.6 * bend))
        half = (theta[1:] + theta[:-1]) * 0.5
        ds = STEM_LEN / (_M - 1)
        x = ROOT[0] + np.concatenate(([0], np.cumsum(np.sin(half)) * ds)).astype(np.float32)
        y = ROOT[1] - np.concatenate(([0], np.cumsum(np.cos(half)) * ds)).astype(np.float32)
        size = BUD * _ss(grow, 0.45, 1.0) + (1 - BUD) * _ss(bloom, 0.05, 0.85)
        return {"x": x, "y": y, "theta": theta, "len": length, "size": size,
                "phi": float(np.interp(length, g, theta)),
                "tip": (float(np.interp(length, g, x)), float(np.interp(length, g, y)))}

    @staticmethod
    def _centre(p, bloom):
        """Screen centre of the cone and the cone's scale (it swells a little as it opens)."""
        cs = p["size"] ** 0.6
        c = 0.45 * CONE_H * cs * math.cos(_head_tilt(bloom))
        return (p["tip"][0] + math.sin(p["phi"]) * c, p["tip"][1] - math.cos(p["phi"]) * c), cs

    def head(self, grow, bloom, bend):
        """(x, y) of the head centre (the middle of the cone) in logical px."""
        return self._centre(self._pose(float(grow), float(bloom), float(bend)), float(bloom))[0]

    def hit(self, x, y, grow, bloom, bend):
        """True when (x, y) is on the bud or flower head (generous, for click-to-bloom)."""
        if grow <= 0:
            return False
        p = self._pose(float(grow), float(bloom), float(bend))
        (hx, hy), _ = self._centre(p, float(bloom))
        return math.hypot(x - hx, y - hy) <= max(32.0, 0.62 * BRACT_LEN * p["size"])

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
        self._halo(canvas, p, bloom, glow, t)
        head = self._head(p, grow, bloom, glow, t)
        # painter's order: side branches and their heads, stem, leaves, head (bracts and florets depth-sorted)
        for i in range(len(BRANCHES)):
            self._branch(canvas, p, i, grow, bloom, bend, head)
        for part in (self._stem(p, grow), self._leaves(p, grow, bend, t)):
            if part is not None:
                _splat(canvas, *part)
        if head is not None:
            X, up, col, offs = head
            _splat(canvas, *self._roll(X, up, p["tip"], p["phi"]), col, offs)
        self._sparks(canvas, p, bloom, _ss(bloom, 0.6, 1.0) * glow, t)

    # Each part returns (x, y, colours, stamps) or None.
    def _stem(self, p, grow):
        def make():
            n = int(np.searchsorted(self._st_s, p["len"], side="right"))
            s = self._st_s[:n]
            return s, self._st_lat[:n] * 5.2 * (1 - 0.25 * s / STEM_LEN) * np.clip((p["len"] - s) / 14 + 0.45, 0.45, 1.0)
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
                + 0.03 * (0.4 + 0.6 * abs(bend)) * np.sin(1.3 * t + 2.1 * np.arange(len(LEAVES), dtype=np.float32)))
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

    def _bract_table(self, open_p, size, cs):
        """Per-bract shape for this frame: angle, curl, length, half-width, base radius and height, cos/sin azimuth."""
        L = self._b_len * BRACT_LEN * size * (0.62 + 0.38 * open_p)   # folded bracts cup the bud's lower part
        return np.stack((self._b_ac + (self._b_ao - self._b_ac) * open_p + self._b_aj * open_p,
                         self._b_kc + (self._b_ko - self._b_kc) * open_p,
                         L, self._b_hw * L * (0.3 + 0.7 * open_p), self._b_r0 * cs, self._b_h0 * cs,
                         self._b_ct, self._b_st))   # closed bracts are folded narrow

    @staticmethod
    def _bract_xyz(T, u, v, w):
        """Bract points as head-local X, h, Z. The centreline is an arc of constant curvature:
        angle A from the axis at the base, turning by K over the bract (closed form via sinc)."""
        A, K, L, half, r0, h0, ct, st = T
        x = K * u * 0.5
        s = L * u * _sinc(x)
        r = r0 + s * np.sin(A + x)
        h = h0 + s * np.cos(A + x)
        lat = v * w * half
        return ct * r - st * lat, h, st * r + ct * lat

    def _branch(self, canvas, p, i, grow, bloom, bend, head):
        """Splat side branch i and its small head. It leaves the stem at an angle and curves back up; its
        bud hangs outward on a hook and lifts with the main bloom."""
        s0, side, L, k, g0 = BRANCHES[i]
        s = s0 * STEM_LEN
        gb = _ss(grow, g0, g0 + 0.4) * float(np.clip((p["len"] - s) / 10, 0, 1))
        if gb <= 0:
            return
        g, u = self._grid, self._br_grid
        sx, sy, th = (float(np.interp(s, g, p[q])) for q in ("x", "y", "theta"))
        length = L * (1 - (1 - gb) ** 2)
        droop = _ss(gb, 0.5, 1.0) * (1 - _ss(bloom, 0.0, 0.55))
        theta = (th + side * (0.3 + 0.95 * gb) * (1 - 0.75 * u) + 1.2 * BEND_TIP * bend * u
                 + side * droop * 2.3 * _ss(u, 0.5, 1.0))
        half = (theta[1:] + theta[:-1]) * 0.5
        ds = length / (len(u) - 1)
        x = sx + np.concatenate(([0], np.cumsum(np.sin(half)) * ds))
        y = sy - np.concatenate(([0], np.cumsum(np.cos(half)) * ds))
        n = int(np.searchsorted(self._br_u, length / L, side="right"))
        q = self._br_u[:n] * (L / max(length, 1e-3))
        bx, by, bt = (np.interp(q, u, a).astype(np.float32) for a in (x, y, theta))
        off = self._br_lat[:n] * 3.2 * (1 - 0.3 * q)
        _splat(canvas, bx + np.cos(bt) * off, by + np.sin(bt) * off, self._br_col[:n], self._br_offs[:n])
        if head is not None:
            X, up, col, offs = (a[::SIDE_EVERY] for a in head)
            _splat(canvas, *self._roll(X, up, (x[-1], y[-1]), float(theta[-1]), k), col * np.float32(0.8), offs)

    @staticmethod
    def _roll(X, up, tip, phi, k=1.0):
        """Head-local dots to screen: the head is rigid, rolled in the screen plane to the stem tip's angle."""
        sp, cp = math.sin(phi) * k, math.cos(phi) * k
        return tip[0] + X * cp + up * sp, tip[1] + X * sp - up * cp

    def _head(self, p, grow, bloom, glow, t):
        """Head-local dots for this frame (X right, up along the axis), colours and stamps, or None."""
        if p["size"] <= 0.02:
            return None
        X, up, col, offs, a, b, base, ph, w, amp = self._memo(
            "head", (grow, bloom), lambda: self._head_shape(p["size"], bloom))
        m = np.sin(ph - w * t)                                   # shimmer and twinkle
        m *= amp
        m += 0.6 + 0.45 * glow                                   # the cone brightens with glow
        np.multiply(base, m[:, None], out=col[a:b])
        return X, up, col, offs

    def _head_shape(self, size, bloom):
        """Head-local dots in paint order: X, up, colours, stamps, the slice [a:b] holding the cone,
        and the cone's colours before glow, shimmer phase, speed and amplitude per dot."""
        cs = size ** 0.6
        tilt = _head_tilt(bloom)
        s, c = math.sin(tilt), math.cos(tilt)

        # bracts: each opens on its own window; painter's order by the depth of its middle
        open_p = _ss(bloom, self._b_ws, self._b_ws + 0.45).astype(np.float32)
        T = self._bract_table(open_p, size, cs)
        key = self._tilt(*self._bract_xyz(T, 0.45, 0.0, 1.0), tilt)[2]
        order = np.argsort(key)
        take = self._bt_n[order]
        # cone: florets facing us (and a little past the rim, so bumps show on the outline), far first
        N, P = self._cn_N, self._cn_P
        fo = np.flatnonzero(N[1] * s + N[2] * c > -0.3)
        fo = fo[np.argsort((P[1] * s + P[2] * c)[fo])]
        # the cone sits among the bracts at the depth of its lower part
        cut = int(take[:int(np.searchsorted(key[order], 0.2 * CONE_H * cs * s))].sum())

        def layout():          # the paint order changes only now and then while blooming: gather once per order
            idx = _prefixes(self._bt_start[order], take)
            boffs = _rows(self._bt_offs, idx)
            cone = (a[fo].ravel() for a in (self._cn_X, self._cn_H, self._cn_Z, self._cn_ph, self._cn_w, self._cn_amp))
            return (np.take(self._bt_uvw, idx, axis=1), _rows(self._bt_col, idx), np.repeat(order, take), *cone,
                    self._cn_col[fo], np.concatenate((boffs[:cut], self._cn_offs[fo].reshape(-1, 5), boffs[cut:])))
        (u, v, w), bcol, bid, cX, cH, cZ, ph, wt, amp, ccol, offs = self._memo(
            "layout", (order.tobytes(), fo.tobytes(), cut), layout)

        bX, bh, bZ = self._bract_xyz(np.take(T, bid, axis=1), u, v, w)
        bX, bup, depth = self._tilt(bX, bh, bZ, tilt)
        Lb = BRACT_LEN * size
        shade = np.clip(0.66 + 0.34 * np.clip(0.5 + 0.5 * depth / Lb, 0, 1) + 0.12 * bh / Lb, 0.5, 1.1)
        shade *= (0.6 + 0.4 * open_p)[bid]                       # folded bracts show their dim backs
        bcol = bcol * shade[:, None]

        X, up, _ = self._tilt(cX * cs, cH * cs, cZ * cs, tilt)
        # the florets light up in a wave climbing from base to tip, a bright band at its front
        hf = self._cn_h[fo]
        front = -0.12 + 1.3 * _ss(bloom, 0.08, 0.92)
        flash = np.exp(-((front - hf) / 0.07) ** 2) * (1 - _ss(bloom, 0.85, 1.0))
        lit = _ss(front - hf, 0.0, 0.12)[:, None]
        tint = ((_DIM + (1 - _DIM) * lit) * (0.8 + 0.2 * lit + 0.55 * flash[:, None])).astype(np.float32)
        n = len(X)
        return (np.concatenate((bX[:cut], X, bX[cut:])), np.concatenate((bup[:cut], up, bup[cut:])),
                np.concatenate((bcol[:cut], np.empty((n, 3), np.float32), bcol[cut:])), offs,
                cut, cut + n, (ccol * tint[:, None, :]).reshape(-1, 3), ph, wt,
                amp * np.float32(0.3 + 0.7 * _ss(bloom, 0.7, 1.0)))

    def _halo(self, canvas, p, bloom, glow, t):
        """A soft twinkling cloud of cyan-violet light behind the head: faint for the bud, wide when open."""
        if glow <= 0.01 or p["size"] <= 0.02:
            return
        (hx, hy), cs = self._centre(p, bloom)
        R = CONE_H * cs * (0.85 + 0.55 * bloom)
        b = self._ha_b * (0.75 + 0.25 * np.sin(1.3 * t + self._ha_ph)) * (0.16 * glow * (0.5 + 0.5 * bloom))
        _splat(canvas, hx + self._ha_x * R, hy + self._ha_y * R, self._ha_col * b[:, None], _STAMP[0, :1], add=True)

    def _sparks(self, canvas, p, bloom, aura, t):
        """Motes of light rising off the cone and drifting out, like bubbles in lit water."""
        if aura <= 0.01:
            return
        (hx, hy), cs = self._centre(p, bloom)
        R = 0.9 * CONE_H * cs
        life = (0.08 * t * self._sp_speed + self._sp_ph) % 1.0
        rho = self._sp_r * R * (0.5 + 0.6 * life)
        x = hx + self._sp_ca * rho
        y = hy + self._sp_sa * rho * 0.7 - life * 0.55 * R
        fade = np.sin(np.pi * life) * (aura * (0.7 + 0.3 * np.sin(5 * t + 6 * self._sp_ph)))
        _splat(canvas, x, y, self._sp_col * fade[:, None], self._sp_offs, add=True)
