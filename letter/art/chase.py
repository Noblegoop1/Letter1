"""The chase game's pure core (SPEC §12, §13 step 1).

The player's mouse pointer, a big red ASCII arrow cursor, chases the NO button through a side-scrolling
runner: a ground line low on the canvas, the pointer lower left, block walls arriving from the right, the
NO button floating ahead. Space jumps and nothing else does; the mouse steers the pointer inside its lane.
The course is a seeded script in three phases, always fair; a collision is a short stumble, never a game
over. When the course ends the scrolling eases to a stop with NO trapped against an end wall, `cornered`
turns True and the pointer follows the mouse freely; the scene takes over (tremble, click, ending).

Logical px of the SIZE x SIZE canvas, y down; the world scrolls by `cam` px. Physics runs on fixed STEP
steps from an accumulator, so the course and its timings are the same at any frame rate; picture(),
no_rect() and pointer_rect() interpolate between the last two steps. The NO button is not in picture():
the scene draws the envelope's button art into no_rect(). Pure Python: no pygame.
"""
import math
import random
from bisect import bisect_right

from letter.engine.timeline import approach, clamp, hash32, smoothstep

SIZE = 320                  # logical canvas is SIZE x SIZE px
CELL = (8, 12)              # logical px per glyph cell (glyphs are drawn from their cell's top-left)
STEP = 1 / 120              # fixed simulation step

_CW, _CH = CELL
_CAP = 6                    # px from a '+' glyph's top to its ink (13 px bold, the same at every scale)
_MAX_DT = 0.25              # a longer hitch plays as this much (no catch-up spiral)

# --- layout (screen px) ---------------------------------------------------------------------------
_GROUND = 252               # things stand here: the ground line's ink starts at this y
_RIDGE = 214                # the distant hills' foot (ink y); they rise up to _RIDGE_H above it
_RIDGE_H = 16
_PARALLAX = 0.25            # the hills scroll this much per px of ground
_LANE = (16.0, 112.0)       # the pointer's tip x while running
_HOME = 40.0                # ... until the mouse moves
_STEER_TAU, _FREE_TAU = 0.08, 0.05     # s: the pointer's follow of the mouse, running and cornered
_WALL_X = 256               # the end wall's left edge once the scrolling has stopped
_HINT = ("[ SPACE ]", 124, 52)
_HINT_FROM = 0.6            # s; then shown until the first jump or the first obstacle is passed

# --- the pointer: the classic arrow cursor, outline and dotted fill, its tip at (0, 0) -------------
_ARROW_ROWS = ("|\\", "|.\\", "|..\\", "|...\\", "|....\\", "|_.___\\", "  \\..\\", "   \\__\\")
_ARROW = tuple((ch, c * 5.0 - 3, r * 6.5 - 2) for r, row in enumerate(_ARROW_ROWS)
               for c, ch in enumerate(row) if ch != " ")
_PW, _PH = 34.0, 59.5       # tip to the right-most / bottom ink
_BOX = (4.0, 3.0, 24.0, _PH - 3.0)      # collision box from the tip: forgiving at the wing and the stem
_HOVER = 2.0                # it glides this far above the ground line
_TRAIL = ((12, 0.0), (26, 0.37), (40, 0.71))    # speed lines: (y from the tip, phase)
_TRAIL_FROM = 60.0          # px/s; the speed lines show above this pace

# --- motion ----------------------------------------------------------------------------------------
_JUMP_T, _JUMP_H = 1.05, 104.0  # fixed jump duration (s) and height (px): a smooth, floaty arc
_COYOTE, _BUFFER = 0.1, 0.15    # a late jump still works this long after the ground ends; an early press
                                # is remembered this long
_REACT = 0.35               # reaction time in the fairness rule: gap >= speed * (jump + reaction)
_STUMBLE, _GRACE = 0.6, 0.25    # stumble length; then no new stumble for a moment
_SLOW = 0.35                # share of the run speed while stumbling
_FLASHES = ((0.08, 0.16), (0.30, 0.38))     # pointer hidden in these windows of a stumble: two flashes
_DIP = 12.0                 # px the pointer sinks into a ground gap it didn't jump
_BRAKE = 50.0               # px/s^2 the scrolling slows at as the course ends
_FIRST = 3.5                # s before the first obstacle reaches the pointer
_RUNOUT = 2.5               # s of clear ground after the last obstacle

