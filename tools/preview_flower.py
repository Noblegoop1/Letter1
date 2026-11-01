"""Render sea holly previews to build/previews/flower/ (PNG): the flower on the real night.

    .venv/Scripts/python.exe tools/preview_flower.py

Each state is drawn as the scene draws it: sky -> meadow back -> flower -> meadow front -> a copy of the
scene's glow pass. Writes one PNG per state, a 2x nearest-neighbour crop of the head (*_x2.png), a strip
of the whole sequence, a bend grid, and prints particle counts and init and render times.
"""
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from letter.art import flower, meadow, sky  # noqa: E402

S = 640
OUT = os.path.join(ROOT_DIR, "build", "previews", "flower")
# name, grow, bloom, glow, t
STATES = (
    ("grow_030", 0.3, 0.0, 0.08, 1.0), ("grow_060", 0.6, 0.0, 0.15, 2.0), ("grow_085", 0.85, 0.0, 0.21, 3.0),
    ("bud", 1.0, 0.0, 0.25, 4.0),
    ("bloom_025", 1.0, 0.25, 0.44, 5.0), ("bloom_050", 1.0, 0.5, 0.62, 5.5), ("bloom_075", 1.0, 0.75, 0.81, 6.0),
    ("bloomed_a", 1.0, 1.0, 1.0, 9.0), ("bloomed_b", 1.0, 1.0, 0.95, 23.7),
)


def glow(c, strength):
    """The scene's bloom pass: 1/8 samples above 0.42, blurred, scaled up and added (8-bit)."""
    small = (c[2::8, 2::8] + c[6::8, 6::8]) * 0.5
    g = np.clip((small - 0.42) * (255 * strength), 0, 255).astype(np.uint8)
    surf = pygame.image.frombuffer(np.ascontiguousarray(g), (S // 8, S // 8), "RGB")
    halo = pygame.transform.smoothscale(pygame.transform.gaussian_blur(surf, 2), (S, S))
    return np.clip(np.clip(c, 0, 1) * 255 + pygame.surfarray.array3d(halo).swapaxes(0, 1), 0, 255).astype(np.uint8)


def save(rgb, name, crop=None, k=2):
    if crop:
        x, y, w, h = crop
        rgb = np.repeat(np.repeat(rgb[y:y + h, x:x + w], k, 0), k, 1)
    pygame.image.save(pygame.surfarray.make_surface(np.ascontiguousarray(rgb.swapaxes(0, 1))), os.path.join(OUT, name))


def main():
    os.makedirs(OUT, exist_ok=True)
    t0 = time.perf_counter()
    f = flower.Flower()
    init_ms = (time.perf_counter() - t0) * 1000
    m, sk = meadow.Meadow(), sky.Sky()
    c = np.empty((S, S, 3), np.float32)

    def scene(grow, bloom, gl, t, bend=0.0):
        after = max(0.0, bloom * 2 + (t - 9.0) if bloom >= 1 else bloom * 2)   # s since the bloom began
        sk.render(c, t, 1.0, min(1.0, after / 9.0), min(1.0, max(0.0, after - 1.0) / 9.0))
        light = (320, meadow.GROUND_Y - 8, gl)
        m.render_back(c, t, 1.0, light)
        f.render(c, grow, bloom, gl, bend, t)
        m.render_front(c, t, 1.0, light)
        np.clip(c, 0, None, out=c)
        return glow(c, 0.6 + 0.6 * gl)

    shots = []
    for name, grow, bloom, gl, t in STATES:
        rgb = scene(grow, bloom, gl, t)
        save(rgb, name + ".png")
        hx, hy = f.head(grow, bloom, 0.0)
        x0, y0 = int(np.clip(hx - 110, 0, S - 220)), int(np.clip(hy - 110, 0, S - 220))
        if grow >= 1:
            save(rgb, name + "_x2.png", (x0, y0, 220, 220))
        shots.append(rgb)
        print(f"{name:10s} head ({hx:6.1f}, {hy:6.1f})")

    strip = np.concatenate([s[::2, ::2] for s in shots], axis=1)        # the whole sequence at half size
    save(strip, "sequence.png")
    grid = np.concatenate([np.concatenate([scene(1.0, b, gl, 4.0, bend)[::2, ::2] for bend in (-1.0, 0.0, 1.0)], axis=1)
                           for b, gl in ((0.0, 0.25), (1.0, 1.0))], axis=0)
    save(grid, "bend_grid.png")

    c[:] = 0
    best = []
    for state in ((1.0, 1.0, 1.0), (1.0, 0.0, 0.25)):
        for i in range(5):
            f.render(c, *state, 0.3, i / 60)
        runs = []
        for _ in range(5):
            ms = 0.0
            for i in range(30):
                c[:] = 0
                t1 = time.perf_counter()
                f.render(c, *state, 0.4 * np.sin(i * 0.1), i / 60)
                ms += time.perf_counter() - t1
            runs.append(ms / 30 * 1000)
        best.append(min(runs))
    ms = []
    for i in range(61):                                                 # the 2 s bloom, every frame new
        c[:] = 0
        t1 = time.perf_counter()
        f.render(c, 1.0, i / 60, 0.25 + 0.75 * i / 60, 0.2, i / 60)
        ms.append((time.perf_counter() - t1) * 1000)
    print(f"particles {f.counts}")
    print(f"init {init_ms:.0f} ms; render bloomed {best[0]:.2f} ms, bud {best[1]:.2f} ms (best of 5 x 30); "
          f"while blooming mean {np.mean(ms):.2f} ms, max {np.max(ms):.2f} ms")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
