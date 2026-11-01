"""Render chase-game preview PNGs to build/previews/chase/ (look at them).

    .venv/Scripts/python.exe tools/preview_chase.py

Plays the course with a bot that jumps where a player would (and one that never jumps, for a stumble),
draws picture() on dark paper at 320 x 320 with the bundled mono-bold 13 px font, and saves each moment
scaled 3x nearest-neighbour, plus a contact sheet at 1x.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from letter.art import chase  # noqa: E402
from letter.engine.glyphs import Atlas  # noqa: E402

OUT = ROOT / "build" / "previews" / "chase"
BG = (12, 9, 16)
RGB = {"g": (122, 108, 96), "h": (66, 58, 70), "o": (196, 168, 132), "w": (150, 132, 116),
       "m": (220, 60, 70), "r": (110, 40, 50), "n": (180, 176, 214), "x": (214, 120, 110), "t": (236, 224, 199)}
DT = 1 / 60


def wants_jump(c):
    """Press where a player would: centre the jump over the next obstacle group ahead."""
    if c._jump is not None:
        return False
    centre = c._mx + sum(chase._BOX) / 2
    for x0, x1, *_ in c._groups[c._next:c._next + 2]:
        if (x0 + x1) / 2 > centre:
            return (x0 + x1) / 2 - centre <= c._v * chase._JUMP_T / 2
    return False


def draw(atlas, items):
    surf = pygame.Surface((chase.SIZE, chase.SIZE))
    surf.fill(BG)
    atlas.draw(surf, ((ch, RGB[role], (round(x), round(y))) for ch, role, x, y in items))
    return surf


def save(surf, name, scale=3):
    big = pygame.transform.scale_by(surf, scale) if scale != 1 else surf
    pygame.image.save(big, str(OUT / name))
    print("wrote", OUT / name)


def play(bot, until):
    """Step a fresh chase at 60 fps; yield it after each frame until until(c) is true."""
    c = chase.Chase()
    while not until(c):
        if bot and wants_jump(c):
            c.press()
        c.update(DT)
        yield c


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1, 1))
    atlas = Atlas("mono-bold", 13)
    shots, done = [], {}

    def grab(c, name, shake=(0.0, 0.0)):
        if name not in done:
            done[name] = c.t
            surf = draw(atlas, c.picture(shake))
            shots.append(surf)
            save(surf, f"{len(shots)}_{name}_t{c.t:05.1f}.png")

    corner_t = None
    for c in play(True, lambda c: c.cornered and c.t > corner_t + 0.5 if corner_t else False):
        if c.t >= 1.5:
            grab(c, "hint")
        if c.phase == "B" and c.t > 30 and c._h > 55:
            grab(c, "jump")
        if c.t >= 42:
            grab(c, "mid_B")
        if c.phase == "C" and c.t > 78:
            grab(c, "phase_C")
        if c.cornered and corner_t is None:
            corner_t = c.t
        if c._mx > c._end - 70:
            grab(c, "wall_in")
    grab(c, "cornered", (1.5, -1.0))
    for c in play(False, lambda c: c._trip > 0 and c.t - c._trip > 0.22):
        pass
    grab(c, "stumble")
    print({k: round(v, 2) for k, v in done.items()}, "cornered at", round(corner_t, 2))
    w = chase.SIZE
    sheet = pygame.Surface((w * 4, w * 2))
    for i, s in enumerate(shots):
        sheet.blit(s, (i % 4 * w, i // 4 * w))
    save(sheet, "sheet.png", 1)


if __name__ == "__main__":
    main()
