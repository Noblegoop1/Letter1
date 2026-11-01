"""Placeholder flower: a drooping bud on a Bezier stem that lifts and opens into a glowing bloom.

Ported from the ideas in docs/flowers.md (stem curve, constant-curvature petal arcs, layered petals,
stamens, halo); the real flower will replace this file, so everything sits behind SIZE, BASE and frame().
Pure and MicroPython-safe; main.py owns the DOM.

Geometry is in square units relative to BASE: x right in columns, y up in half-rows (a cell is about twice
as tall as wide). Cells are only worked out when something is drawn.
"""
import math

from stage import clamp, hash32, lerp, smoothstep

COLS, ROWS = 41, 24
SIZE = (COLS, ROWS)
BASE = (20, 23)
HEART = (21, 9)      # the open flower's centre: main.py aims the fireflies and pointer lean here
_BC, _BR = BASE
_N = COLS * ROWS


def _jit(i, amp):
    """Seeded jitter in [-amp, amp]: the same slightly imperfect flower every time."""
    return ((hash32(i, 101, 7) & 1023) / 511.5 - 1.0) * amp


def _sinc(x):
    return 1.0 if -1e-6 < x < 1e-6 else math.sin(x) / x


def _profile(u):
    """Petal/leaf width envelope: pinched base, widest near 40%, pointed tip."""
    return 0.0 if u <= 0.0 or u >= 1.0 else math.sin(math.pi * u ** 0.75) ** 0.85


def _flat(f):
    """Near-horizontal line glyph by its height inside the cell (f: 0 top .. 1 bottom): ' - . _"""
    return "'" if f < 0.3 else "-" if f < 0.58 else "." if f < 0.8 else "_"


def _stem_glyph(dx, dy, curl, f):
    """Stem glyph from its direction (square units, y up), curvature sign and height in the cell."""
    if dy < 0:
        dx, dy, curl = -dx, -dy, -curl
    q = dx / (dy * 0.5 + 1e-9)                      # columns per row
    a = q if q > 0 else -q
    if a < 0.45:
        return "|"
    if a < 0.9 and (curl > 0.004 or curl < -0.004):
        return ")" if curl > 0 else "("
    if a < 1.25:
        return "/" if q > 0 else "\\"
    return _flat(f)


def _rim_glyph(dx, dy, out):
    """Outline glyph for a rim running (dx, dy) whose outside is to the right (out > 0) or left;
    None for a near-flat run, whose glyph depends on its height inside each cell."""
    if dy < 0:
        dx, dy = -dx, -dy
    q = dx / (dy * 0.5 + 1e-9)
    a = q if q > 0 else -q
    if a < 0.6:
        return ")" if out > 0 else "("
    if a < 1.25:
        return "/" if q > 0 else "\\"
    return None


# ---- stem: one cubic Bezier sampled at fixed parameters, so growth is a prefix of the same samples
_NS = 48
_BEZ = []
for _j in range(_NS):
    _s = _j / (_NS - 1)
    _q = 1 - _s
    _BEZ.append((_s, _q * _q * _q, 3 * _q * _q * _s, 3 * _q * _s * _s, _s * _s * _s,
                 3 * _q * _q, 6 * _q * _s, 3 * _s * _s, 6 * _q, 6 * _s))

# poses: droop (a shepherd's crook, tip hanging) and upright; the lift walks the tip along a curved path
_DROOP_TIP = (10.0 + _jit(1, 0.5), 22.0 + _jit(2, 0.6))
_LIFT_VIA = (9.0, 30.0)
_UP_TIP = (0.5 + _jit(3, 0.4), 27.0)
_TH_DROOP = 3.21 + _jit(4, 0.05)    # tip direction from straight up (radians, clockwise): hanging
_TH_UP = -0.06


