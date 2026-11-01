"""Timing helpers shared by every scene: easing, windows, smoothing, a stable cell hash, Bayer dither.

Pure (no pygame). Carried over from the web version's stage.py.
"""
import math


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, k):
    return a + (b - a) * k


def span(t, window):
    """0..1 through a (start, end) window of a timeline."""
    return clamp((t - window[0]) / (window[1] - window[0]))


def ease(x):
    """Cubic ease-in-out."""
    x = clamp(x)
    return 4 * x * x * x if x < 0.5 else 1 - (2 - 2 * x) ** 3 / 2


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x * x


def smoothstep(a, b, x):
    x = clamp((x - a) / (b - a))
    return x * x * (3 - 2 * x)


def approach(current, target, dt, tau):
    """Exponential smoothing toward target with time constant tau; never overshoots."""
    return current + (target - current) * (1 - math.exp(-dt / tau))


def lean_target(dx, dy, radius, cap):
    """Pointer lean: toward the pointer's side, fading with distance. Peaks at exactly cap, with the
    pointer level with the point and radius / sqrt(2) to one side."""
    near = math.exp(-(dx * dx + dy * dy) / (radius * radius))
    return clamp(dx / radius * near * math.sqrt(2 * math.e), -1.0, 1.0) * cap   # sqrt(2e): 1 / max of x e^-x^2


def quake(e, duration, peak):
    """Earthquake offset (dx, dy) at e seconds: decaying sums of sines with unrelated frequencies, peaking
    near `peak` early on and settling to exactly (0, 0) at `duration`."""
    if not 0 <= e < duration:
        return 0.0, 0.0
    env = peak * (1 - e / duration) ** 2 * min(1.0, e / 0.04)   # a 40 ms onset, so it doesn't start with a jump
    tau = 2 * math.pi * e
    dx = 0.62 * math.sin(tau * 11.3) + 0.38 * math.sin(tau * 17.9 + 1.1)
    dy = 0.55 * math.sin(tau * 13.7 + 0.4) + 0.45 * math.sin(tau * 7.1 + 2.3)
    return env * dx, env * dy


def drift(t, periods, phases=(0.0, 1.3, 2.9)):
    """Sum of slow sines with unrelated periods, in [-1, 1]: motion that never visibly loops."""
    return sum(math.sin(2 * math.pi * t / p + ph) for p, ph in zip(periods, phases)) / len(periods)


def hash32(a, b, c=0):
    """Stable pseudo-random int for a cell (and tick)."""
    h = (a * 374761393 + b * 668265263 + c * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1103515245) & 0xFFFFFFFF
    return h ^ (h >> 16)


_BAYER4 = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)


def bayer(x, y):
    """Ordered-dither threshold in (0, 1): dissolves look like even, pixel-like grain."""
    return (_BAYER4[(y % 4) * 4 + x % 4] + 0.5) / 16
