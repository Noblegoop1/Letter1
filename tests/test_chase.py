"""The chase core (SPEC §12, §13 step 1): C1-C10, fairness, determinism, cost. Bots read private state."""
import copy
import math
import os
import random
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.art import chase  # noqa: E402

ROLES = set("ghomwxtr")
BOX = chase._BOX


def front(c):
    """World x of the pointer box's centre."""
    return c._cam + c._px + BOX[0] + BOX[2] / 2


def jumper(jitter=0.0, seed=1):
    """A bot that presses where a player would: centred over the next obstacle group, give or take
    jitter seconds (a typical player's timing)."""
    rng = random.Random(seed)
    late = {}

    def bot(c):
        if c._jump is not None:
            return False
        for gi in range(c._next, min(c._next + 2, len(c._groups))):
            x0, x1 = c._groups[gi][:2]
            if (x0 + x1) / 2 > front(c):
                e = late.setdefault(gi, rng.uniform(-jitter, jitter))
                return (x0 + x1) / 2 - front(c) <= c._v * (chase._JUMP_T / 2 - e)
        return False
    return bot


def advance(c, secs, fps=120):
    """update() plays at most 0.25 s per call (a hitch guard), so step through longer spans."""
    for _ in range(round(secs * fps)):
        c.update(1 / fps)


def play(bot=None, fps=60, seed=3, each=None, limit=200.0):
    """Run a chase at fps until it is cornered; -> (seconds of frames played, the chase, stumbles)."""
    c, dt, n, trips, last = chase.Chase(seed), 1 / fps, 0, 0, -math.inf
    while not c.cornered and n * dt < limit:
        if bot and bot(c):
            c.press()
        c.update(dt)
        n += 1
        if c._trip != last:
            trips, last = trips + 1, c._trip
        if each:
            each(c)
    return n * dt, c, trips


def record(bot):
    """A full run at 60 fps with every frame's picture and rects."""
    log = []
    secs, c, trips = play(bot, each=lambda c: log.append(
        dict(t=c.t, phase=c.phase, progress=c.progress, v=c._v, trip=c._trip, h=c._h, bonus=c._bonus,
             no=c.no_rect(), me=c.pointer_rect(), pic=c.picture())))
    return dict(secs=secs, c=c, trips=trips, log=log)


# where the 13 px bold font puts each glyph's ink in its box: (x0, x1, y0, y1), measured with pygame
INK = {"|": (3, 5, 3, 16), "+": (0, 7, 6, 13), "-": (1, 6, 8, 10), "#": (0, 8, 4, 14), "_": (0, 7, 14, 16),
       "\\": (1, 7, 2, 16), ".": (2, 5, 11, 14)}


def ink(glyphs):
    """(x0, x1, y0, y1) of the ink of glyphs [(ch, x, y)]."""
    boxes = [(x + INK[ch][0], x + INK[ch][1], y + INK[ch][2], y + INK[ch][3]) for ch, x, y in glyphs]
    return min(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), max(b[3] for b in boxes)


_RUNS = {}


class Runs(unittest.TestCase):
    """Two full runs, recorded once for the whole module: a typical player and one who never jumps."""
    @classmethod
    def setUpClass(cls):
        if not _RUNS:
            _RUNS.update(typical=record(jumper(jitter=0.08)), never=record(None))
        cls.typical, cls.never = _RUNS["typical"], _RUNS["never"]


