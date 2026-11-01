import os
import sys
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.art import fireflies  # noqa: E402

HEAD = (320.0, 300.0)
SIZE = fireflies.SIZE


def gust(x, t):
    """Stand-in for the meadow's wind(x, t): travelling gusts in [-1, 1]."""
    return np.sin(x / 110.0 - 0.9 * t) * (0.5 + 0.5 * np.sin(0.21 * t))


def fly(ff, seconds, dt, wind=gust, attract=HEAD):
    """Step ff for `seconds`; -> (steps + 1, count, 2) positions, the start included."""
    out = [ff.positions]
    for n in range(1, int(round(seconds / dt)) + 1):
        ff.update(dt, n * dt, wind, attract)
        out.append(ff.positions)
    return np.array(out)


def coverage(path, cells=16):
    """Share of a cells x cells grid over the night that any firefly visited."""
    c = np.clip((path.reshape(-1, 2) / SIZE * cells).astype(int), 0, cells - 1)
    return len(set(map(tuple, c))) / cells ** 2


class SteeringTests(unittest.TestCase):
    def test_positions_stay_inside_the_square_for_ten_minutes(self):
        for wind in (gust, lambda x, t: np.ones_like(x)):
            p = fly(fireflies.Fireflies(), 600, 1 / 30, wind)
            self.assertTrue(np.isfinite(p).all())
            self.assertGreaterEqual(p.min(), 0.0)
            self.assertLess(p.max(), SIZE)

    def test_no_teleport_at_any_frame_rate(self):
        for dt in (1 / 144, 1 / 60, 1 / 20):
            p = fly(fireflies.Fireflies(), 60, dt)
            speed = np.hypot(*np.diff(p, axis=0).transpose(2, 0, 1)) / dt
            self.assertLess(speed.max(), 70.0, f"dt={dt}")

    def test_frame_rate_independent(self):
        a = fly(fireflies.Fireflies(), 5, 1 / 30)
        b = fly(fireflies.Fireflies(), 5, 1 / 120)
        self.assertAlmostEqual(coverage(a), coverage(b), delta=0.05)
        travel = lambda p: np.hypot(*np.diff(p, axis=0).transpose(2, 0, 1)).sum(0).mean()  # noqa: E731
        self.assertAlmostEqual(travel(a) / travel(b), 1.0, delta=0.1)
        end_gap = np.hypot(*(a[-1] - b[-1]).T)
        self.assertLess(np.median(end_gap), 10.0)   # same waypoints, so paths stay close (not identical)

    def test_they_cover_all_four_quadrants_in_30_s(self):
        p = fly(fireflies.Fireflies(), 30, 1 / 60)
        quad = (p[..., 0] >= SIZE / 2).astype(int) + 2 * (p[..., 1] >= SIZE / 2)
        for q in range(4):
            visitors = (quad == q).any(axis=0).sum()
            self.assertGreaterEqual(visitors, 3, f"quadrant {q}")
        # And they travel, not just circle where they started: most range over 200+ px in a minute.
        p = fly(fireflies.Fireflies(), 60, 1 / 60)
        extent = np.hypot(*(p.max(axis=0) - p.min(axis=0)).T)
        self.assertGreater(np.median(extent), 200)

    def test_a_few_visit_the_flower_most_wander_elsewhere(self):
        p = fly(fireflies.Fireflies(), 60, 1 / 60)
        d = np.hypot(p[..., 0] - HEAD[0], p[..., 1] - HEAD[1])
        visitors = (d.min(axis=0) < 60).sum()
        self.assertGreaterEqual(visitors, 3)
        far_share = (d > 120).mean(axis=0)
        self.assertGreater((far_share > 0.5).mean(), 0.7)

    def test_deterministic_per_seed(self):
        a, b, c = (fly(fireflies.Fireflies(seed=s), 3, 1 / 60)[-1] for s in (7, 7, 8))
        np.testing.assert_array_equal(a, b)
        self.assertFalse(np.allclose(a, c))


