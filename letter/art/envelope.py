"""The ASCII envelope (SPEC §9, ported from the web version): layers of glyphs plus a role per cell.

A layer is (rows, roles): equal-width strings. Roles:
' ' see-through   p paper   o fold or edge line   O lit top edge   k bottom edge   i lining   h wax   H seal edge
`colours()` turns roles into per-cell glyph and background colours, lit from directly above.
Pure (NumPy only).
"""
import math

import numpy as np

from letter.art import heart
from letter.engine.timeline import hash32

ENV_W, ENV_H = 67, 27              # body size in cells
CX, CY = ENV_W // 2, ENV_H // 2    # where the folds meet: flap tip and seal
HEAD = CY                          # rows above the body for the opening flap to swing into
TOP, BOT = HEAD, HEAD + ENV_H - 1  # the body's border rows inside a layer
TIP = TOP + CY
ROWS = HEAD + ENV_H


def _grid():
    return [[" "] * ENV_W for _ in range(ROWS)], [[" "] * ENV_W for _ in range(ROWS)]


def _put(g, x, y, ch, k):
    if 0 <= y < ROWS and 0 <= x < ENV_W:
        g[0][y][x], g[1][y][x] = ch, k


def line(g, x0, y0, x1, y1, k="o"):
    """Sloped line drawn with `-. / .-' runs; returns {row: (first_col, last_col)}. g=None measures only."""
    if y0 > y1:
        x0, y0, x1, y1 = x1, y1, x0, y0
    n, m = y1 - y0 + 1, abs(x1 - x0) + 1
    right = x1 >= x0
    spans = {}
    for i in range(n):
        a = i * m // n
        run = max(1, (i + 1) * m // n - a)
        if run == 1:
            s = "\\" if right else "/"
        else:
            s = "`" + "-" * (run - 2) + "." if right else "." + "-" * (run - 2) + "'"
        start = x0 + a if right else x0 - a - run + 1
        spans[y0 + i] = (start, start + run - 1)
        if g:
            for j, ch in enumerate(s):
                _put(g, start + j, y0 + i, ch, k)
    return spans


def _fill(g, left, right, tex, k):
    for y in left:
        if y in right:
            for x in range(left[y][1] + 1, right[y][0]):
                _put(g, x, y, tex[y][x], k)


def _grain(x, y):
    h = hash32(x, y) % 23
    return ".',"[h] if h < 3 else " "


def _lining(x, y):
    return "." if (x + 2 * y) % 6 == 0 or (x - 2 * y) % 6 == 0 else " "


GRAIN = [[_grain(x, y) for x in range(ENV_W)] for y in range(ROWS)]
LINING = [[_lining(x, y) for x in range(ENV_W)] for y in range(ROWS)]
POCKET = (line(None, 1, TOP + 1, CX, TIP), line(None, ENV_W - 2, TOP + 1, CX, TIP))


def _layers():
    """Back: lining in the pocket plus the top edge (the far edge: the sheet passes in front of it).
    Front: the opaque body with the pocket left see-through, side-flap edges and lower folds."""
    back, front, right = _grid(), _grid(), ENV_W - 1
    _fill(back, POCKET[0], POCKET[1], LINING, "i")
    for x in range(1, right):
        _put(back, x, TOP, "-", "O")
        _put(front, x, BOT, "-", "k")
    for x in (0, right):
        _put(back, x, TOP, ".", "O")
        _put(front, x, BOT, "'", "k")
    for y in range(TOP + 1, BOT):
        _put(front, 0, y, "|", "o")
        _put(front, right, y, "|", "o")
        for x in range(1, right):
            _put(front, x, y, GRAIN[y][x], "p")
    for y in POCKET[0]:
        if y in POCKET[1]:
            for x in range(POCKET[0][y][1] + 1, POCKET[1][y][0]):
                _put(front, x, y, " ", " ")
    line(front, 1, TOP + 1, CX, TIP)
    line(front, right - 1, TOP + 1, CX, TIP)
    line(front, CX, TIP, 1, BOT - 1)
    line(front, CX, TIP, right - 1, BOT - 1)
    return back, front


BACK, FRONT = _layers()
SEAL = [(c, r, ch, "h" if wax else "H") for c, r, ch, wax in heart.cells()]


def _squash(cells, k):
    """Seal cells squashed vertically to k of their height (the flap foreshortens as it turns)."""
    h = heart.SIZE[1]
    nh = max(1, round(h * k))
    rows = {}
    for i in range(nh):
        rows.setdefault(int((i + 0.5) * h / nh), []).append(i)
    return [(c, i, ch, k_) for c, r, ch, k_ in cells for i in rows.get(r, [])]


def flap_depth(theta):
    """Rows from hinge to flap tip for a flap opened theta degrees: CY closed, 0 flat, -CY folded up."""
    return round(CY * math.cos(theta * math.pi / 180))


def layers(d, seal=True):
    """(back, front) with the flap tip d rows below the hinge (negative: folded up behind the sheet)."""
    back = [r[:] for r in BACK[0]], [r[:] for r in BACK[1]]
    front = [r[:] for r in FRONT[0]], [r[:] for r in FRONT[1]]
    if d:
        g, s = (front, 1) if d > 0 else (back, -1)
        left = line(g, 1, TOP + s, CX, TOP + d)
        right = line(g, ENV_W - 2, TOP + s, CX, TOP + d)
        _fill(g, left, right, GRAIN if d > 0 else LINING, "p" if d > 0 else "i")
    if d > 0 and seal:  # the seal rides on the flap tip and turns away from us past 90 degrees
        x0, y0 = CX - heart.SIZE[0] // 2, TOP + d - heart.SIZE[1] * d // CY // 2
        for c, r, ch, k in _squash(SEAL, d / CY):
            _put(front, x0 + c, y0 + r, ch, k)
    return ("".join(r) for r in back[0]), ("".join(r) for r in back[1]), \
        ("".join(r) for r in front[0]), ("".join(r) for r in front[1])


def envelope(d, seal=True):
    """{'back': (rows, roles), 'front': (rows, roles)}."""
    br, bk, fr, fk = (list(x) for x in layers(d, seal))
    return {"back": (br, bk), "front": (fr, fk)}


# --- light ----------------------------------------------------------------------------------------

def light():
    """Per-cell light, lit from directly above: bright top, gentle falloff, darker into the edges,
    the top flap catching the most light and the side flaps tucked under it. Shape (ROWS, ENV_W)."""
    y, x = np.mgrid[0:ROWS, 0:ENV_W].astype(np.float32)
    v = 1.10 - 0.55 * np.clip((y - TOP) / ENV_H, 0, 1)
    d = np.minimum(np.minimum(x, ENV_W - 1 - x), np.clip(np.minimum(y - TOP, BOT - y), 0, None))
    v *= 1 - 0.25 * np.exp(-d / 2.5)
    reach = np.abs(x - CX) * CY / CX
    flap = (TIP - y) > reach
    sides = ~flap & ~((y - TIP) > reach)
    return v * np.where(flap, 1.06, np.where(sides, 0.93, 1.0))  # gentle: cell-sized steps show at the folds


LIGHT = light()
PAPER_BG = np.array((74, 60, 64), np.float32)    # warm paper under a lamp, on a dark page
PAPER_FG = np.array((168, 150, 128), np.float32)
LINE = np.array((246, 234, 210), np.float32)
LINING_BG = np.array((44, 26, 36), np.float32)
LINING_FG = np.array((168, 98, 128), np.float32)
WAX = np.array((226, 52, 70), np.float32)
SEAL_EDGE = np.array((120, 30, 44), np.float32)


def colours(rows, roles):
    """(fg (H, W, 3) uint8, bg (H, W, 4) uint8) for a layer; bg alpha 0 where a cell is see-through."""
    r = np.array([list(s) for s in roles])
    lit = LIGHT[..., None]
    fg = np.zeros(r.shape + (3,), np.float32)
    bg = np.zeros(r.shape + (4,), np.float32)
    paper = np.isin(r, ["p", "o", "O", "k", "h", "H"])
    bg[..., :3] = np.where(paper[..., None], PAPER_BG * lit, 0)
    bg[..., :3] = np.where((r == "i")[..., None], LINING_BG * (0.6 + 0.4 * lit), bg[..., :3])
    bg[..., 3] = np.where(r != " ", 255, 0)
    fg[:] = PAPER_FG * lit
    fg = np.where(np.isin(r, ["o", "O"])[..., None], LINE * np.clip(lit + 0.15, 0, 1.2), fg)
    fg = np.where((r == "k")[..., None], LINE * 0.55 * lit, fg)
    fg = np.where((r == "i")[..., None], LINING_FG * (0.6 + 0.4 * lit), fg)
    fg = np.where((r == "h")[..., None], WAX * (0.85 + 0.25 * lit), fg)
    fg = np.where((r == "H")[..., None], SEAL_EDGE, fg)
    return np.clip(fg, 0, 255).astype(np.uint8), np.clip(bg, 0, 255).astype(np.uint8)
