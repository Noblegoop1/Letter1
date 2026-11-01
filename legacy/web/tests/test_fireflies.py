import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "site"))

import fireflies  # noqa: E402

CENTRE = (500.0, 400.0)
RADIUS = 200.0
FPS = 60
FIRST = range(fireflies.COUNT)


def path(i, seconds, start=0.0):
    return [fireflies.position(i, start + n / FPS, CENTRE, RADIUS) for n in range(int(seconds * FPS) + 1)]


def dist(p):
    return math.hypot(p[0] - CENTRE[0], p[1] - CENTRE[1])


class Position(unittest.TestCase):
    def test_stays_inside_the_allowed_region(self):
        for i in FIRST:
            for x, y in path(i, 600):
                self.assertLessEqual(abs(x - CENTRE[0]), 1.7 * RADIUS + 1e-6)
                self.assertGreaterEqual(y, CENTRE[1] - 1.2 * RADIUS - 1e-6)  # up
                self.assertLessEqual(y, CENTRE[1] + 0.7 * RADIUS + 1e-6)     # down to grass level

    def test_no_jumps(self):
        cap = RADIUS * 1.0 / FPS  # one radius per second: calm, and well above the observed peak (~0.9)
        for i in FIRST:
            p = path(i, 300)
            for a, b in zip(p, p[1:]):
                self.assertLess(math.hypot(b[0] - a[0], b[1] - a[1]), cap)

    def test_paths_differ(self):
        paths = [path(i, 60)[::30] for i in FIRST]
        for i in FIRST:
            for j in range(i + 1, fireflies.COUNT):
                mean = sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(paths[i], paths[j])) / len(paths[i])
                self.assertGreater(mean, 0.2 * RADIUS, (i, j))

    def test_each_drifts_both_close_and_far(self):
        for i in FIRST:
            for minute in range(5):
                d = [dist(p) for p in path(i, 60, minute * 60.0)[::6]]
                self.assertLess(min(d), 0.5 * RADIUS, (i, minute))
                self.assertGreater(max(d), 1.0 * RADIUS, (i, minute))

    def test_scales_with_centre_and_radius(self):
        x0, y0 = fireflies.position(3, 12.3, (0.0, 0.0), 1.0)
        x1, y1 = fireflies.position(3, 12.3, (10.0, 20.0), 50.0)
        self.assertAlmostEqual(x1, 10.0 + 50.0 * x0)
        self.assertAlmostEqual(y1, 20.0 + 50.0 * y0)


class Style(unittest.TestCase):
    def test_values_in_range(self):
        for i in FIRST:
            glyph, period, delay, peak, depth = fireflies.style(i)
            self.assertIn(glyph, ("*", "."))
            self.assertTrue(1.6 <= period <= 3.6)
            self.assertTrue(0.0 <= delay <= period)
            self.assertTrue(0.6 <= peak <= 1.0)
            self.assertTrue(0.0 <= depth <= 1.0)

    def test_blinks_are_individual(self):
        def phase(i, t):
            _, period, delay, _, _ = fireflies.style(i)
            return ((t - delay) / period) % 1.0

        for i in FIRST:
            for j in range(i + 1, fireflies.COUNT):
                together = 0
                for n in range(600):  # 30 s
                    d = abs(phase(i, n * 0.05) - phase(j, n * 0.05))
                    together += min(d, 1.0 - d) < 0.1
                self.assertLess(together / 600, 0.5, (i, j))  # chance is ~20%; "in step" would be ~100%

    def test_distant_ones_are_dim_dots_and_both_kinds_exist(self):
        styles = [fireflies.style(i) for i in FIRST]
        self.assertEqual({s[0] for s in styles}, {"*", "."})
        for glyph, _, _, _, depth in styles:
            if glyph == ".":
                self.assertLess(depth, 0.4)

    def test_style_is_stable(self):
        self.assertEqual(fireflies.style(4), fireflies.style(4))


class Arrival(unittest.TestCase):
    def test_one_by_one_from_half_a_second(self):
        times = [fireflies.arrival(i) for i in FIRST]
        self.assertAlmostEqual(times[0], 0.5)
        self.assertAlmostEqual(times[1] - times[0], 0.7)
        self.assertEqual(times, sorted(set(times)))


if __name__ == "__main__":
    unittest.main()
