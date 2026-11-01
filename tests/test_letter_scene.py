"""Headless scene tests for the letter (SPEC §9: L1, L3, L5, L6, L7)."""
import math
import os
import pathlib
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from letter import config  # noqa: E402
from letter.app import App  # noqa: E402
from letter.engine.timeline import drift, quake  # noqa: E402
from letter.scenes import letter as letter_scene  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


class CalmMotion(unittest.TestCase):
    def test_animations_off_calms_the_float_wave_and_sway(self):
        """A11: with Windows animations off (forced here by LETTER_CALM=1) the ambient motion is calmer."""
        import subprocess
        probe = ("from letter import config; from letter.engine.timeline import drift; "
                 "print(config.CALM, config.MOTION)")
        env = dict(os.environ, LETTER_CALM="1")
        out = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, env=env, capture_output=True, text=True)
        calm, motion = out.stdout.split()
        self.assertEqual(calm, "True")
        self.assertLess(float(motion), 0.5)
        self.assertEqual(config.MOTION, float(motion) if config.CALM else 1.0)


class Resize(unittest.TestCase):
    def test_every_window_size_letterboxes_and_keeps_the_buttons_clickable(self):
        app = App(size=(1280, 800))
        app.run_script([], until=2.6)
        for size in ((1920, 1080), (1366, 768), (640, 400), (1280, 800)):
            app.screen = pygame.display.set_mode(size, pygame.RESIZABLE)
            app.resize(size)
            app.frame(1 / 60)
            scene, v = app.scene(), app.scene().view
            self.assertTrue(v.size[0] == size[0] or v.size[1] == size[1], size)   # fills one side, centred
            for side in (0, 1):   # centred (an odd leftover pixel goes to one side)
                self.assertLessEqual(abs(v.offset[side] * 2 + v.size[side] - size[side]), 1, size)
            for name in scene.buttons:
                self.assertEqual(scene._button_at(scene.target(name)), name, size)
        pygame.display.set_mode((1280, 800))


