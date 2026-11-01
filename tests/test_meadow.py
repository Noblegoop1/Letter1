"""Night meadow: wind field, soil, grass emergence, light and the per-frame budget (SPEC 10.2, 15)."""
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import numpy as np

from letter.art import meadow

NIGHT = np.array([7, 10, 20], np.float32) / 255.0
LIGHT = (320.0, 470.0, 1.0)


def blank():
    c = np.empty((meadow.SIZE, meadow.SIZE, 3), np.float32)
    c[:] = NIGHT
    return c


class WindTest(unittest.TestCase):
    def test_range_over_ten_minutes_and_the_whole_width(self):
        x = np.linspace(0, 640, 161)[None, :]
        t = np.arange(0, 600, 0.25)[:, None]
        w = meadow.wind(x, t)
        self.assertEqual(w.shape, (len(t), x.shape[1]))
        self.assertTrue(np.isfinite(w).all())
        self.assertLessEqual(np.abs(w).max(), 1.0)
        self.assertGreater(np.abs(w).max(), 0.4)              # it does blow

    def test_scalars_and_arrays_agree(self):
        xs = np.array([0.0, 120.0, 333.0, 640.0])
        arr = meadow.wind(xs, 12.5)
        self.assertEqual(arr.shape, (4,))
        for x, a in zip(xs, arr):
            self.assertAlmostEqual(meadow.wind(float(x), 12.5), float(a), places=6)

    def test_distant_points_differ_at_the_same_time(self):
        t = np.arange(0, 60, 0.5)
        d = np.abs(meadow.wind(40.0, t) - meadow.wind(420.0, t))
        self.assertGreater(d.mean(), 0.05)

    def test_varies_over_time_and_does_not_repeat_within_a_minute(self):
        t = np.arange(0, 120, 0.1)
        w = meadow.wind(200.0, t)
        self.assertGreater(w.std(), 0.05)
        window = w[:200]                                       # the first 20 s ...
        for lag in range(10, 600, 10):                         # ... never comes back within 60 s
            self.assertGreater(np.abs(w[lag:lag + 200] - window).max(), 0.05, lag)


class MeadowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = meadow.Meadow()

    def render(self, t=0.0, emerge=1.0, light=None, front=True):
        c = blank()
        self.m.render_back(c, t, emerge, light)
        if front:
            self.m.render_front(c, t, emerge, light)
        return c

    def test_surface_meets_the_root(self):
        self.assertAlmostEqual(float(meadow.surface(320.0)), meadow.GROUND_Y, places=6)

    def test_emerge_zero_is_soil_only(self):
        c = self.render(emerge=0.0)
        self.assertTrue((c[:meadow.SOIL_TOP] == NIGHT).all())   # nothing above the soil band
        self.assertFalse((c[meadow.SOIL_TOP:] == NIGHT).all())  # but the soil is there
        c1 = self.render(emerge=1.0)
        self.assertGreater(np.abs(c1[:meadow.SOIL_TOP] - NIGHT).max(), 0.02)

    def test_grass_coverage_grows_with_emerge(self):
        soil = self.render(emerge=0.0)
        counts = [int((np.abs(self.render(t=2.0, emerge=e) - soil).max(axis=2) > 1e-4).sum())
                  for e in np.linspace(0, 1, 11)]
        self.assertEqual(counts[0], 0)
        self.assertEqual(counts, sorted(counts), counts)
        self.assertGreater(counts[-1], 8000)

    def test_light_brightens_near_and_leaves_far_unchanged(self):
        dark = self.render(t=3.0)
        lit = self.render(t=3.0, light=LIGHT)
        near = (slice(470, 560), slice(250, 390))
        self.assertGreater(lit[near].sum(), dark[near].sum() * 1.15)
        self.assertTrue((lit[:, :120] == dark[:, :120]).all())
        self.assertTrue((lit[:, 520:] == dark[:, 520:]).all())
        faint = self.render(t=3.0, light=(320.0, 440.0, 0.25))
        self.assertGreater(faint[near].sum(), dark[near].sum())
        self.assertLess(faint[near].sum(), lit[near].sum())

    def test_soil_and_grass_fade_at_the_edges(self):
        c = np.zeros((meadow.SIZE, meadow.SIZE, 3), np.float32)
        self.m.render_back(c, 0.0, 1.0)
        band = c[505:600]
        self.assertLess(band[:, :8].mean(), 0.1 * band[:, 316:324].mean())
        self.assertLess(band[:, -8:].mean(), 0.1 * band[:, 316:324].mean())

    def test_front_blades_stay_near_the_stem(self):
        c = blank()
        self.m.render_front(c, 0.0, 1.0)
        ys, xs = np.nonzero(np.abs(c - NIGHT).max(axis=2) > 1e-4)
        self.assertGreater(len(xs), 50)
        self.assertTrue((np.abs(xs - 320) < 70).all() and (ys > 460).all())

    def test_everything_finite(self):
        for t, e, light in [(0.0, 0.0, None), (1e4, 0.37, (0.0, 0.0, 1.0)), (77.7, 1.0, (640.0, 640.0, 0.5)),
                            (5.0, 0.8, (-50.0, 900.0, 1.0)), (2.0, 1.0, (320.0, 300.0, 0.0))]:
            self.assertTrue(np.isfinite(self.render(t, e, light)).all(), (t, e, light))

    def test_frame_budget(self):
        """SPEC 15: grass <= 3 ms. Asserts 6 ms for headroom; the best of 3 rounds hides scheduler noise."""
        c = blank()
        rounds = []
        for r in range(3):
            ts = []
            for i in range(60):
                t = r * 20 + i / 60
                c[:] = NIGHT
                t0 = time.perf_counter()
                self.m.render_back(c, t, 1.0, LIGHT)
                self.m.render_front(c, t, 1.0, LIGHT)
                ts.append(time.perf_counter() - t0)
            rounds.append(np.mean(ts) * 1e3)
        print("\nmeadow back+front, emerge 1, full light: %.2f ms mean (rounds: %s)"
              % (min(rounds), ", ".join("%.2f" % r for r in rounds)), file=sys.stderr)
        self.assertLessEqual(min(rounds), 6.0)


if __name__ == "__main__":
    unittest.main()
