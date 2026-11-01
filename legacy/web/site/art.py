"""ASCII art for the love letter: headline, envelope layers, buttons and the HTML they become.

Pure functions only: no browser imports, so this runs in MicroPython (PyScript) and in CPython tests.
A frame is (chars, cls): two lists of equal-width strings, the characters and a colour class per cell.
Class ' ' is plain and see-through; any other class may also paint the cell's background (opaque paper).
"""
import math

from stage import hash32

# 5x7 pixel font with two descender rows; '#' is ink. Each pixel prints as two columns so the
# letters come out roughly square in a monospace cell (about twice as tall as wide).
FONT = {
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#", ".....", "....."),
    "i": ("#", ".", "#", "#", "#", "#", "#", ".", "."),
    "l": ("#.", "#.", "#.", "#.", "#.", "#.", ".#", "..", ".."),
    "y": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#", "....#", ".###."),
    "o": (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###.", ".....", "....."),
    "u": (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#", ".....", "....."),
    "p": (".....", ".....", "####.", "#...#", "#...#", "#...#", "####.", "#....", "#...."),
    "e": (".....", ".....", ".###.", "#...#", "#####", "#....", ".###.", ".....", "....."),
    "n": (".....", ".....", "#.##.", "##..#", "#...#", "#...#", "#...#", ".....", "....."),
    "?": (".###.", "#...#", "....#", "..##.", "..#..", ".....", "..#..", ".....", "....."),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#..", ".....", "....."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####", ".....", "....."),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####.", ".....", "....."),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#", ".....", "....."),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###.", ".....", "....."),
    " ": ("...",) * 9,
}

# Hand-drawn wax seal; ':' marks the inside, filled with wax glyphs when stamped.
HEART = (
    '  .-""-.   .-""-.  ',
    " /::::::\\ /::::::\\ ",
    "|::::::::V::::::::|",
    "|:::::::::::::::::|",
    " \\:::::::::::::::/ ",
    "  `.:::::::::::.'  ",
    "    `.:::::::.'    ",
    "      `.:::.'      ",
    "        `v'        ",
)

ENV_W, ENV_H = 67, 27              # envelope body, outer size in cells
CX, CY = ENV_W // 2, ENV_H // 2    # flap tip / seal position inside the body
HEAD = CY                          # empty rows above the body for the opening flap to swing into
TOP, BOT = HEAD, HEAD + ENV_H - 1  # the body's border rows inside an envelope layer
TIP = TOP + CY                     # where the X crosses: flap tip and seal at rest
WRITING = ((TIP + 6, "RAHHH"), (TIP + 8, "SHE OPENED IT"))   # (row, text), centred on CX

SHADES = "ABCD"                    # paper lit from above: A brightest ... D dimmest
VINE = "~-.,_,.-~'*'~-.,_,.-~  <3  ~-.,_,.-~'*'~-.,_,.-~"
REST = "#"                         # button letters at rest
SCRAMBLE = "#@%&$*+=8B"            # look-alike dense glyphs: a scrambling letter keeps its weight
WILD = "!?*~^+=<>"                 # NO's tantrum
RIPPLE = 0.7                       # seconds for a hover scramble to settle
WAX = "@@#%"
BTN_IN = 40                        # button inner width: YES (34 cols) plus padding


def _pad(row, w):
    left = (w - len(row)) // 2
    return " " * left + row + " " * (w - len(row) - left)


def _frame(rows, k):
    return rows, ["".join(k if ch != " " else " " for ch in r) for r in rows]


def big_mask(text):
    """Big pixel letters as rows of '#' and spaces, blank rows trimmed."""
    rows = []
    for r in range(9):
        rows.append(".".join(FONT[ch][r] for ch in text).replace("#", "##").replace(".", "  "))
    while not rows[0].strip():
        rows.pop(0)
    while not rows[-1].strip():
        rows.pop()
    return rows


# --- headline ---------------------------------------------------------------------------------

def _italic(mask):
    """Shear one column per row (top leans right): the same slope as '/', so strokes read as italic."""
    h = len(mask)
    return [" " * (h - 1 - r) + row + " " * r for r, row in enumerate(mask)]


def _strokes(mask):
    """Solid strokes with a '/' leading edge, so each sheared stroke reads as one leaning pen line."""
    return ["".join("/" if ch != " " and (x == 0 or row[x - 1] == " ") else ch for x, ch in enumerate(row))
            for row in mask]


def headline(narrow=False):
    """'Will you open ?' as lit italic letters with a drop shadow and a vine underneath."""
    if narrow:  # two lines for portrait screens
        a, b = _strokes(_italic(big_mask("Will you"))), _strokes(_italic(big_mask("open ?")))
        w = max(len(a[0]), len(b[0]))
        ink = [_pad(r, w) for r in a] + [" " * w] + [_pad(r, w) for r in b]
    else:
        ink = _strokes(_italic(big_mask("Will you open ?")))
    h, w = len(ink), len(ink[0]) + 2
    chars = [[" "] * w for _ in range(h + 3)]
    cls = [[" "] * w for _ in range(h + 3)]
    for y, row in enumerate(ink):  # soft dotted shadow first, one row down and two columns right
        for x, ch in enumerate(row):
            if ch != " ":
                chars[y + 1][x + 2], cls[y + 1][x + 2] = (":" if ch == "#" else "."), "z"
    for y, row in enumerate(ink):  # then the letters, brightest at the top as if lit from above
        band = "tuvx"[y * 4 // h]
        for x, ch in enumerate(row):
            if ch != " ":
                chars[y][x], cls[y][x] = ch, band
    vine = _pad(VINE, w)
    chars[h + 2] = list(vine)
    cls[h + 2] = ["l" if ch != " " else " " for ch in vine]
    return ["".join(r) for r in chars], ["".join(r) for r in cls]


# --- buttons ----------------------------------------------------------------------------------

def churn(mask, glyphs, t, hz=6):
    """Same shape as mask; each filled cell re-picks its glyph hz times a second at its own phase."""
    out = []
    for r, row in enumerate(mask):
        cells = []
        for c, ch in enumerate(row):
            if ch == " ":
                cells.append(" ")
            else:
                k = int(t * hz + (hash32(r, c) % 64) / 64)
                cells.append(glyphs[hash32(r, c, k) % len(glyphs)])
        out.append("".join(cells))
    return out


def ripple(mask, e):
    """Hover scramble e seconds in: each cell flickers at 30 Hz until its own moment, then settles."""
    out = []
    for r, row in enumerate(mask):
        cells = []
        for c, ch in enumerate(row):
            if ch == " " or e >= 0.25 + 0.45 * (hash32(r, c, 7) % 100) / 100:
                cells.append(REST if ch != " " else " ")
            else:
                cells.append(SCRAMBLE[hash32(r, c, int(e * 30)) % len(SCRAMBLE)])
        out.append("".join(cells))
    return out


def button(word, t, since=None, wild=False):
    """ASCII-framed button. since = when a hover scramble started (None = at rest); wild = NO's tantrum."""
    mask = big_mask(word)
    if wild:
        word_rows = churn(mask, WILD, t, 24)
    elif since is not None and 0 <= t - since < RIPPLE:
        word_rows = ripple(mask, t - since)
    else:
        word_rows = [row.replace("#", REST) for row in mask]
    k = word[0].lower()
    edge = "-" * BTN_IN
    chars = ["." + edge + ".", "|" + " " * BTN_IN + "|"]
    cls = ["f" * (BTN_IN + 2), "f" + " " * BTN_IN + "f"]
    for row in word_rows:
        row = _pad(row, BTN_IN)
        chars.append("|" + row + "|")
        cls.append("f" + "".join(k if ch != " " else " " for ch in row) + "f")
    chars += [chars[1], "'" + edge + "'"]
    cls += [cls[1], cls[0]]
    return chars, cls


# --- envelope ---------------------------------------------------------------------------------

def _grid(w, h):
    return [[" "] * w for _ in range(h)], [[" "] * w for _ in range(h)]


def _put(g, x, y, ch, k):
    chars, cls = g
    if 0 <= y < len(chars) and 0 <= x < len(chars[0]):
        chars[y][x] = ch
        cls[y][x] = k


def _line(g, x0, y0, x1, y1, k="o"):
    """Draw a sloped line with `-. / .-' runs; return {row: (first_col, last_col)}. g=None: measure only."""
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
                x = start + j
                _put(g, x, y0 + i, ch, k(x, y0 + i) if callable(k) else k)
    return spans


def _fill(g, left, right, layer, k):
    """Fill between two lines' spans with a texture layer; k is a class or a function of (x, y)."""
    for y in left:
        if y in right:
            for x in range(left[y][1] + 1, right[y][0]):
                _put(g, x, y, layer[y][x], k(x, y) if callable(k) else k)


def _paper(x, y):
    h = hash32(x, y) % 29
    return ".'"[h] if h < 2 else " "


def _lining(x, y):
    return "." if (x + 2 * y) % 6 == 0 or (x - 2 * y) % 6 == 0 else " "


def shade(x, y):
    """Paper shade for a body cell: lit from above; the flap catches most light, side flaps tuck under."""
    band = (y - TOP) * 4 // ENV_H
    dy, reach = y - TIP, abs(x - CX) * CY / CX  # rows from the crossing to the X lines at this column
    region = -1 if -dy > reach else 0 if dy > reach else 1
    return SHADES[min(3, max(0, band + region))]


def edge(x, y):
    """Outline class on the opaque front: cream ink over that spot's paper shade (a..d match A..D)."""
    return "abcd"[SHADES.index(shade(x, y))]


def _writing_cells():
    for y, text in WRITING:
        x0 = CX - len(text) // 2
        for i, ch in enumerate(text):
            yield x0 + i, y, ch


# Everything that never changes is built once at import: MicroPython took ~35 ms to build a whole
# frame, far over a 16 ms frame budget. Each frame copies these and draws only the flap and seal.
PAPER = [[_paper(x, y) for x in range(ENV_W)] for y in range(HEAD + ENV_H)]
LINING = [[_lining(x, y) for x in range(ENV_W)] for y in range(HEAD + ENV_H)]
SEAL = [("".join(WAX[hash32(dx, dy) % len(WAX)] if ch == ":" else ch for dx, ch in enumerate(row)),
         "".join("h" if ch == ":" else " " if ch == " " else "H" for ch in row))
        for dy, row in enumerate(HEART)]
POCKET = (_line(None, 1, TOP + 1, CX, TIP), _line(None, ENV_W - 2, TOP + 1, CX, TIP))


def _layers():
    """Back: the lined pocket. Front: opaque shaded body with the pocket left see-through for the sheet."""
    back, front, right = _grid(ENV_W, HEAD + ENV_H), _grid(ENV_W, HEAD + ENV_H), ENV_W - 1
    _fill(back, POCKET[0], POCKET[1], LINING, "i")
    for y in range(TOP + 1, BOT):
        _put(front, 0, y, "|", "o")
        _put(front, right, y, "|", "o")
        for x in range(1, right):
            _put(front, x, y, PAPER[y][x], shade(x, y))
    for x in range(1, right):
        _put(back, x, TOP, "-", "O")    # top edge catches the light; it is the far edge, so the sheet passes in front
        _put(front, x, BOT, "-", "k")   # bottom edge sits in shadow
    for x in (0, right):
        _put(back, x, TOP, ".", "O")
        _put(front, x, BOT, "'", "k")
    for y in POCKET[0]:
        if y in POCKET[1]:
            for x in range(POCKET[0][y][1] + 1, POCKET[1][y][0]):
                _put(front, x, y, " ", " ")
    _line(front, 1, TOP + 1, CX, TIP, edge)   # side flaps' top edges stay when the flap lifts
    _line(front, right - 1, TOP + 1, CX, TIP, edge)
    _line(front, CX, TIP, 1, BOT - 1, edge)
    _line(front, CX, TIP, right - 1, BOT - 1, edge)
    for x, y, _ in _writing_cells():    # clean paper under the writing overlay
        _put(front, x, y, " ", shade(x, y))
    return back, front


BACK, FRONT = _layers()


def _squash(rows, k):
    h = max(1, round(len(rows) * k))
    return [rows[int((i + 0.5) * len(rows) / h)] for i in range(h)]


def _stamp(g, rows, cx, cy):
    x0, y0 = cx - len(rows[0][0]) // 2, cy - len(rows) // 2
    for dy, (chars, cls) in enumerate(rows):
        for dx, ch in enumerate(chars):
            if ch != " ":
                _put(g, x0 + dx, y0 + dy, ch, cls[dx])


def _done(g):
    return ["".join(r) for r in g[0]], ["".join(r) for r in g[1]]


def flap_depth(theta):
    """Rows from hinge to flap tip for a flap opened theta degrees: CY closed, 0 flat, -CY flipped up."""
    return round(CY * math.cos(theta * math.pi / 180))


def envelope(d):
    """(back, front) layers with the flap tip d rows below the hinge (negative = folded up above it).
    The sheet goes between them: the closed flap is in front of it, the folded-up flap behind it."""
    back = [r[:] for r in BACK[0]], [r[:] for r in BACK[1]]
    front = [r[:] for r in FRONT[0]], [r[:] for r in FRONT[1]]
    if d:
        g, s, k = (front, 1, edge) if d > 0 else (back, -1, "o")
        left_edge = _line(g, 1, TOP + s, CX, TOP + d, k)
        right_edge = _line(g, ENV_W - 2, TOP + s, CX, TOP + d, k)
        # outside of the flap is lit paper; once it folds past upright we see its lined inside
        _fill(g, left_edge, right_edge, PAPER if d > 0 else LINING, shade if d > 0 else "i")
    if d > 0:  # the seal rides on the flap tip and turns away from us past 90 degrees
        _stamp(front, _squash(SEAL, d / CY), CX, TOP + d)
    return _done(back), _done(front)


def writing():
    """The words on the envelope as (col, row, char) in envelope-layer coordinates."""
    return list(_writing_cells())


PUFF_S = 0.5
_SPECKS = ((-1, 0.2), (1, 0.3), (-2, 0.8), (2, 0.6), (-3, 0.1), (3, 0.4))   # (direction, lift)


def puff(e):
    """Dust kicked up by the landing seed, e seconds after impact: 15 x 3 cells centred on column 7."""
    chars = [[" "] * 15 for _ in range(3)]
    if 0 <= e < PUFF_S:
        k = e / PUFF_S
        for dx, lift in _SPECKS:
            x = 7 + round(dx * (0.6 + 1.6 * k))
            y = 2 - round(lift * 2 * math.sin(math.pi * k))
            chars[y][x] = ".,`'"[int(k * 4)]
    return _frame(["".join(r) for r in chars], "d")


def shadow():
    """Soft ASCII shadow under the floating envelope."""
    rows = [_pad("." * 40, ENV_W), _pad("..:" + ":" * 50 + ":..", ENV_W), _pad("." * 40, ENV_W)]
    return _frame(rows, "s")


# --- HTML -------------------------------------------------------------------------------------

def to_html(chars, cls):
    """Frame -> HTML for a <pre>: one <span class> per run of same-coloured cells."""
    lines = []
    for row, ks in zip(chars, cls):
        out, i, n = [], 0, len(row)
        if n and ks.count(ks[0]) == n:  # one colour across the row: skip the per-cell scan (slow in MicroPython)
            i = n
            text = row.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            out.append(text if ks[0] == " " else '<span class="' + ks[0] + '">' + text + "</span>")
        while i < n:
            k, j = ks[i], i + 1
            while j < n and ks[j] == k:
                j += 1
            text = row[i:j]
            if "&" in text or "<" in text or ">" in text:
                text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            out.append(text if k == " " else '<span class="' + k + '">' + text + "</span>")
            i = j
        lines.append("".join(out))
    return "\n".join(lines)


if __name__ == "__main__":  # preview in a terminal: py site/art.py
    frames = [headline(), headline(True)] + list(envelope(CY)) + list(envelope(-CY))  # no *-unpacking: MicroPython
    for frame in frames + [button("YES", 0.0), button("YES", 1.2, since=1.0), shadow()]:
        print("\n".join(frame[0]) + "\n")
