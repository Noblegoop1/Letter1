"""The ending's art (SPEC §13): the cornered tremble, the glitch, the dissolve, the face and its one tear.

Pure (no pygame). Items are the chase frame's glyphs, (ch, role, x, y) in logical px on the 320 x 320
canvas with 8 x 12 cells; roles: g ground, h horizon, o obstacle, m mouse pointer, n NO button, w wall,
x scatter, t hint text. Pass the same frozen frame every call (never a previous output): every effect is
a function of (items, time, seed), with hash-based randomness, so it is deterministic.
"""
import functools
import math

from letter.engine.timeline import clamp, ease_in, hash32, smoothstep

CW, CH = 8, 12                 # chase cell, logical px

# A kaomoji, like the emotes the user chose (2026-11-01): the quiet, sad "shobon" face. One line, drawn large
# and crisp by the scene; its few non-ASCII glyphs (´ • ω `) are all in the bundled JetBrains Mono.
FACE = ("(´•ω•`)",)
TEAR_EYE = (2, 0.82)           # (character, line) where the tear wells: just under the left eye
TEAR_END = 2.6                 # line where it has faded, below the face
TEAR_FORM, TEAR_FALL = 1.0, 3.5

# -- cornered: the tremble -------------------------------------------------------------------------
SHAKE_NEAR, SHAKE_FAR = 20.0, 200.0   # px from the NO button: full shake inside NEAR, base tremble past FAR
SHAKE_BASE, SHAKE_PEAK = 0.4, 4.5     # logical px


def shake_amplitude(distance):
    """Tremble in logical px for a pointer `distance` px away: smooth, never rising with distance."""
    return SHAKE_BASE + (SHAKE_PEAK - SHAKE_BASE) * (1 - smoothstep(SHAKE_NEAR, SHAKE_FAR, distance))


def proximity_shake(distance, t):
    """(dx, dy) at t seconds: the amplitude times sums of fast sines with unrelated frequencies.
    The scene should smooth `distance` (approach()) so the amplitude never jumps with the pointer."""
    a = shake_amplitude(distance)
    w = 2 * math.pi * t
    dx = 0.5 * math.sin(w * 13.7) + 0.3 * math.sin(w * 21.1 + 1.3) + 0.2 * math.sin(w * 5.3 + 0.7)
    dy = 0.45 * math.sin(w * 11.9 + 0.4) + 0.35 * math.sin(w * 17.3 + 2.1) + 0.2 * math.sin(w * 3.7 + 1.9)
    return a * dx, a * 0.6 * dy


# -- caught: the glitch ----------------------------------------------------------------------------
GLITCH_LEN = 2.0
NOISE = "#%&@$!?/\\|<>[]{}=+*~^:;"
CORRUPT = {             # what each role decays into: it stays itself, only wrong
    "g": "_-=~#/\\.",
    "h": "_-=~.:'",
    "m": "%#&@*oO0<>",
    "n": "[]|N0Q#{}<>",
    "w": "|!:#I]",
}
FLASH_SLOT, FLASH_LEN = 0.5, 0.08     # at most one flash per slot, inside it: <= 3 in any 1 s window


def glitch_intensity(e):
    """0.12 .. 1 over the glitch, building."""
    return clamp(0.12 + 0.88 * (e / GLITCH_LEN) ** 1.6)


def _flash(e, seed, k):
    slot = int(e / FLASH_SLOT)
    h = hash32(slot, seed, 41)
    if e < 0.3 or h % 1000 >= 1150 * k - 200:
        return 0.0
    u = (e - slot * FLASH_SLOT - 0.05 - (h >> 10) % 100 / 100 * 0.3) / FLASH_LEN
    return 1 - u if 0 <= u < 1 else 0.0


