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


def gathered(dt=1 / 60, settle=True, seed=7):
    """A swarm that has wandered 13 s and then gathered (for GATHER s, if settle) into the message.
    -> (ff, targets, t at the start of the gathering, t now)."""
    from letter.art import invitation
    targets = invitation.cells()
    ff = fireflies.Fireflies(seed=seed)
    fly(ff, 13.0, dt)
    t0 = round(13.0 / dt) * dt
    ff.gather(targets, t0, GATHER)
    t = t0
    if settle:
        for n in range(1, int(round((GATHER + 0.2) / dt)) + 1):
            t = t0 + n * dt
            ff.update(dt, t, gust, HEAD)
    return ff, targets, t0, t


GATHER = 7.0
SPEED_CAP = 360.0   # px/s: the gathering and the scatter are brisker than wandering, never a jump


class InvitationTests(unittest.TestCase):
    def test_gathering_is_staggered_smooth_and_settles_at_any_frame_rate(self):
        for dt in (1 / 30, 1 / 60, 1 / 144):
            ff, targets, t0, _ = gathered(dt, settle=False)
            was = ff.positions
            prev, prev_vis = ff._m_pos.copy(), ff._m_vis.copy()
            share = []
            for n in range(1, int(round(GATHER / dt)) + 1):
                t = t0 + n * dt
                ff.update(dt, t, gust, HEAD)
                step = np.hypot(*(ff._m_pos - prev).T)
                seen = (ff._m_vis > 0) | (prev_vis > 0)
                self.assertLess(step[seen].max(initial=0), SPEED_CAP * dt, f"dt={dt} t={t - t0:.2f}")   # no teleport
                wander = np.hypot(*(ff.positions - was).T)   # wanderers hand over without a jump
                self.assertLess(wander.max(), SPEED_CAP * dt, f"dt={dt} t={t - t0:.2f}")
                done = ff._m_set & (t >= ff._m_s + ff._m_F)
                if done.any():   # no snapping: they glide the last of the way
                    late = done & (t - dt < ff._m_s + ff._m_F)
                    self.assertLess(step[late].max(initial=0), 1.0, f"dt={dt}")
                prev, prev_vis, was = ff._m_pos.copy(), ff._m_vis.copy(), ff.positions
                share.append(ff.formed())
            share = np.array(share)
            # staggered: the message fills over seconds, not at one moment
            self.assertGreater(np.ptp(ff._m_s), 0.3 * GATHER, f"dt={dt}")
            third = len(share) // 3
            self.assertLess(share[third], 0.1)
            self.assertTrue(0.05 < share[2 * third] < 0.95, f"dt={dt}: {share[2 * third]:.2f}")
            self.assertEqual(share[-1], 1.0, f"dt={dt}")
            err = np.hypot(*(ff._m_pos - targets).T)
            self.assertLess(err.max(), 0.5, f"dt={dt}")   # on its place, hovering a fraction of a pixel

    def test_one_firefly_per_target_and_the_wanderers_join(self):
        ff, targets, _, _ = gathered()
        self.assertEqual(ff._m_n, len(targets))
        np.testing.assert_array_equal(ff._m_P[3], targets)
        self.assertEqual(len(np.unique(targets, axis=0)), len(targets))
        own = ff._m_src[ff._m_src >= 0]
        self.assertEqual(len(own), (ff._band > 0).sum())        # mid and near wanderers take places
        self.assertEqual(len(np.unique(own)), len(own))
        np.testing.assert_allclose(ff.positions[own], np.clip(targets[ff._m_src >= 0], 24, SIZE - 25), atol=0.5)
        np.testing.assert_allclose(ff._keep[own], 0.0, atol=1e-6)   # their light is now the message dot's
        self.assertTrue((ff._keep[ff._band == 0] == 1).all())       # the far band keeps wandering

    def test_joiners_start_outside_the_message_and_fade_in(self):
        from letter.art import invitation
        x0, y0, w, h = invitation.BOX
        ff, targets, t0, _ = gathered(settle=False)
        join = ff._m_src < 0
        self.assertGreater(join.sum(), 0.9 * len(targets))
        p0 = ff._m_P[0, join]
        grass, edge = p0[:, 1] >= 455, (p0[:, 0] < 0) | (p0[:, 0] >= SIZE)
        self.assertTrue((grass | edge).all())
        self.assertTrue(0.3 < grass.mean() < 0.8)
        first = np.full((len(targets), 2), np.nan)
        first_b = np.zeros(len(targets))
        for n in range(1, int(GATHER * 60) + 1):
            t = t0 + n / 60
            ff.update(1 / 60, t, gust, HEAD)
            b = ff._message_bright(t)
            new = join & (b > 0) & np.isnan(first[:, 0])
            first[new], first_b[new] = ff._m_pos[new], b[new]
        self.assertFalse(np.isnan(first[join]).any())
        f = first[join]
        inside = (f[:, 0] > x0 - 20) & (f[:, 0] < x0 + w + 20) & (f[:, 1] > y0 - 20) & (f[:, 1] < y0 + h + 20)
        self.assertFalse(inside.any())                    # they appear in the grass or at the edges
        self.assertLess(first_b[join].max(), 0.1)          # and fade in, no pop
        self.assertGreater(np.ptp(ff._m_s[join]), 3.0)     # one after another

    def test_the_formed_message_reads_and_glows_softly(self):
        from letter.art import invitation
        x0, y0, w, h = invitation.BOX
        ff, targets, _, t = gathered()
        c = np.zeros((SIZE, SIZE, 3), np.float32)
        ff.render(c, t, layer="near")
        lum = c.sum(-1)
        on = lum[np.round(targets[:, 1]).astype(int), np.round(targets[:, 0]).astype(int)]
        self.assertGreater(np.quantile(on, 0.05), 0.5)     # every letter is lit
        self.assertLess(c.max(), 1.6)                      # pointillist, never a hot neon sign
        x, y, s = ff.lights(t)
        msg = (x >= x0) & (x < x0 + w) & (y >= y0) & (y < y0 + h)
        self.assertGreater(msg.sum(), 50)
        self.assertLess(s[msg].max(), 0.35)                # a modest halo per 8 px cell
        # they keep pulsing once formed, never in unison
        trace = np.array([ff._message_bright(t + k / 30)[:200] for k in range(120)])
        self.assertGreater(np.ptp(trace, axis=0).min(), 0.05)
        r = np.corrcoef(trace.T[:40])
        np.fill_diagonal(r, 0)
        self.assertLess(r.max(), 0.99)

    def test_scatter_flies_outward_and_fades(self):
        for gentle, reach in ((False, (120, 600)), (True, (8, 90))):
            ff, targets, _, t = gathered()
            own = ff._m_src[ff._m_src >= 0]
            ff.scatter(t, 3.0, gentle=gentle)
            prev = ff._m_pos.copy()
            peak = 0.0
            for n in range(1, 3 * 60 + 2):
                ff.update(1 / 60, t + n / 60, gust, HEAD)
                step = np.hypot(*(ff._m_pos - prev).T)
                self.assertLess(step.max(), SPEED_CAP / 60, f"gentle={gentle}")
                prev = ff._m_pos.copy()
                peak = max(peak, float(ff._message_bright(t + n / 60).max()))
                if n == 30:
                    self.assertLess(ff.formed(), 1.0)
            away = np.hypot(*(ff._m_pos - targets).T)
            self.assertTrue(reach[0] < np.median(away) < reach[1], f"gentle={gentle}: {np.median(away):.0f}")
            self.assertEqual(ff._message_bright(t + 3.1).max(), 0.0)   # all faded
            self.assertEqual(ff.formed(), 0.0)
            np.testing.assert_allclose(ff._keep[own], 0.0, atol=1e-6)   # the wanderers that joined left too
            if not gentle:
                self.assertGreater(peak, 1.0)                  # they glow up as they break away
            c = np.zeros((SIZE, SIZE, 3), np.float32)
            ff.render(c, t + 3.1, layer="near")
            self.assertTrue(np.isfinite(c).all())

    def test_gather_is_deterministic_per_seed(self):
        a, b = gathered(seed=7)[0], gathered(seed=7)[0]
        np.testing.assert_array_equal(a._m_s, b._m_s)
        np.testing.assert_array_equal(a._m_pos, b._m_pos)
        c = gathered(seed=8)[0]
        self.assertFalse(np.allclose(a._m_s, c._m_s))


