"""Big ASCII banners for the questions (SPEC §9).

The question is set in JetBrains Mono Bold, slanted and a little heavier, at 1 px per logical px, then
cut into character cells. Each cell takes the mark whose shape best matches the ink under it, so outlines
come out as / \\ ( ) | _ ' and friends; inside the strokes a bevel light from the top left picks heavy
marks (@ % #) where it is lit and lighter ones (* +) in shade. A sparse extrusion down and to the right
(. : / _) gives the letters depth, and a small vine runs underneath.

banner(text) -> dict: "rows" (list of str) and per-cell arrays "kind" (0 empty, 1 face, 2 side, 3 vine),
"light" (0..1, the face's bevel light) and "band" (0 top .. 1 bottom of the lettering), plus "glyph_px" and
"cell" (logical px): smaller lettering uses smaller marks, so every question keeps about the same detail.
The scene colours and animates it.
"""
import numpy as np
import pygame

from letter.engine import assets, glyphs

GLYPH_PX = (7.0, 10.0)                   # logical px of the marks: min, max (at EM_MAX)
CELL = (0.6, 0.9)                        # cell size in glyph px: rows packed a little so strokes connect
SUB = (3, 5)                             # samples per cell (x, y) for shape matching
MARKS = " .,:;'`\"^~-_=+*!|/\\()[]{}<>#%@&$"
SIDE = " .,:;'`-_/\\|"                    # the extrusion uses only light marks
INNER = "+*#%@"                          # stroke interiors, shade -> lit
TRACK, SPACE = 0.5, 0.28                 # letter advance and word space in em (the font's own is 0.6)
WEIGHT = 2                               # px of extra stroke weight at EM_MAX
DEPTH = 7                                # extrusion steps of (1, 1.1) px down-right at EM_MAX
EM_MAX, EM_MIN = 128, 70                 # a line that would be smaller than EM_MIN wraps onto two
LINE = 1.12                              # inked height of a line, in em
VINE = "~-.,_,.-~'*'~-.,_,.-~  <3  ~-.,_,.-~'*'~-.,_,.-~"
LIGHT = np.array([-0.55, -0.7, 0.45]) / np.linalg.norm([-0.55, -0.7, 0.45])   # from the top left, toward us
_templates = {}


def _font(em):
    f = pygame.font.Font(assets.path("fonts", glyphs.FILES["mono-bold"]), round(em))
    f.italic = True
    return f


def _width(text):
    """Advance of a line in em."""
    return sum(SPACE if c == " " else TRACK for c in text) + 0.6


def lines(text, box_w=1180):
    """One line, or two balanced ones when one line would be set smaller than EM_MIN."""
    if box_w / _width(text) >= EM_MIN or " " not in text:
        return [text]
    words = text.split(" ")
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return [" ".join(words[:best]), " ".join(words[best:])]


def _ink(text, f, em, weight):
    """Coverage (H, W) float32 of one line, 1 px per logical px, cropped to the ink."""
    out = np.zeros((f.get_height(), int(_width(text) * em + em)), np.float32)
    x = 0.3 * em
    for c in text:
        if c != " ":
            g = pygame.surfarray.array_alpha(f.render(c, True, (255, 255, 255))).T.astype(np.float32) / 255
            x0 = int(round(x - (0.6 - TRACK) * em / 2))
            w = min(g.shape[1], out.shape[1] - x0)
            np.maximum(out[:, x0:x0 + w], g[:, :w], out=out[:, x0:x0 + w])
        x += (SPACE if c == " " else TRACK) * em
    for _ in range(weight):   # a little heavier: max over the 4-neighbourhood
        out = np.maximum.reduce([out, np.roll(out, 1, 0), np.roll(out, -1, 0), np.roll(out, 1, 1), np.roll(out, -1, 1)])
    ys, xs = np.nonzero(out > 0.05)
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _blur(a, r):
    """Box blur of radius r (edges repeat)."""
    for axis in (0, 1):
        pad = [(r + 1, r) if i == axis else (0, 0) for i in range(2)]
        c = np.cumsum(np.pad(a, pad, mode="edge"), axis=axis)
        n = c.shape[axis]
        a = (np.take(c, range(2 * r + 1, n), axis) - np.take(c, range(0, n - 2 * r - 1), axis)) / (2 * r + 1)
    return a


def _sample(a, cols, rows):
    """Area-average a (H, W) 0..1 array onto rows x cols cells of SUB samples: (rows, cols, SUB[0]*SUB[1])."""
    s = pygame.Surface(a.shape[::-1], pygame.SRCALPHA)
    pygame.surfarray.pixels_alpha(s)[...] = (np.clip(a, 0, 1).T * 255).astype(np.uint8)
    small = pygame.surfarray.array_alpha(pygame.transform.smoothscale(s, (cols * SUB[0], rows * SUB[1])))
    small = small.T.astype(np.float32) / 255
    return small.reshape(rows, SUB[1], cols, SUB[0]).transpose(0, 2, 1, 3).reshape(rows, cols, -1)