def glitch(items, e, seed=0, calm=False):
    """(new_items, flash) e seconds into the glitch. calm (A11): gentler, no tearing, never a flash."""
    k = glitch_intensity(e) * (0.3 if calm else 1.0)
    flash = 0.0 if calm else _flash(e, seed, k)
    tick, held, slot = int(e * 18), int(e * 6), int(e * 4)
    rows = sorted({int(y // CH) for _, _, _, y in items})
    # a short tear: a band of rows thrown sideways for a few frames
    h = hash32(slot, seed, 5)
    band = None
    if not calm and h % 1000 < 700 * k and e - slot / 4 < 0.05 + (h >> 12) % 5 * 0.012:
        r0 = rows[(h >> 4) % len(rows)] - (h >> 20) % 2 if rows else 0
        band = (r0, r0 + 2 + (h >> 9) % 5, ((h >> 14) % 6 + 2) * CW * (1 if h & 1 else -1))
    # block dropouts, in cells
    blocks = []
    for j in range(3):
        h = hash32(int(e * 8), j, seed + 21)
        if items and h % 1000 < 600 * k:
            _, _, x, y = items[(h >> 3) % len(items)]
            c, r = int(x // CW) - (h >> 25) % 3, int(y // CH) - (h >> 28) % 2
            blocks.append((c, r, c + 2 + (h >> 15) % 7, r + 1 + (h >> 19) % 3))
    # rows sliding sideways by whole cells
    slide = {}
    for r in rows:
        h = hash32(r, held, seed + 11)
        if h % 1000 < 420 * k:
            slide[r] = ((h >> 10) % 4 + 1) * CW * (1 if h & 2 else -1)
    # one row echoed onto the row below
    h = hash32(held, seed, 33)
    echo = rows[(h >> 5) % len(rows)] if rows and h % 1000 < 500 * k else None
    scramble = 0.03 + 0.32 * k + 0.4 * flash
    out = []
    for ch, role, x, y in items:
        r = int(y // CH)
        c = int(x // CW)
        if blocks and any(c0 <= c < c1 and r0 <= r < r1 for c0, r0, c1, r1 in blocks):
            continue
        x += slide.get(r, 0)
        if band and band[0] <= r < band[1]:
            x += band[2]
        h = hash32(int(x) * 7 + int(y) * 131, tick, seed + 7)
        if h % 1000 < 1000 * (scramble + (0.1 * k if role in "mn" else 0)):
            pool = CORRUPT.get(role, NOISE) if h & 4 else NOISE
            ch = pool[(h >> 10) % len(pool)]
        out.append((ch, role, x, y))
        if r == echo:
            out.append((ch, role, x + CW * ((h >> 3) % 3 - 1), y + CH))
    return out, flash


# -- caught: the dissolve --------------------------------------------------------------------------
DISSOLVE_LEN = 2.5
WAVE = {"o": 0, "x": 0, "t": 0, "g": 1, "h": 1, "w": 1, "m": 2, "n": 3}
# per wave: first break, last break, longest fragment life (progress units). Each wave's last speck is gone
# by last break + 0.03 + life: obstacles 0.45, ground 0.62, pointer 0.72, then the NO stands alone until 0.78
# and its last speck is gone before 1.
WAVES = ((0.00, 0.16, 0.26), (0.10, 0.34, 0.25), (0.36, 0.48, 0.21), (0.78, 0.83, 0.14))
SPECK = ".'`,:-"
SPIN = "|/-\\"


@functools.lru_cache(maxsize=4)
def _shatter_plan(items, seed):
    """Per glyph, fixed for a frozen frame: (ch, role, x, y, break moment, hash, fragments), each fragment
    (start, life, vx, vy, half gravity, sway rate, sway phase, spin rate or 0, speck glyph or '')."""
    plan = []
    for ch, role, x, y in items:
        wave = WAVE.get(role, 0)
        lo, hi, life = WAVES[wave]
        h = hash32(int(x * 4) + 7919 * wave, int(y * 4), seed * 97 + 1)
        u = (h % 1000) / 1000
        if wave == 1:   # the ground crumbles from the left, where the pointer came from, toward the wall
            u = 0.6 * clamp(x / 320) + 0.4 * u
        b = lo + (hi - lo) * u
        frags = []
        for j in range(1 + (h >> 10) % 3):
            hj = hash32(h, j, seed)
            frags.append((
                b + 0.015 * j, life * (0.55 + 0.45 * (hj % 100) / 100),
                ((hj >> 7) % 100 / 100 - 0.5) * (44 if j else 26),
                8 - (hj >> 14) % 100 / 100 * 30,                # some pop up before they fall
                0.5 * (25 + (hj >> 21) % 100 * 1.5),            # light specks drift, heavy ones drop
                4 + j, hj & 7,
                8 + (hj >> 3) % 8 if j == 0 and hj & 0x30000000 == 0 else 0,   # a quarter of the chunks tumble
                SPECK[(hj >> 3) % len(SPECK)] if j else "",
            ))
        plan.append((ch, role, x, y, b, h, frags))
    return plan


def dissolve(items, p, seed=0):
    """[(ch, role, x, y, alpha)] at progress p (0..1 over DISSOLVE_LEN): each glyph holds until its
    wave reaches it, then breaks into 1-3 fragments that pop, drift and fall as they fade.
    Items must be tuples (the frozen frame is cached by value)."""
    out, sin = [], math.sin
    add = out.append
    for ch, role, x, y, b, h, frags in _shatter_plan(tuple(items), seed):
        if p < b:   # whole, with a shiver just before it breaks
            add((ch, role, x + (hash32(h, int(p * 50)) % 3 - 1 if b - p < 0.04 else 0), y, 1.0))
            continue
        for start, life, vx, vy, g2, w, ph, spin, speck in frags:
            age = p - start
            if not 0 <= age < life:
                continue
            a, s = age / life, age * DISSOLVE_LEN      # life fraction, seconds
            glyph = speck or (SPIN[int(s * spin) % 4] if spin else ch if a < 0.45 else ":" if a < 0.7 else ".")
            add((glyph, role, x + vx * s + 3 * sin(s * w + ph), y + vy * s + g2 * s * s, (1 - a) ** 1.1))
    return out


# -- the face's one tear ---------------------------------------------------------------------------
def tear(e):
    """[(ch, col, row, alpha)] e seconds after the tear begins, in FACE cells: it wells up under the eye
    over TEAR_FORM, then slides down the cheek over TEAR_FALL, hesitating twice, and fades near the jaw.
    Always exactly one."""
    col, row = TEAR_EYE
    if e < TEAR_FORM:
        u = clamp(e / TEAR_FORM)
        return [("." if u < 0.55 else "o", col, row, smoothstep(0.0, 0.5, u))]
    u = clamp((e - TEAR_FORM) / TEAR_FALL)
    v = ease_in(u)
    v += 0.8 * math.sin(4 * math.pi * v) / (4 * math.pi)   # stick-slip; derivative stays >= 0
    pos = row + (TEAR_END - row) * v
    return [("o" if u < 0.7 else ".", col, pos, 1 - smoothstep(0.6, 1.0, u))]
