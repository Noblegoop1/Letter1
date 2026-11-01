"""Sound (SPEC §21): the cue sheet's names, the generated music, cue timing, silence without a device, pause
and mute. Runs headless with SDL's dummy audio driver."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import numpy as np  # noqa: E402
import pygame  # noqa: E402

import sounds  # noqa: E402  (tools/sounds.py)
from letter import soundtrack  # noqa: E402
from letter.app import App  # noqa: E402
from letter.art import chase, music  # noqa: E402
from letter.engine import assets, audio  # noqa: E402

SCENE_SOUNDS = ("hover", "jump", "stumble", "heartbeat")   # played by the scenes, not the cue sheet


def cue_names():
    return {cue[2] for cues in soundtrack.CUES.values() for cue in cues if len(cue) > 2 and cue[2] != "*"}


def run_for(app, seconds):
    end = app.t + seconds
    while app.t < end - 1e-9:
        app.frame(1 / 60)


class Names(unittest.TestCase):
    """S1: every name has something to play."""

    def test_every_cue_and_level_names_a_sound_or_a_track(self):
        known = set(sounds.SOUNDS) | set(music.TRACKS)
        for name in cue_names() | set(SCENE_SOUNDS) | set(soundtrack.LEVEL):
            self.assertIn(name, known, name)
        for name in cue_names() | set(SCENE_SOUNDS):
            self.assertIn(name, soundtrack.LEVEL, name)

    def test_every_cue_is_in_a_story_phase_and_known_action(self):
        from letter.engine import story
        phases = set(story.YES_ROUTE) | set(story.NO_ROUTE) | {"intro", "letter"}
        for phase, cues in soundtrack.CUES.items():
            self.assertIn(phase, phases)
            for cue in cues:
                self.assertIn(cue[1], ("play", "loop", "fade", "stop"))
                self.assertGreaterEqual(cue[0], 0.0)

    def test_the_sound_files_exist(self):
        folder = assets.path("sounds")
        if not os.path.isdir(folder):
            self.skipTest("assets/sounds/ not made yet (tools/sounds.py)")
        for name in sounds.SOUNDS:
            self.assertTrue(os.path.isfile(os.path.join(folder, name + ".wav")), name)


class Music(unittest.TestCase):
    """S1: every track generates clean, and the loops repeat without a seam."""

    @classmethod
    def setUpClass(cls):
        cls.tracks = {name: (make(), loops) for name, (make, loops) in music.TRACKS.items()}

    def test_tracks_are_finite_stereo_and_below_full_scale(self):
        for name, (x, _) in self.tracks.items():
            self.assertEqual(x.ndim, 2, name)
            self.assertEqual(x.shape[1], 2, name)
            self.assertTrue(np.isfinite(x).all(), name)
            self.assertLess(np.abs(x).max(), 1.0, name)
            self.assertGreater(np.abs(x).max(), 0.05, name)   # not silent

    def test_loops_have_no_seam(self):
        for name, (x, loops) in self.tracks.items():
            if loops:
                step = np.abs(np.diff(x, axis=0)).max()
                self.assertLessEqual(np.abs(x[0] - x[-1]).max(), step, name)

    def test_cues_end_in_silence(self):
        for name, (x, loops) in self.tracks.items():
            if not loops:
                self.assertLess(np.abs(x[-50:]).max(), 0.01, name)

    def test_upsampling_keeps_level_and_the_loop_seam(self):
        t = np.arange(music.RATE) / music.RATE
        tone = np.stack([0.5 * np.sin(2 * np.pi * 441 * t)] * 2, axis=1).astype(np.float32)   # whole cycles
        y = audio.upsample(tone, loop=True)
        self.assertEqual(len(y), 2 * len(tone))
        self.assertAlmostEqual(np.abs(y).max(), 0.5, delta=0.01)
        self.assertLess(np.abs(y[0] - y[-1]).max(), np.abs(np.diff(y, axis=0)).max() * 1.01)

    def test_the_theme_and_its_minor_twin_follow_the_same_tune(self):
        self.assertEqual(music.midi("A4"), 69)
        self.assertEqual(music.midi("Bb4"), 70)
        self.assertEqual(music._minor_name("A4"), "Ab4")
        self.assertEqual(music._minor_name("E5"), "E5")   # the leading tone stays


class Cues(unittest.TestCase):
    """S2: each cue fires once, on its beat, in its phase."""

    def test_follow_fires_each_cue_once_as_time_passes(self):
        a = audio.Audio({"p": [(0.0, "play", "x"), (0.5, "play", "y")], "q": [(0.0, "stop")]}, {}, {}, music.RATE)
        a.played.clear()
        for e in (0.0, 0.2, 0.49, 0.51, 0.8):
            a.follow("p", e)
        self.assertEqual([p[2:] for p in a.played], [("play", "x"), ("play", "y")])
        self.assertEqual(a.played[1][1], 0.51)
        a.follow("q", 0.03)   # a new phase fires its cues from 0
        self.assertEqual(a.played[-1][2], "stop")

    def test_the_intro_starts_the_theme_and_writes_the_dedication(self):
        app = App(size=(1280, 800))
        run_for(app, 1.0)
        got = [(p[0], p[2], p[3]) for p in app.audio.played]
        self.assertEqual(got, [("intro", "loop", "theme"), ("intro", "play", "pencil_short")])
        self.assertAlmostEqual(app.audio.played[1][1], 0.4, delta=1 / 60 + 1e-3)   # logged to 1 ms

    def test_the_no_route_cues_land_in_order(self):
        app = App(size=(1280, 800), start="no-4")
        run_for(app, 8.4)
        self.assertEqual(app.phase, "chase")
        plays = [p for p in app.audio.played if p[0] == "no-4" and p[2] == "play"]
        self.assertEqual([p[3] for p in plays], ["press", "crack", "shatter", "poof", "pencil", "flap", "sheet",
                                                 "hop", "land", "riser"])
        self.assertEqual(sorted(p[1] for p in plays), [p[1] for p in plays])
        self.assertIn(("chase", "loop", "chase"), [(p[0], p[2], p[3]) for p in app.audio.played])

    def test_the_invitations_yes_plays_the_joy_and_nothing_from_the_no_route(self):
        app = App(size=(1280, 800), start="invite")
        run_for(app, 1.5)
        pos = app.scene().target("date-yes")
        for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            app.handle(pygame.event.Event(kind, pos=pos, button=1))
        run_for(app, 8.2)
        self.assertEqual(app.phase, "joy")
        names = [p[3] for p in app.audio.played]
        self.assertIn("joy", names)
        for no_sound in ("sad", "letgo", "chase", "glitch", "theme_minor"):
            self.assertNotIn(no_sound, names)

    def test_hovering_a_button_ticks_once(self):
        app = App(size=(1280, 800), start="letter")
        run_for(app, 0.1)
        pos = app.scene().target("yes")
        for _ in range(3):   # moving within the button doesn't tick again
            app.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
        self.assertEqual([p[3] for p in app.audio.played].count("hover"), 1)

    def test_the_chase_counts_jumps_for_its_sound(self):
        game = chase.Chase()
        game.press()
        game.update(0.1)
        self.assertEqual(game.jumps, 1)

    def test_the_heartbeat_grows_as_the_pointer_nears(self):
        far, mid, near = (soundtrack.heartbeat(d) for d in (1e3, 60.0, 0.0))
        self.assertAlmostEqual(far, 0.2, places=6)
        self.assertAlmostEqual(near, 1.0, places=6)
        self.assertTrue(far <= mid <= near)


class Silence(unittest.TestCase):
    """S3: no audio device, or no sound files: the app runs silently."""

    def test_without_an_audio_device(self):
        with mock.patch.object(pygame.mixer, "get_init", return_value=None), \
                mock.patch.object(pygame.mixer, "quit"), \
                mock.patch.object(pygame.mixer, "init", side_effect=pygame.error("no device")):
            a = audio.Audio(soundtrack.CUES, soundtrack.LEVEL, music.TRACKS, music.RATE)
        self.assertFalse(a.on)
        for e in (0.0, 0.5, 1.0):
            a.follow("intro", e)
            a.update(1 / 60)
        a.play("hover")
        a.pause(True)
        a.toggle_mute()
        self.assertEqual([p[3] for p in a.played], ["theme", "pencil_short", "hover"])

    def test_without_sound_files(self):
        real = assets.path
        nowhere = lambda *parts: real("no-such-folder") if parts == ("sounds",) else real(*parts)  # noqa: E731
        with mock.patch.dict(audio._effects, clear=True), mock.patch.object(assets, "path", side_effect=nowhere):
            app = App(size=(1280, 800), start="no-2")
            run_for(app, 0.5)
            self.assertIn("quake", app.audio.missing)


class Controls(unittest.TestCase):
    """S4: focus pauses the sound with the story; M mutes."""

    def test_losing_focus_pauses_and_m_mutes(self):
        app = App(size=(1280, 800), start="night")
        run_for(app, 0.5)
        app.handle(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        app.frame(1 / 60)
        self.assertTrue(app.audio.paused)
        app.handle(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        app.frame(1 / 60)
        self.assertFalse(app.audio.paused)
        for kind in (pygame.KEYDOWN, pygame.KEYUP):
            app.handle(pygame.event.Event(kind, key=pygame.K_m, mod=0, unicode="m"))
        self.assertTrue(app.audio.muted)
        run_for(app, 0.2)
        for entry in app.audio.loops.values():
            self.assertEqual(entry["channel"].get_volume(), 0.0)
        app.handle(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0, unicode="m"))
        self.assertFalse(app.audio.muted)


if __name__ == "__main__":
    unittest.main()
