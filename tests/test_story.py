import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.engine import story  # noqa: E402


def run(events, t_step=0.05, until=200.0, phase="intro"):
    """Walk the machine: events is a list of (time, event); returns phases seen in order."""
    since, seen, t, queue = 0.0, [phase], 0.0, list(events)
    while t < until:
        t += t_step
        while queue and queue[0][0] <= t:
            phase, since = story.step(phase, since, t, queue.pop(0)[1])
        phase, since = story.step(phase, since, t)
        if phase != seen[-1]:
            seen.append(phase)
    return seen


class Story(unittest.TestCase):
    def test_intro_hands_off_to_the_letter(self):
        self.assertEqual(run([], until=5)[:2], ["intro", "letter"])

    def test_clicks_during_the_intro_are_ignored(self):
        self.assertEqual(story.step("intro", 0.0, 0.5, "yes"), ("intro", 0.0))

    def test_yes_route_runs_to_the_bloomed_garden(self):
        seen = run([(3.0, "yes"), (30.0, "flower")])
        self.assertEqual(seen, ["intro", "letter", "yes-reveal", "night", "seed", "grown", "bloom", "bloomed"])

    def test_flower_click_before_grown_does_nothing(self):
        seen = run([(3.0, "yes"), (6.0, "flower")], until=20)
        self.assertEqual(seen[-1], "grown")

    def test_double_yes_starts_the_reveal_once(self):
        phase, since = story.step("letter", 0.0, 3.0, "yes")
        self.assertEqual(story.step(phase, since, 3.05, "yes"), (phase, since))

    def test_no_route_walks_every_beat_in_order(self):
        seen = run([(3, "no"), (5, "no"), (7, "no"), (9, "no"), (25, "course-end"), (27, "catch")], until=60)
        self.assertEqual(seen, ["intro", "letter", "no-1", "no-2", "no-3", "no-4", "chase", "cornered",
                                "glitch", "face", "black"])

    def test_no_clicks_during_a_lock_are_dropped(self):
        phase, since = story.step("letter", 0.0, 3.0, "no")
        self.assertEqual(story.step(phase, since, 3.1, "no"), ("no-1", since))
        self.assertTrue(story.locked(phase, since, 3.1))
        self.assertFalse(story.locked(phase, since, 3.0 + story.duration("no-1")))

    def test_yes_still_wins_during_the_questions(self):
        for phase in ("no-1", "no-2", "no-3"):
            self.assertEqual(story.step(phase, 0.0, 10.0, "yes")[0], "yes-reveal")

    def test_after_the_shatter_the_no_route_is_committed(self):
        for phase in ("no-4", "chase", "cornered", "glitch", "face", "black"):
            self.assertEqual(story.step(phase, 0.0, 0.01, "yes")[0], phase)

    def test_catch_only_counts_when_cornered(self):
        self.assertEqual(story.step("chase", 0.0, 50.0, "catch")[0], "chase")
        self.assertEqual(story.step("cornered", 0.0, 1.0, "catch")[0], "glitch")

    def test_black_is_forever(self):
        self.assertEqual(story.step("black", 0.0, 1e6), ("black", 0.0))
        for event in story.EVENT_NAMES:
            self.assertEqual(story.step("black", 0.0, 9.0, event)[0], "black")

    def test_routes_are_labelled(self):
        self.assertEqual(story.route("bloom"), "yes")
        self.assertEqual(story.route("chase"), "no")
        self.assertIsNone(story.route("letter"))


if __name__ == "__main__":
    unittest.main()