class LookTests(unittest.TestCase):
    def test_pulses_are_never_in_unison(self):
        ts = np.arange(0, 20, 1 / 60)[:, None]
        for count in (20, 40, 80):
            r = np.corrcoef(fireflies.Fireflies(count).pulse(ts).T)
            np.fill_diagonal(r, 0)
            self.assertLess(r.max(), 0.9, f"count={count}")

    def test_pulse_periods_and_range(self):
        ff = fireflies.Fireflies()
        b = ff.pulse(np.arange(0, 20, 1 / 60)[:, None])
        self.assertTrue(((b > 0) & (b <= 1)).all())
        self.assertGreater(np.ptp(b, axis=0).min(), 0.2)   # every one visibly pulses

    def test_flashes_rise_fast_and_fade_slowly(self):
        ff = fireflies.Fireflies(80)
        dt = 1 / 240
        b = ff.pulse(np.arange(0, 12, dt)[:, None])
        a = int(4 / dt)
        single, double = ~ff._glow & (ff._echo == 0), ff._echo > 0
        self.assertTrue(single.any() and double.any() and ff._glow.any())   # all three rhythms
        for j in np.flatnonzero(single):
            k = a + int(np.argmax(b[a:a + int(4 / dt), j]))   # a flash with its whole rise and fall in view
            lo, hi = b[:, j].min(), b[k, j]
            rise = k - np.flatnonzero(b[:k, j] < lo + 0.1 * (hi - lo))[-1]
            fall = np.flatnonzero(b[k:, j] < lo + 0.5 * (hi - lo))[0]
            self.assertLess(rise, fall, f"firefly {j}")
        for j in np.flatnonzero(double):   # two separate blinks per cycle
            w = b[a:, j]
            on = w > w.min() + 0.3 * (w.max() - w.min())
            blinks = np.count_nonzero(on[1:] & ~on[:-1])
            cycles = 8.0 / ff._period[j]
            self.assertTrue(1.5 * cycles <= blinks <= 2 * cycles + 2.1, f"firefly {j}: {blinks} in {cycles:.1f}")

    def test_arrival_fades_them_in(self):
        ff = fireflies.Fireflies()
        fly(ff, 20, 1 / 30)   # spread out, so a neighbour's halo never lights a waiting one
        bg = np.full((SIZE, SIZE, 3), 0.01, np.float32)
        c = bg.copy()
        ff.render(c, 20.0, arrival=0.0)
        np.testing.assert_array_equal(c, bg)

        lit = lambda c: (c - bg)[ff.positions[:, 1].astype(int), ff.positions[:, 0].astype(int)].sum(-1) > 0  # noqa: E731
        c = bg.copy()
        ff.render(c, 20.0, arrival=1.0)
        self.assertTrue(lit(c).all())
        c = bg.copy()
        ff.render(c, 20.0, arrival=0.5)
        self.assertTrue(0.25 < lit(c).mean() < 0.75)

    def test_layers_add_up_to_the_whole(self):
        ff = fireflies.Fireflies()
        fly(ff, 2, 1 / 60)
        whole, far, near, bokeh = (np.zeros((SIZE, SIZE, 3), np.float32) for _ in range(4))
        ff.render(whole, 2.0)
        for c, layer in ((far, "far"), (near, "near"), (bokeh, "bokeh")):
            ff.render(c, 2.0, layer=layer)
            self.assertGreater(c.sum(), 0, layer)
        self.assertGreater(near.sum(), far.sum())   # the far band is the dimmest share
        np.testing.assert_allclose(far + near + bokeh, whole, atol=1e-5)
        with self.assertRaises(ValueError):
            ff.render(whole, 2.0, layer="front")

    def test_bokeh_are_a_few_big_soft_discs(self):
        for count in (20, 40, 80):
            ff = fireflies.Fireflies(count)
            r = ff._bk_r
            self.assertTrue(3 <= r.size <= 6, f"count={count}")
            self.assertTrue(((r >= 9) & (r <= 25)).all())
            c = np.zeros((SIZE, SIZE, 3), np.float32)
            ff.render(c, 20.0, layer="bokeh")
            self.assertLess(c.max(), 0.3)                          # low alpha: soft, never a hard spot
            lit = (c[..., 1] > 1e-3).sum()
            self.assertGreater(lit, 0.8 * np.pi * r.max() ** 2)    # big: at least the largest disc's area
            self.assertLess(lit, (np.pi * (r + 3) ** 2).sum())
        # they drift slowly, not jump
        a, b = ff._bokeh(20.0, 1.0)[0], ff._bokeh(21.0, 1.0)[0]
        self.assertLess(np.hypot(*(a - b).T).max(), 15.0)

    def test_lights_match_the_visible_fireflies(self):
        ff = fireflies.Fireflies()
        fly(ff, 20, 1 / 30)
        x, y, s = ff.lights(20.0, 0.0)
        self.assertEqual(x.size, 0)
        x, y, s = ff.lights(20.0, 1.0)
        np.testing.assert_array_equal(np.stack([x, y], -1), ff.positions)   # all are out at arrival 1
        self.assertTrue(((s > 0) & (s <= 1)).all())
        x, y, s = ff.lights(20.0, 0.5)
        self.assertTrue(0.25 < x.size / ff.count < 0.75)
        c = np.zeros((SIZE, SIZE, 3), np.float32)
        ff.render(c, 20.0, 0.5)
        self.assertTrue((c[y.astype(int), x.astype(int)].sum(-1) > 0).all())   # each light is a drawn one
        # strength follows the flashes
        trace = np.array([ff.lights(t, 1.0)[2] for t in np.arange(2, 10, 1 / 30)])
        self.assertGreater(np.ptp(trace, axis=0).min(), 0.05)

    def test_arrival_rises_from_the_grass(self):
        """They wait in the grass, then one by one fade in as they lift off; nobody pops in mid-air."""
        ff = fireflies.Fireflies()
        dt = 1 / 60
        first_y = np.full(ff.count, np.nan)
        first_t = np.full(ff.count, np.nan)
        first_s = np.zeros(ff.count)
        later_y = np.full(ff.count, np.nan)
        for n in range(1, int(13 / dt) + 1):
            t = n * dt
            ff.update(dt, t, gust, HEAD)
            x, y, s = ff.lights(t, float(np.clip((t - 0.3) / 6.0, 0.0, 1.0)))
            i = np.flatnonzero(np.isin(ff.positions[:, 0], x))   # which ones are lit now
            new = i[np.isnan(first_y[i])]
            first_y[new], first_t[new] = ff.positions[new, 1], t
            first_s[new] = s[np.isin(x, ff.positions[new, 0])]
            due = np.isnan(later_y) & (t >= first_t + 4.0)
            later_y[due] = ff.positions[due, 1]
            hidden = np.isnan(first_y)
            self.assertTrue((ff.positions[hidden, 1] >= 455).all(), f"t={t:.2f}")   # waiting in the grass
        self.assertFalse(np.isnan(first_y).any())
        self.assertTrue(((first_y >= 455) & (first_y <= 500)).all())   # each appears in the grass
        self.assertLess(first_s.max(), 0.3)                            # and fades in, no pop
        self.assertGreater(np.ptp(first_t), 3.0)                       # staggered over the arrival
        rise = first_y - later_y
        self.assertGreater((rise > 20).mean(), 0.8)                    # then lifts off into the night
        self.assertGreater(np.median(rise), 40)

    def test_render_only_adds_light(self):
        ff = fireflies.Fireflies(80)
        rng = np.random.default_rng(1)
        c = rng.random((SIZE, SIZE, 3), np.float32)
        for n in range(1, 241):
            ff.update(1 / 60, n / 60, gust, HEAD)
            before = c.copy()
            ff.render(c, n / 60, arrival=n / 240)
            self.assertTrue((c >= before).all())

    def test_cores_are_hot_enough_to_bloom_but_stay_restrained(self):
        ff = fireflies.Fireflies()
        peaks = []
        for n in range(1, 301):
            ff.update(1 / 60, n / 60, gust, HEAD)
            c = np.zeros((SIZE, SIZE, 3), np.float32)
            ff.render(c, n / 60)
            peaks.append(c.max())
        self.assertGreater(max(peaks), 1.0)
        self.assertLess(max(peaks), 3.0)


class BudgetTests(unittest.TestCase):
    def test_update_and_render_fit_the_frame_budget(self):
        """SPEC 15: fireflies (update, the three layers and lights) <= 2 ms per frame at 40 (and <= 4 ms
        at 80) on this PC."""
        for count, budget_ms in ((40, 2.0), (80, 4.0)):
            ff = fireflies.Fireflies(count)
            c = np.zeros((SIZE, SIZE, 3), np.float32)
            t = 0.0
            best = float("inf")
            for _ in range(4):   # best of a few runs, so a busy moment on the machine can't fail it
                start = time.perf_counter()
                for _ in range(200):
                    t += 1 / 60
                    ff.update(1 / 60, t, gust, HEAD)
                    for layer in ("far", "near", "bokeh"):   # as the scene draws them
                        ff.render(c, t, layer=layer)
                    ff.lights(t)
                best = min(best, (time.perf_counter() - start) / 200 * 1000)
            print(f"\n  fireflies x{count}: {best:.3f} ms per frame (budget {budget_ms} ms)", end="")
            self.assertLess(best, budget_ms)


if __name__ == "__main__":
    unittest.main()