class Controls(Runs):
    def test_c1_update_alone_never_jumps(self):
        self.assertEqual(max(f["h"] for f in self.never["log"]), 0.0)
        c = chase.Chase()
        for x in (16, 300, 60, None):           # the mouse steers; it never jumps
            c.aim(x, 10)
            advance(c, 0.5)
            self.assertEqual(c._h, 0.0)

    def test_c1_press_jumps_on_a_fixed_arc(self):
        c = chase.Chase()
        advance(c, 0.5)
        y0 = c.pointer_rect()[1]
        c.press()
        peak = 0.0
        for _ in range(round(chase._JUMP_T * 120) + 2):
            c.update(chase.STEP)
            peak = max(peak, y0 - c.pointer_rect()[1])
        self.assertAlmostEqual(peak, chase._JUMP_H, delta=0.5)
        self.assertEqual((c._h, c.pointer_rect()[1]), (0.0, y0))

    def test_a_press_in_the_air_is_not_a_second_jump(self):
        c = chase.Chase()
        advance(c, 0.5)
        c.press()
        advance(c, 0.2)
        c.press()                                   # long before landing: the buffer expires
        advance(c, chase._JUMP_T - 0.2 + 0.05)
        self.assertEqual(c._h, 0.0)

    def test_the_buffer_catches_an_early_press(self):
        c = chase.Chase()
        advance(c, 0.5)
        c.press()
        advance(c, chase._JUMP_T - 0.05)
        c.press()                                   # 50 ms before landing
        advance(c, 0.15)
        self.assertGreater(c._h, 0.0)

    def test_coyote_time_lets_a_late_jump_off_a_gap_edge(self):
        c = chase.Chase()
        gi, gx = next((i, x) for i, g in enumerate(c._groups) for x, k in g[4] if k == "gap")
        while front(c) < gx + 4 + 0.05 * c._v:       # 50 ms over the gap (earlier obstacles trip it: fine)
            c.update(chase.STEP)
        trip = c._trip
        c.press()
        c.update(chase.STEP)
        self.assertGreater(c._h, 0.0)
        advance(c, 1.2)
        self.assertEqual((c._trip, (gi, 0) in c._spent), (trip, False))

    def test_presses_do_nothing_once_cornered(self):
        c = copy.deepcopy(self.never["c"])
        cam = c._cam
        c.press()
        advance(c, 1.0)
        self.assertEqual((c._h, c._cam, c.phase), (0.0, cam, "cornered"))

    def test_c7_the_mouse_steers_the_pointer_inside_its_lane(self):
        c = chase.Chase()
        lo, hi = chase._LANE
        for x, want in ((300, hi), (-40, lo), (70, 70)):
            c.aim(x, 20)
            advance(c, 0.6)
            self.assertAlmostEqual(c._px, want, delta=0.5)
        y = c.pointer_rect()[1]
        c.aim(70, 300)                              # running, y is ignored
        advance(c, 0.3)
        self.assertEqual(c.pointer_rect()[1], y)
        c.aim(None)                                 # the mouse left the window: it holds
        advance(c, 0.3)
        self.assertAlmostEqual(c._px, 70, delta=0.5)

    def test_c7_steering_keeps_working_mid_jump(self):
        c = chase.Chase()
        advance(c, 0.5)
        c.press()
        advance(c, 0.1)
        x0 = c._px
        c.aim(110)
        advance(c, 0.4)
        self.assertGreater(c._h, 20)
        self.assertGreater(c._px, x0 + 40)

    def test_c7_cornered_the_pointer_follows_the_mouse_freely(self):
        c = copy.deepcopy(self.never["c"])
        for x, y in ((200, 150), (30, 40), (260, 230)):
            c.aim(x, y)
            advance(c, 0.5)
            self.assertAlmostEqual(c._px, x, delta=0.5)
            self.assertAlmostEqual(c._py, y, delta=0.5)
            mx = min(g[2] for g in c.picture() if g[1] == "m")
            self.assertAlmostEqual(mx, x - 3, delta=1.0)        # the arrow's tip is at the mouse
        c.aim(999, -50)                             # clamped to the canvas
        advance(c, 0.5)
        self.assertTrue(0 <= c._px <= chase.SIZE - chase._PW and 0 <= c._py <= chase.SIZE - chase._PH)


