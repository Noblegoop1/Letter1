"""ASCII art for the love letter.

Pure functions only: no browser imports, so this runs in MicroPython (PyScript) and in CPython tests.
A frame is (chars, cls): two lists of equal-width strings, the characters and a colour class per cell.
"""
import math

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

SOLID = "#@%&$"                    # dense glyphs: churning letters still read as solid shapes
WILD = "!?*~^+=<>"                 # NO's tantrum
WAX = "@@#%"
BTN_IN = 40                        # button inner width: YES (34 cols) plus padding


def _hash(a, b, c=0):
    h = (a * 374761393 + b * 668265263 + c * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1103515245) & 0xFFFFFFFF
    return h ^ (h >> 16)


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


def headline(narrow=False):
    if narrow:  # two lines for portrait screens
        a, b = big_mask("Will you"), big_mask("open ?")
        w = max(len(a[0]), len(b[0]))
        mask = [_pad(r, w) for r in a] + [" " * w] + [_pad(r, w) for r in b]
    else:
        mask = big_mask("Will you open ?")
    return _frame(mask, "t")


def churn(mask, glyphs, t, hz=6):
    """Same shape as mask; each filled cell re-picks its glyph hz times a second at its own phase."""
    out = []
    for r, row in enumerate(mask):
        cells = []
        for c, ch in enumerate(row):
            if ch == " ":
                cells.append(" ")
            else:
                k = int(t * hz + (_hash(r, c) % 64) / 64)
                cells.append(glyphs[_hash(r, c, k) % len(glyphs)])
        out.append("".join(cells))
    return out


def button(word, t, wild=False):
    """ASCII-framed button whose big letters churn; colour class is the word's first letter."""
    word_rows = churn(big_mask(word), WILD if wild else SOLID, t, 24 if wild else 12)
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


# --- envelope -------------------------------------------------------------------------------

def _grid(w, h):
    return [[" "] * w for _ in range(h)], [[" "] * w for _ in range(h)]


def _put(g, x, y, ch, k):
    chars, cls = g
    if 0 <= y < len(chars) and 0 <= x < len(chars[0]):
        chars[y][x] = ch
        cls[y][x] = k if ch != " " else " "


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
                _put(g, start + j, y0 + i, ch, k)
    return spans


def _fill(g, left, right, layer, k):
    for y in left:
        if y in right:
            for x in range(left[y][1] + 1, right[y][0]):
                _put(g, x, y, layer[y][x], k)


def _paper(x, y):
    h = _hash(x, y) % 29
    return ".'"[h] if h < 2 else " "


def _lining(x, y):
    return "." if (x + 2 * y) % 6 == 0 or (x - 2 * y) % 6 == 0 else " "


# Everything that never changes is built once at import: MicroPython took ~35 ms to build a whole
# frame, far over a 16 ms frame budget. Each frame now copies these and draws only the flap and seal.
PAPER = [[_paper(x, y) for x in range(ENV_W)] for y in range(HEAD + ENV_H)]
LINING = [[_lining(x, y) for x in range(ENV_W)] for y in range(HEAD + ENV_H)]
SEAL = [("".join(WAX[_hash(dx, dy) % len(WAX)] if ch == ":" else ch for dx, ch in enumerate(row)),
         "".join("h" if ch == ":" else " " if ch == " " else "H" for ch in row))
        for dy, row in enumerate(HEART)]


def _body():
    """Border, paper, the lined pocket under the flap and the lower seams."""
    g = _grid(ENV_W, HEAD + ENV_H)
    top, bot, right = HEAD, HEAD + ENV_H - 1, ENV_W - 1
    for y in range(top + 1, bot):
        _put(g, 0, y, "|", "o")
        _put(g, right, y, "|", "o")
        for x in range(1, right):
            _put(g, x, y, PAPER[y][x], "p")
    for x in range(1, right):
        _put(g, x, top, "-", "o")
        _put(g, x, bot, "-", "o")
    for x in (0, right):
        _put(g, x, top, ".", "o")
        _put(g, x, bot, "'", "o")
    tip = top + CY
    # lining shows wherever the flap no longer covers its pocket
    _fill(g, _line(None, 1, top + 1, CX, tip), _line(None, right - 1, top + 1, CX, tip), LINING, "i")
    _line(g, CX, tip, 1, bot - 1)
    _line(g, CX, tip, right - 1, bot - 1)
    return g


BODY = _body()


def _squash(rows, k):
    h = max(1, round(len(rows) * k))
    return [rows[int((i + 0.5) * len(rows) / h)] for i in range(h)]


def _stamp(g, rows, cx, cy):
    x0, y0 = cx - len(rows[0][0]) // 2, cy - len(rows) // 2
    for dy, (chars, cls) in enumerate(rows):
        for dx, ch in enumerate(chars):
            if ch != " ":
                _put(g, x0 + dx, y0 + dy, ch, cls[dx])


def flap_depth(theta):
    """Rows from hinge to flap tip for a flap opened theta degrees: CY closed, 0 flat, -CY flipped up."""
    return round(CY * math.cos(theta * math.pi / 180))


def envelope(d):
    """The envelope with its flap tip d rows below the hinge (negative = folded up above it)."""
    g = [r[:] for r in BODY[0]], [r[:] for r in BODY[1]]
    if d:
        s, top = (1 if d > 0 else -1), HEAD
        left_edge = _line(g, 1, top + s, CX, top + d)
        right_edge = _line(g, ENV_W - 2, top + s, CX, top + d)
        # outside of the flap is paper; once it folds past upright we see its lined inside
        _fill(g, left_edge, right_edge, PAPER if d > 0 else LINING, "p" if d > 0 else "i")
    if d > 0:  # the seal rides on the flap tip and turns away from us past 90 degrees
        _stamp(g, _squash(SEAL, d / CY), CX, HEAD + d)
    return ["".join(r) for r in g[0]], ["".join(r) for r in g[1]]


# --- helpers for main.py ------------------------------------------------------------------------

def ease(x):
    """Cubic ease-in-out, clamped to [0, 1]."""
    x = 0 if x < 0 else 1 if x > 1 else x
    return 4 * x * x * x if x < 0.5 else 1 - (2 - 2 * x) ** 3 / 2


def to_html(chars, cls):
    """Frame -> HTML for a <pre>: one <span class> per run of same-coloured cells."""
    lines = []
    for row, ks in zip(chars, cls):
        out, i, n = [], 0, len(row)
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
    for frame in (headline(), headline(True), envelope(CY), envelope(CY // 2), envelope(-CY),
                  button("YES", 0.0), button("NO", 0.0)):
        print("\n".join(frame[0]) + "\n")