def _shapes(chars):
    """Each mark's ink over the cell it is drawn in (glyphs hang from the cell's top-left), sampled like _sample."""
    if chars not in _templates:
        k = 8   # render big, then area-average down
        f = pygame.font.Font(assets.path("fonts", glyphs.FILES["mono-bold"]), round(GLYPH_PX[1] * k))
        out = []
        for ch in chars:   # the shapes are the same at any size: measure them once at the largest
            box = pygame.Surface((round(CELL[0] * GLYPH_PX[1] * k), round(CELL[1] * GLYPH_PX[1] * k)), pygame.SRCALPHA)
            if ch != " ":
                box.blit(f.render(ch, True, (255, 255, 255)), (0, 0))
            out.append(pygame.surfarray.array_alpha(pygame.transform.smoothscale(box, SUB)).T.ravel() / 255)
        _templates[chars] = np.array(out, np.float32)
    return _templates[chars]


def _match(cells, chars):
    """Best-fitting mark per cell (cells: (rows, cols, n) coverage)."""
    t = _shapes(chars)
    k = _shapes(MARKS)[MARKS.index("@")].mean()   # a solid cell should match the densest mark
    d = ((cells[:, :, None, :] * k - t[None, None]) ** 2).sum(-1)
    return np.array(list(chars))[d.argmin(-1)]


def banner(text, box_w=1180, box_h=192):
    parts = lines(text, box_w)
    vine_h = 2 * CELL[1] * GLYPH_PX[1]
    em = min(EM_MAX, box_w * 0.97 / max(_width(p) for p in parts), (box_h - vine_h) / (len(parts) * LINE))
    gp = min(GLYPH_PX[1], max(GLYPH_PX[0], GLYPH_PX[1] * em / EM_MAX))
    cell = (CELL[0] * gp, CELL[1] * gp)
    depth = max(3, round(DEPTH * em / EM_MAX))
    f = _font(em)
    inks = [_ink(p, f, em, max(1, round(WEIGHT * em / EM_MAX))) for p in parts]
    gap = round(0.1 * em)
    w = max(i.shape[1] for i in inks) + 2 * depth + 4
    h = sum(i.shape[0] for i in inks) + gap * (len(inks) - 1) + 2 * depth + 4
    face = np.zeros((h, w), np.float32)
    down = np.zeros((h, 1), np.float32)   # 0 at the top of each line's lettering, 1 at its bottom
    y = 2
    for i in inks:
        x = (w - depth - i.shape[1]) // 2
        face[y:y + i.shape[0], x:x + i.shape[1]] = i
        down[y:y + i.shape[0], 0] = np.linspace(0, 1, i.shape[0])
        y += i.shape[0] + gap
    side = np.zeros_like(face)
    for k in range(1, depth + 1):
        dx, dy = k, round(k * 1.1)
        np.maximum(side[dy:, dx:], face[:-dy, :-dx], out=side[dy:, dx:])
    side = np.clip(side - 1.5 * face, 0, 1)
    hgt = _blur(_blur(face, 3), 3)
    gy, gx = np.gradient(hgt)
    n = np.stack([-gx, -gy, np.full_like(hgt, 0.12)])
    lit = np.clip(np.tensordot(LIGHT, n / np.linalg.norm(n, axis=0), 1), 0, 1) * face

    rows, cols = int(np.ceil(h / cell[1])), int(np.ceil(w / cell[0]))
    pad = lambda a: np.pad(a, ((0, max(0, round(rows * cell[1]) - h)), (0, max(0, round(cols * cell[0]) - w))))  # noqa: E731
    fc, sc = _sample(pad(face), cols, rows), _sample(pad(side), cols, rows)
    cov, scov = fc.mean(-1), sc.mean(-1)
    light = _sample(pad(lit), cols, rows).sum(-1) / np.maximum(fc.sum(-1), 1e-6)
    band = _sample(pad(face * down), cols, rows).sum(-1) / np.maximum(fc.sum(-1), 1e-6)
    chars = _match(fc, MARKS)
    inner = cov > 0.8
    ramp = np.array(list(INNER))
    chars[inner] = ramp[(np.clip((light[inner] - 0.15) / 0.75, 0, 0.999) * len(INNER)).astype(int)]
    is_side = (cov < 0.12) & (scov > 0.12)
    chars[is_side] = _match(sc, SIDE)[is_side]
    kind = np.where(cov >= 0.12, 1, np.where(is_side, 2, 0)).astype(np.uint8)
    chars[kind == 0] = " "
    kind[chars == " "] = 0

    # the vine, one blank row below the lettering
    vine = VINE.center(cols)[:cols]
    chars = np.vstack([chars, np.full((1, cols), " "), np.array(list(vine))[None]])
    kind = np.vstack([kind, np.zeros((1, cols), np.uint8), np.where(np.array(list(vine)) != " ", 3, 0)[None]])
    light = np.vstack([light, np.zeros((2, cols), np.float32)])
    band = np.vstack([band, np.ones((2, cols), np.float32)]).clip(0, 1).astype(np.float32)
    return {"rows": ["".join(r) for r in chars], "kind": kind, "light": light.astype(np.float32), "band": band,
            "glyph_px": gp, "cell": cell}
