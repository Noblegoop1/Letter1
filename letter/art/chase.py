"""The chase game's pure core (SPEC §12, §13 step 1).

The player, a red ASCII mouse pointer (the arrow cursor), glides right after the fleeing NO button along
an ASCII ground; Space jumps, and nothing else does anything. The course is a seeded, scripted list of obstacle groups in three phases of rising
pace, spaced so it is always fair; a collision is a short stumble, never a game over. When the course
ends the camera eases to a stop, NO backs into a wall at the right and `cornered` turns True; the scene
takes over from there (pointer tremble, click, ending).

World units are logical px of the SIZE x SIZE canvas; x grows to the right and the camera follows the
mouse. Physics runs on fixed STEP steps from an accumulator, so the course and its timings are the same at
any frame rate; picture() interpolates between the last two steps. Pure Python: no pygame.
"""
import math
import random
from bisect import bisect_right

from letter.engine.timeline import approach, hash32

SIZE = 320                  # logical canvas is SIZE x SIZE px
CELL = (8, 12)              # logical px per glyph cell (glyphs are drawn from their cell's top-left)
STEP = 1 / 120              # fixed simulation step

_CW, _CH = CELL
# The 13 px font's ink sits about 2..16 px below a glyph's top. Everything stands on _FOOT, where a
# standing glyph's ink ends; the ground's surface ink starts just below it.
_GY = 240                   # top of the ground's surface row
_FOOT = _GY + 6
_HY = 166                   # top of the horizon row
_PARALLAX = 0.3             # horizon scroll per px of camera
_MOUSE_X = 40               # mouse pointer's left edge on screen while the camera follows it
_WALL_X = 288               # wall's left edge on screen once the camera has stopped
_WALL_ROWS = 9              # above the ground
_CAM_L = 240.0              # the camera eases to a stop over the mouse's last _CAM_L px, so the mouse
                            # walks _CAM_L / 2 on across the screen and stops a little way off NO
_MAX_DT = 0.25              # a longer hitch plays as this much (no catch-up spiral)
_HINT = ("[ SPACE ]", 124, 108)
_HINT_FROM = 0.6            # s; then shown until the first jump or the first obstacle is passed

_JUMP_T, _JUMP_H = 0.8, 60.0    # fixed jump duration (s) and height (px)
_COYOTE, _BUFFER = 0.1, 0.15    # a late jump still works this long after leaving the ground; an early
                                # press is remembered this long
_REACT = 0.35               # reaction time in the fairness rule: gap >= speed * (jump + reaction)
_STUMBLE, _GRACE = 0.6, 0.25    # stumble length; then no new stumble for a moment
_SLOW = 0.35                # share of the run speed while stumbling
_FLASHES = ((0.08, 0.16), (0.30, 0.38))     # pointer hidden in these windows of a stumble: two flashes
_LEAD_BONUS, _LEAD_MAX = 24.0, 48.0         # NO's extra lead per stumble, and its cap
_BRAKE = 80.0               # px/s^2 the mouse slows at as the course ends
_RUNOUT = 2.5               # s of clear ground after the last obstacle
_FIRST = 4.0                # s before the first obstacle reaches the mouse

# (name, run speed px/s, nominal seconds, gap range s, NO's lead px)
_PHASES = (
    ("A", 90.0, 20.0, (2.4, 3.2), 184.0),
    ("B", 104.0, 45.0, (1.35, 2.25), 160.0),
    ("C", 118.0, 25.0, (1.25, 1.75), 112.0),
)


def _glyphs(rows, pitch, bottom):
    """((ch, dx, dy), ...) for rows of text: the last row's glyph top at dy = bottom, rows pitch px apart."""
    n = len(rows)
    return tuple((ch, c * _CW, bottom - (n - 1 - r) * pitch)
                 for r, line in enumerate(rows) for c, ch in enumerate(line) if ch != " ")


