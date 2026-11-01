"""Fireflies: per-firefly drifting paths and blink styles. Pure: MicroPython (PyScript) and CPython tests.

Each path is the flower-relative offset (a few slow sines per axis) scaled by a slowly breathing factor, so a
firefly sometimes drifts in close to the flower and then away. main.py owns the DOM and adds the wind push.
"""
import math
from stage import hash32, lerp

COUNT = 10
_TAU = 2 * math.pi
_REACH = 1.7                     # horizontal reach, in radii
_Y_MID, _Y_AMP = -0.25, 0.95     # vertical band in radii (negative = above): -1.2 .. +0.7
_X_AMPS, _X_PERIODS = (0.6, 0.3, 0.1), ((14, 30), (8, 18), (6, 12))   # slow sines wide, quick ones small
_Y_AMPS, _Y_PERIODS = (0.65, 0.35), ((12, 30), (6, 14))


def _r(i, slot):
    """Stable 0..1 number for firefly i, slot `slot`. (Salt 30 was picked so every one drifts both close and far.)"""
    return hash32(i + 1, slot, 30) / 4294967295.0


def _sines(i, slot, amps, periods):
    """((amp, omega, phase), ...) with unrelated periods and phases for firefly i."""
    return tuple((a, _TAU / lerp(p[0], p[1], _r(i, slot + n)), _TAU * _r(i, slot + 8 + n))
                 for n, (a, p) in enumerate(zip(amps, periods)))


# Built once at import: position() then does no hashing.
_PATHS = tuple((_sines(i, 0, _X_AMPS, _X_PERIODS),
                _sines(i, 3, _Y_AMPS, _Y_PERIODS),
                _TAU / lerp(10.0, 22.0, _r(i, 6)), _TAU * _r(i, 16)) for i in range(COUNT))


def position(i, t, centre, radius):
    """-> (x, y) px for firefly i at stage time t."""
    xs, ys, wb, pb = _PATHS[i]
    ux = 0.0
    for a, w, p in xs:
        ux += a * math.sin(w * t + p)
    uy = 0.0
    for a, w, p in ys:
        uy += a * math.sin(w * t + p)
    k = 0.6 + 0.4 * math.sin(wb * t + pb)   # 0.2 (close in) .. 1.0 (far out)
    return (centre[0] + _REACH * radius * k * ux,
            centre[1] + radius * (_Y_MID + _Y_AMP * uy) * k)


def style(i):
    """-> (glyph, period_s, delay_s, peak, depth)."""
    depth = _r(i, 20)
    # Periods sit in shuffled, evenly spaced bands (7 is coprime with COUNT) so no two blink at the same rate.
    period = lerp(1.6, 3.6, (i * 7 % COUNT + 0.2 + 0.6 * _r(i, 21)) / COUNT)
    return ('*' if depth > 0.35 else '.', period, _r(i, 22) * period, lerp(0.6, 1.0, _r(i, 23)), depth)


def arrival(i):
    """Seconds after the bloom ends when firefly i starts to fade in."""
    return 0.5 + 0.7 * i
