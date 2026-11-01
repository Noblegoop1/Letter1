"""Render night-sky preview PNGs to build/previews/sky/ (look at them).

    .venv/Scripts/python.exe tools/preview_sky.py

For each state: the sky alone (sky_*.png), the sky behind the real meadow and flower with a stand-in
for the scene's glow pass (scene_*.png; a rough island and warm blob if those modules fail to load),
and a 2x nearest-neighbour crop of the moon and of the clouds (*_x2.png). The last image shows the
canvas centred between side bars painted from base_column(), to check the edges for a seam.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from letter.art.sky import S, Sky  # noqa: E402

OUT = ROOT / "build" / "previews" / "sky"
# name, t, moon, clouds, flower bloom
STATES = (
    ("clear", 3.0, 0.0, 0.0, 0.0),
    ("half", 20.0, 0.5, 0.5, 0.5),
    ("full_a", 40.0, 1.0, 1.0, 1.0),
    ("full_b", 95.0, 1.0, 1.0, 1.0),
)


def foreground():
    """-> draw(canvas, t, bloom): the real meadow and flower, or a rough stand-in."""
    try:
        from letter.art import flower, meadow
        m, f = meadow.Meadow(), flower.Flower()

        def draw(c, t, bloom):
            light = (320, meadow.GROUND_Y - 8, 0.25 + 0.75 * bloom)
            m.render_back(c, t, 1.0, light)
            f.render(c, 1.0, bloom, 0.25 + 0.75 * bloom, 0.0, t)
            m.render_front(c, t, 1.0, light)
        return draw
    except Exception as exc:   # flower or meadow mid-edit: judge composition on a stand-in
        print("stand-in foreground:", exc)
        yy, xx = np.mgrid[:S, :S]
        blob = np.exp(-((xx - 320) ** 2 + (yy - 230) ** 2) / (2 * 40.0 ** 2))[..., None] * np.float32((1.0, 0.55, 0.25))
        island = (yy >= 486) & (np.abs(xx - 320) < 210)

        def draw(c, t, bloom):
            c += blob * (0.4 + 0.8 * bloom)
            c[island] = (0.10, 0.07, 0.05)
        return draw


def glow(c, strength):
    """The scene's bloom pass: 1/8 samples above 0.42, blurred, scaled up and added (8-bit)."""
    small = (c[2::8, 2::8] + c[6::8, 6::8]) * 0.5
    g = np.clip((small - 0.42) * (255 * strength), 0, 255).astype(np.uint8)
    surf = pygame.image.frombuffer(np.ascontiguousarray(g), (S // 8, S // 8), "RGB")
    halo = pygame.transform.smoothscale(pygame.transform.gaussian_blur(surf, 2), (S, S))
    return np.clip(c * 255 + pygame.surfarray.array3d(halo).swapaxes(0, 1), 0, 255).astype(np.uint8)


def save(rgb, name, crop=None):
    if crop:
        x, y, w, h = crop
        rgb = np.repeat(np.repeat(rgb[y:y + h, x:x + w], 2, 0), 2, 1)
    pygame.image.save(pygame.surfarray.make_surface(np.ascontiguousarray(rgb.swapaxes(0, 1))), str(OUT / name))
    print("wrote", OUT / name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sky = Sky()
    draw = foreground()
    c = np.empty((S, S, 3), np.float32)
    for name, t, moon, clouds, bloom in STATES:
        sky.render(c, t, 1.0, moon, clouds)
        bare = (np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)
        save(bare, f"sky_{name}.png")
        draw(c, t, bloom)
        np.clip(c, 0, None, out=c)
        rgb = glow(c, 0.6 + 0.6 * bloom)
        save(rgb, f"scene_{name}.png")
        if moon > 0:
            save(rgb, f"scene_{name}_moon_x2.png", (360, 0, 280, 230))
            save(bare, f"sky_{name}_clouds_x2.png", (40, 20, 320, 240))
        if name == "full_b":   # framed between bars from base_column(), as the window shows it
            bars = (np.clip(sky.base_column(), 0, 1) * 255 + 0.5).astype(np.uint8)
            wide = np.repeat(bars[:, None, :], 1024, axis=1)
            wide[:, 192:192 + S] = rgb
            save(wide, "framed.png")
    # a moment when a cloud veils the moon, found by scanning time
    x, y, r = sky.moon_pos(1.0)
    for t in np.arange(30.0, 400.0, 1.0):
        T = sky._clouds(c, float(t), 1.0, 1.0, 1.0)
        if 0.35 < T[int(y), int(x)] < 0.7:
            sky.render(c, float(t), 1.0, 1.0, 1.0)
            draw(c, float(t), 1.0)
            np.clip(c, 0, None, out=c)
            rgb = glow(c, 1.2)
            save(rgb, "scene_veiled.png")
            save(rgb, "scene_veiled_moon_x2.png", (360, 0, 280, 230))
            print(f"veiled at t = {t:.0f} s")
            break


if __name__ == "__main__":
    main()
