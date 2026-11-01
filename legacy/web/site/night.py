"""Night meadow: the black page's paper fibres dissolve into grass that sways in a travelling wind.

Pure: runs in MicroPython (PyScript) and CPython tests; main.py owns the DOM. A frame is (chars, cls)
like art.py: equal-width strings, one colour-class letter per cell (' ' = no colour).
"""
import math

from stage import bayer, clamp, hash32, smoothstep

BAND = 0.35            # share of the rows that is grass
LIT = "abcdegh"        # grass, dark to bright: a-d at rest (back/bases darkest), e-h only under the light
WARM = "w"             # nearest tips under a strong light
FIBRE = "f"            # dim cream paper fibre
HAZE = "sk"            # sky haze near the horizon, dimmer then brighter
FLUTTERS = 8           # per-blade flutter buckets: each blade sways on its own phase and speed
MID = 12               # glyph tables hold 2 * MID + 1 lean levels; index MID = upright


def horizon(rows):
    """First row of the grass band."""
    return rows - max(2, int(rows * BAND + 0.5))


# --- wind -----------------------------------------------------------------------------------------
# Two gusts travel across the field (one rightwards, one leftwards, weighted by the wind direction) plus a
# short ripple. sin(kx - wt) = sin kx cos wt - cos kx sin wt, so the wind splits into an x-only basis and a
# t-only set of coefficients: ground() caches the basis per column and pays only multiply-adds per frame.
K1, W1 = 0.11, 1.3     # rightward gust: wavenumber per column, angular speed per second
K2, W2 = 0.083, 1.05   # leftward gust
K3, W3 = 0.37, 2.9     # ripple riding on the gusts


def _basis(x):
    u = K3 * x + 1.7 * math.sin(0.05 * x)
    return (math.sin(K1 * x), math.cos(K1 * x), math.sin(K2 * x), math.cos(K2 * x), math.sin(u), math.cos(u))


def _coef(t):
    s, c = math.sin, math.cos
    d = 0.7 * s(0.043 * t + 1.0) + 0.3 * s(0.017 * t + 4.0)          # direction, -1 (left) .. 1 (right)
    a = 0.58 + 0.2 * s(0.19 * t + 0.7) + 0.12 * s(0.071 * t + 2.9) + 0.1 * s(0.53 * t + 4.1)  # strength 0.16..1
    r, l, q = 0.275 * a * (1 + d), 0.275 * a * (1 - d), 0.15 * a
    p1, p2, p3 = W1 * t, W2 * t + 2.0, W3 * t
    return (0.3 * a * d, r * c(p1), -r * s(p1), l * c(p2), l * s(p2), q * c(p3), -q * s(p3))


def _lean(k, b):
    return k[0] + k[1] * b[0] + k[2] * b[1] + k[3] * b[2] + k[4] * b[3] + k[5] * b[4] + k[6] * b[5]


def wind(x, t):
    """Lean in [-1, 1] (positive = rightwards) at column x, time t seconds. Shared with flower and fireflies."""
    return _lean(_coef(t), _basis(x))


# --- layout: everything that depends only on the grid size, built once per size --------------------

def _table(l2, l1, up, r1, r2):
    """Lean level -> glyph: strong left, slight left, upright (under 1.5 levels either way), slight right,
    strong right. Wide enough for the largest lean ((1 + flutter) * 6 + bias 3 < MID), so no clamping."""
    return l2 * (MID - 3) + l1 * 2 + up * 3 + r1 * 2 + r2 * (MID - 3)


TIP = _table("\\", "`", "'", "'", "/")
BODY = _table("\\", "\\", "|", "/", "/")
BASES = (_table(";", ";", ";", ";", ";"), _table('"', '"', '"', '"', '"'), BODY)
FAR = _table(",", ",", ",", ",", ",")   # root of a distant blade
NONE = " " * (2 * MID + 1)


