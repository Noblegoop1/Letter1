"""The ASCII heart seal (kept from the web version). Its glyph cells double as shatter fragments."""
import math

from letter.engine.timeline import hash32

# hand-drawn; ':' marks the inside, filled with wax glyphs
SPRITE = (
    '  .-""-.   .-""-.  ',
    " /::::::\\ /::::::\\ ",
    "|::::::::V::::::::|",
    "|:::::::::::::::::|",
    " \\:::::::::::::::/ ",
    "  `.:::::::::::.'  ",
    "    `.:::::::.'    ",
    "      `.:::.'      ",
    "        `v'        ",
)
WAX = "@@#%"
SIZE = (len(SPRITE[0]), len(SPRITE))


def cells():
    """[(col, row, char, is_wax)] for every visible cell of the seal."""
    out = []
    for r, row in enumerate(SPRITE):
        for c, ch in enumerate(row):
            if ch == ":":
                out.append((c, r, WAX[hash32(c, r) % len(WAX)], True))
            elif ch != " ":
                out.append((c, r, ch, False))
    return out


# --- NO route: crack and shatter (SPEC §11 no-4) -------------------------------------------------------

def _crack_path():
    """[(col, row, glyph)]: a jagged crack from the top notch down to the point, then two short branches."""
    cols = (9, 8, 9, 10, 9, 8, 9)                               # rows 2..8
    path = [(9, 2, "V")]
    for r in range(3, 9):
        dx = cols[r - 2] - cols[r - 3]
        path.append((cols[r - 2], r, "/" if dx < 0 else "\\" if dx > 0 else "|"))
    return path + [(7, 3, "_"), (6, 4, "/"), (11, 5, "\\"), (12, 6, "_")]


CRACK = _crack_path()
_SPINE = {r: c for c, r, _ in CRACK[:7]}                       # the crack's column on each row
FRAGMENTS = ".,'`:;*+~^\"%#@=-/\\|o"                           # what the heart breaks into
SPIN = r"/-\|"


def cracked(p, split=0.35):
    """[(col, row, char, kind, dx)] for the seal as a crack grows across it (p 0..1): crack cells take crack
    glyphs (kind 'c') in order, and the two halves part by up to `split` cells (dx)."""
    shown = {(c, r): g for c, r, g in CRACK[:round(p * len(CRACK))]}
    out = []
    for c, r, ch, wax in cells():
        side = 0 if r not in _SPINE else (-1 if c < _SPINE[r] else 1 if c > _SPINE[r] else 0)
        if (c, r) in shown:
            out.append((c, r, shown.pop((c, r)), "c", 0.0))
        else:
            out.append((c, r, ch, "h" if wax else "H", side * split * p))
    out += [(c, r, g, "c", 0.0) for (c, r), g in shown.items()]   # crack cells outside the sprite's ink
    return out


def shatter(t, cell=(9.0, 14.4), per_cell=2):
    """The burst, t seconds after it starts: [(x, y, char, alpha, kind)] in logical px from the seal's
    top-left. Every cell throws `per_cell` fragments with their own glyph, direction, speed, lifetime and
    spin; they kick outward and up, slow, fall and fade. Nothing is left after about 1.6 s."""
    cw, ch = cell
    cx, cy = (SIZE[0] - 1) / 2 * cw, (SIZE[1] - 1) / 2 * ch
    out = []
    for c, r, glyph, wax in cells():
        x0, y0 = c * cw, r * ch
        for k in range(per_cell):
            h = hash32(c, r, k + 7)
            u = [((h >> s) & 255) / 255 for s in (0, 8, 16, 24)]
            life = 0.55 + 1.05 * u[0]
            if t >= life:
                continue
            ang = math.atan2(y0 - cy, x0 - cx) + (u[1] - 0.5) * 1.6
            speed = 60 + 240 * u[2] ** 1.5                     # px/s: a few fly far, most drift
            drag = 2.2
            k_t = (1 - math.exp(-drag * t)) / drag             # distance factor under drag
            x = x0 + math.cos(ang) * speed * k_t
            y = y0 + (math.sin(ang) * speed - 90 * u[3]) * k_t + 0.5 * 260 * t * t   # an upward kick, then gravity
            if u[3] > 0.7:                                      # some tumble
                g = SPIN[int(t * (8 + 10 * u[1]) + 4 * u[0]) % 4]
            else:
                g = FRAGMENTS[hash32(c, r, k) % len(FRAGMENTS)] if k else glyph
            out.append((x, y, g, (1 - t / life) ** 1.4, "h" if wax else "H"))
    return out
