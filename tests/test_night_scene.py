"""Headless tests for the night scene's sway and pointer lean (SPEC §10.4, Y4)."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from letter.app import App  # noqa: E402
from letter.art import flower  # noqa: E402
from letter.engine.timeline import lean_target  # noqa: E402
from letter.scenes import night  # noqa: E402

SIX_DEGREES = math.radians(6)


class LeanTarget(unittest.TestCase):
    def test_peaks_at_cap_and_never_passes_it(self):
        r = 220.0
        peak = max(abs(lean_target(dx, dy, r, 1.0)) for dx in range(-400, 401, 2) for dy in range(-300, 301, 10))
        self.assertAlmostEqual(peak, 1.0, places=3)
        self.assertAlmostEqual(lean_target(r / math.sqrt(2), 0, r, 0.6), 0.6, places=6)
        self.assertGreater(lean_target(50, 0, r, 1), 0)    # toward the pointer's side
        self.assertLess(lean_target(-50, 0, r, 1), 0)
        self.assertLess(abs(lean_target(1000, 0, r, 1)), 1e-6)   # far away: no lean

    def test_the_cap_is_six_degrees_at_the_head(self):
        self.assertAlmostEqual(night.LEAN_CAP * flower.BEND_TIP, SIX_DEGREES, places=9)


class Resize(unittest.TestCase):
    def test_the_bud_is_clickable_at_every_window_size(self):
        for size in ((1920, 1080), (1366, 768), (640, 400), (1280, 800)):
            app = App(size=size, start="grown")
            app.frame(1 / 60)
            v = app.scene().view
            self.assertTrue(v.size[0] == size[0] or v.size[1] == size[1], size)   # square canvas, letterboxed
            pos = app.scene().target("flower")
            for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                app.handle(pygame.event.Event(kind, pos=pos, button=1))
            self.assertEqual(app.phase, "bloom", size)


class Sway(unittest.TestCase):
    def setUp(self):
        self.app = App(size=(1280, 800), start="bloomed")
        self.scene = self.app.scene()
        self.app.frame(1 / 60)

    def move(self, logical):
        pos = self.scene.view.to_window(*logical)
        self.app.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))

    def run_for(self, seconds, track=None):
        for _ in range(round(seconds * 60)):
            self.app.frame(1 / 60)
            if track is not None:
                track.append(self.scene.lean)

    def test_pointer_lean_is_capped_and_returns_to_rest(self):
        leans = []
        hx, hy = self.scene.flower.head(1, 1, 0)
        for dx in (-160, -110, -60, 60, 110, 160):   # sweep both sides, settling at each spot
            self.move((hx + dx, hy))
            self.run_for(1.5, leans)
        self.assertLessEqual(max(abs(v) for v in leans) * flower.BEND_TIP, SIX_DEGREES + 1e-9)
        self.assertGreater(max(leans) * flower.BEND_TIP, math.radians(4))   # big enough to see
        self.assertLess(min(leans), 0)
        self.app.handle(pygame.event.Event(pygame.WINDOWLEAVE))
        self.run_for(2.0)
        self.assertLess(abs(self.scene.lean), 0.01)

    def test_wind_keeps_the_flower_moving_without_a_pointer(self):
        bends = []
        for _ in range(4 * 60):
            self.app.frame(1 / 60)
            bends.append(self.scene.state[3])
        self.assertEqual(self.scene.lean, 0.0)
        self.assertGreater(max(bends) - min(bends), 0.05)
        self.assertLessEqual(max(abs(b) for b in bends), 1.0)


if __name__ == "__main__":
    unittest.main()
