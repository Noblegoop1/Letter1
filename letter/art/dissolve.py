"""Text crumbling into ASCII specks (SPEC §10.1). Pure.

Each character crumbles through a ramp of lighter glyphs at its own moment (Bayer-ordered, so the
pattern is even, not left-to-right), then sheds specks that drift up and sideways and fade.
"""
from letter.engine.timeline import bayer, hash32

CRUMBLE = "#+:."
FALL = 0.22      # share of progress a letter takes to crumble
LIFE = 0.35      # share of progress a speck lives
SPECKS = 4       # specks per letter
SPAN = 1 - LIFE - 0.08  # letters are gone by here, so every speck has faded by progress 1


def letters(text, p):
    """[(index, glyph or None)] at progress p: the original letter, a crumble glyph, or None (gone)."""
    out = []
    q = p / SPAN
    for i, ch in enumerate(text):
        if ch == " ":
            out.append((i, None))
            continue
        d = (q * (1 + FALL) - bayer(i, i // 4 + 1)) / FALL
        out.append((i, ch if d < 0 else CRUMBLE[int(d * len(CRUMBLE))] if d < 1 else None))
    return out


def specks(text, p):
    """[(index, dx, dy, glyph, alpha)]: dx/dy in letter widths/heights from the letter's spot."""
    out = []
    for i, ch in enumerate(text):
        if ch == " ":
            continue
        gone = (bayer(i, i // 4 + 1) + FALL) / (1 + FALL) * SPAN
        for j in range(SPECKS):
            age = (p - gone - j * 0.03) / LIFE
            if 0 <= age < 1:
                h = hash32(i, j, 3)
                dx = ((h % 100) / 100 - 0.5) * 1.6 * age
                dy = -0.2 - 2.4 * age - (h >> 8) % 7 * 0.05
                out.append((i, dx, dy, ".'`,"[(h >> 4) % 4], 1 - age))
    return out
