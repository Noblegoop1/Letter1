import os
import sys
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.art import sky  # noqa: E402
from letter.engine import audio  # noqa: E402

S = sky.S
SKY = sky.Sky()   # one shared instance: building one takes ~0.1 s


def render(t=40.0, dark=1.0, moon=1.0, clouds=1.0, s=SKY):
    c = np.full((S, S, 3), np.nan, np.float32)
    s.render(c, t, dark, moon, clouds)
    return c


def disc(moon, inset=3):
    x, y, r = sky.Sky.moon_pos(moon)
    yy, xx = np.mgrid[:S, :S]
    return np.hypot(xx - x, yy - y) < r - inset


class ContractTests(unittest.TestCase):
    def test_overwrites_the_whole_canvas_in_place(self):
        for state in ((1.0, 0.0, 0.0), (0.5, 0.0, 0.0), (1.0, 0.4, 0.6), (1.0, 1.0, 1.0)):
            c = np.full((S, S, 3), np.nan, np.float32)
            self.assertIs(SKY.render(c, 12.0, *state), c)
            self.assertEqual((c.shape, c.dtype), ((S, S, 3), np.float32))
            self.assertTrue(np.isfinite(c).all(), state)
            self.assertGreaterEqual(c.min(), 0.0)

    def test_finite_over_time_and_inputs(self):
        for t in (0.0, 0.01, 7.3, 99.0, 1000.0, 86400.0):
            for moon, clouds in ((0.0, 1.0), (0.3, 0.2), (1.0, 1.0)):
                self.assertTrue(np.isfinite(render(t, 1.0, moon, clouds)).all())

    def test_dark_zero_is_black(self):
        self.assertEqual(render(dark=0.0).max(), 0.0)
        self.assertEqual(render(dark=0.0, moon=0.0, clouds=0.0).max(), 0.0)

    def test_base_column_is_the_old_night_gradient(self):
        y = np.linspace(0, 1, S, dtype=np.float32)[:, None]
        top, low = np.array((4, 5, 12), np.float32) / 255, np.array((16, 22, 44), np.float32) / 255
        col = SKY.base_column()
        self.assertEqual((col.shape, col.dtype), ((S, 3), np.float32))
        np.testing.assert_allclose(col, top + (low - top) * y ** 1.6, atol=1e-6)

    def test_edge_columns_stay_the_base_gradient(self):
        """The side bars continue base_column(): no seam even with the moon up and the sky full."""
        col = SKY.base_column()
        for t in (5.0, 40.0, 95.0, 230.0):
            c = render(t)
            for x in (0, S - 1):
                np.testing.assert_allclose(c[:, x], col, atol=1 / 255, err_msg=f"t={t} x={x}")


class MoonTests(unittest.TestCase):
    def test_no_moon_leaves_its_place_dark(self):
        c = render(moon=0.0, clouds=0.0)
        for m in (0.0, 1.0):
            self.assertLess((c[disc(m)].max(-1) > 0.2).mean(), 0.02)   # a star or two, no disc

    def test_full_moon_is_a_bright_disc_at_moon_pos(self):
        c = render(moon=1.0, clouds=0.0)
        self.assertGreater(c[disc(1.0)].mean(), 0.5)
        x, y, r = sky.Sky.moon_pos(1.0)
        self.assertLess(c[int(y), int(x + 3 * r)].max(), 0.2)   # a disc, not a smear

    def test_it_rises_and_fades_in(self):
        ys = [sky.Sky.moon_pos(m)[1] for m in np.linspace(0, 1, 11)]
        self.assertTrue(all(a > b for a, b in zip(ys, ys[1:])))
        self.assertGreater(ys[0] - ys[-1], 20)
        lum = [render(moon=m, clouds=0.0)[disc(m)].mean() for m in (0.25, 0.5, 1.0)]
        self.assertTrue(lum[0] < lum[1] < lum[2], lum)

    def test_clouds_veil_it_sometimes_but_it_shows_through(self):
        inner = disc(1.0)
        ratio = np.array([render(t)[inner].mean() / render(t, clouds=0.0)[inner].mean() for t in range(0, 400, 8)])
        self.assertGreater((ratio < 0.9).mean(), 0.1)    # partly veiled now and then
        self.assertGreater(np.median(ratio), 0.8)        # but mostly clear
        self.assertGreater(ratio.min(), 0.4)             # and never hidden


