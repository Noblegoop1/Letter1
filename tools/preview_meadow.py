"""Render meadow preview PNGs to build/previews/meadow/ (look at them).

    .venv/Scripts/python.exe tools/preview_meadow.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np
import pygame

from letter.art import meadow

OUT = os.path.join(ROOT, "build", "previews", "meadow")
NIGHT = np.array([7, 10, 20], np.float32) / 255.0


def frame(m, t, emerge, light=None):
    canvas = np.empty((meadow.SIZE, meadow.SIZE, 3), np.float32)
    canvas[:] = NIGHT
    m.render_back(canvas, t, emerge, light)
    m.render_front(canvas, t, emerge, light)
    return canvas


def save(canvas, name):
    rgb = (np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8)
    pygame.image.save(pygame.surfarray.make_surface(rgb.swapaxes(0, 1)), os.path.join(OUT, name))


def main():
    os.makedirs(OUT, exist_ok=True)
    m = meadow.Meadow()
    for e in (0.0, 0.5, 1.0):
        save(frame(m, 0.0, e), f"emerge_{e:.1f}.png")
    for t in (0, 7, 19):
        save(frame(m, float(t), 1.0), f"wind_t{t:02d}.png")
    save(frame(m, 0.0, 1.0, (320, 470, 1.0)), "light_bloom.png")
    save(frame(m, 0.0, 1.0, (320, 440, 0.25)), "light_bud.png")
    # the square centred in a wider window with night bars, to check that the edges fade without a box
    wide = np.empty((meadow.SIZE, 1100, 3), np.float32)
    wide[:] = NIGHT
    wide[:, 230:230 + meadow.SIZE] = frame(m, 3.0, 1.0)
    save(wide, "framed.png")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