class Course(Runs):
    def test_c2_a_typical_player_finishes_in_60_to_120_s(self):
        for run in (self.typical, play(jumper())):
            secs, c = (run["secs"], run["c"]) if isinstance(run, dict) else run[:2]
            self.assertTrue(c.cornered)
            self.assertTrue(60 <= secs <= 120, secs)

    def test_c2_a_player_who_never_jumps_finishes_under_130_s(self):
        self.assertTrue(self.never["c"].cornered)
        self.assertLess(self.never["secs"], 130)
        self.assertGreater(self.never["trips"], 20)

    def test_phases_run_a_b_c_then_cornered_near_their_lengths(self):
        seen, first = [], {}
        for f in self.typical["log"]:
            if not seen or seen[-1] != f["phase"]:
                seen.append(f["phase"])
                first[f["phase"]] = f["t"]
        self.assertEqual(seen, ["A", "B", "C", "cornered"])
        a, b = first["B"] - first["A"], first["C"] - first["B"]
        self.assertTrue(16 <= a <= 24 and 38 <= b <= 50, (a, b))

    def test_c3_after_a_collision_it_recovers_and_progress_keeps_rising(self):
        log = self.never["log"]
        p = [f["progress"] for f in log]
        self.assertTrue(all(b >= a for a, b in zip(p, p[1:])))
        for t0 in sorted({f["trip"] for f in log if f["trip"] > 0}):
            after = [f for f in log if t0 + 1.1 <= f["t"] <= t0 + 1.2 and f["trip"] == t0]
            if after and after[0]["progress"] < 0.97:    # back to run pace within a moment
                self.assertGreater(after[0]["v"], 0.85 * chase._PHASES[0][1])
            later = [f["progress"] for f in log if t0 <= f["t"] <= t0 + 0.6]
            self.assertGreater(later[-1], later[0])

    def test_a_collision_gives_no_a_little_more_lead(self):
        hit = chase.Chase()
        while hit._trip < 0:
            hit.update(1 / 60)
        clean = chase.Chase()
        bot = jumper()
        while clean.t < hit.t:
            if bot(clean):
                clean.press()
            clean.update(1 / 60)
        advance(hit, 1.6)
        advance(clean, 1.6)
        self.assertGreater(hit.no_rect()[0], clean.no_rect()[0] + 3)

    def test_c5_cornered_time_is_the_same_at_30_60_and_144_fps(self):
        for bot, tol in ((None, 1 / 30 + chase.STEP), (jumper, 0.25)):
            times = [play(bot() if bot else None, fps)[0] for fps in (30, 60, 144)]
            self.assertLess(max(times) - min(times), tol, times)

    def test_cornered_no_is_trapped_against_the_wall_and_the_scrolling_stops(self):
        c = copy.deepcopy(self.typical["c"])
        self.assertEqual((c.phase, c.progress), ("cornered", 1.0))
        x, y, w, h = c.no_rect()
        wall = min(g[2] for g in c.picture() if g[1] == "w")
        self.assertAlmostEqual(x + w, wall, delta=1.0)
        ground = [g[2] for g in c.picture() if g[1] == "g"]
        ys = []
        for _ in range(240):                        # 2 s: it hovers gently, it doesn't escape
            c.update(1 / 120)
            ys.append(c.no_rect()[1])
            self.assertAlmostEqual(c.no_rect()[0], x, delta=0.5)
        self.assertEqual([g[2] for g in c.picture() if g[1] == "g"], ground)
        self.assertTrue(1.0 < max(ys) - min(ys) <= chase._FLOAT_A / 2 + 0.5, (min(ys), max(ys)))


