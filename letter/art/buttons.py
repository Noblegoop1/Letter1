"""YES / NO buttons as ASCII: a framed box around big pixel letters (kept from the web version, SPEC §9).

Pure text: returns rows of characters plus a per-cell role ("f" frame, "w" word, " " empty).
"""
from letter.engine.timeline import hash32

# 5x7 pixel letters; each pixel prints as two columns so letters come out roughly square
FONT = {
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
}
REST = "#"
LOOKALIKE = "#@%&$8B*+="   # dense glyphs: a scrambling letter keeps its weight
WILD = "!?*~^+=<>"
SETTLE = (0.12, 0.6)       # every cell is back to rest within this window (seconds after hover)
INNER = 38                 # cells inside the frame: YES is 34 wide plus padding


def big_mask(word):
    """Rows of '#'/' ' for a word in the pixel font."""
    return [".".join(FONT[ch][r] for ch in word).replace("#", "##").replace(".", "  ") for r in range(7)]


def scramble(mask, e):
    """Hover shift e seconds in: each cell cycles look-alike glyphs at ~30 Hz until its own moment,
    then settles; the shape (which cells are ink) never changes."""
    out = []
    for r, row in enumerate(mask):
        cells = []
        for c, ch in enumerate(row):
            settle = SETTLE[0] + (SETTLE[1] - SETTLE[0]) * (hash32(r, c, 7) % 100) / 100
            if ch == " " or e >= settle:
                cells.append(" " if ch == " " else REST)
            else:
                cells.append(LOOKALIKE[hash32(r, c, int(e * 30)) % len(LOOKALIKE)])
        out.append("".join(cells))
    return out


def tantrum(mask, t):
    """NO's wild frame: glyphs jump about quickly (used by the NO route)."""
    return ["".join(" " if ch == " " else WILD[hash32(r, c, int(t * 24)) % len(WILD)]
                    for c, ch in enumerate(row)) for r, row in enumerate(mask)]


def _pad(row, w):
    left = (w - len(row)) // 2
    return " " * left + row + " " * (w - len(row) - left)


def frame(word, hover_e=None, wild_t=None):
    """(rows, roles) for a framed button. hover_e: seconds since hover began (None = at rest)."""
    mask = big_mask(word)
    if wild_t is not None:
        word_rows = tantrum(mask, wild_t)
    elif hover_e is not None and hover_e < SETTLE[1]:
        word_rows = scramble(mask, hover_e)
    else:
        word_rows = [row.replace("#", REST) for row in mask]
    edge = "-" * INNER
    rows, roles = ["." + edge + ".", "|" + " " * INNER + "|"], ["f" * (INNER + 2), "f" + " " * INNER + "f"]
    for row in word_rows:
        row = _pad(row, INNER)
        rows.append("|" + row + "|")
        roles.append("f" + "".join("w" if ch != " " else " " for ch in row) + "f")
    rows += [rows[1], "'" + edge + "'"]
    roles += [roles[1], roles[0]]
    return rows, roles


SIZE = (INNER + 2, 11)  # cells
