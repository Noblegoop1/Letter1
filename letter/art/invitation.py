"""The invitation (SPEC 10.7): the question the fireflies spell, and the night's own YES / NO buttons.

cells() sets the question in JetBrains Mono Bold, rasterises it and samples the ink on a jittered
hexagonal grid: every occupied cell is one firefly's place, so the letters are filled, not outlined. The
message sits in the upper sky (BOX), centred, above the sea holly's bract tips; the moon is just past the
end of the lines.

button() is one invitation button as luminous points: a soft dotted rounded outline with a spark that
travels round it, and a dot-matrix label made of the same points as the message. YES is warm firefly
gold, NO pale moon lavender. They flank the flower, under the message. draw() splats one with the
fireflies' dot kernel. Geometry is built once per spacing / button and cached.
"""
import numpy as np
import pygame

from letter.art import fireflies
from letter.engine import glyphs

MESSAGE = "Will you go on a date Tuesday?"
LINES = ("Will you go on", "a date Tuesday?")
EM = 48                     # font px of the message: strokes about 6 px, two dots wide
PITCH = 1.12                # line pitch in em
SPACING = 3.0               # default px between neighbouring firefly places
COVER = 0.4                 # share of a cell the ink must cover for it to get a firefly
JITTER = 0.08               # share of the spacing each place is nudged, so it reads as fireflies, not a grid
BOX = (104, 26, 432, 118)   # x, y, w, h in the 640 x 640 night: clear of the flower (its top is about y 135)

BUTTONS = {"yes": (42, 200, 116, 42), "no": (482, 200, 116, 42)}   # flanking the flower's head
LABELS = {"yes": "Yes", "no": "No"}
COLOUR = {"yes": np.array([1.0, 0.80, 0.40], np.float32), "no": np.array([0.80, 0.78, 1.0], np.float32)}
LABEL_EM, LABEL_SPACING = 24, 2.2
OUTLINE_STEP, CORNER, INSET = 3.4, 13.0, 3.0   # dot spacing along the outline, corner radius, inset (px)
LIFT = 2.0                  # px the dots rise at full hover
CORE, HALO = 2.4, 1.0       # dot kernel gains for draw()

_cache = {}


def _font(px):
    if not pygame.font.get_init():
        pygame.font.init()
    return glyphs.font("mono-bold", px)