class NoButton(Runs):
    def test_c4_no_is_inside_the_canvas_every_frame(self):
        for run in (self.typical, self.never):
            for f in run["log"]:
                x, y, w, h = f["no"]
                self.assertTrue(0 <= x and x + w <= chase.SIZE and 0 <= y and y + h <= chase.SIZE, (f["t"], f["no"]))

    def test_c8_no_is_a_third_of_the_width_with_the_envelope_aspect(self):
        _, _, w, h = self.typical["log"][0]["no"]
        self.assertAlmostEqual(w / chase.SIZE, 1 / 3, delta=0.03)
        self.assertAlmostEqual(w / h, 40 * 0.6 / (11 * 1.1), delta=0.1)

    def test_c8_no_floats_smoothly(self):
        ys = [f["no"][1] for f in self.typical["log"] if f["phase"] == "A"]
        self.assertGreater(max(ys) - min(ys), 8)
        self.assertLess(max(abs(b - a) for a, b in zip(ys, ys[1:])), 1.5)      # px per 60 fps frame

    def test_c8_no_evades_it_pulls_ahead_and_pauses(self):
        log = [f for f in self.typical["log"] if f["phase"] == "B"]
        gaps = [f["no"][0] - (f["me"][0] + f["me"][2]) for f in log]
        self.assertGreater(max(gaps) - min(gaps), 20)                          # the distance changes
        dx = [abs(b["no"][0] - a["no"][0]) for a, b in zip(log, log[1:])]
        still = sum(1 for d in dx if d < 0.02) / len(dx)
        self.assertGreater(still, 0.1)                                          # it pauses ...
        self.assertLess(still, 0.9)                                             # ... and resumes

    def test_no_keeps_ahead_of_the_pointer_and_never_overlaps_obstacles(self):
        for run in (self.typical, self.never):
            for f in run["log"]:
                if f["phase"] == "cornered":
                    continue
                x, y, w, h = f["no"]
                self.assertGreater(x, f["me"][0] + f["me"][2])
                for ch, role, gx, gy in f["pic"]:
                    if role == "o":
                        self.assertFalse(x < gx + 8 and gx < x + w and y < gy + 16 and gy < y + h, (f["t"], ch))

    def test_no_is_visibly_closer_in_phase_c(self):
        xs = {"A": [], "C": []}
        for f in self.typical["log"]:
            if f["phase"] in xs and f["progress"] < 0.97:
                xs[f["phase"]].append(f["no"][0])
        self.assertLess(sum(xs["C"]) / len(xs["C"]), sum(xs["A"]) / len(xs["A"]) - 15)

    def test_no_is_not_in_the_picture(self):
        self.assertFalse(any(g[1] == "n" for f in self.typical["log"][::50] for g in f["pic"]))


class Pointer(Runs):
    def arrow(self, pic):
        return [(ch, x, y) for ch, role, x, y in pic if role == "m"]

    def test_c6_the_pointer_is_an_arrow_cursor(self):
        glyphs = chase._ARROW                                   # the art itself, before any tilt
        rows = {}
        for ch, x, y in glyphs:
            rows.setdefault(y, []).append((x, ch))
        ys = sorted(rows)
        left = [min(rows[y])[1] for y in ys]
        self.assertEqual(left[:6], ["|"] * 6)                  # a straight left edge from the tip down
        ends = [max(rows[y]) for y in ys[:6]]
        self.assertTrue(all(ch == "\\" for _, ch in ends))      # a diagonal right edge ...
        self.assertTrue(all(b[0] > a[0] for a, b in zip(ends, ends[1:])))      # ... widening downwards
        self.assertEqual(rows[ys[0]][0][0], min(x for _, x, _ in glyphs))      # the tip is the top-left
        for y in ys[6:]:                                         # below the head, ONE stem: no legs
            xs = sorted(x for x, _ in rows[y])
            self.assertTrue(all(b - a <= 5.0 for a, b in zip(xs, xs[1:])), xs)
            self.assertGreater(xs[0], min(x for _, x, _ in glyphs) + 5)

    def test_c6_no_glyph_hangs_below_the_collision_box(self):
        for run in (self.typical, self.never):
            for f in run["log"][::7]:
                arrow = [(ch, x, y) for ch, role, x, y in f["pic"] if role == "m"]
                if not arrow:
                    continue                                     # a stumble flash
                x0, x1, y0, y1 = ink(arrow)
                bx, by, bw, bh = f["me"]
                self.assertLessEqual(y1, by + bh + 0.01, f["t"])
                self.assertTrue(x0 < bx and bx + bw < x1 and y0 < by, f["t"])

    def test_c6_the_pointer_is_red_role_m_with_a_trail_r(self):
        pic = self.typical["log"][120]["pic"]                   # 2 s in, before any obstacle
        self.assertTrue({"m", "r"} <= {g[1] for g in pic})
        self.assertEqual(len([g for g in pic if g[1] == "m"]), len(chase._ARROW))

    def test_the_stumble_flashes_at_most_twice_and_scatters_glyphs(self):
        c = chase.Chase()
        while c._trip < 0:
            c.update(1 / 60)
        seen, bits = [], 0
        for _ in range(int(chase._STUMBLE * 144) + 10):
            c.update(1 / 144)
            pic = c.picture()
            seen.append(any(g[1] == "m" for g in pic))
            bits = max(bits, sum(g[1] == "x" for g in pic))
        self.assertLessEqual(sum(1 for a, b in zip(seen, seen[1:]) if a and not b), 2)
        self.assertTrue(seen[-1])
        self.assertGreaterEqual(bits, 5)