def _blades(cols, rows, top):
    """Scatter blades and small tufts over the band, back to front so nearer grass covers farther grass.
    Roots run a few rows past the bottom edge so the front is full. -> {(x, y): (j, h, blade hash, side)}:
    j rows above the root, blade height h, side -1/0/1 within a tuft."""
    cells = {}
    span = max(1, rows - 1 - top)
    for y in range(top, rows + 4):
        depth = min(1.0, (y - top) / span)                 # 0 at the horizon, 1 at the bottom edge
        for x in range(cols):
            hs = hash32(x, y, 11)
            if hs % 1000 >= 50 + 80 * depth:               # far grass sparse and fine, near grass fuller
                continue
            h = 2 + (hs >> 10) % (1 + int(3 * depth + 0.5))   # far blades short, near ones up to 5
            parts = [(0, h, 0)]
            if h >= 3 and hs >> 14 & 1:                    # a tuft: shorter side blades leaning out, \|/
                parts.append((-1, h - 1, -1))
            if h >= 3 and hs >> 15 & 1:
                parts.append((1, h - 1, 1))
            for dx, hh, side in parts:
                if 0 <= x + dx < cols:
                    bh = hash32(x + dx, y, 13)
                    for j in range(hh):
                        if top <= y - j < rows:
                            cells[(x + dx, y - j)] = (j, hh, bh, side)
    return cells


def _layout(cols, rows):
    """Per-row constants for one grid size. Band rows keep, per cell: glyph table T, flutter bucket P, lean
    gain A and offset B (level = (wind + flutter) * A + B), emergence threshold, shade (-1 = gap), tip flag."""
    top = horizon(rows)
    span = max(1, rows - 1 - top)
    blades = _blades(cols, rows, top)
    out = {"basis": [_basis(x) for x in range(cols)], "rows": []}
    for y in range(top):                                   # sky: a few dim dots close to the horizon
        k = y - (top - 6)
        hz = "".join("." if k >= 0 and hash32(x, y, 5) % 1000 < k * k * 2 else " " for x in range(cols))
        out["rows"].append({
            "sky": hz, "sky_cls": "".join((HAZE[1] if k >= 4 else HAZE[0]) if ch != " " else " " for ch in hz),
            "thr": [0.55 + 0.4 * bayer(x, y) for x in range(cols)],   # haze comes once the grass is well up
            "before": " " * cols, "before_cls": " " * cols})
    for y in range(top, rows):
        depth = (y - top) / span
        far = (0.3 + 0.7 * smoothstep(0, 0.7, depth)) * (1 - 0.25 * smoothstep(0.8, 1, depth))  # haze, ground shade
        T, P, A, B, thr, sh, tip, fib = [], [], [], [], [], [], [], []
        for x in range(cols):
            hs = hash32(x, y, 3)
            fib.append(".'"[hs >> 8 & 1] if hs % 100 < 6 else " ")
            thr.append(0.02 + 0.82 * (rows - 1 - y) / (rows - top) + 0.14 * bayer(x, y))   # bottom rows first
            b = blades.get((x, y))
            if b is None:
                T.append(NONE); P.append(0); A.append(0.0); B.append(MID + 0.5); sh.append(-1); tip.append(False)
                continue
            j, h, bh, side = b
            flex = (j + 1) / h                             # tips bend most, roots hardly at all
            stiff = (bh >> 4 & 15) / 15
            bias = ((bh >> 12 & 15) / 15 - 0.5) * 1.6 * flex + 2.2 * side   # crooked blades; tufts fan out
            T.append(TIP if j == h - 1 else BODY if j or side else BASES[bh % 3] if depth > 0.3 else FAR)
            P.append(bh >> 16 & (FLUTTERS - 1))
            A.append(6.0 * flex * (1 - 0.4 * stiff))
            B.append(MID + 0.5 + bias)
            v = far * (0.4 + 0.6 * j / (h - 1)) + ((hs >> 12 & 7) - 3.5) / 40
            sh.append(int(clamp(v * 4, 0, 3.99)))
            tip.append(j == h - 1)
        last, ks = " ", []
        for s in sh:                                       # gaps take the class on their left: fewer spans
            last = LIT[s] if s >= 0 else last
            ks.append(last)
        before = "".join(fib)
        out["rows"].append({
            "T": T, "P": P, "A": A, "B": B, "thr": thr, "sh": sh, "tip": tip, "after_cls": "".join(ks),
            "before": before, "before_cls": "".join(FIBRE if ch != " " else " " for ch in before)})
    # a blade grows from its base: no cell emerges before the cell below it in the same blade
    for y in range(rows - 2, top - 1, -1):
        thr, under = out["rows"][y]["thr"], out["rows"][y + 1]["thr"]
        for x in range(cols):
            b = blades.get((x, y))
            if b is not None and b[0] > 0 and under[x] > thr[x]:
                thr[x] = under[x]
    for R in out["rows"]:
        R["lo"], R["hi"] = min(R["thr"]), max(R["thr"])
    return out