# The player is a mouse pointer: the classic arrow cursor (outline, # fill, the short stem at the bottom
# right), 6 cells wide and 7 rows at a 10 px pitch so its edges join up. It glides with its stem tip
# just above the ground; its hitbox is the arrow's head (forgiving at the stem). Glyph offsets are from
# its left edge and _FOOT; a shear (px per px of height) leans it.
_BOX = (8, 32)
_ARROW = _glyphs(("|\\", "|#\\", "|##\\", "|###\\", "|#/\\_\\", "|/ \\#\\", "    \\/"), 10, -17)
_TRAIL = (("-", -11, -57), ("=", -13, -45), ("-", -23, -45), ("-", -10, -33))   # faint speed lines
_TRAIL_FROM = 60.0          # px/s; the speed lines show above this pace

# NO button: a framed box on little feet, 4 cells wide.
_NW = 4 * _CW
_NO_TOP = -49               # box's top glyph row, relative to _FOOT
_NO_BOX = _glyphs((".--.", "|NO|", "'--'"), 12, _NO_TOP + 24)
_NO_FEET = tuple(_glyphs((f,), 0, -15) for f in (" /\\ ", " |\\ ", " /| "))
_NO_STAND = _glyphs((" || ",), 0, -15)

# Obstacles: rows (top to bottom, standing on the ground), hitbox x range from their left edge, height px.
_KINDS = {
    "rock": (("o",), (1, 7), 6),
    "debris": ((",;.",), (2, 22), 5),
    "barrier": (("|#|",), (3, 21), 9),
    "stack": (("[#]", "[#]"), (4, 20), 20),
    "gap": ((), (6, 26), 0),        # 4 missing ground cells: trips you only while you're on the ground
}
_GAP_W = 32
_GROUPS = {                         # cleared by one jump: (kind, cell offset)
    "rocks": (("rock", 0), ("rock", 2)),
    "rubble": (("debris", 0), ("rock", 3)),
    "rockbar": (("rock", 0), ("barrier", 2)),
}
_A_ORDER = ("rock", "debris", "barrier", "gap", "rock", "barrier", "debris")
_POOL = {
    "B": ("rock", "debris", "barrier", "stack", "gap", "rocks", "rubble"),
    "C": ("rock", "barrier", "stack", "gap", "rocks", "rubble", "rockbar"),
}
_ART = {k: _glyphs(rows, _CH, -14) for k, (rows, _, _) in _KINDS.items()}
_SCATTER = "*'.,`:+"


def _width(kind):
    return _GAP_W if kind == "gap" else len(_KINDS[kind][0][0]) * _CW


def _parts(kind):
    """[(dx px, single kind)] for a group or a single obstacle, and its width."""
    parts = [(c * _CW, k) for k, c in _GROUPS.get(kind, ((kind, 0),))]
    return parts, max(dx + _width(k) for dx, k in parts)


def _build(seed):
    """-> (groups, phase starts, mouse end x). groups: (x0, x1, phase, ((x, kind), ...)) sorted by x;
    phase starts are mouse-box-front x where phases B and C begin; gaps use the speed of their phase."""
    rng = random.Random(seed)
    groups, starts = [], [-math.inf]
    ref = _MOUSE_X + _BOX[1]        # x the next gap is measured from: the last group's end
    t = t_end = 0.0
    for p, (name, v, dur, (lo, hi), _) in enumerate(_PHASES):
        t_end += dur
        k, last = 0, None
        while True:
            if name == "A":
                if k == len(_A_ORDER):
                    break
                kind = _A_ORDER[k]
            else:
                kind = rng.choice([c for c in _POOL[name] if c != last])
            g = _FIRST if not groups else rng.uniform(lo, hi)
            parts, w = _parts(kind)
            x = math.ceil((ref + v * g) / _CW) * _CW         # on the ground's cell grid
            if t + (x - ref + w) / v > t_end:
                break
            if k == 0 and p:
                starts.append((ref + x) / 2)
            t += (x - ref + w) / v
            groups.append((x, x + w, p, tuple((x + dx, kk) for dx, kk in parts)))
            ref, last, k = x + w, kind, k + 1
    end = math.ceil((ref + _PHASES[-1][1] * _RUNOUT - _BOX[1]) / _CW) * _CW   # camera stops on the grid
    return groups, starts, float(end)