class Obstacles(unittest.TestCase):
    def setUp(self):
        self.groups, self.starts, self.end = chase._build(3)

    def test_c9_obstacles_are_block_shapes(self):
        for kind, (glyphs, boxes, (w, top)) in chase._ART.items():
            self.assertTrue({ch for ch, _, _ in glyphs} <= set("+-|#"), kind)
            if kind != "gap":
                x0, x1, y0, y1 = ink(glyphs)
                self.assertEqual((y1, x0), (0, 0), kind)           # standing on the ground, from its left edge
                self.assertEqual((x1, y0), (w - 1, top), kind)

    def test_c9_each_collision_box_is_inside_its_drawing(self):
        for kind, (glyphs, boxes, _) in chase._ART.items():
            if kind == "gap":
                continue
            x0, x1, y0, y1 = ink(glyphs)
            for lo, hi, top in boxes:                            # inside, and only a little smaller
                self.assertTrue(x0 < lo < hi < x1 and y0 < top < 0, (kind, lo, hi, top, x0, x1, y0))
            self.assertLessEqual(min(b[0] for b in boxes) - x0, 3, kind)
            self.assertLessEqual(x1 - max(b[1] for b in boxes), 3, kind)
            self.assertLessEqual(min(b[2] for b in boxes) - y0, 4, kind)

    def test_c9_jumping_clears_every_kind_with_margin(self):
        """Sweep the press time over a lone group of each kind at its slowest phase's speed, through the
        real physics: the presses that clear it span at least 0.2 s."""
        slowest = {}
        for _, _, p, kind, _ in self.groups:
            slowest.setdefault(kind, p)
        self.assertEqual(set(slowest), set(chase._KINDS) | set(chase._CLUSTERS))
        for kind, p in slowest.items():
            c = chase.Chase()
            c._starts = [-math.inf] * (p + 1)
            c._v = chase._PHASES[p][1]
            parts, w = chase._parts(kind)
            x = math.ceil((chase._FRONT + c._v * 2.0) / 8) * 8
            c._groups = [(x, x + w, p, kind, tuple((x + dx, k) for dx, k in parts))]
            c._x0s, c._end, c._out = [x], 1e9, 1e9
            advance(c, 1.0)
            ok = []
            for i in range(60):                                  # presses 1.0 .. 2.2 s in
                trial = copy.deepcopy(c)
                trial.press()
                advance(trial, 2.5)
                ok.append(trial._trip == -math.inf)
                advance(c, 0.02)
            run = best = 0
            for o in ok:
                run = run + 1 if o else 0
                best = max(best, run)
            self.assertGreaterEqual(best * 0.02, 0.2, (kind, best * 0.02))

    def test_gaps_between_groups_leave_a_landing_plus_a_reaction(self):
        for a, b in zip(self.groups, self.groups[1:]):
            v = chase._PHASES[b[2]][1]
            self.assertGreaterEqual(b[0] - a[1], v * (chase._JUMP_T + chase._REACT), (a, b))

    def test_the_course_has_every_kind_and_phase_a_is_gentle(self):
        kinds = {g[3] for g in self.groups}
        self.assertEqual(kinds, set(chase._KINDS) | set(chase._CLUSTERS))
        self.assertTrue({g[3] for g in self.groups if g[2] == 0} <= {"barrier", "block", "wall", "gap"})
        self.assertTrue(any(g[3] in chase._CLUSTERS for g in self.groups if g[2] == 1))

    def test_deterministic_per_seed(self):
        self.assertEqual(chase._build(3), (self.groups, self.starts, self.end))
        self.assertNotEqual(chase._build(3)[0], chase._build(4)[0])
        frames = []
        for _ in range(2):
            c, seq = chase.Chase(3), []
            for _ in range(600):
                c.update(1 / 60)
                seq.append((c.picture(), c.no_rect(), c.pointer_rect()))
            frames.append(seq)
        self.assertEqual(frames[0], frames[1])

    def test_a_gap_is_a_visible_missing_stretch_of_ground(self):
        c = chase.Chase()
        gx = next(x for g in c._groups for x, k in g[4] if k == "gap")
        while gx - c._cam > 200:
            c.update(chase.STEP)
        line = [g[2] for g in c.picture() if g[1] == "g" and g[3] == chase._GROUND - 14]
        sx = gx - c._cam
        self.assertFalse(any(sx - 6 < x < sx + chase._GAP_W for x in line))
        self.assertTrue(any(sx + chase._GAP_W <= x < sx + chase._GAP_W + 12 for x in line))


