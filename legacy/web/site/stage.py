"""Shared timing for the whole journey: phases, a pausable clock, easing, a cell hash and Bayer dithering.

Pure: runs in MicroPython (PyScript) and CPython tests. main.py owns the DOM; every scene module imports
its helpers from here.
"""
import math

PHASES = ("letter", "reveal", "night", "seed", "grown", "bloom", "bloomed")
DURATIONS = {"reveal": 4.5, "night": 3.0, "seed": 5.0, "bloom": 2.5}   # seconds
EVENTS = {"yes": "letter", "flower": "grown"}   # event -> the only phase that accepts it
REDUCED = 0.4                                   # timed phases become short fades under reduced motion

# timelines inside timed phases, in seconds from the phase start (tests check they fit DURATIONS)
NIGHT_FADE = 1.5            # background eases to the night colour
NIGHT_EMERGE = (0.3, 2.8)   # grass comes up through the paper fibres
SEED_FALL = (0.0, 1.4)      # the seed drops ...
SEED_GROW = (2.2, 5.0)      # ... and after the puff and a breath, the flower grows


def duration(phase, reduced=False):
    d = DURATIONS.get(phase)
    if d is None:
        return None
    return min(d, REDUCED) if reduced else d


def step(phase, since, t, event=None, reduced=False):
    """-> (phase, since). Events count only in their own phase; timed phases hand off on their own."""
    if event is not None:
        if EVENTS.get(event) == phase:
            return PHASES[PHASES.index(phase) + 1], t
        return phase, since
    d = duration(phase, reduced)
    while d is not None and t - since >= d:  # a long gap (hidden tab) can cross several phases
        phase, since = PHASES[PHASES.index(phase) + 1], since + d
        d = duration(phase, reduced)
    return phase, since


def progress(phase, since, t, reduced=False):
    """0..1 through a timed phase; 1 for phases that wait for the viewer."""
    d = duration(phase, reduced)
    return 1.0 if d is None else clamp((t - since) / d, 0.0, 1.0)


class Clock:
    """Stage time = frame time minus time spent paused."""

    def __init__(self):
        self.offset = 0.0
        self.paused_at = None

    def now(self, raw):
        return (raw if self.paused_at is None else self.paused_at) - self.offset

    def pause(self, raw):
        if self.paused_at is None:
            self.paused_at = raw

    def resume(self, raw):
        if self.paused_at is not None:
            self.offset += raw - self.paused_at
            self.paused_at = None


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def lerp(a, b, k):
    return a + (b - a) * k


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


def span(t, window):
    """0..1 through a (start, end) window of a timeline."""
    return clamp((t - window[0]) / (window[1] - window[0]))


def lean_target(dx, dy, radius, cap):
    """Pointer lean: toward the pointer's side, fading with distance, never past cap."""
    near = math.exp(-(dx * dx + dy * dy) / (radius * radius))
    return clamp(dx / radius, -1.0, 1.0) * near * cap


def approach(current, target, dt, tau):
    """Exponential smoothing: move toward target with time constant tau, never overshooting."""
    return current + (target - current) * (1 - math.exp(-dt / tau))


def hash32(a, b, c=0):
    """Stable pseudo-random int for a cell (and tick): same picture on every screen and frame rate."""
    h = (a * 374761393 + b * 668265263 + c * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1103515245) & 0xFFFFFFFF
    return h ^ (h >> 16)


_BAYER4 = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)


def bayer(x, y):
    """Ordered-dither threshold in (0, 1) for a cell: dissolves look like even, pixel-like grain."""
    return (_BAYER4[(y % 4) * 4 + x % 4] + 0.5) / 16
