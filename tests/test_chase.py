import math
import os
import random
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.art import chase  # noqa: E402

ROLES = set("ghomnwxtr")


def jumper(jitter=0.0, seed=1):
    """A bot that presses where a player would: centred over the next obstacle group, give or take
    jitter seconds (a typical player's timing)."""
    rng = random.Random(seed)
    late = {}

    def bot(c):
        if c._jump is not None:
            return False
        centre = c._mx + sum(chase._BOX) / 2
        for gi in range(c._next, min(c._next + 2, len(c._groups))):
            x0, x1 = c._groups[gi][:2]
            if (x0 + x1) / 2 > centre:
                e = late.setdefault(gi, rng.uniform(-jitter, jitter))
                return (x0 + x1) / 2 - centre <= c._v * (chase._JUMP_T / 2 - e)
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


class Controls(unittest.TestCase):
    def test_c1_update_alone_never_leaves_the_ground(self):
        heights = []
        play(each=lambda c: heights.append(c._h), limit=135)
        self.assertEqual(max(heights), 0.0)

    def test_c1_press_jumps_with_a_fixed_arc(self):
        c = chase.Chase()
        advance(c, 0.5)
        c.press()
        peak = 0.0
        for _ in range(int(chase._JUMP_T * 120) + 2):
            c.update(chase.STEP)
            peak = max(peak, c._h)
        self.assertAlmostEqual(peak, chase._JUMP_H, delta=0.5)
        self.assertEqual(c._h, 0.0)

    def test_a_press_in_the_air_is_not_a_second_jump(self):
        c = chase.Chase()
        advance(c, 0.5)
        c.press()
        advance(c, 0.2)
        c.press()                                   # long before landing: the buffer expires
        advance(c, chase._JUMP_T - 0.2 + 0.05)
        self.assertEqual(c._h, 0.0)

    def test_jump_buffer_catches_an_early_press(self):
        c = chase.Chase()
        advance(c, 0.5)
        c.press()
        advance(c, chase._JUMP_T - 0.05)
        c.press()                                   # 50 ms before landing
        advance(c, 0.15)
        self.assertGreater(c._h, 0.0)

    def test_presses_do_nothing_once_cornered(self):
        _, c, _ = play()
        x = c._mx
        c.press()
        advance(c, 1.0)
        self.assertEqual((c._h, c._mx, c.phase), (0.0, x, "cornered"))


class Course(unittest.TestCase):
    def test_c2_typical_and_careful_players_finish_in_60_to_120_s(self):
        for bot in (jumper(), jumper(jitter=0.08)):
            secs, c, trips = play(bot)
            self.assertTrue(c.cornered)
            self.assertTrue(60 <= secs <= 120, secs)

    def test_c2_a_player_who_never_jumps_finishes_under_130_s(self):
        secs, c, trips = play()
        self.assertTrue(c.cornered)
        self.assertLess(secs, 130)
        self.assertGreater(trips, 20)

    def test_phases_run_a_then_b_then_c_then_cornered(self):
        seen = []
        secs, _, _ = play(jumper(), each=lambda c: seen.append(c.phase) if not seen or seen[-1] != c.phase else None)
        self.assertEqual(seen, ["A", "B", "C", "cornered"])

    def test_c3_after_a_collision_it_recovers_and_progress_keeps_rising(self):
        log = []
        play(each=lambda c: log.append((c.t, c.progress, c._v, c._trip)))
        p = [row[1] for row in log]
        self.assertTrue(all(b >= a for a, b in zip(p, p[1:])))
        trips = sorted({row[3] for row in log if row[3] > 0})
        self.assertGreater(len(trips), 20)
        for t0 in trips:
            after = [row for row in log if t0 + 0.9 <= row[0] <= t0 + 1.1 and row[3] == t0]
            if after:                               # recovered to run pace within a second
                self.assertGreater(after[0][2], 0.85 * chase._PHASES[0][1])
            later = [row[1] for row in log if t0 <= row[0] <= t0 + 0.7]
            self.assertGreater(later[-1], later[0])

    def test_a_collision_gives_no_a_little_more_lead(self):
        c = chase.Chase()
        while c._trip < 0:
            c.update(1 / 60)
        lead = c._lead
        advance(c, 1.0)
        self.assertGreater(c._lead, lead + 5)

    def test_c4_no_is_inside_the_canvas_every_frame(self):
        def check(c):
            n = [g for g in c.picture() if g[1] == "n"]
            self.assertGreaterEqual(len(n), 8)
            for _, _, x, y in n:
                self.assertTrue(0 <= x <= chase.SIZE - chase.CELL[0] and 0 <= y <= chase.SIZE - chase.CELL[1],
                                (c.t, x, y))
        for bot in (jumper(), None):
            play(bot, each=check)

    def test_c5_cornered_time_is_the_same_at_30_60_and_144_fps(self):
        for bot, tol in ((None, 1 / 30 + chase.STEP), (jumper, 0.25)):
            times = [play(bot() if bot else None, fps)[0] for fps in (30, 60, 144)]
            self.assertLess(max(times) - min(times), tol, times)

    def test_no_is_visibly_closer_in_phase_c(self):
        xs = {"A": [], "C": []}
        play(jumper(), each=lambda c: xs.get(c.phase, []).append(c.no_rect()[0]))
        self.assertLess(sum(xs["C"]) / len(xs["C"]), sum(xs["A"]) / len(xs["A"]) - 40)

    def test_cornered_no_backs_onto_the_wall_and_the_pointer_stops_short(self):
        _, c, _ = play(jumper())
        self.assertEqual(c.phase, "cornered")
        self.assertEqual(c.progress, 1.0)
        x, y, w, h = c.no_rect()
        wall = min(g[2] for g in c.picture() if g[1] == "w")
        self.assertEqual(x + w, wall)
        pointer = max(g[2] for g in c.picture() if g[1] == "m") + chase.CELL[0]
        self.assertTrue(16 <= x - pointer <= 80, x - pointer)
        advance(c, 2.0)
        self.assertEqual(c.no_rect(), (x, y, w, h))

    def test_no_rect_covers_the_no_glyphs(self):
        c = chase.Chase()
        for t in (1.0, 20.0, 50.0):
            advance(c, t - c.t)
            x, y, w, h = c.no_rect()
            for _, role, gx, gy in c.picture():
                if role == "n":
                    self.assertTrue(x <= gx < x + w and y <= gy < y + h, (gx, gy, x, y))