class LetterScene(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = App(size=(1280, 800))
        cls.app.run_script([], until=2.6)
        cls.scene = cls.app.scene()

    def test_story_reaches_the_letter(self):
        self.assertEqual(self.app.phase, "letter")

    def test_hitboxes_stay_fixed_while_hovered(self):
        before = {n: self.scene.hitbox(n) for n in self.scene.buttons}
        pos = self.scene.target("yes")
        self.app.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
        for _ in range(20):
            self.app.frame(1 / 60)
            self.assertEqual({n: self.scene.hitbox(n) for n in self.scene.buttons}, before)
        self.assertTrue(self.scene.buttons["yes"].hovered)

    def test_buttons_keep_their_colours(self):
        self.assertEqual(self.scene.buttons["yes"].colour, config.YES)
        self.assertEqual(self.scene.buttons["no"].colour, config.NO)
        self.assertEqual(config.YES, (255, 134, 173))
        self.assertEqual(config.NO, (180, 176, 214))

    def test_clicking_yes_starts_the_reveal(self):
        app = App(size=(1280, 800))
        failures = app.run_script([(2.5, "click", "yes"), (2.6, "expect", "yes-reveal")])
        self.assertEqual(failures, [])


class Dedication(unittest.TestCase):
    def test_to_esther_is_the_dedication(self):
        self.assertEqual(letter_scene.DEDICATION[0], "To Esther")

    def test_old_intro_text_is_gone_from_the_app(self):
        for path in (ROOT / "letter").rglob("*.py"):
            self.assertNotIn("RAHH", path.read_text(encoding="utf-8").upper(), path)

    def test_float_never_visibly_repeats_within_a_minute(self):
        samples = [drift(i / 10, (7.3, 11.9, 17.3)) for i in range(1200)]
        for lag in range(50, 600):  # 5 s .. 60 s
            diff = sum(abs(a - b) for a, b in zip(samples, samples[lag:])) / (len(samples) - lag)
            self.assertGreater(diff, 0.08, "looks periodic at a %.1f s lag" % (lag / 10))


if __name__ == "__main__":
    unittest.main()


class NoIntro(unittest.TestCase):
    """SPEC §11 steps 1-3 (N1-N3): each NO click's effect, in order."""

    def click(self, app, name):
        pos = app.scene().target(name)
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            app.handle(pygame.event.Event(kind, pos=pos, button=1))

    def run_to(self, app, t):
        while app.t < t:
            app.frame(1 / 60)

    def test_three_nos_ask_shake_and_swap(self):
        app = App(size=(1280, 800))
        app.run_script([], until=2.6)
        scene = app.scene()
        colours = {n: b.colour for n, b in scene.buttons.items()}
        self.click(app, "no")
        self.assertEqual((app.phase, scene.question), ("no-1", "Are You Sure?"))
        self.click(app, "no")                                   # locked while the question crossfades
        self.assertEqual(app.phase, "no-1")
        self.run_to(app, app.t + 0.7)
        self.click(app, "no")
        self.assertEqual((app.phase, scene.question), ("no-2", "Is This What You Really Want?"))
        self.run_to(app, app.t + 1.0)
        self.click(app, "no")
        self.assertEqual((app.phase, scene.question), ("no-3", letter_scene.ASK))
        self.assertEqual({n: b.slot for n, b in scene.buttons.items()}, {"yes": "right", "no": "left"})
        self.run_to(app, app.t + 1.0)
        for name, b in scene.buttons.items():                   # identity, colour and hitbox travel together
            self.assertEqual(b.colour, colours[name])
            self.assertEqual(scene._swap_offset(b, app.t), (0.0, 0.0))
            self.assertEqual(scene._button_at(scene.target(name)), name)
        self.assertLess(scene.target("no")[0], scene.target("yes")[0])

    def test_yes_still_wins_mid_route(self):
        app = App(size=(1280, 800))
        app.run_script([], until=2.6)
        self.click(app, "no")
        self.run_to(app, app.t + 0.7)
        self.click(app, "yes")
        self.assertEqual(app.phase, "yes-reveal")

    def test_the_earthquake_peaks_then_settles_exactly(self):
        dur, peak = letter_scene.QUAKE
        offsets = [quake(i / 1000, dur, peak) for i in range(int(dur * 1000))]
        self.assertTrue(10 <= max(math.hypot(*o) for o in offsets) <= 14)
        self.assertEqual(quake(dur, dur, peak), (0.0, 0.0))
        self.assertEqual(quake(0.0, dur, peak), (0.0, 0.0))     # starts from rest: no jump
        self.assertLess(math.hypot(*offsets[-1]), 0.01)


class NoShatterAndEscape(unittest.TestCase):
    """SPEC §11 no-4 (N4-N8): shatter, message, auto-open, NO hops onto the sheet; input locked."""

    def test_the_message_ends_fully_written(self):
        from letter.scenes import no_route
        end = no_route.NO4["message"][1] / config.SPEED
        self.assertTrue(all(a == 0 for a in no_route.ink(0.0)))
        self.assertTrue(all(a == 1 for a in no_route.ink(end)))
        mid = no_route.ink(end - 0.7)
        self.assertEqual(mid, sorted(mid, reverse=True))          # written left to right
        self.assertTrue(0 < sum(mid) < len(mid))

    def test_the_no_button_hops_onto_the_sheet_and_stays_recognisable(self):
        from letter.scenes import no_route
        start, target = (300.0, 700.0), (700.0, 300.0)
        self.assertEqual(no_route.hop(0.0, start, target, 80)[:2], start)
        x, y, tumble, scale = no_route.hop(1.0, start, target, 80)
        self.assertAlmostEqual(x, target[0])
        self.assertAlmostEqual(y, target[1])
        self.assertAlmostEqual(tumble, 0.0)
        self.assertGreaterEqual(scale, 0.2)
        mx, my, *_ = no_route.hop(0.5, start, target, 80)
        self.assertLess(my, (start[1] + target[1]) / 2)            # it arcs up on the way

    def test_no4_plays_to_the_chase_with_input_locked(self):
        app = App(size=(1280, 800), start="no-3")
        scene = app.scene()
        scene.enter("no-3", 0.0)
        while app.t < 1.0:
            app.frame(1 / 60)
        app.emit("no")
        self.assertEqual(app.phase, "no-4")
        for name in ("yes", "no"):                                  # nothing can be clicked from here on
            app.emit(name)
            self.assertEqual(app.phase, "no-4")
        start = app.t
        while app.t - start < 6.4:
            app.frame(1 / 60)
        from letter.scenes import no_route
        e = app.t - app.since
        self.assertEqual(no_route.beat(e, "open"), 1.0)             # the envelope opened on its own
        self.assertEqual(scene._no4_envelope(e)[1], letter_scene.SHEET_RISE)   # and the sheet is all the way up
