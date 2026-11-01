"""Render chase-game preview PNGs to build/previews/chase/ (look at them).

    .venv/Scripts/python.exe tools/preview_chase.py

Plays the course with a bot that jumps where a player would (and one that never jumps, for a stumble),
and draws moments the way the scene does: dark paper, picture()'s glyphs crisp at 3x (a 39 px atlas at
3x positions), and the envelope's NO button art fitted into no_rect(). Writes each moment at 960 x 960
and a contact sheet at half size.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pygame  # noqa: E402

from letter.art import buttons, chase  # noqa: E402
from letter.engine.glyphs import Atlas  # noqa: E402

OUT = ROOT / "build" / "previews" / "chase"
BG = (12, 9, 16)
RGB = {"g": (122, 108, 96), "h": (66, 58, 70), "o": (196, 168, 132), "w": (150, 132, 116),
       "m": (220, 60, 70), "r": (110, 40, 50), "x": (214, 120, 110), "t": (236, 224, 199)}
NO_WORD, NO_FRAME = (180, 176, 214), (244, 231, 204)
S = 3                                    # window px per logical px
DT = 1 / 60
NO_ROWS = buttons.frame("NO")


def wants_jump(c):
    """Press where a player would: centre the jump over the next obstacle group ahead."""
    if c._jump is not None:
        return False
    x, _, w, _ = c.pointer_rect()
    centre = c._cam + x + w / 2
    for x0, x1, *_ in c._groups[c._next:c._next + 2]:
        if (x0 + x1) / 2 > centre:
            return (x0 + x1) / 2 - centre <= c._v * chase._JUMP_T / 2
    return False


def draw(atlas, no_atlas, c):
    surf = pygame.Surface((chase.SIZE * S, chase.SIZE * S))
    surf.fill(BG)
    items = c.picture()
    world = [i for i in items if i[1] not in "rmx"]
    atlas.draw(surf, ((ch, RGB[role], (round(x * S), round(y * S))) for ch, role, x, y in world))
    x, y, w, h = c.no_rect()                 # NO between the world and the pointer, like the scene
    rows, roles = NO_ROWS
    cw, rh = w * S / len(rows[0]), h * S / len(rows)
    no_atlas.draw(surf, ((ch, NO_FRAME if role == "f" else NO_WORD, (round(x * S + i * cw), round(y * S + r * rh)))
                         for r, (row, rr) in enumerate(zip(rows, roles)) for i, (ch, role) in enumerate(zip(row, rr))))
    atlas.draw(surf, ((ch, RGB[role], (round(x * S), round(y * S))) for ch, role, x, y in items if role in "rmx"))
    return surf


def save(surf, name):
    pygame.image.save(surf, str(OUT / name))
    print("wrote", OUT / name)


def play(bot, until, aim=None):
    """Step a fresh chase at 60 fps; yield it after each frame until until(c) is true."""
    c = chase.Chase()
    while not until(c):
        if bot and wants_jump(c):
            c.press()
        if aim:
            c.aim(*aim(c))
        c.update(DT)
        yield c


def first_kind(c, kinds):
    """The next group ahead is one of kinds and its centre is about to pass under the pointer."""
    x, _, w, _ = c.pointer_rect()
    g = c._groups[c._next] if c._next < len(c._groups) else None
    return g and g[3] in kinds and abs((g[0] + g[1]) / 2 - (c._cam + x + w / 2)) < 6


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    pygame.init()
    pygame.display.set_mode((1, 1))
    atlas = Atlas("mono-bold", 13 * S)
    no_atlas = Atlas("mono-bold", 104 * S / 40 / 0.6)
    shots, done = [], {}

    def grab(c, name):
        if name not in done:
            done[name] = c.t
            surf = draw(atlas, no_atlas, c)
            shots.append(surf)
            save(surf, f"{len(shots)}_{name}_t{c.t:05.1f}.png")

    corner_t = None
    for c in play(True, lambda c: corner_t is not None and c.t > corner_t + 0.6):
        if c.t >= 1.5:
            grab(c, "hint")
        if first_kind(c, ("wall",)):
            grab(c, "jump_wall")
        if first_kind(c, ("tall", "stack")):
            grab(c, "jump_tall")
        if first_kind(c, ("gap", "ditch")):
            grab(c, "gap")
        if first_kind(c, ("twin", "step")):
            grab(c, "cluster")
        if c.t >= 42:
            grab(c, "mid_B")
        if c.phase == "C" and c.t > 78:
            grab(c, "phase_C")
        if c._cam > c._end - 40 and c._end + chase._WALL_X - c._cam < chase.SIZE - 20:
            grab(c, "wall_in")
        if c.cornered and corner_t is None:
            corner_t = c.t
    grab(c, "cornered")
    c.aim(*(v + 10 for v in c.no_rect()[:2]))
    for _ in range(40):
        c.update(DT)
    grab(c, "cornered_pointer_near")
    for c in play(False, lambda c: c._trip > 0 and c.t - c._trip > 0.22):
        pass
    grab(c, "stumble")
    for c in play(True, lambda c: c.t > 30, aim=lambda c: (16 + 96 * (c.t % 4 > 2), None)):
        pass
    grab(c, "steered")
    print({k: round(v, 2) for k, v in done.items()}, "cornered at", round(corner_t, 2))
    w = chase.SIZE * S // 2
    cols = 4
    sheet = pygame.Surface((w * cols, w * ((len(shots) + cols - 1) // cols)))
    for i, s in enumerate(shots):
        sheet.blit(pygame.transform.smoothscale(s, (w, w)), (i % cols * w, i // cols * w))
    save(sheet, "sheet.png")


if __name__ == "__main__":
    main()