class CloudTests(unittest.TestCase):
    @staticmethod
    def cover(clouds, t):
        """Share of the upper sky (inside the edge fades) the clouds change visibly."""
        a, b = render(t, clouds=clouds)[:250, 100:540], render(t, clouds=0.0)[:250, 100:540]
        return (np.abs(a - b).max(-1) > 0.02).mean()

    def test_more_clouds_cover_more_sky_but_never_all_of_it(self):
        for t in (30.0, 120.0, 300.0):
            cov = [self.cover(k, t) for k in (0.0, 0.25, 0.5, 0.75, 1.0)]
            self.assertEqual(cov[0], 0.0)
            self.assertTrue(all(a < b for a, b in zip(cov, cov[1:])), cov)
            self.assertTrue(0.25 < cov[-1] < 0.75, cov)   # filled, not overcast: gaps remain

    def test_only_the_moon_and_its_rims_are_bright_enough_to_bloom(self):
        """The scene blooms 1/8 samples above 0.42; the clouds must stay dim elsewhere."""
        x, y, r = sky.Sky.moon_pos(1.0)
        for t in np.arange(0.0, 300.0, 11.0):
            c = render(t)
            hot = np.nonzero(((c[2::8, 2::8] + c[6::8, 6::8]) * 0.5).max(-1) > 0.42)
            far = np.hypot(hot[1] * 8 + 4 - x, hot[0] * 8 + 4 - y)
            self.assertTrue((far < r + 60).all(), f"t={t}")

    def test_drifts_and_twinkles_and_is_deterministic(self):
        a, b = render(50.0), render(50.5)
        self.assertGreater(np.abs(a - b).max(), 0.02)
        self.assertGreater(np.abs(render(50.0, clouds=0.0) - render(50.5, clouds=0.0)).max(), 0.02)   # stars
        np.testing.assert_array_equal(render(50.0, s=sky.Sky(seed=11)), a)
        self.assertFalse(np.allclose(render(50.0, s=sky.Sky(seed=12)), a))

    def test_frame_by_frame_matches_a_fresh_render(self):
        """A slice of the band is refreshed per frame; it never lags visibly behind a full redraw."""
        s, c = sky.Sky(), np.zeros((S, S, 3), np.float32)
        for n in range(120):
            k = min(1.0, n / 100)
            s.render(c, 10 + n / 60, 1.0, k, k)
        fresh = render(10 + 119 / 60, 1.0, 1.0, 1.0, s=sky.Sky())
        self.assertLess(np.abs(c - fresh).max(), 0.03)


class BudgetTests(unittest.TestCase):
    QUIET_COPY_MS = 0.2   # one full 640 x 640 x 3 canvas copy on this PC when it is otherwise idle

    @classmethod
    def setUpClass(cls):
        audio.wait_for_music()   # an earlier test's app may still be making music: time on a quiet machine

    def test_render_fits_the_frame_budget(self):
        """Sky <= 2.5 ms per frame on this PC (best of many short runs), steady and while ramping in.

        The sky is memory bound, so when other programs load the machine it slows about as much as a plain
        canvas copy does. A copy is timed between the runs; if it is slower than on an idle machine, the
        budget is scaled by the same factor (it stays 2.5 ms on an idle machine)."""
        start = time.perf_counter()
        s = sky.Sky()
        print(f"\n  sky init: {(time.perf_counter() - start) * 1000:.0f} ms", end="")
        c, ref = np.zeros((S, S, 3), np.float32), np.ones((S, S, 3), np.float32)
        for name, state in (("steady", lambda n: (1.0, 1.0)), ("ramp", lambda n: (n / 720, n / 720))):
            best = copy = float("inf")
            for run in range(12):
                start = time.perf_counter()
                for n in range(20):
                    np.copyto(c, ref)
                copy = min(copy, (time.perf_counter() - start) / 20 * 1000)
                start = time.perf_counter()
                for n in range(60):
                    s.render(c, run + n / 60, 1.0, *state(run * 60 + n))
                best = min(best, (time.perf_counter() - start) / 60 * 1000)
            budget = 2.5 * max(1.0, copy / self.QUIET_COPY_MS)
            print(f"\n  sky render ({name}): {best:.3f} ms per frame (budget {budget:.2f} ms; "
                  f"canvas copy {copy:.3f} ms)", end="")
            self.assertLess(best, budget)


if __name__ == "__main__":
    unittest.main()
