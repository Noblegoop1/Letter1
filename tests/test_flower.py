"""Tests for letter/art/flower.py (the pointillist sea holly)."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np  # noqa: E402

from letter.art import flower  # noqa: E402

BG = (0.01, 0.012, 0.03)


def blank():
    c = np.empty((640, 640, 3), np.float32)
    c[:] = BG
    return c


def frame(f, grow, bloom, glow=1.0, bend=0.0, t=1.0):
    c = blank()
    f.render(c, grow, bloom, glow, bend, t)
    return c


def drawn(c):
    return np.any(c != np.float32(BG), axis=2)


class FlowerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.f = flower.Flower()

    def test_contract_constants(self):
        self.assertEqual(flower.GROUND_Y, 500)
        self.assertEqual(flower.ROOT, (320, 500))

    def test_particle_budget(self):
        total = self.f.counts["total"]
        self.assertTrue(20000 <= total <= 30000, total)
        self.assertLess(flower.Flower(quality=0.5).counts["total"], 0.6 * total)

    def test_untouched_at_grow_zero(self):
        c = blank()
        self.f.render(c, 0.0, 0.0, 1.0, 0.5, 2.0)
        self.assertFalse(drawn(c).any())

    def test_offscreen_dots_are_dropped(self):
        c = blank()
        x = np.array([-9.0, 700.0, 320.0, 0.2], np.float32)
        y = np.array([300.0, 10.0, 320.0, 639.9], np.float32)
        col = np.ones((4, 3), np.float32)
        flower._splat(c, x, y, col, flower._STAMP[np.full(4, 1)])
        self.assertEqual(int(drawn(c).sum()), 5)                      # only the on-screen plus stamp

    def test_stem_starts_at_root(self):
        p = self.f._pose(1.0, 0.0, 0.7)
        self.assertAlmostEqual(float(p["x"][0]), flower.ROOT[0], places=3)
        self.assertAlmostEqual(float(p["y"][0]), flower.ROOT[1], places=3)

    def test_growing_never_removes_stem_dots(self):
        dots, counts = [], []
        for g in np.linspace(0.05, 1.0, 12):
            c = blank()
            stem = self.f._stem(self.f._pose(g, 0.0, 0.0), g)
            flower._splat(c, *stem)                                      # the stem alone
            dots.append(len(stem[0]))
            counts.append(int(drawn(c).sum()))
        self.assertEqual(dots, sorted(dots), dots)
        # pixels may dip slightly once the stem is full length: the tightening hook overlaps dots
        self.assertTrue(all(b >= 0.99 * a for a, b in zip(counts, counts[1:])), counts)
        self.assertGreater(counts[-1], 3 * counts[0])
        whole = [int(drawn(frame(self.f, g, 0.0, 0.25)).sum()) for g in (0.2, 0.5, 0.8, 1.0)]
        self.assertEqual(whole, sorted(whole), whole)

    def test_bud_droops_and_bloom_stands_upright(self):
        for bloom, drooping in ((0.0, True), (1.0, False)):
            p = self.f._pose(1.0, bloom, 0.0)
            top = float(p["y"][self.f._grid <= p["len"]].min())          # stem's highest point
            hy = self.f.head(1.0, bloom, 0.0)[1]
            if drooping:
                self.assertGreater(hy, top + 5)                           # screen y grows downward
            else:
                self.assertLess(hy, top - 5)

    def test_bloom_changes_the_frame(self):
        changed = np.any(frame(self.f, 1.0, 0.0, 0.25) != frame(self.f, 1.0, 1.0, 1.0), axis=2).sum()
        self.assertGreater(changed, 15000)

    def test_bend_moves_head_its_way(self):
        for bloom in (0.0, 1.0):
            x0 = self.f.head(1.0, bloom, 0.0)[0]
            self.assertGreaterEqual(self.f.head(1.0, bloom, 1.0)[0] - x0, 10)
            self.assertLessEqual(self.f.head(1.0, bloom, -1.0)[0] - x0, -10)

    def test_hit(self):
        for bloom in (0.0, 1.0):
            hx, hy = self.f.head(1.0, bloom, 0.3)
            self.assertTrue(self.f.hit(hx, hy, 1.0, bloom, 0.3))
            self.assertFalse(self.f.hit(40, 40, 1.0, bloom, 0.3))
            self.assertFalse(self.f.hit(hx, hy + 150, 1.0, bloom, 0.3))
        self.assertFalse(self.f.hit(*flower.ROOT, 0.0, 0.0, 0.0))

    def test_finite_and_deterministic(self):
        f2 = flower.Flower(quality=0.3)
        for g, b, gl, bend, t in ((0.3, 0, 0.2, -1, 0.5), (1, 0, 0.25, 0.4, 3), (1, 0.5, 0.6, -0.2, 7),
                                  (1, 1, 1, 1, 30), (1, 1, 0, 0, 1)):
            for ff in (self.f, f2):
                c = frame(ff, g, b, gl, bend, t)
                self.assertTrue(np.isfinite(c).all())
                self.assertTrue(np.array_equal(c, frame(ff, g, b, gl, bend, t)))
            self.assertTrue(all(np.isfinite(v) for v in self.f.head(g, b, bend)))

    # ---- sea holly ----
    def test_bracts_spread_outward_with_bloom(self):
        spread = []
        for bloom in (0.0, 0.5, 1.0):
            X, _, _, _, a, b, *_ = self.f._head_shape(0.8, bloom)       # same size: only the opening differs
            spread.append(float(np.abs(np.r_[X[:a], X[b:]]).max()))
        self.assertEqual(spread, sorted(spread), spread)
        self.assertGreater(spread[-1], 2.5 * spread[0], spread)

    def test_open_head_is_taller_than_wide(self):
        X, up, _, _, a, b, *_ = self.f._head_shape(1.0, 1.0)
        self.assertGreater(np.ptp(up[a:b]), 1.15 * np.ptp(X[a:b]))      # the cone, as drawn

    def test_head_dots_are_blue(self):
        for bloom, glow in ((0.0, 0.25), (1.0, 1.0)):
            c = frame(self.f, 1.0, bloom, glow)
            hx, hy = self.f.head(1.0, bloom, 0.0)
            box = c[int(hy) - 25:int(hy) + 25, int(hx) - 20:int(hx) + 20]
            r, g, b = box[drawn(box)].mean(axis=0)
            self.assertGreater(b, 1.5 * g, (bloom, r, g, b))
            self.assertGreater(b, 2.5 * r, (bloom, r, g, b))

    def test_stays_in_its_box_clear_of_the_moon(self):
        # the moon rises to (550, 82..118), radius 28 plus halo; the flower keeps to x 150-490, y >= 70
        for grow, bloom, glow in ((0.6, 0.0, 0.15), (1.0, 0.0, 0.25), (1.0, 0.4, 0.55), (1.0, 1.0, 1.0)):
            for bend in (-1.0, 1.0):
                for t in (0.0, 6.5, 13.0, 40.0):
                    ys, xs = np.nonzero(drawn(frame(self.f, grow, bloom, glow, bend, t)))
                    self.assertGreaterEqual(xs.min(), 150, (grow, bloom, bend, t))
                    self.assertLessEqual(xs.max(), 490, (grow, bloom, bend, t))
                    self.assertGreaterEqual(ys.min(), 70, (grow, bloom, bend, t))
        hx, hy = self.f.head(1.0, 1.0, 0.0)
        self.assertLess(abs(hx - 320), 25)
        self.assertLess(abs(hy - 230), 25)

    def test_render_time_budget(self):
        c = blank()
        for i in range(5):
            self.f.render(c, 1.0, 1.0, 1.0, 0.3, i / 60)
        runs = []
        for _ in range(5):                                               # best of 5: the machine may be busy
            total = 0.0
            for i in range(30):
                c[:] = BG
                t0 = time.perf_counter()
                self.f.render(c, 1.0, 1.0, 1.0, 0.4 * np.sin(i * 0.1), i / 60)
                total += time.perf_counter() - t0
            runs.append(total / 30 * 1000)
        ms = min(runs)
        print(f"\n  flower render, full bloom: {ms:.2f} ms average over 30 calls (best of 5)", file=sys.stderr)
        self.assertLessEqual(ms, 5.0)


if __name__ == "__main__":
    unittest.main()
