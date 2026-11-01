"""Render ending preview PNGs to build/previews/ending/ (look at them).

    .venv/Scripts/python.exe tools/preview_ending.py

A stand-in chase frame (ground, horizon, obstacles, red mouse, [NO] at the wall), then glitch moments
(glitch_*.png), dissolve moments (dissolve_*.png) and the face with its tear (face_*.png), each drawn on
the 320 x 320 canvas and scaled 3x nearest-neighbour; sheet_*.png puts each set side by side.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from letter.art import ending  # noqa: E402
from letter.engine.glyphs import Atlas  # noqa: E402
from letter.engine.timeline import hash32  # noqa: E402

OUT = ROOT / "build" / "previews" / "ending"
PAPER = (12, 9, 16)
BLACK = (0, 0, 0)
ROLE_RGB = {
    "g": (150, 132, 150), "h": (74, 64, 92), "o": (206, 194, 178), "m": (226, 58, 66),
    "n": (180, 176, 214), "w": (128, 116, 140), "x": (226, 58, 66), "t": (236, 224, 199),
}
FACE_RGB, TEAR_RGB = (176, 172, 206), (186, 214, 255)
FACE_XY = (64, 88)        # 24 x 12 cells of 8 x 12 px, centred on 320 x 320
Y_NUDGE = -3              # the 13 px font's 18 px glyph box, centred in a 12 px row


def frame():
    """A stand-in for the chase core's cornered frame: [(ch, role, x, y)]."""
    items = []
    for c in range(40):
        h = hash32(c, 1)
        items.append(("_-=~"[0 if h % 5 < 3 else h % 4], "g", c * 8, 240))
        if h % 3 == 0:
            items.append((".-_"[h % 3], "h", c * 8, 168))
    for c in range(40):
        if hash32(c, 9) % 3 == 0:
            items.append(("=~"[c % 2], "g", c * 8, 252))
    sprites = (
        (48, 228, ",;."), (96, 228, "o"), (152, 228, "|#|"), (200, 216, "[#]"), (200, 228, "[#]"),
    )
    for x, y, s in sprites:
        items += [(ch, "o", x + i * 8, y) for i, ch in enumerate(s)]
    for r, row in enumerate((" ()()  ", "~(  '> ", " ^  ^  ")):
        items += [(ch, "m", 232 + i * 8, 204 + r * 12) for i, ch in enumerate(row) if ch != " "]
    items += [(ch, "n", 280 + i * 8, 228) for i, ch in enumerate("[NO]")]
    items += [("|", "w", 312, 156 + r * 12) for r in range(8)]
    return items


def fade(rgb, a, bg):
    a = round(a * 16) / 16        # quantised so the glyph cache stays small
    return tuple(int(b + (c - b) * a) for c, b in zip(rgb, bg))


def canvas(bg):
    s = pygame.Surface((320, 320))
    s.fill(bg)
    return s


def draw_items(atlas, s, items, bg, extra=(0, 0)):
    atlas.draw(s, [(ch, fade(ROLE_RGB[role], a, bg), (round(x + extra[0]), round(y + extra[1]) + Y_NUDGE))
                   for ch, role, x, y, *rest in items for a in (rest[0] if rest else 1.0,) if a > 0])


def draw_flash(atlas, s, flash, e):
    """The scene's flash: half the cells of the canvas fill with noise glyphs, pale, at 0.4 x the flash."""
    tick = int(e * 60)
    rgb = fade((226, 220, 240), 0.4 * flash, PAPER)
    atlas.draw(s, [(ending.NOISE[h % len(ending.NOISE)], rgb, (c * 8, r * 12 + Y_NUDGE))
                   for r in range(27) for c in range(40) for h in (hash32(c, r, tick),) if h & 0x100])


def save(surface, name, shots):
    big = pygame.transform.scale_by(surface, 3)
    pygame.image.save(big, str(OUT / name))
    shots.append(big)
    print("wrote", OUT / name)


def sheet(shots, name, cols=3):
    w, h = shots[0].get_size()
    rows = (len(shots) + cols - 1) // cols
    out = pygame.Surface((cols * w + (cols - 1) * 6, rows * h + (rows - 1) * 6))
    out.fill((60, 60, 60))
    for i, s in enumerate(shots):
        out.blit(s, ((i % cols) * (w + 6), (i // cols) * (h + 6)))
    pygame.image.save(pygame.transform.smoothscale_by(out, 0.5), str(OUT / name))
    print("wrote", OUT / name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.init()
    atlas = Atlas("mono-bold", 13)
    items = frame()

    shots = []
    s = canvas(PAPER)
    draw_items(atlas, s, items, PAPER)
    save(s, "frame.png", shots)
    for d in (300, 120, 60, 10):     # the cornered tremble, a few instants each
        s = canvas(PAPER)
        rest = [it for it in items if it[1] != "n"]
        draw_items(atlas, s, rest, PAPER)
        for t in (0.0, 0.031, 0.077):
            dx, dy = ending.proximity_shake(d, t)
            draw_items(atlas, s, [(ch, r, x + dx, y + dy, 0.45) for ch, r, x, y in items if r == "n"], PAPER)
        save(s, f"tremble_d{d:03d}.png", shots)
    sheet(shots, "sheet_frame.png")

    shots = []
    flash_e = next(e / 1000 for e in range(300, 2000) if ending.glitch(items, e / 1000)[1] > 0.8)
    for e in (0.2, 0.7, 1.2, 1.6, 1.95, flash_e):
        out, flash = ending.glitch(items, e)
        s = canvas(PAPER)
        draw_items(atlas, s, out, PAPER)
        if flash:
            draw_flash(atlas, s, flash, e)
        save(s, f"glitch_{e:.2f}{'_flash' if flash else ''}.png", shots)
    sheet(shots, "sheet_glitch.png")

    shots = []
    for p in (0.08, 0.25, 0.42, 0.6, 0.75, 0.9):
        s = canvas(PAPER)
        # the scene fades the paper to black over the dissolve
        bg = fade(PAPER, 1 - p, BLACK)
        s.fill(bg)
        draw_items(atlas, s, ending.dissolve(items, p), bg)
        save(s, f"dissolve_{p:.2f}.png", shots)
    sheet(shots, "sheet_dissolve.png")

    shots = []
    for name, face_a, te in (("in", 0.5, None), ("held", 1.0, None), ("tear0.4", 1.0, 0.4), ("tear0.9", 1.0, 0.9),
                             ("tear2.0", 1.0, 2.0), ("tear3.0", 1.0, 3.0), ("tear4.0", 1.0, 4.0),
                             ("tear4.4", 1.0, 4.4), ("out", 0.4, None)):
        s = canvas(BLACK)
        fx, fy = FACE_XY
        rgb = fade(FACE_RGB, face_a, BLACK)
        atlas.draw(s, [(ch, rgb, (fx + c * 8, fy + r * 12 + Y_NUDGE)) for r, row in enumerate(ending.FACE)
                       for c, ch in enumerate(row)])
        if te is not None:
            for ch, col, row, a in ending.tear(te):
                atlas.draw(s, [(ch, fade(TEAR_RGB, a, BLACK), (fx + col * 8, round(fy + row * 12) + Y_NUDGE))])
        save(s, f"face_{name}.png", shots)
    sheet(shots, "sheet_face.png")


if __name__ == "__main__":
    main()