class Picture(Runs):
    def test_pure_ascii_and_known_roles(self):
        for run in (self.typical, self.never):
            for f in run["log"]:
                for ch, role, x, y in f["pic"]:
                    self.assertTrue(len(ch) == 1 and 32 < ord(ch) < 127, repr(ch))
                    self.assertIn(role, ROLES)

    def test_every_element_shows_up(self):
        roles = set()
        for run in (self.typical, self.never):
            for f in run["log"]:
                roles.update(g[1] for g in f["pic"])
        self.assertEqual(roles, ROLES)

    def test_the_hint_shows_once(self):
        shown = [any(g[1] == "t" for g in f["pic"]) for f in self.typical["log"]]
        first = shown.index(True)
        gone = shown.index(False, first)
        self.assertGreater(gone - first, 30)
        self.assertNotIn(True, shown[gone:])

    def test_c10_it_reads_as_a_runner(self):
        f = self.typical["log"][120]
        line = [g for g in f["pic"] if g[1] == "g"]
        self.assertGreater(min(g[3] for g in line), chase.SIZE * 0.7)              # ground low
        x, y, w, h = f["me"]
        self.assertTrue(x + w < chase.SIZE / 2 and y + h > chase.SIZE * 0.7)       # pointer lower left
        nx, ny, nw, nh = f["no"]
        self.assertTrue(nx > x + w and ny + nh < chase.SIZE * 0.7)                 # NO ahead, above
        entered = {}
        for f in self.typical["log"]:                                              # obstacles from the right
            for ch, role, gx, gy in f["pic"]:
                if role == "o":
                    entered.setdefault(round(gy), gx)
            if len(entered) > 3:
                break
        self.assertGreater(min(entered.values()), chase.SIZE - 12)

    def test_picture_interpolates_between_steps(self):
        c = chase.Chase()
        advance(c, 1.0)

        def gx():
            return min(g[2] for g in c.picture() if g[1] == "g")
        a = gx()
        c.update(chase.STEP / 2)
        b = gx()
        c.update(chase.STEP / 2)
        d = gx()
        self.assertTrue(a > b > d or a < b < d, (a, b, d))

    def test_update_and_picture_cost_well_under_a_millisecond(self):
        c = chase.Chase()
        advance(c, 40.0)                                 # mid B: the busiest stretch
        frames, t0 = 1500, time.perf_counter()
        for _ in range(frames):
            c.update(1 / 60)
            c.picture()
        ms = (time.perf_counter() - t0) / frames * 1000
        self.assertLess(ms, 1.0, f"{ms:.3f} ms per frame")


if __name__ == "__main__":
    unittest.main()
