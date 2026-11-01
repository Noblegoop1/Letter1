"""Render invitation preview PNGs to build/previews/invitation/ (look at them).

    .venv/Scripts/python.exe tools/preview_invitation.py

The real night in the scene's draw order: sky (moon 1, clouds 1), far fireflies, meadow, the bloomed sea
holly, near fireflies with the message, bokeh, the invitation buttons, then a copy of the scene's glow pass
(1/8 samples above 0.42 plus each lights() splat, blurred, added). Moments: wandering, attraction,
convergence, nearly formed, formed, formed with the buttons (YES hovered), the YES scatter twice and the
NO dispersal, each at 2x nearest-neighbour; the formed frame also at the window's 1.25x and 1.7x; and a
long exposure of the gathering's paths.
"""
import copy
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from letter.art import flower, invitation, meadow, sky  # noqa: E402
from letter.art.fireflies import SIZE as S, Fireflies  # noqa: E402

OUT = ROOT / "build" / "previews" / "invitation"
DT = 1 / 60
ARRIVE = (0.3, 6.3)                       # as the scene: arrival ramps over 6 s once bloomed
G = 12.8                                  # gather starts after the arrival and config.WANDER (6.5 s)
GATHER, SCATTER, LETGO = 7.0, 3.0, 2.5
X = G + 10.0                              # the reader answers
FLY_GLOW = 220 * np.array([0.7, 1.0, 0.3], np.float32)   # as letter/scenes/night.py
MOMENTS = (("1_wandering", G - 2.0), ("2_attraction", G + 1.4), ("3_convergence", G + 3.4),
           ("4_nearly", G + 5.2), ("5_formed", G + 7.6), ("6_buttons_yes_hover", G + 9.2),
           ("7_scatter_yes_a", X + 0.8), ("8_scatter_yes_b", X + 1.8))
LETGO_AT = ("9_letgo_no", X + 1.2)


def bend(t):
    return float(np.clip(1.2 * meadow.wind(320.0, t), -1.0, 1.0))


def glow(c, strength, lights):
    """The scene's bloom: 1/8 samples above 0.42 plus each light, blurred, scaled up and added (8-bit)."""
    small = (c[2::8, 2::8] + c[6::8, 6::8]) * 0.5
    g = np.clip((small - 0.42) * (255 * strength), 0, None)
    x, y, s = lights
    gx, gy = x / 8 - 0.5, y / 8 - 0.5
    x0, y0 = np.floor(gx).astype(np.intp), np.floor(gy).astype(np.intp)
    fx, fy, n = gx - x0, gy - y0, S // 8
    for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        np.add.at(g, (np.clip(y0 + dy, 0, n - 1), np.clip(x0 + dx, 0, n - 1)), (s * w)[:, None] * FLY_GLOW)
    surf = pygame.image.frombuffer(np.ascontiguousarray(np.minimum(g, 255).astype(np.uint8)), (n, n), "RGB")
    halo = pygame.transform.smoothscale(pygame.transform.gaussian_blur(surf, 2), (S, S))
    return np.clip(np.clip(c, 0, 1) * 255 + pygame.surfarray.array3d(halo).swapaxes(0, 1), 0, 255).astype(np.uint8)


def save(rgb, name, scale=2.0):
    surf = pygame.surfarray.make_surface(np.ascontiguousarray(rgb.swapaxes(0, 1)))
    if scale != 1:
        surf = pygame.transform.scale(surf, (round(surf.get_width() * scale), round(surf.get_height() * scale)))
    pygame.image.save(surf, str(OUT / name))
    print("wrote", OUT / name)


class Night:
    def __init__(self):
        self.sky, self.meadow, self.flower = sky.Sky(), meadow.Meadow(), flower.Flower()
        self.c = np.zeros((S, S, 3), np.float32)

    def frame(self, ff, t, buttons=0.0, hover=None):
        c, b = self.c, bend(t)
        arr = float(np.clip((t - ARRIVE[0]) / (ARRIVE[1] - ARRIVE[0]), 0, 1))
        glow_k = 0.92 + 0.08 * (0.85 + 0.15 * np.sin(t * 2 * np.pi / 3.0))
        light = (320, meadow.GROUND_Y - 8, glow_k)
        self.sky.render(c, t, 1.0, 1.0, 1.0)
        ff.render(c, t, arr, layer="far")
        self.meadow.render_back(c, t, 1.0, light)
        self.flower.render(c, 1.0, 1.0, glow_k, b, t)
        self.meadow.render_front(c, t, 1.0, light)
        ff.render(c, t, arr, layer="near")
        ff.render(c, t, arr, layer="bokeh")
        for name in ("yes", "no"):
            invitation.draw(c, name, 1.0 if name == hover else 0.0, t, buttons)
        return glow(c, 0.6 + 0.6 * glow_k, ff.lights(t, arr))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    night = Night()
    ff = Fireflies()
    targets = invitation.cells()
    print(f"{len(targets)} message fireflies; BOX {invitation.BOX}")
    exposure = np.zeros((S, S, 3), np.float32)
    frames, letgo = 0, None
    t = 0.0
    todo = list(MOMENTS)
    for n in range(1, int((X + 2.5) / DT) + 1):
        t = n * DT
        if abs(t - G) < DT / 2:
            ff.gather(targets, t, GATHER)
        if abs(t - X) < DT / 2:
            letgo = copy.deepcopy(ff)
            letgo.scatter(t, LETGO, gentle=True)
            ff.scatter(t, SCATTER)
        ff.update(DT, t, meadow.wind, night.flower.head(1, 1, bend(t)))
        if letgo is not None:
            letgo.update(DT, t, meadow.wind, night.flower.head(1, 1, bend(t)))
        if G <= t < G + GATHER and n % 3 == 0:
            ff.render(exposure, t, layer="near")
            frames += 1
        while todo and t >= todo[0][1] - DT / 2:
            name, at = todo.pop(0)
            rgb = night.frame(ff, t, 1.0 if name.startswith("6") else 0.0, "yes" if "hover" in name else None)
            save(rgb, f"{name}.png")
            print(f"   t = {t - G:+.1f} s from the gathering, formed {ff.formed():.2f}")
            if name == "5_formed":
                save(rgb, "5_formed_window_1280x800.png", 1.25)
                save(rgb, "5_formed_window_1920x1080.png", 1.7)
                save(rgb[0:180, 60:580], "5_formed_message_x2.png", 2)
            if name.startswith("6"):
                save(rgb[170:260, 20:620], "6_buttons_x2.png", 2)
        if abs(t - LETGO_AT[1]) < DT / 2:
            save(night.frame(letgo, t), f"{LETGO_AT[0]}.png")
    bg = night.sky.render(np.zeros((S, S, 3), np.float32), G, 1.0, 1.0, 1.0)
    save((np.clip(bg + exposure * (12.0 / frames), 0, 1) * 255).astype(np.uint8), "long_exposure_gathering.png", 1)


if __name__ == "__main__":
    main()