def _ground(seed, groups, cols, wall_col):
    """Ground rows over the whole world: a `= - ~ _` surface, then sparser specks; gaps cut a pit."""
    rows = []
    for r, (chars, keep) in enumerate((("==-=~==_-=", 100), ("-.~,. -", 38), (".,", 18), (".", 8))):
        row = []
        for k in range(cols):
            h = hash32(k // (2 if r == 0 else 1), r, seed)
            row.append(chars[h % len(chars)] if (h >> 8) % 100 < keep and k < wall_col else " ")
        rows.append(row)
    n = _GAP_W // _CW
    for _, _, _, parts in groups:
        for x, kind in parts:
            if kind == "gap":
                c = x // _CW
                for i in range(n):
                    rows[0][c + i] = rows[2][c + i] = " "
                    rows[1][c + i] = "\\" if i == 0 else "/" if i == n - 1 else " "
    return ["".join(row) for row in rows]


def _horizon(seed, cols=120):
    """One periodic row of low distant hills, at least cols cells long."""
    rng = random.Random(seed + 101)
    feats = ("_.-~-._", "_.--._", "_.-._", "__", "___", "_.", "____", "  ", "_ _")
    row = ""
    while len(row) < cols:
        row += rng.choice(feats)
    return row


class Chase:
    def __init__(self, seed=3):
        self._groups, self._starts, self._end = _build(seed)
        self._x0s = [g[0] for g in self._groups]
        self._cam_end = self._end - _MOUSE_X - _CAM_L / 2
        self._wall = self._cam_end + _WALL_X
        self._rows = _ground(seed, self._groups, int(self._cam_end + SIZE) // _CW + 2, int(self._wall) // _CW)
        self._hills = _horizon(seed)
        self._rng = random.Random(seed * 7919 + 1)
        self.t = 0.0
        self.cornered = False
        self._acc = 0.0
        self._mx = float(_MOUSE_X)      # mouse sprite's left edge, world px
        self._v = _PHASES[0][1]
        self._h = 0.0                   # feet above the ground, px
        self._jump = None               # seconds into the current jump
        self._off = 0.0                 # seconds on the ground over a gap
        self._buf = 0.0                 # seconds the last press stays remembered
        self._trip = -math.inf          # when the last stumble began
        self._spent = set()             # obstacles already hit
        self._next = 0                  # first group the mouse hasn't passed
        self._lead = _PHASES[0][4]      # NO's left edge minus the mouse's, px
        self._bonus = 0.0
        self._bits = []                 # stumble scatter: (t0, x, y, vx, vy, ch)
        self._hint_gone = False
        self._prev = self._state()

    # --- public -------------------------------------------------------------------------------------
    @property
    def phase(self):
        return "cornered" if self.cornered else _PHASES[self._phase_index(self._mx)][0]

    @property
    def progress(self):
        return min(1.0, (self._mx - _MOUSE_X) / (self._end - _MOUSE_X))

    def press(self):
        """Space went down."""
        if not self.cornered:
            self._buf = _BUFFER

    def update(self, dt):
        """Advance by dt real seconds in fixed STEP steps."""
        self._acc += min(max(dt, 0.0), _MAX_DT)
        while self._acc >= STEP - 1e-9:
            self._acc -= STEP
            self._prev = self._state()
            self._step()

    def picture(self, shake=(0.0, 0.0)):
        """Every glyph to draw this frame, back to front: [(ch, role, x, y)], glyph top-left in logical px."""
        t, mx, h, lead = self._lerp()
        cam = self._cam(mx)
        out = []
        off = cam * _PARALLAX
        k0 = math.floor(off / _CW)
        for k in range(k0, k0 + SIZE // _CW + 1):
            ch = self._hills[k % len(self._hills)]
            if ch != " ":
                out.append((ch, "h", k * _CW - off, _HY))
        k0 = max(0, math.floor(cam / _CW))
        for r, row in enumerate(self._rows):
            for k in range(k0, min(len(row), k0 + SIZE // _CW + 1)):
                if row[k] != " ":
                    out.append((row[k], "g", k * _CW - cam, _GY + r * _CH))
        i = bisect_right(self._x0s, cam + SIZE)
        for _, x1, _, parts in self._groups[max(0, i - 6):i]:
            if x1 > cam:
                for x, kind in parts:
                    out.extend((ch, "o", x + dx - cam, _FOOT + dy) for ch, dx, dy in _ART[kind])
        wx = self._wall - cam
        if wx < SIZE:
            for r in range(_WALL_ROWS + 2):
                y = _FOOT - 14 - (_WALL_ROWS - 1 - r) * _CH
                out.append(("." if r == 0 else "|", "w", wx, y))
                for c in range(1, (SIZE - _WALL_X) // _CW):
                    out.append(("_" if r == 0 else "#=="[(c + r) % 3], "w", wx + c * _CW, y))
        nx, ny, pinned = self._no(mx, lead, cam)
        sx, sy = shake if self.cornered else (0.0, 0.0)
        feet = _NO_STAND if pinned else _NO_FEET[int(nx + cam) // 9 % 3]
        out.extend((ch, "n", nx + dx + sx, ny + dy + sy) for ch, dx, dy in _NO_BOX + feet)
        e = t - self._trip
        if not any(a <= e < b for a, b in _FLASHES):
            out.extend((ch, role, mx - cam + dx, _FOOT + dy - h) for ch, role, dx, dy in self._pointer(t, e))
        for t0, x, y, vx, vy, ch in self._bits:
            e = t - t0
            by = y + vy * e + 300 * e * e
            if 0 <= e < _STUMBLE and by < _FOOT - 8:
                out.append((ch, "x", x + vx * e - cam, by))
        if t >= _HINT_FROM and not self._hint_gone:
            text, x, y = _HINT
            out.extend((ch, "t", x + c * _CW, y) for c, ch in enumerate(text) if ch != " ")
        return out

    def no_rect(self):
        """(x, y, w, h) logical px around the NO button's glyph cells now (box and feet), without shake."""
        _, mx, _, lead = self._lerp()
        nx, ny, _ = self._no(mx, lead, self._cam(mx))
        return nx, ny + _NO_TOP, _NW, -_NO_TOP

    # --- private ------------------------------------------------------------------------------------
    def _state(self):
        return self.t, self._mx, self._h, self._lead

    def _lerp(self):
        a = min(1.0, max(0.0, self._acc / STEP))
        return tuple(p + (c - p) * a for p, c in zip(self._prev, self._state()))

    def _phase_index(self, mx):
        return bisect_right(self._starts, mx + _BOX[1]) - 1

    def _cam(self, mx):
        """Camera follows the mouse, then eases to a stop (C1-smooth) over the mouse's last _CAM_L px."""
        u0 = self._end - _MOUSE_X - _CAM_L
        s = min(1.0, (mx - _MOUSE_X - u0) / _CAM_L)
        return mx - _MOUSE_X if s <= 0 else u0 + _CAM_L * (s - s * s / 2)

    def _no(self, mx, lead, cam):
        """NO's screen x and _FOOT-based y (glyph offsets add to these), and whether it is at the wall."""
        x = mx + lead
        pinned = x >= self._wall - _NW
        x = min(x, self._wall - _NW)
        c = x + _NW / 2
        hop = 0.0
        i = bisect_right(self._x0s, c)
        for x0, x1, _, parts in self._groups[max(0, i - 2):i + 1]:
            d = c - (x0 + x1) / 2
            reach = (x1 - x0 + _NW) / 2 + 10
            if abs(d) < reach:
                top = max(_KINDS[k][2] for _, k in parts)
                hop = max(hop, (top + 14 if top else 8) * (1 - (d / reach) ** 2))
        bob = 0.0 if pinned else 2.0 * abs(math.sin(math.pi * x / 18))
        return min(x - cam, SIZE - _NW - _CW), _FOOT - hop - bob, pinned

    def _pointer(self, t, e):
        """The pointer's glyphs (ch, role, dx, dy) for this moment: it leans into its glide with a slight
        bob, tilts back rising and forward falling in a jump, and wobbles through a stumble."""
        bob = -1.5 * (1 + math.sin(2 * math.pi * 2.1 * t))
        if e < _STUMBLE:
            shear = 0.16 * math.sin(2 * math.pi * 5 * e) * (1 - e / _STUMBLE)
        elif self._jump is not None:
            shear, bob = -0.08 * (1 - 2 * self._jump / _JUMP_T), 0.0
        else:
            shear = 0.035 * self._v / _PHASES[-1][1] + 0.012 * math.sin(2 * math.pi * 0.9 * t)
        out = [(ch, "r", dx, dy + bob) for ch, dx, dy in _TRAIL] if self._v > _TRAIL_FROM else []
        out += [(ch, "m", dx - shear * (dy + 17), dy + bob) for ch, dx, dy in _ARROW]
        return out

    def _step(self):
        self.t += STEP
        if self.cornered:
            return
        p = self._phase_index(self._mx)
        stumbling = self.t - self._trip < _STUMBLE
        target = _PHASES[p][1] * (_SLOW if stumbling else 1.0)
        self._v = min(approach(self._v, target, STEP, 0.2), math.sqrt(2 * _BRAKE * max(0.0, self._end - self._mx)))
        self._mx += self._v * STEP
        if self._end - self._mx < 0.01:
            self._mx, self._v = self._end, 0.0

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

        b0, b1 = self._mx + _BOX[0], self._mx + _BOX[1]
        while self._next < len(self._groups) and self._groups[self._next][1] <= b0:
            self._next += 1
            self._hint_gone = True
        gap, hit = None, False
        for gi in range(self._next, len(self._groups)):
            x0, _, _, parts = self._groups[gi]
            if x0 >= b1:
                break
            for pi, (x, kind) in enumerate(parts):
                (lo, hi), height = _KINDS[kind][1:]
                if (gi, pi) in self._spent:
                    continue
                if kind == "gap":
                    if x + lo <= (b0 + b1) / 2 <= x + hi:
                        gap = (gi, pi)
                elif b0 < x + hi and x + lo < b1 and self._h < height:
                    self._spent.add((gi, pi))
                    hit = True
        self._off = self._off + STEP if gap and self._jump is None else 0.0
        if self._off > _COYOTE:
            self._spent.add(gap)
            hit = True
        if hit and self.t - self._trip >= _STUMBLE + _GRACE:
            self._stumble()

        self._bonus = approach(self._bonus, 0.0, STEP, 3.0)
        self._lead = approach(self._lead, _PHASES[p][4] + self._bonus, STEP, 1.2)
        if self._mx >= self._end and self._jump is None:
            self.cornered = True

    def _stumble(self):
        self._trip = self.t
        self._bonus = min(_LEAD_MAX, self._bonus + _LEAD_BONUS)
        rng = self._rng
        x, y = self._mx + _BOX[1], _FOOT - 16 - self._h      # knocked off its front, up and forward
        self._bits = [(self.t, x + rng.uniform(-6, 6), y, rng.uniform(-30, 110), rng.uniform(-170, -70),
                       rng.choice(_SCATTER)) for _ in range(7)]