# (name, scroll speed px/s, nominal seconds, gap range s, NO's left edge on screen, NO's evasion px x/y)
_PHASES = (
    ("A", 105.0, 20.0, (2.6, 3.3), 180.0, (8.0, 4.0)),
    ("B", 118.0, 45.0, (1.5, 2.3), 194.0, (14.0, 12.0)),
    ("C", 125.0, 25.0, (1.9, 2.6), 152.0, (10.0, 8.0)),
)

# --- the NO button (the scene draws the envelope's art into this rect) ----------------------------
_NW, _NH = 104.0, 52.0      # a third of the play width; the envelope button's 40 x 11 cells are w/h ~2
_NY = 124.0                 # its top at rest: its bottom stays above the tallest obstacle
_NX_MAX = SIZE - _NW - 8.0
_NO_GAP = 20.0              # it keeps at least this far ahead of the pointer
_FLOAT_T, _FLOAT_A = 3.2, 8.0   # rise-pause-fall-pause period (s) and height (px); half when cornered
_LEAD_BONUS, _LEAD_MAX = 14.0, 24.0         # NO's extra lead per stumble, and its cap

# --- obstacles: block shapes on the 8 x 12 grid, (cell offset, rows up, rows top to bottom) --------
_KINDS = {
    "barrier": ((0, 0, ("+--+", "|##|")),),
    "block": ((0, 0, ("+--+", "|##|", "|##|")),),
    "wall": ((0, 0, ("+--+", "|##|", "|##|", "|##|")),),
    "tall": ((0, 0, ("+--+", "|##|", "|##|", "|##|", "|##|")),),
    "stack": ((0, 0, ("+----+", "|####|")), (1, 2, ("+--+", "|##|"))),
    "gap": (),              # a missing stretch of ground, _GAP_W wide
}
_GAP_W = 40
_CLUSTERS = {               # cleared by one jump: (kind, cell offset)
    "twin": (("barrier", 0), ("barrier", 4)),
    "step": (("barrier", 0), ("block", 4)),
    "ditch": (("barrier", 0), ("gap", 5)),
}
_A_ORDER = ("barrier", "block", "barrier", "gap", "block", "wall")
_POOL = {"B": ("block", "wall", "tall", "stack", "gap", "twin", "step"),
         "C": ("barrier", "block", "wall", "gap", "twin", "ditch")}
_SCATTER = "*'.,`+"


def _art(blocks):
    """A kind's glyphs (ch, dx, dy from its left edge and _GROUND), its collision boxes (x0, x1, top: each
    down to the ground) and its drawn extent (width, top). A box sits inside the drawn ink: 2 px in at the
    sides, 3 px down from the top."""
    glyphs, boxes, w, top = [], [], 0, 0
    for c0, up, rows in blocks:
        n = len(rows)
        glyphs += [(ch, (c0 + c) * _CW, -16 - (n - 1 - r + up) * _CH)
                   for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != " "]
        ink = -16 - (n - 1 + up) * _CH + _CAP
        boxes.append(((c0 * _CW) + 2.0, (c0 + len(rows[0])) * _CW - 3.0, ink + 3.0))
        w, top = max(w, (c0 + len(rows[0])) * _CW), min(top, ink)
    return tuple(glyphs), tuple(boxes), (w if blocks else _GAP_W, top)


_ART = {k: _art(blocks) for k, blocks in _KINDS.items()}
_FRONT = _HOME + _BOX[0] + _BOX[2]      # the pointer box's right edge on screen, at home


def _parts(kind):
    """[(dx px, single kind)] for a cluster or a single obstacle, and its drawn width."""
    parts = [(c * _CW, k) for k, c in _CLUSTERS.get(kind, ((kind, 0),))]
    return parts, max(dx + _ART[k][2][0] for dx, k in parts)