class BudgetTests(unittest.TestCase):
    def test_message_fits_the_frame_budget(self):
        """SPEC 15: the message fireflies (~1,200) while gathering and formed: update, the three layers
        and lights for the whole swarm <= 3 ms per frame on this PC (best of runs)."""
        import copy
        ff, _, t0, _ = gathered(settle=False)
        for n in range(1, 121):   # into the thick of the gathering
            ff.update(1 / 60, t0 + n / 60, gust, HEAD)
        c = np.zeros((SIZE, SIZE, 3), np.float32)
        for label, start, skip in (("gathering", t0 + 2.0, 0.0), ("formed", t0 + 2.0, GATHER)):
            snap = copy.deepcopy(ff)
            t = start
            for n in range(int(skip * 60)):
                t += 1 / 60
                snap.update(1 / 60, t, gust, HEAD)
            best = float("inf")
            for _ in range(3):
                run, tt = copy.deepcopy(snap), t
                begin = time.perf_counter()
                for _ in range(120):
                    tt += 1 / 60
                    run.update(1 / 60, tt, gust, HEAD)
                    for layer in ("far", "near", "bokeh"):
                        run.render(c, tt, layer=layer)
                    run.lights(tt)
                best = min(best, (time.perf_counter() - begin) / 120 * 1000)
            print(f"\n  fireflies + message x{ff._m_n} {label}: {best:.3f} ms per frame (budget 3 ms)", end="")
            self.assertLess(best, 3.0)

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
