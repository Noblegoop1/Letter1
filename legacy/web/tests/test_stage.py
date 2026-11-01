import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "site"))

import stage  # noqa: E402


class Phases(unittest.TestCase):
    def test_yes_only_counts_on_the_letter(self):
        self.assertEqual(stage.step("letter", 0.0, 5.0, "yes"), ("reveal", 5.0))
        self.assertEqual(stage.step("reveal", 5.0, 5.1, "yes"), ("reveal", 5.0))
        self.assertEqual(stage.step("night", 9.0, 9.5, "yes"), ("night", 9.0))

    def test_flower_click_only_counts_when_grown(self):
        self.assertEqual(stage.step("seed", 0.0, 1.0, "flower"), ("seed", 0.0))
        self.assertEqual(stage.step("grown", 0.0, 1.0, "flower"), ("bloom", 1.0))
        self.assertEqual(stage.step("bloomed", 0.0, 1.0, "flower"), ("bloomed", 0.0))

    def test_timed_phase_hands_off_exactly_at_its_duration(self):
        d = stage.DURATIONS["reveal"]
        self.assertEqual(stage.step("reveal", 2.0, 2.0 + d - 0.01), ("reveal", 2.0))
        self.assertEqual(stage.step("reveal", 2.0, 2.0 + d), ("night", 2.0 + d))

    def test_a_long_gap_walks_through_several_timed_phases(self):
        far = 1000.0
        self.assertEqual(stage.step("reveal", 0.0, far)[0], "grown")
        self.assertEqual(stage.step("bloom", 0.0, far)[0], "bloomed")

    def test_waiting_phases_never_end_on_their_own(self):
        for phase in ("letter", "grown", "bloomed"):
            self.assertEqual(stage.step(phase, 0.0, 1e6), (phase, 0.0))

    def test_reduced_motion_shortens_timed_phases(self):
        self.assertEqual(stage.step("reveal", 0.0, stage.REDUCED, reduced=True)[0], "night")

    def test_progress_is_clamped(self):
        self.assertEqual(stage.progress("reveal", 10.0, 5.0), 0.0)
        self.assertEqual(stage.progress("reveal", 0.0, 100.0), 1.0)
        self.assertEqual(stage.progress("letter", 0.0, 3.0), 1.0)


class Timelines(unittest.TestCase):
    def test_phase_timelines_fit_inside_their_phases(self):
        self.assertLessEqual(stage.NIGHT_FADE, stage.DURATIONS["night"])
        self.assertLessEqual(stage.NIGHT_EMERGE[1], stage.DURATIONS["night"])
        self.assertLessEqual(stage.SEED_FALL[1], stage.SEED_GROW[0])
        self.assertLessEqual(stage.SEED_GROW[1], stage.DURATIONS["seed"])

    def test_span_is_clamped(self):
        self.assertEqual(stage.span(0.0, (1.0, 2.0)), 0.0)
        self.assertEqual(stage.span(1.5, (1.0, 2.0)), 0.5)
        self.assertEqual(stage.span(9.0, (1.0, 2.0)), 1.0)

    def test_lean_follows_the_pointer_side_and_stays_capped(self):
        self.assertGreater(stage.lean_target(50, 0, 200, 0.45), 0)
        self.assertLess(stage.lean_target(-50, 0, 200, 0.45), 0)
        for dx in range(-2000, 2001, 37):
            for dy in (-300, 0, 120):
                self.assertLessEqual(abs(stage.lean_target(dx, dy, 200, 0.45)), 0.45)
        self.assertLess(abs(stage.lean_target(2000, 0, 200, 0.45)), 1e-6)


class ClockAndHelpers(unittest.TestCase):
    def test_paused_time_does_not_count(self):
        c = stage.Clock()
        self.assertEqual(c.now(10.0), 10.0)
        c.pause(10.0)
        self.assertEqual(c.now(15.0), 10.0)
        c.resume(15.0)
        self.assertEqual(c.now(16.0), 11.0)

    def test_approach_moves_toward_target_without_overshoot(self):
        x = 0.0
        for _ in range(200):
            x = stage.approach(x, 1.0, 1 / 60, 0.35)
            self.assertLessEqual(x, 1.0)
        self.assertGreater(x, 0.99)

    def test_easing_ends(self):
        for f in (stage.ease, stage.ease_out, stage.ease_in):
            self.assertEqual(f(0), 0)
            self.assertEqual(f(1), 1)
            self.assertEqual(f(-3), 0)
            self.assertEqual(f(3), 1)
        self.assertEqual(stage.smoothstep(0.2, 0.4, 0.1), 0)
        self.assertEqual(stage.smoothstep(0.2, 0.4, 0.5), 1)

    def test_bayer_thresholds_cover_the_range_once_per_tile(self):
        values = sorted(stage.bayer(x, y) for y in range(4) for x in range(4))
        self.assertEqual(values, [(i + 0.5) / 16 for i in range(16)])

    def test_hash_is_stable_and_spread(self):
        self.assertEqual(stage.hash32(3, 4), stage.hash32(3, 4))
        self.assertGreater(len({stage.hash32(x, 7) % 16 for x in range(64)}), 12)


if __name__ == "__main__":
    unittest.main()
