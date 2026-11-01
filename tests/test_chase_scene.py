"""Headless scene tests for the chase and the ending (SPEC §12-§13: C1, E1, E2, E4)."""
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


def click(app, pos):
    for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
        app.handle(pygame.event.Event(kind, pos=pos, button=1))


def key(app, k):
    for kind in (pygame.KEYDOWN, pygame.KEYUP):
        app.handle(pygame.event.Event(kind, key=k, mod=0, unicode=" "))


def run(app, seconds):
    end = app.t + seconds
    while app.t < end:
        app.frame(1 / 60)


class Chase(unittest.TestCase):
    def test_e1_clicking_the_fleeing_no_does_nothing(self):
        app = App(size=(1280, 800), start="chase")
        run(app, 1.0)
        click(app, app.scene().target("no"))
        key(app, pygame.K_RETURN)
        self.assertEqual(app.phase, "chase")

    def test_c1_space_reaches_the_game_only_in_the_chase(self):
        app = App(size=(1280, 800), start="chase")
        run(app, 1.0)
        presses = []
        app.scene().game.press = lambda: presses.append(app.phase)
        key(app, pygame.K_SPACE)
        app._advance(("cornered", app.t))
        key(app, pygame.K_SPACE)
        self.assertEqual(presses, ["chase"])

    def test_the_course_end_corners_no(self):
        app = App(size=(1280, 800), start="chase")
        for _ in range(1000):   # one update plays at most 0.25 s: step the game to its end
            if app.scene().game.cornered:
                break
            app.scene().game.update(0.25)
        app.frame(1 / 60)
        self.assertEqual(app.phase, "cornered")


class Cornered(unittest.TestCase):
    def tremble(self, app, logical):
        app.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=app.scene().view.to_window(*logical),
                                      rel=(0, 0), buttons=(0, 0, 0)))
        peak = 0.0
        for _ in range(90):   # 1.5 s: the smoothed distance settles, then take the largest shake
            app.frame(1 / 60)
            peak = max(peak, math.hypot(*app.scene().shake))
        return peak

    def test_e2_the_tremble_grows_as_the_pointer_comes_near(self):
        app = App(size=(1280, 800), start="cornered")
        x, y, w, h = app.scene().game.no_rect()
        far = self.tremble(app, (20, 20))
        near = self.tremble(app, (x + w / 2, y + h / 2))
        self.assertGreater(near, 3 * far)

    def test_catching_no_starts_the_ending_and_then_nothing_responds(self):
        app = App(size=(1280, 800), start="cornered")
        run(app, 0.2)
        click(app, app.scene().target("no"))
        self.assertEqual(app.phase, "glitch")
        self.assertTrue(app.caught)          # the ending glitches the frame it was caught on
        run(app, 4.9 + 11.8 + 0.5)
        self.assertEqual(app.phase, "black")
        for k in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
            key(app, k)
        click(app, (640, 400))
        run(app, 1.0)
        self.assertEqual(app.phase, "black")  # E4: black is forever


if __name__ == "__main__":
    unittest.main()