def _ink(lines, px):
    """Coverage (H, W) float32 of the centred lines, 1 px per canvas px, cropped to the ink."""
    f = _font(px)
    rows = [pygame.surfarray.array_alpha(f.render(s, True, (255, 255, 255))).T.astype(np.float32) / 255 for s in lines]
    pitch = round(PITCH * px)
    w = max(r.shape[1] for r in rows)
    out = np.zeros((pitch * (len(rows) - 1) + rows[-1].shape[0], w), np.float32)
    for k, r in enumerate(rows):
        x = (w - r.shape[1]) // 2
        out[k * pitch:k * pitch + r.shape[0], x:x + r.shape[1]] = r
    ys, xs = np.nonzero(out > 0.05)
    return out[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def _sample(ink, spacing, seed):
    """(N, 2) float32 points (ink px) of a jittered hexagonal grid whose cells the ink covers at least
    COVER of (averaged over 3 x 3 samples per cell, so thin hooks and tails keep their dots)."""
    h, w = ink.shape
    rows = np.arange(0.5 * spacing, h, spacing * 0.866)
    pts = [(x, y) for j, y in enumerate(rows) for x in np.arange((0.25 + 0.5 * (j % 2)) * spacing, w, spacing)]
    p = np.array(pts, np.float32)
    p += np.random.default_rng(seed).uniform(-JITTER, JITTER, p.shape).astype(np.float32) * spacing
    cover = 0.0
    for dy in (-spacing / 3, 0.0, spacing / 3):
        for dx in (-spacing / 3, 0.0, spacing / 3):
            xi = np.clip(np.round(p[:, 0] + dx).astype(int), 0, w - 1)
            yi = np.clip(np.round(p[:, 1] + dy).astype(int), 0, h - 1)
            cover = cover + ink[yi, xi] / 9
    return p[cover >= COVER]


def cells(spacing=None):
    """(N, 2) float32 target points (canvas px, x, y): one per occupied cell of the message bitmap, centred
    in BOX, in reading order (top line first, left to right). About 1,000 at the default spacing."""
    s = float(spacing or SPACING)
    key = ("cells", s)
    if key not in _cache:
        ink = _ink(LINES, EM)
        p = _sample(ink, s, 3)
        x, y, w, h = BOX
        p += np.array([x + (w - ink.shape[1]) / 2, y + (h - ink.shape[0]) / 2], np.float32)
        p = p[np.lexsort((p[:, 0], np.round(p[:, 1] / (EM * PITCH * 0.5))))]
        p.flags.writeable = False
        _cache[key] = p
    return _cache[key]


def _outline(rect):
    """(M, 2) points evenly spaced round a rounded rectangle inset in rect, and each one's arc position 0..1."""
    x, y, w, h = rect
    x0, y0, x1, y1 = x + INSET, y + INSET, x + w - INSET, y + h - INSET
    r = min(CORNER, (x1 - x0) / 2, (y1 - y0) / 2)
    sw, sh, arc = x1 - x0 - 2 * r, y1 - y0 - 2 * r, 0.5 * np.pi * r
    total = 2 * (sw + sh) + 4 * arc
    s = np.arange(0, total, total / round(total / OUTLINE_STEP))
    out = np.empty((s.size, 2), np.float32)
    # walk: top edge, top-right corner, right edge, bottom-right corner, bottom, bottom-left, left, top-left
    segs = ((sw, (x0 + r, y0), (1, 0), None), (arc, (x1 - r, y0 + r), None, -0.5 * np.pi),
            (sh, (x1, y0 + r), (0, 1), None), (arc, (x1 - r, y1 - r), None, 0.0),
            (sw, (x1 - r, y1), (-1, 0), None), (arc, (x0 + r, y1 - r), None, 0.5 * np.pi),
            (sh, (x0, y1 - r), (0, -1), None), (arc, (x0 + r, y0 + r), None, np.pi))
    start = 0.0
    for length, (cx, cy), d, a0 in segs:
        m = (s >= start) & (s < start + length)
        u = s[m] - start
        if d is not None:
            out[m] = np.stack([cx + d[0] * u, cy + d[1] * u], -1)
        else:
            a = a0 + u / r
            out[m] = np.stack([cx + r * np.cos(a), cy + r * np.sin(a)], -1)
        start += length
    return out, s / total


def _geometry(name):
    if ("button", name) not in _cache:
        rect = BUTTONS[name]
        ring, arc = _outline(rect)
        ink = _ink((LABELS[name],), LABEL_EM)
        lab = _sample(ink, LABEL_SPACING, 5)
        x, y, w, h = rect
        lab += np.array([x + (w - ink.shape[1]) / 2, y + (h - ink.shape[0]) / 2 + 0.5], np.float32)
        rng = np.random.default_rng(17 if name == "yes" else 23)
        n = len(ring) + len(lab)
        _cache[("button", name)] = {
            "xy": np.concatenate([ring, lab]).astype(np.float32), "ring": len(ring), "arc": arc,
            "rate": rng.uniform(1.2, 3.2, n), "phase": rng.uniform(0, 2 * np.pi, n),
            "white": np.concatenate([np.zeros(len(ring)), np.full(len(lab), 0.25)])[:, None],
        }
    return _cache[("button", name)]


def button(name, hover=0.0, t=0.0):
    """(xy (M, 2), rgb (M, 3), brightness (M,)) float32 dots that draw button `name` ("yes" / "no"):
    outline first, then the label. hover 0..1 brightens it and lifts it LIFT px (the hitbox stays the
    rect); the dots shimmer over t and a spark travels round the outline."""
    g = _geometry(name)
    h = float(np.clip(hover, 0.0, 1.0))
    xy = g["xy"].copy()
    xy[:, 1] -= LIFT * h
    k = g["ring"]
    shimmer = 1.0 + 0.14 * np.sin(g["rate"] * t + g["phase"])
    b = np.empty(len(xy))
    d = (g["arc"] - (0.11 * t) % 1.0 + 0.5) % 1.0 - 0.5          # arc distance to the travelling spark
    b[:k] = (0.45 + 0.4 * h) * shimmer[:k] + (0.6 + 0.4 * h) * np.exp(-(d / 0.04) ** 2)
    b[k:] = (0.7 + 0.3 * h) * shimmer[k:]
    rgb = np.broadcast_to(COLOUR[name] + (1.0 - COLOUR[name]) * g["white"], (len(xy), 3))
    return xy, np.ascontiguousarray(rgb, np.float32), b.astype(np.float32)


def draw(canvas, name, hover=0.0, t=0.0, alpha=1.0):
    """Add button `name` to the night canvas ((640, 640, 3) float32, in place); alpha 0..1 fades it in."""
    if alpha <= 0:
        return
    xy, rgb, b = button(name, hover, t)
    c = rgb * (b * float(alpha))[:, None]
    fireflies.dots(canvas, xy, c * CORE, c * HALO)