def _build(seed):
    """-> (groups, phase starts, scroll end). groups: (x0, x1, phase, kind, ((x, single kind), ...)) in
    world px, sorted; phase starts are scroll positions where B and C begin; the course ends (the scrolling
    stops) at the scroll end. Gaps between groups use their phase's speed, so every one is fair."""
    rng = random.Random(seed)
    groups, starts = [], [-math.inf]
    ref = _FRONT                    # where the next gap is measured from: the last group's end
    t = t_end = 0.0
    for p, (name, v, dur, (lo, hi), *_) in enumerate(_PHASES):
        t_end += dur
        deck, k = [], 0
        while True:
            if name == "A":
                if k == len(_A_ORDER):
                    break
                kind = _A_ORDER[k]
            else:
                if not deck:        # every kind once per shuffled deck, never twice in a row
                    deck = list(_POOL[name])
                    rng.shuffle(deck)
                    if deck[-1] == groups[-1][3]:
                        deck.reverse()
                kind = deck.pop()
            g = _FIRST if not groups else rng.uniform(lo, hi)
            parts, w = _parts(kind)
            x = math.ceil((ref + v * g) / _CW) * _CW         # on the ground's cell grid
            if t + (x - ref + w) / v > t_end:
                break
            if k == 0 and p:
                starts.append((ref + x) / 2 - _FRONT)
            t += (x - ref + w) / v
            groups.append((x, x + w, p, kind, tuple((x + dx, kk) for dx, kk in parts)))
            ref, k = x + w, k + 1
    return groups, starts, ref + _PHASES[-1][1] * _RUNOUT - _FRONT


def _ridge(seed, cols=160):
    """Distant hills, periodic: px above _RIDGE per 6 px column, a smooth rolling profile."""
    rng = random.Random(seed + 101)
    a, b = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    return [round(_RIDGE_H * max(0.0, 0.5 + 0.4 * math.sin(2 * math.pi * k / cols * 3 + a)
                                 + 0.3 * math.sin(2 * math.pi * k / cols * 7 + b))) for k in range(cols)]


def _float(t):
    """NO's hover, 0 (bottom) to 1 (top): rises, pauses, falls, pauses."""
    u = t % _FLOAT_T / _FLOAT_T
    if u < 0.375:
        return smoothstep(0.0, 0.375, u)
    if u < 0.5:
        return 1.0
    return 1.0 - smoothstep(0.5, 0.875, u)


