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

    def test_yes_route_runs_to_the_invitation_and_waits(self):
        seen = run([(3.0, "yes"), (30.0, "flower")], until=120)
        self.assertEqual(seen, ["intro", "letter", "yes-reveal", "night", "seed", "grown", "bloom", "bloomed",
                                "gather", "invite"])

    def test_the_fireflies_wander_for_the_configured_delay_first(self):
        from letter import config
        self.assertGreaterEqual(story.duration("bloomed"), config.WANDER / config.SPEED)

    def test_invitation_yes_ends_with_joy_and_exit(self):
        seen = run([(3.0, "yes"), (30.0, "flower"), (60.0, "date-yes")], until=120)
        self.assertEqual(seen[-4:], ["invite", "farewell", "joy", "exit"])

    def test_invitation_no_goes_straight_to_the_crying_face(self):
        seen = run([(3.0, "yes"), (30.0, "flower"), (60.0, "date-no")], until=120)
        self.assertEqual(seen[seen.index("invite"):], ["invite", "letgo", "face", "black"])

    def test_the_three_decisions_stay_separate(self):
        self.assertEqual(story.step("invite", 0.0, 5.0, "yes")[0], "invite")       # the envelope's events
        self.assertEqual(story.step("invite", 0.0, 5.0, "no")[0], "invite")
        self.assertEqual(story.step("invite", 0.0, 5.0, "catch")[0], "invite")     # the chase's catch
        for phase in ("letter", "no-3", "cornered", "bloomed", "gather"):          # date-* only in invite
            for event in ("date-yes", "date-no"):
                self.assertEqual(story.step(phase, 0.0, 50.0, event)[0], phase)

    def test_invitation_buttons_wait_for_their_fade_in(self):
        self.assertEqual(story.step("invite", 10.0, 10.5, "date-yes")[0], "invite")
        self.assertEqual(story.step("invite", 10.0, 10.01 + story.duration("invite"), "date-yes")[0], "farewell")

    def test_endings_lock_every_input(self):
        for phase in ("farewell", "joy", "letgo", "exit"):
            for event in story.EVENT_NAMES:
                self.assertEqual(story.step(phase, 0.0, 0.01, event)[0], phase)

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