def _stem(lift, bend):
    """-> P0..P3 as 8 floats. The tip direction is an angle, so the head turns without flipping."""
    k, q = lift, 1 - lift
    x3 = q * q * _DROOP_TIP[0] + 2 * q * k * _LIFT_VIA[0] + k * k * _UP_TIP[0] + bend * 3.0
    y3 = q * q * _DROOP_TIP[1] + 2 * q * k * _LIFT_VIA[1] + k * k * _UP_TIP[1]
    th0 = lerp(_TH_DROOP, _TH_UP, k)
    th = th0 + bend * lerp(0.15, 0.32, k) * math.cos(th0)    # turn the head toward +x for bend > 0
    d = lerp(14.0, 8.0, k) - 7.0 * math.sin(math.pi * k)
    return (0.0, 0.0, -1.5 + bend * 0.8, lerp(20.0, 13.0, k),
            x3 - d * math.sin(th), y3 - d * math.cos(th), x3, y3)


# ---- petals: a lily-like ring of six, three outer and three inner (docs/flowers.md 7.4: constant-curvature
# arcs, pitched toward the viewer). Closed they make a bud seen from the side; open, a star facing us.
# Each opens in its own smoothstep window: outer ones first, and not in ring order.
_U = (0.0, 0.17, 0.34, 0.51, 0.68, 0.84, 1.0)
_PROF = tuple(_profile(u) for u in _U)
# per layer: closed/open angle from the axis, closed/open curl, length, closed/open half-width,
# first window start, rim class, fill ramp (base -> tip) and its classes
_LAYERS = (
    (0.22, 1.18, -0.95, 0.45, 1.0, 0.3, 0.19, 0.05, "d", ":.  ", "dd  "),    # outer three: deep violet
    (0.18, 0.98, -0.85, 0.35, 0.9, 0.3, 0.16, 0.30, "e", ":.  ", "rr  "),    # inner three: pink, pale rims
)
_PETALS = []
for _i in range(6):
    _ac, _ao, _kc, _ko, _L, _wc, _wo, _a, _krim, _ramp, _rcls = _LAYERS[_i % 2]
    _th = -math.pi / 2 + math.pi / 3 * _i + _jit(10 + _i, 0.08)
    _a += 0.08 * ((_i // 2) * 2 % 3) + _jit(20 + _i, 0.02)     # staggered, not in ring order
    _PETALS.append((_i % 2, math.cos(_th), math.sin(_th), _ac, _ao + _jit(30 + _i, 0.06), _kc,
                    _ko + _jit(40 + _i, 0.08), _L * (1 + _jit(50 + _i, 0.06)), _wc, _wo, _a, _a + 0.45,
                    _krim, _ramp, _rcls))
_PETALS.sort()

# cells (col, row) cleared around the open flower's heart
_CLEAR = ((-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, -1), (0, -1), (1, -1), (-1, 1), (0, 1), (1, 1))

# ---- leaves: (attach s, side, length, angle above horizontal, curl, unfurl window)
_LEAVES = (
    (0.20, 1, 6.5 + _jit(60, 0.6), 0.5, -0.95, 0.30, 0.72),
    (0.33, -1, 6.0 + _jit(61, 0.6), 0.62, -0.75, 0.45, 0.88),
)
_LU = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
_LPROF = tuple(_profile(u) for u in _LU)

# ---- halo: a seeded stipple around the head, densest near it; sorted so a glow level shows a prefix
# (nothing at glow 0, more and farther cells as it rises)
_HALO = []
for _dr in range(-8, 9):
    for _dc in range(-17, 18):
        _d = math.sqrt(_dc * _dc + 4 * _dr * _dr) / 17.0
        if 0.2 < _d < 1.0:                          # not inside the dark ring around the heart
            _b = (1 - _d) ** 2.5
            _k = ((hash32(_dc + 64, _dr + 64, 9) & 0xFFFF) + 1) / 65537.0 / (_b * 0.8)
            if _k <= 1.0:
                _HALO.append((_k, _dc, _dr, _b))
_HALO.sort()


def _dot(ch, cl, x, y, g, k):
    """Put one glyph at a point in square units."""
    c = int(_BC + x + 100.5) - 100
    r = int(_BR - y * 0.5 + 100.5) - 100
    if 0 <= c < COLS and 0 <= r < ROWS:
        ch[r * COLS + c] = g
        cl[r * COLS + c] = k


def _shape(ch, cl, cx, cy, wx, wy, krim, ktip, ramp, rcls):
    """A petal/leaf from its centreline and half-width vectors: interior rows filled, then outlined."""
    lo = [COLS] * ROWS
    hi = [-1] * ROWS
    rim = []                                        # (cell, glyph, class, col, row)
    rmin, rmax = ROWS, -1
    m = len(cx) - 1
    for sgn in (1.0, -1.0):
        start = len(rim)
        last = -1
        for k in range(m):
            x0, y0 = cx[k] + sgn * wx[k], cy[k] + sgn * wy[k]
            dx, dy = cx[k + 1] + sgn * wx[k + 1] - x0, cy[k + 1] + sgn * wy[k + 1] - y0
            g = _rim_glyph(dx, dy, sgn * (wx[k] + wx[k + 1]))    # None: flat, picked per cell below
            kk = krim if k < m * 0.6 else ktip
            c0, r0 = _BC + x0 + 100.5, _BR - y0 * 0.5 + 100.5
            dr = -dy * 0.5
            n = int(max(dx if dx > 0 else -dx, dr if dr > 0 else -dr)) + 1
            sx, sr = dx / n, dr / n
            for j in range(n + 1 if k == m - 1 else n):
                rf = r0 + sr * j
                c = int(c0 + sx * j) - 100
                r = int(rf) - 100
                if c < 0 or c >= COLS or r < 0 or r >= ROWS:
                    continue
                i = r * COLS + c
                if i == last:
                    continue
                while len(rim) > start + 1 and -1 <= rim[-2][3] - c <= 1 and -1 <= rim[-2][4] - r <= 1:
                    rim.pop()                       # skip corners: outlines stay one cell wide
                rim.append((i, g or _flat(rf - int(rf)), kk, c, r))
                last = i
                if c < lo[r]:
                    lo[r] = c
                if c > hi[r]:
                    hi[r] = c
                if r < rmin:
                    rmin = r
                if r > rmax:
                    rmax = r
    # interior: fill between the outline's extremes on each row, density ramp from base to tip
    bx, by = cx[0], cy[0]
    tx, ty = cx[m] - bx, cy[m] - by
    inv = 1.0 / (tx * tx + ty * ty + 1e-9)
    nr = len(ramp)
    for r in range(rmin, rmax + 1):
        a, b = lo[r] + 1, hi[r]
        if a < b:
            py = ((_BR - r) * 2.0 - by) * ty
            base = r * COLS
            for c in range(a, b):
                g = int(((c - _BC - bx) * tx + py) * inv * nr)
                g = 0 if g < 0 else nr - 1 if g >= nr else g
                ch[base + c] = ramp[g]
                cl[base + c] = rcls[g]
    for (i, g, k, c, r) in rim:
        ch[i] = g
        cl[i] = k


def _leaf(ch, cl, x, y, side, length, a0, curl, k):
    a0 += (1 - k) * 0.8                             # young leaves point up, then unfurl outward
    L = length * k
    cx, cy, wx, wy = [], [], [], []
    for j, u in enumerate(_LU):
        h = curl * u * 0.5
        am, al, sc = a0 + h, a0 + curl * u, L * u * _sinc(h)
        cx.append(x + sc * side * math.cos(am))
        cy.append(y + sc * math.sin(am))
        w = 0.22 * L * _LPROF[j]
        wx.append(-w * math.sin(al) * side)
        wy.append(w * math.cos(al))
    _shape(ch, cl, cx, cy, wx, wy, "l", "k", ":. ", "ll ")


def _head(ch, cl, hx, hy, ax, ay, S, bloom):
    """Petals around the axis (ax, ay) at the anchor (hx, hy): outer layer then inner, far before near."""
    rx, ry = ay, -ax                                # the head's right-hand side on screen
    tau = 0.25 + 0.72 * smoothstep(0.1, 0.8, bloom)  # pitch: side-on bud -> looking into the flower
    ct, st = math.cos(tau), math.sin(tau)
    ring = (0.04 + 0.12 * smoothstep(0.1, 0.6, bloom)) * S
    drawn = []
    for (ly, cth, sth, ac, ao, kc, ko, Lm, wc, wo, wa, wb, krim, ramp, rcls) in _PETALS:
        o = smoothstep(wa, wb, bloom)
        A0 = ac + (ao - ac) * o
        K = kc + (ko - kc) * o
        Lp = S * Lm
        if ly:                                      # inner petals grow out of the opening bud
            Lp *= smoothstep(wa - 0.2, wa + 0.15, bloom)
            if Lp < 0.6:
                continue
        w = (wc + (wo - wc) * o) * Lp
        lx = -sth * rx - cth * st * ax              # across the petal, (-sin th, 0, cos th), after the pitch
        ly_ = -sth * ry - cth * st * ay
        cx, cy, wx, wy = [], [], [], []
        z = 0.0
        for j, u in enumerate(_U):
            h = K * u * 0.5
            sc = Lp * u * _sinc(h)
            rr = sc * math.sin(A0 + h) + ring
            hh = sc * math.cos(A0 + h)
            yp = hh * ct - sth * rr * st
            cx.append(hx + cth * rr * rx + yp * ax)
            cy.append(hy + cth * rr * ry + yp * ay)
            ww = w * _PROF[j]
            wx.append(ww * lx)
            wy.append(ww * ly_)
            if j == 3:
                z = hh * st + sth * rr * ct         # depth of the petal's middle: bigger is nearer
        drawn.append((ly, z, cx, cy, wx, wy, krim, ramp, rcls))
    drawn.sort(key=lambda d: (d[0], d[1]))
    for (ly, z, cx, cy, wx, wy, krim, ramp, rcls) in drawn:
        _shape(ch, cl, cx, cy, wx, wy, krim, krim, ramp, rcls)
    # stamens (anthers between the petals) and the bright centre come late in the bloom
    ss = smoothstep(0.5, 0.92, bloom)
    if ss > 0.05:
        x, y = hx + 0.1 * S * ct * ax, hy + 0.1 * S * ct * ay
        if ss > 0.3:                                # a dark ring around the heart makes it glow
            for dc, dr in _CLEAR:
                _dot(ch, cl, x + dc, y - 2 * dr, " ", " ")
        rr = 0.32 * S * ss
        for k in range(6):
            a = math.pi / 3 * k
            c2, s2 = math.cos(a), math.sin(a)
            yp = 0.1 * S * ct - s2 * rr * st
            _dot(ch, cl, hx + c2 * rr * rx + yp * ax, hy + c2 * rr * ry + yp * ay, "*'"[k & 1], "g")
        if ss > 0.6:
            _dot(ch, cl, x - 1, y, "(", "g")
            _dot(ch, cl, x + 1, y, ")", "g")
        _dot(ch, cl, x, y, "o" if ss < 0.6 else "@", "c")


def _paint(ch, cl, chain, n):
    for (i, g, k, j) in chain:
        if j >= n:
            break
        ch[i] = g
        cl[i] = k


def _rows(buf):
    return ["".join(buf[r * COLS:(r + 1) * COLS]) for r in range(ROWS)]


def frame(grow, bloom, bend, glow):
    """-> (chars, cls): ROWS strings of COLS glyphs and matching colour-class letters (' ' = empty)."""
    ch = [" "] * _N
    cl = [" "] * _N
    n = int(smoothstep(0.0, 0.8, grow) * _NS)     # stem samples revealed, from the ground up
    if n == 0:
        return _rows(ch), _rows(cl)
    x0, y0, x1, y1, x2, y2, x3, y3 = _stem(smoothstep(0.0, 0.6, bloom), clamp(bend, -1.0, 1.0))
    ex1, ey1, ex2, ey2, ex3, ey3 = x1 - x0, y1 - y0, x2 - x1, y2 - y1, x3 - x2, y3 - y2
    fx1, fy1, fx2, fy2 = x2 - 2 * x1 + x0, y2 - 2 * y1 + y0, x3 - 2 * x2 + x1, y3 - 2 * y2 + y1

    # leaves, attached to the current stem curve once the stem has grown past them
    for (sa, side, length, a0, curl, la, lb) in _LEAVES:
        k = smoothstep(la, lb, grow)
        if k > 0.02 and n > sa * _NS:
            q = 1 - sa
            b0, b1, b2, b3 = q * q * q, 3 * q * q * sa, 3 * q * sa * sa, sa * sa * sa
            _leaf(ch, cl, b0 * x0 + b1 * x1 + b2 * x2 + b3 * x3, b0 * y0 + b1 * y1 + b2 * y2 + b3 * y3,
                  side, length, a0, curl, k)

    # stem: the whole curve as a one-cell-wide chain (thinned once, so growth only ever adds cells)
    chain = []                                      # (cell, glyph, class, first sample)
    hx = hy = tdx = 0.0
    tdy = 1.0
    for j in range(_NS):
        s, b0, b1, b2, b3, d0, d1, d2, e0, e1 = _BEZ[j]
        x = b0 * x0 + b1 * x1 + b2 * x2 + b3 * x3
        y = b0 * y0 + b1 * y1 + b2 * y2 + b3 * y3
        dx = d0 * ex1 + d1 * ex2 + d2 * ex3
        dy = d0 * ey1 + d1 * ey2 + d2 * ey3
        if j == n - 1:
            hx, hy, tdx, tdy = x, y, dx, dy         # the growing tip carries the bud
        rf = _BR - y * 0.5 + 100.5
        c = int(_BC + x + 100.5) - 100
        r = int(rf) - 100
        if not (0 <= c < COLS and 0 <= r < ROWS):
            continue
        i = r * COLS + c
        if chain and chain[-1][0] == i:
            continue
        while len(chain) > 1 and -1 <= chain[-2][0] % COLS - c <= 1 and -1 <= chain[-2][0] // COLS - r <= 1:
            chain.pop()                             # a corner the line can skip: keep it one cell wide
        curl = (dx * (e0 * fy1 + e1 * fy2) - dy * (e0 * fx1 + e1 * fx2)) / (dx * dx + dy * dy + 1e-9)
        chain.append((i, _stem_glyph(dx, dy, curl, rf - int(rf)), "v" if s < 0.55 else "w", j))

    # bud/head at the tip, along the tip's direction
    bud = smoothstep(0.5, 1.0, grow)
    tl = math.sqrt(tdx * tdx + tdy * tdy) + 1e-9
    ax, ay = tdx / tl, tdy / tl
    S = bud * lerp(6.0, 10.0, smoothstep(0.05, 0.85, bloom))
    # the closed bud hangs off the stem tip (stem on top, so growth never hides stem cells);
    # the open blossom faces us and hides the top of the stem behind it
    behind = bloom > 0.15
    if behind:
        _paint(ch, cl, chain, n)
    if bud > 0.05:
        _head(ch, cl, hx, hy, ax, ay, S, bloom)
    if not behind:
        _paint(ch, cl, chain, n)

    # halo: soft stipple in the empty cells around the head, denser and brighter toward it
    if glow > 0.0 and bud > 0.05:
        off = (0.5 - 0.4 * smoothstep(0.1, 0.8, bloom)) * S      # middle of the bud, then of the open face
        hc = int(_BC + hx + ax * off + 100.5) - 100
        hr = int(_BR - (hy + ay * off) * 0.5 + 100.5) - 100
        for (key, dc, dr, b) in _HALO:
            if key > glow:
                break
            c, r = hc + dc, hr + dr
            if 0 <= c < COLS and 0 <= r < ROWS:
                i = r * COLS + c
                if ch[i] == " ":
                    lv = glow * b
                    ch[i] = ":" if lv > 0.6 else "'" if lv > 0.35 else "."
                    cl[i] = "b" if lv > 0.45 else "a"

    return _rows(ch), _rows(cl)


if __name__ == "__main__":  # preview in a terminal: py site/flower.py
    for args in ((0.3, 0, 0, 0), (0.7, 0, 0, 0), (1, 0, 0, 0.3), (1, 0.5, 0, 0.6), (1, 1, 0, 1),
                 (1, 1, -1, 1), (1, 1, 1, 1), (1, 0, -1, 0.3), (1, 0, 1, 0.3)):
        chars, cls = frame(*args)
        print("grow=%s bloom=%s bend=%s glow=%s" % args)
        for a, b in zip(chars, cls):
            print("|" + a + "|   |" + b + "|")
        print()