class Fairness(unittest.TestCase):
    def setUp(self):
        self.groups, self.starts, self.end = chase._build(3)

    def test_gaps_leave_a_landing_plus_a_reaction(self):
        for a, b in zip(self.groups, self.groups[1:]):
            v = chase._PHASES[b[2]][1]
            self.assertGreaterEqual(b[0] - a[1], v * (chase._JUMP_T + chase._REACT), (a, b))

    def test_every_group_is_cleared_by_one_jump_with_room_to_spare(self):
        for x0, x1, p, parts in self.groups:
            height = max(chase._KINDS[k][2] for _, k in parts)
            lo = min(x + chase._KINDS[k][1][0] for x, k in parts)
            hi = max(x + chase._KINDS[k][1][1] for x, k in parts)
            air = chase._JUMP_T * math.sqrt(1 - height / chase._JUMP_H)     # time above the obstacle
            span = hi - lo + chase._BOX[1] - chase._BOX[0]
            self.assertGreater(air - span / chase._PHASES[p][1], 0.15, parts)

    def test_course_has_every_kind_and_groups(self):
        kinds = {k for g in self.groups for _, k in g[3]}
        self.assertEqual(kinds, set(chase._KINDS))
        self.assertTrue(any(len(g[3]) > 1 for g in self.groups))
        self.assertTrue(all(len(g[3]) == 1 for g in self.groups if g[2] == 0))     # A: single obstacles

    def test_deterministic_per_seed(self):
        self.assertEqual(chase._build(3), (self.groups, self.starts, self.end))
        self.assertNotEqual(chase._build(3)[0], chase._build(4)[0])
        frames = []
        for _ in range(2):
            c, seq = chase.Chase(3), []
            for _ in range(600):
                c.update(1 / 60)
                seq.append(c.picture())
            frames.append(seq)
        self.assertEqual(frames[0], frames[1])


class Picture(unittest.TestCase):
    def test_pure_ascii_and_known_roles(self):
        def check(c):
            for ch, role, x, y in c.picture((1.5, -2.0)):
                self.assertTrue(len(ch) == 1 and 32 < ord(ch) < 127, repr(ch))
                self.assertIn(role, ROLES)
        play(each=check)

    def test_every_element_shows_up(self):
        roles = set()
        play(each=lambda c: roles.update(g[1] for g in c.picture()))
        self.assertEqual(roles, ROLES)

    def test_hint_shows_once(self):
        shown = []
        play(jumper(), each=lambda c: shown.append(any(g[1] == "t" for g in c.picture())))
        first = shown.index(True)
        gone = shown.index(False, first)
        self.assertGreater(gone - first, 30)
        self.assertNotIn(True, shown[gone:])

    def test_the_stumble_flashes_at_most_twice(self):
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
        self.assertGreaterEqual(bits, 5)                # the glyph scatter

    def test_picture_interpolates_between_steps(self):
        c = chase.Chase()
        advance(c, 1.0)

        def nx():
            return min(g[2] for g in c.picture() if g[1] == "g")
        a = nx()
        c.update(chase.STEP / 2)
        b = nx()
        c.update(chase.STEP / 2)
        d = nx()
        self.assertTrue(a > b > d or a < b < d, (a, b, d))

    def test_shake_moves_only_the_cornered_no(self):
        c = chase.Chase()
        advance(c, 5.0)
        self.assertEqual(c.picture((3.0, 3.0)), c.picture())
        _, c, _ = play()
        still, shaken = c.picture(), c.picture((3.0, -2.0))
        for g, s in zip(still, shaken):
            moved = (s[2] - g[2], s[3] - g[3])
            self.assertEqual(moved, (3.0, -2.0) if g[1] == "n" else (0.0, 0.0))

    def test_update_and_picture_cost_well_under_a_millisecond(self):
        c = chase.Chase()
        frames, t0 = 1500, time.perf_counter()
        for _ in range(frames):
            c.update(1 / 60)
            c.picture()
        ms = (time.perf_counter() - t0) / frames * 1000
        self.assertLess(ms, 1.0, f"{ms:.3f} ms per frame")


if __name__ == "__main__":
    unittest.main()