def _wall():
    """The end wall: courses of block bricks (a seam row, two body rows, every other course offset half a
    brick) from the ground up past NO, with a straight left face, running off the right edge."""
    rows, out = 17, []
    for r in range(rows):
        course, k = divmod(r, 3)
        for c in range((SIZE - _WALL_X) // _CW + 1):
            joint = c == 0 or (c + 2 * (course % 2)) % 4 == 0
            out.append((("+" if joint else "-") if k == 0 else ("|" if joint else "#"), c * _CW,
                        -16 - (rows - 1 - r) * _CH))
    return tuple(out)


_WALL = _wall()


class Chase:
    def __init__(self, seed=3):
        self._groups, self._starts, self._end = _build(seed)
        self._x0s = [g[0] for g in self._groups]
        self._out = self._groups[-1][1] - _HOME - _BOX[0]       # scroll where the last group is behind
        self._ground = self._ground_rows(seed, int(self._end + SIZE) // _CW + 2)
        self._hills = _ridge(seed)
        rng = random.Random(seed * 7919 + 1)
        self._rng = rng
        t, self._moves = 0.0, [(0.0, 0.0, 0.0)]
        while t < 400:              # NO's evasion: (start s, x, y) in -1..1, eased to, then held
            t += rng.uniform(1.6, 3.2)
            self._moves.append((t, rng.uniform(-1, 1), rng.uniform(-1, 0.4)))
        self._move_t = [m[0] for m in self._moves]
        self.t = 0.0
        self.cornered = False
        self._acc = 0.0
        self._cam = 0.0             # px the world has scrolled
        self._v = _PHASES[0][1]
        self._px, self._py = _HOME, _GROUND - _HOVER - _PH      # the pointer's tip on screen
        self._aim = (None, None)
        self._h = 0.0               # jump height, px
        self._dip = 0.0             # px sunk into a gap
        self._jump = None           # seconds into the current jump
        self._off = 0.0             # seconds on the ground over a gap
        self._buf = 0.0             # seconds the last press stays remembered
        self._trip = -math.inf      # when the last stumble began
        self._spent = set()         # obstacles already hit
        self._next = 0              # first group the pointer hasn't passed
        self._bonus = 0.0           # NO's extra lead after stumbles
        self._nx, self._ny = _PHASES[0][4], _NY     # NO's top-left, before its float
        self._na = _FLOAT_A
        self._bits = []             # stumble scatter: (t0, world x, y, vx, vy, ch)
        self._hint_gone = False
        self._prev = self._state()

    # --- public -------------------------------------------------------------------------------------
    @property
    def phase(self):
        return "cornered" if self.cornered else _PHASES[self._phase_index(self._cam)][0]

    @property
    def progress(self):
        return min(1.0, self._cam / self._end)

    def press(self):
        """Space went down."""
        if not self.cornered:
            self._buf = _BUFFER

    def aim(self, x, y=None):
        """The real mouse in logical px, or None when it leaves the window. Running, x steers the pointer
        inside its lane; cornered, the pointer's tip follows (x, y)."""
        self._aim = (x, None if x is None else y)

    def update(self, dt):
        """Advance by dt real seconds in fixed STEP steps."""
        self._acc += min(max(dt, 0.0), _MAX_DT)
        while self._acc >= STEP - 1e-9:
            self._acc -= STEP
            self._prev = self._state()
            self._step()

    def picture(self):
        """Every glyph to draw this frame, back to front: [(ch, role, x, y)], glyph top-left in logical px.
        The world first (h hills, g ground, o obstacles, w end wall, t hint), then the pointer (r speed
        lines, m arrow) and x stumble scatter. NO is not in it: see no_rect()."""
        t, cam, px, py, nx, ny = self._lerp()
        i = bisect_right(self._x0s, cam + SIZE)
        near = [(x - cam, kind) for x0, x1, _, _, parts in self._groups[max(0, i - 6):i] if x1 > cam
                for x, kind in parts]
        # the hills pass behind NO, the obstacles and the arrow (its right edge slants out with height)
        fronts = [(nx, ny, nx + _NW, ny + _NH), (self._end + _WALL_X - cam, 0, SIZE, _GROUND)]
        fronts += [(x, _GROUND + _ART[k][2][1], x + _ART[k][2][0], _GROUND) for x, k in near if k != "gap"]
        out = []
        off = cam * _PARALLAX
        k0 = math.floor(off / 6)
        for k in range(k0, k0 + SIZE // 6 + 2):
            x, y = k * 6 - off, _RIDGE - self._hills[k % len(self._hills)]
            dy = y - py
            if 0 <= dy <= _PH and px - 2 < x + 7 and x < px + min(_PW, 0.8 * dy + 8):
                continue
            if not any(a < x + 7 and x < c and b < y + 2 and y < d for a, b, c, d in fronts):
                out.append(("_", "h", x, y - 14))
        line, rows = self._ground
        k0 = max(0, math.floor(cam / 6))
        out.extend(("_", "g", k * 6 - cam, _GROUND - 14) for k in range(k0, min(len(line), k0 + SIZE // 6 + 2))
                   if line[k])
        k0 = max(0, math.floor(cam / _CW))
        for r, row in enumerate(rows):
            out.extend((row[k], "g", k * _CW - cam, _GROUND - 3 + r * _CH)
                       for k in range(k0, min(len(row), k0 + SIZE // _CW + 1)) if row[k] != " ")
        for x, kind in near:
            out.extend((ch, "o", x + dx, _GROUND + dy) for ch, dx, dy in _ART[kind][0])
        wx = self._end + _WALL_X - cam
        if wx < SIZE:
            out.extend((ch, "w", wx + dx, _GROUND + dy) for ch, dx, dy in _WALL)
        if t >= _HINT_FROM and not self._hint_gone:
            text, x, y = _HINT
            out.extend((ch, "t", x + c * _CW, y) for c, ch in enumerate(text) if ch != " ")
        e = t - self._trip
        if not any(a <= e < b for a, b in _FLASHES):
            out.extend(self._pointer(t, px, py))
        for t0, x, y, vx, vy, ch in self._bits:
            e = t - t0
            by = y + vy * e + 300 * e * e
            if 0 <= e < _STUMBLE and by < _GROUND - 6:
                out.append((ch, "x", x + vx * e - cam, by))
        return out

    def no_rect(self):
        """(x, y, w, h) logical px of the floating NO button now: its float and evasion included."""
        *_, nx, ny = self._lerp()
        return nx, ny, _NW, _NH

    def pointer_rect(self):
        """(x, y, w, h) logical px of the pointer's collision box now."""
        _, _, px, py, _, _ = self._lerp()
        return px + _BOX[0], py + _BOX[1], _BOX[2], _BOX[3]

    # --- private ------------------------------------------------------------------------------------
    def _state(self):
        return self.t, self._cam, self._px, self._py, self._nx, self._ny - self._na * _float(self.t)

    def _lerp(self):
        a = min(1.0, max(0.0, self._acc / STEP))
        return tuple(p + (c - p) * a for p, c in zip(self._prev, self._state()))

    def _phase_index(self, cam):
        return bisect_right(self._starts, cam) - 1

    def _ground_rows(self, seed, cells):
        """The ground line (a '_' every 6 px, overlapping into one solid line: True where drawn) and three
        rows of sparse specks under it (8 px cells), over the whole world. A gap cuts a pit with walls."""
        line = [True] * (cells * _CW // 6)
        rows = [[chars[hash32(k, r, seed) % len(chars)] if (hash32(k, r, seed) >> 8) % 100 < keep else " "
                 for k in range(cells)] for r, (chars, keep) in enumerate(((".-,.", 30), (".,", 18), (".", 9)))]
        for _, _, _, _, parts in self._groups:
            for x, kind in parts:
                if kind == "gap":
                    for k in range(math.ceil((x - 6) / 6), math.ceil((x + _GAP_W) / 6)):
                        line[k] = False
                    for k in range(x // _CW, (x + _GAP_W) // _CW):
                        rows[0][k] = rows[1][k] = " "
                    rows[0][x // _CW - 1] = rows[0][(x + _GAP_W) // _CW] = "|"
        return line, ["".join(r) for r in rows]

    def _pointer(self, t, px, py):
        """The arrow's glyphs: no legs, no run cycle. It leans into its glide, tilts back rising and
        forward falling in a jump, and trails speed lines while it runs fast."""
        if self.cornered:
            shear = 0.0
        elif self._jump is not None:
            shear = -0.07 * (1 - 2 * self._jump / _JUMP_T)
        else:
            shear = 0.04 + 0.01 * math.sin(2 * math.pi * 0.7 * t)
        out = []
        if not self.cornered and self._v > _TRAIL_FROM:
            for y, ph in _TRAIL:
                u = (t * 2.2 + ph) % 1.0
                out += [("-", "r", px - 10 - 22 * u - d, py + y) for d in (0, 5)]
        out.extend((ch, "m", px + dx + shear * (_PH - dy), py + dy) for ch, dx, dy in _ARROW)
        return out

    def _step(self):
        self.t += STEP
        ax, ay = self._aim
        if self.cornered:
            if ax is not None:
                self._px = approach(self._px, clamp(ax, 0.0, SIZE - _PW), STEP, _FREE_TAU)
            if ay is not None:
                self._py = approach(self._py, clamp(ay, 0.0, SIZE - _PH), STEP, _FREE_TAU)
            self._move_no(0.0)
            return
        p = self._phase_index(self._cam)
        stumbling = self.t - self._trip < _STUMBLE
        target = _PHASES[p][1] * (_SLOW if stumbling else 1.0)
        self._v = min(approach(self._v, target, STEP, 0.25), math.sqrt(2 * _BRAKE * max(0.0, self._end - self._cam)))
        self._cam += self._v * STEP
        if self._end - self._cam < 0.01:
            self._cam, self._v = self._end, 0.0
        if ax is not None:
            self._px = approach(self._px, clamp(ax, *_LANE), STEP, _STEER_TAU)

        if self._buf > 0 and self._jump is None and self._off <= _COYOTE:
            self._jump, self._buf, self._off = 0.0, 0.0, 0.0
            self._hint_gone = True
        self._buf = max(0.0, self._buf - STEP)
        if self._jump is not None:
            self._jump += STEP
            if self._jump >= _JUMP_T:
                self._jump = None
        k = 0.0 if self._jump is None else self._jump / _JUMP_T
        self._h = 4 * _JUMP_H * k * (1 - k)

        b0 = self._cam + self._px + _BOX[0]
        b1 = b0 + _BOX[2]
        while self._next < len(self._groups) and self._groups[self._next][1] <= b0:
            self._next += 1
            self._hint_gone = True
        gap, hit = None, False
        for gi in range(self._next, len(self._groups)):
            x0, _, _, _, parts = self._groups[gi]
            if x0 >= b1:
                break
            for pi, (x, kind) in enumerate(parts):
                if (gi, pi) in self._spent:
                    continue
                if kind == "gap":
                    if x + 4 <= (b0 + b1) / 2 <= x + _GAP_W - 4:
                        gap = (gi, pi)
                elif any(b0 < x + hi and x + lo < b1 and _HOVER + self._h < -top for lo, hi, top in _ART[kind][1]):
                    self._spent.add((gi, pi))
                    hit = True
        self._off = self._off + STEP if gap and self._jump is None else 0.0
        if self._off > _COYOTE:
            self._spent.add(gap)
            hit = True
        self._dip = approach(self._dip, _DIP if self._off > _COYOTE else 0.0, STEP, 0.05)
        self._py = _GROUND - _HOVER - _PH - self._h + self._dip
        if hit and self.t - self._trip >= _STUMBLE + _GRACE:
            self._stumble()

        self._bonus = approach(self._bonus, 0.0, STEP, 3.0)
        self._move_no(self._h / _JUMP_H)
        if self._cam >= self._end and self._jump is None and self._dip < 0.5:
            self.cornered = True

    def _move_no(self, leap):
        """NO's target: its phase's distance ahead, eased between seeded evasive moves (each one pauses
        when it gets there), a lead after stumbles, a flinch up and away while the pointer leaps, and
        never closer than _NO_GAP to the pointer. It backs into the end wall as the course ends."""
        if self.cornered or self._cam >= self._out:
            tx, ty = _WALL_X - _NW, _NY
        else:
            p = self._phase_index(self._cam)
            sx, sy = _PHASES[p][5]
            i = bisect_right(self._move_t, self.t) - 1
            (t0, x1, y1), (_, x0, y0) = self._moves[i], self._moves[max(0, i - 1)]
            k = smoothstep(0.0, 0.9, self.t - t0)
            tx = _PHASES[p][4] + sx * (x0 + (x1 - x0) * k) + self._bonus + 10 * leap
            ty = _NY + sy * (y0 + (y1 - y0) * k) - 10 * leap
            tx = max(tx, self._px + _PW + _NO_GAP)
        wall = self._end + _WALL_X - self._cam
        self._nx = min(approach(self._nx, tx, STEP, 0.35), _NX_MAX, wall - _NW)
        self._ny = approach(self._ny, ty, STEP, 0.3)
        self._na = approach(self._na, _FLOAT_A / 2 if self.cornered or self._cam >= self._out else _FLOAT_A, STEP, 0.5)

    def _stumble(self):
        self._trip = self.t
        self._bonus = min(_LEAD_MAX, self._bonus + _LEAD_BONUS)
        rng = self._rng
        x, y = self._cam + self._px + _BOX[0] + _BOX[2], self._py + 36      # knocked off its front
        self._bits = [(self.t, x + rng.uniform(-6, 6), y, rng.uniform(-30, 110), rng.uniform(-170, -70),
                       rng.choice(_SCATTER)) for _ in range(7)]