_cache = {}


def _get(cols, rows):
    key = (cols, rows)
    if key not in _cache:
        _cache.clear()                                    # one live size: a resize replaces it
        _cache[key] = _layout(cols, rows)
    return _cache[key]


# --- frame ------------------------------------------------------------------------------------------

def ground(cols, rows, t, emerge, light=None):
    """Full-grid night frame (sky included). emerge 0..1: fibres -> grass from the bottom up.
    light: None or (col, row, strength 0..1) - grass near it steps up 1-3 brighter classes."""
    L = _get(cols, rows)
    k = _coef(t)
    cw = [_lean(k, b) for b in L["basis"]]
    fl = [0.15 * math.sin((1.6 + 0.23 * p) * t + 2.4 * p) for p in range(FLUTTERS)]
    X = range(cols)
    chars, cls = [], []
    for R in L["rows"]:
        if emerge <= R["lo"]:
            chars.append(R["before"])
            cls.append(R["before_cls"])
            continue
        if "sky" in R:
            now, now_cls = R["sky"], R["sky_cls"]
        else:
            T, P, A, B = R["T"], R["P"], R["A"], R["B"]
            now = "".join([T[i][int((cw[i] + fl[P[i]]) * A[i] + B[i])] for i in X])
            now_cls = R["after_cls"]
        if emerge <= R["hi"]:                              # emerging row: cell by cell
            thr, old, old_cls = R["thr"], R["before"], R["before_cls"]
            now = "".join([now[i] if emerge > thr[i] else old[i] for i in X])
            now_cls = "".join([now_cls[i] if emerge > thr[i] else old_cls[i] for i in X])
        chars.append(now)
        cls.append(now_cls)
    if light is not None and light[2] > 0:
        _spill(L, cls, emerge, light)
    return chars, cls


def _spill(L, cls, emerge, light):
    lx, ly, s = light
    r = 3 + 20 * s                                         # radius in columns; rows count 2.2x (flat pool)
    rows, cols = len(cls), len(cls[0])
    for y in range(max(horizon(rows), int(ly - r / 2.2)), min(rows, int(ly + r / 2.2) + 2)):
        R = L["rows"][y]
        sh, tip, thr = R["sh"], R["tip"], R["thr"]
        dy = (y - ly) * 2.2
        row = None
        for x in range(max(0, int(lx - r)), min(cols, int(lx + r) + 2)):
            if sh[x] < 0 or emerge <= thr[x]:
                continue
            f = 1 - ((x - lx) * (x - lx) + dy * dy) / (r * r)
            if f <= 0:
                continue
            if row is None:
                row = list(cls[y])
            row[x] = WARM if tip[x] and s > 0.6 and f > 0.85 else LIT[sh[x] + min(3, 1 + int(3 * s * f))]
        if row is not None:
            cls[y] = "".join(row)


if __name__ == "__main__":  # preview in a terminal: py site/night.py
    for t, e, lit in ((0.0, 0.0, None), (1.0, 0.5, None), (4.0, 1.0, None), (11.0, 1.0, None),
                      (11.0, 1.0, (40, 34, 1.0))):
        chars, cls = ground(80, 36, t, e, lit)
        print("t=%s emerge=%s light=%s" % (t, e, lit))
        print("\n".join(chars[horizon(36) - 7:]))
        if lit:
            print("\n".join(cls[horizon(36):]))
        print()
