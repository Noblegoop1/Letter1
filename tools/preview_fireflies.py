"""Render firefly preview PNGs to build/previews/fireflies/ (look at them).

    .venv/Scripts/python.exe tools/preview_fireflies.py

A stand-in night in the scene's draw order: sky, far band, island (soil and grass blades drawn "over",
so far fireflies pass behind them), an orange blob for the flower, near bands, bokeh, then a copy of the
scene's bloom pass (1/8-size sample above 0.42, plus each firefly's lights() splat, blurred, added) and
a nearest-neighbour upscale to the window's scale at 1280 x 800. Moments during the arrival and after
it (one also at 1920 x 1080 scale), a 2x crop, a contact sheet, and a 20 s long exposure of their paths.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import pygame  # noqa: E402

from letter.art.fireflies import SIZE, Fireflies  # noqa: E402

OUT = ROOT / "build" / "previews" / "fireflies"
HEAD = (320.0, 230.0)
DT = 1 / 60
ARRIVE = (0.3, 6.3)                   # as in the scene: arrival ramps over 6 s once the flower has bloomed
MOMENTS = (1.4, 2.6, 4.2, 8.0, 15.0, 31.0)
EXPOSURE = (10.0, 30.0)
LIGHT_RGB = np.array([0.7, 1.0, 0.3])     # colour of a firefly's bloom halo
LIGHT_GAIN = 220.0                    # lights() strength -> 8-bit value in the 80 x 80 bloom buffer
SCALE = 1.25                          # window scale at 1280 x 800 (1.7 at 1920 x 1080)


def wind(x, t):
    """Stand-in gusts; the real wind(x, t) lives with the meadow."""
    return 0.6 * np.sin(x / 110.0 - 0.9 * t) * (0.5 + 0.5 * np.sin(0.21 * t))


def arrival(t):
    return float(np.clip((t - ARRIVE[0]) / (ARRIVE[1] - ARRIVE[0]), 0.0, 1.0))


def sky():
    y = np.linspace(0, 1, SIZE, dtype=np.float32)[:, None, None]
    top, low = np.array((4, 5, 12), np.float32) / 255, np.array((16, 22, 44), np.float32) / 255
    return np.ascontiguousarray(np.broadcast_to(top + (low - top) * y ** 1.6, (SIZE, SIZE, 3)), np.float32)


def island():
    """(alpha, rgb) layers drawn over the far band: a soil band about x 110..530 and grass blades."""
    rng = np.random.default_rng(3)
    a = np.zeros((SIZE, SIZE), np.float32)
    rgb = np.zeros((SIZE, SIZE, 3), np.float32)
    yy, xx = np.mgrid[:SIZE, :SIZE]
    top = 498 + 6 * ((xx - 320) / 210.0) ** 2
    bottom = 500 + 110 * np.sqrt(np.clip(1 - ((xx - 320) / 215.0) ** 2, 0, 1))
    soil = (yy >= top) & (yy <= bottom) & (np.abs(xx - 320) < 215)
    a[soil] = 1.0
    depth = np.clip((yy - top) / 110.0, 0, 1)
    rgb[soil] = (np.array([0.3, 0.22, 0.16]) * (1 - 0.8 * depth[soil])[:, None]
                 * rng.uniform(0.6, 1.2, (soil.sum(), 1)))
    for x in rng.uniform(112, 528, 420):
        h = rng.uniform(12, 46) * (1 - 0.6 * (abs(x - 320) / 210) ** 2)
        base = int(498 + 6 * ((x - 320) / 210.0) ** 2)
        lean = rng.uniform(-0.25, 0.25)
        for k in range(int(h)):
            px = int(x + lean * k * k / h)
            a[base - k, px] = 1.0
            rgb[base - k, px] = np.array([0.07, 0.17, 0.1]) + (0.1 * k / h) * np.array([0.5, 1.0, 0.5])
    return a[..., None], rgb


def flower():
    """(alpha, rgb) stand-in for the warm sunrise flower: an orange blob, a stem and a dotted aura ring."""
    yy, xx = np.mgrid[:SIZE, :SIZE]
    r2 = (xx - HEAD[0]) ** 2 + ((yy - HEAD[1]) * 1.35) ** 2
    a = np.clip(1.4 * np.exp(-r2 / (2 * 50.0 ** 2)), 0, 1) * (np.random.default_rng(4).random((SIZE, SIZE)) < 0.5)
    rgb = np.zeros((SIZE, SIZE, 3), np.float32)
    rgb[:] = (0.95, 0.45, 0.25)
    rgb[r2 < 30 ** 2] = (1.0, 0.72, 0.3)
    stem = (np.abs(xx - 320 - 3 * np.sin(yy / 60.0)) < 2) & (yy > HEAD[1] + 40) & (yy < 500)
    a[stem] = 1.0
    rgb[stem] = (0.25, 0.55, 0.5)
    rng = np.random.default_rng(5)
    ang = rng.uniform(0, 2 * np.pi, 900)
    rad = 150 + rng.normal(0, 1.5, 900)
    rx, ry = (HEAD[0] + rad * np.cos(ang)).astype(int), (HEAD[1] + rad * np.sin(ang)).astype(int)
    a[ry, rx] = 0.55
    rgb[ry, rx] = (1.0, 0.7, 0.5)
    return a[..., None].astype(np.float32), rgb


def frame(ff, t, bg, isl, flo, arr):
    """One scene-like frame: (640, 640, 3) uint8 after the bloom pass."""
    c = bg.copy()
    ff.render(c, t, arr, layer="far")
    for a, rgb in (isl, flo):
        c *= 1 - a
        c += a * rgb
    ff.render(c, t, arr, layer="near")
    ff.render(c, t, arr, layer="bokeh")
    np.clip(c, 0, 1, out=c)
    small = (c[2::8, 2::8] + c[6::8, 6::8]) * 0.5
    g = np.clip((small - 0.42) * 255 * 1.2, 0, 255)
    x, y, s = ff.lights(t, arr)
    gx, gy = x / 8 - 0.5, y / 8 - 0.5          # cell centres sit at 8k + 4
    ix, iy = np.floor(gx).astype(int), np.floor(gy).astype(int)
    fx, fy = gx - ix, gy - iy
    for dx in (0, 1):
        for dy in (0, 1):
            w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * s * LIGHT_GAIN
            np.add.at(g, (np.clip(iy + dy, 0, 79), np.clip(ix + dx, 0, 79)), w[:, None] * LIGHT_RGB)
    glow = pygame.image.frombuffer(np.ascontiguousarray(np.clip(g, 0, 255).astype(np.uint8)).tobytes(), (80, 80), "RGB")
    halo = pygame.transform.smoothscale(pygame.transform.gaussian_blur(glow, 2), (SIZE, SIZE))
    out = pygame.image.frombuffer((c * 255).astype(np.uint8).tobytes(), (SIZE, SIZE), "RGB").copy()
    out.blit(halo, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    return pygame.surfarray.array3d(out).swapaxes(0, 1)


def save(rgb, name, scale=SCALE):
    surf = pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
    if scale != 1:
        surf = pygame.transform.scale(surf, (round(surf.get_width() * scale), round(surf.get_height() * scale)))
    pygame.image.save(surf, str(OUT / name))
    print("wrote", OUT / name)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    bg, isl, flo = sky(), island(), flower()
    ff = Fireflies()
    exposure = np.zeros_like(bg)
    frames = 0
    shots = []
    for n in range(int(max(MOMENTS + EXPOSURE) / DT) + 1):
        t = n * DT
        ff.update(DT, t, wind, HEAD)
        if EXPOSURE[0] <= t < EXPOSURE[1]:
            ff.render(exposure, t, layer="far")
            ff.render(exposure, t, layer="near")
            frames += 1
        for m, at in enumerate(MOMENTS):
            if abs(t - at) < DT / 2:
                rgb = frame(ff, t, bg, isl, flo, arrival(t))
                shots.append(rgb)
                save(rgb, f"moment_{m + 1}_t{at:04.1f}_arrival{arrival(t):.2f}.png")
                if m == 4:   # the same at 1920 x 1080 scale, and a 2x crop around the brightest firefly
                    save(rgb, f"moment_{m + 1}_t{at:04.1f}_1920x1080.png", 1.7)
                    x, y, s = ff.lights(t, 1.0)
                    j = np.argmax(s * (y < 440) * (np.hypot(x - HEAD[0], y - HEAD[1]) > 150))   # against the sky
                    x0, y0 = int(np.clip(x[j] - 80, 0, SIZE - 160)), int(np.clip(y[j] - 80, 0, SIZE - 160))
                    save(rgb[y0:y0 + 160, x0:x0 + 160], "detail_2x.png", 2)
    sheet = np.concatenate([np.concatenate(shots[:3], 1), np.concatenate(shots[3:], 1)], 0)
    save(sheet, "sheet.png", 1)
    save((np.clip(bg + exposure * (40.0 / frames), 0, 1) * 255).astype(np.uint8), "long_exposure.png", 1)


if __name__ == "__main__":
    main()
