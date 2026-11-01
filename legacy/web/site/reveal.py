"""YES choreography pieces: the writing crumbling into particles, the sheet that is pulled out, and timing.

Pure: runs in MicroPython (PyScript) and CPython tests. Frames are (chars, cls) like art.py.
"""
import art
from stage import bayer, hash32

# reveal timeline, seconds after YES (the stage phase lasts 4.5 s)
WRITE = (0.0, 1.4)    # writing crumbles
FLAP = (0.2, 1.5)     # flap folds open
PULL = (0.6, 2.3)     # sheet slides up out of the pocket
ZOOM = (2.3, 4.5)     # camera dives into the sheet's black middle

SHEET_W, SHEET_H = 47, 17
INSIDE = (3, 2, SHEET_W - 3, SHEET_H - 2)   # the empty black window: x0, y0, x1, y1 (exclusive)
FALL = 0.25            # how much progress a letter takes to crumble through the ramp
CRUMBLE = "#+:."       # a letter's last moments
MAX_PARTICLES = 30
LIFE = 0.35            # progress a particle lives for
RISE = 7               # rows a particle climbs over its life
SPAN = 1 - LIFE - 0.07  # letters are gone by here, so every speck has faded by progress 1

_BLANK = " " * art.ENV_W
_CELLS = [(x, y, ch, bayer(x, y)) for x, y, ch in art.writing() if ch != " "]
_LOW, _HIGH = min(c[1] for c in _CELLS) - RISE - 1, max(c[1] for c in _CELLS)


def writing(p):
    """Writing overlay at dissolve progress p (0 = intact, 1 = gone), same size as the envelope layers."""
    rows = range(art.HEAD + art.ENV_H)
    # only rows the words and their rising specks can reach are built as lists (MicroPython is slow)
    chars = [list(_BLANK) if _LOW <= y <= _HIGH else _BLANK for y in rows]
    cls = [list(_BLANK) if _LOW <= y <= _HIGH else _BLANK for y in rows]
    shown, q = 0, p / SPAN
    for i, (x, y, ch, th) in enumerate(_CELLS):
        d = (q * (1 + FALL) - th) / FALL  # <0 intact, 0..1 crumbling, >1 gone
        if d < 1:
            chars[y][x], cls[y][x] = (ch if d < 0 else CRUMBLE[int(d * len(CRUMBLE))]), "w"
            continue
        gone = (th + FALL) / (1 + FALL) * SPAN
        for j in range(2):  # each letter sheds two specks that drift up and fade
            age = p - gone - j * 0.06
            if 0 <= age < LIFE and shown < MAX_PARTICLES:
                py = y - 1 - int(age / LIFE * RISE)
                px = x + (hash32(i, j) % 3) - 1 + (1 if age > LIFE / 2 and hash32(j, i) % 2 else 0)
                if 0 <= py and 0 <= px < art.ENV_W and chars[py][px] == " ":
                    chars[py][px], cls[py][px] = ("." if age < LIFE * 0.6 else "'"), "m"
                    shown += 1
    return ["".join(r) for r in chars], ["".join(r) for r in cls]


def _sheet():
    chars, cls = [], []
    x0, y0, x1, y1 = INSIDE
    for y in range(SHEET_H):
        row, ks = [], []
        for x in range(SHEET_W):
            if y0 <= y < y1 and x0 <= x < x1:
                row.append(" ")
                ks.append("K")  # empty black window: it becomes the night
            else:
                h = hash32(x + 100, y)
                row.append(".'"[h % 2] if h % 9 == 0 else " ")
                ks.append("EFG"[y * 3 // SHEET_H])  # cream paper, lit from above
        chars.append("".join(row))
        cls.append("".join(ks))
    return chars, cls


SHEET = _sheet()


def sheet():
    """The second paper: a cream border around an empty black window."""
    return SHEET


def cover_scale(box, view_w, view_h):
    """Scale about the centre of box (x0, y0, x1, y1, in px) that makes it cover the whole viewport."""
    x0, y0, x1, y1 = box
    if x1 - x0 < 1 or y1 - y0 < 1:  # nothing laid out yet (hidden window): don't zoom
        return 1.0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return max(2 * max(cx, view_w - cx) / (x1 - x0), 2 * max(cy, view_h - cy) / (y1 - y0)) * 1.05
