import os
import sys
import unittest

import numpy as np
import pygame

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from letter.art import banner, envelope as env  # noqa: E402

QUESTIONS = ("Will you open?", "Are You Sure?", "Is This What You Really Want?", "If you really feel that way, prove it.")


def ascii_ok(rows):
    return all(32 <= ord(c) < 127 for r in rows for c in r)


class Envelope(unittest.TestCase):
    def test_every_flap_depth_gives_same_size_ascii_layers(self):
        for d in range(-env.CY, env.CY + 1):
            for rows, roles in env.envelope(d).values():
                self.assertEqual(len(rows), env.ROWS)
                self.assertTrue(all(len(r) == env.ENV_W for r in rows + roles))
                self.assertTrue(ascii_ok(rows))

    def test_closed_envelope_has_the_seal_on_the_fold_crossing(self):
        _, roles = env.envelope(env.CY)["front"]
        self.assertEqual(roles[env.TIP][env.CX], "h")

    def test_closed_front_is_opaque_below_the_top_edge(self):
        _, roles = env.envelope(env.CY)["front"]
        for y in range(env.TOP + 1, env.BOT + 1):
            self.assertNotIn(" ", roles[y], "row %d" % y)

    def test_open_envelope_shows_the_pocket_and_folds_the_flap_up_behind(self):
        layers = env.envelope(-env.CY)
        self.assertEqual(layers["front"][1][env.TOP + 3][env.CX], " ")
        self.assertTrue(layers["back"][0][0].strip())
        self.assertNotIn("h", "".join(layers["front"][1]) + "".join(layers["back"][1]))

    def test_head_rows_are_empty_while_closed(self):
        for rows, _ in env.envelope(env.CY).values():
            self.assertEqual("".join(rows[:env.HEAD]).strip(), "")

    def test_lit_from_above(self):
        fg, bg = env.colours(*env.envelope(env.CY)["front"])
        col = bg[env.TOP + 4:env.TIP + 10, 3, :3].astype(int).sum(1)  # inside the left side flap, below the edge darkening
        self.assertGreater(col[:5].mean(), col[-5:].mean())
        self.assertTrue((np.diff(col) <= 2).all())                     # never brightens going down

    def test_top_flap_catches_more_light_than_the_side_flaps(self):
        _, bg = env.colours(*env.envelope(env.CY)["front"])
        y = env.TOP + 3
        self.assertGreater(bg[y, env.CX, :3].sum(), bg[y + 1, 2, :3].sum())

    def test_flap_depth_follows_angle(self):
        self.assertEqual((env.flap_depth(0), env.flap_depth(90), env.flap_depth(180)), (env.CY, 0, -env.CY))


class Banner(unittest.TestCase):
    BOX = (1180, 192)

    @classmethod
    def setUpClass(cls):
        pygame.init()   # the banner sets the question in a bundled font
        cls.art = {q: banner.banner(q, *cls.BOX) for q in QUESTIONS}

    def test_every_question_renders_as_rectangular_ascii_inside_its_box(self):
        for q, art in self.art.items():
            rows = art["rows"]
            self.assertTrue(all(len(r) == len(rows[0]) for r in rows))
            self.assertTrue(ascii_ok(rows))
            for key in ("kind", "light", "band"):
                self.assertEqual(art[key].shape, (len(rows), len(rows[0])))
            self.assertLessEqual(len(rows[0]) * art["cell"][0], self.BOX[0], q)
            self.assertLessEqual(len(rows) * art["cell"][1], self.BOX[1] + art["cell"][1], q)

    def test_long_questions_wrap_onto_two_lines(self):
        self.assertEqual(banner.lines(QUESTIONS[0]), [QUESTIONS[0]])
        self.assertEqual(banner.lines(QUESTIONS[2]), [QUESTIONS[2]])   # one line still sets it larger
        self.assertEqual(len(banner.lines(QUESTIONS[3])), 2)

    def test_many_different_marks_not_one_repeated_glyph(self):
        art = self.art[QUESTIONS[0]]
        face = {c for r, k in zip(art["rows"], art["kind"]) for c, kk in zip(r, k) if kk == 1}
        self.assertGreaterEqual(len(face), 12)
        self.assertTrue({"@", "%", "#"} <= face and ({"/", "\\"} & face))

    def test_lit_from_the_top_left_with_a_side_down_right(self):
        art = self.art[QUESTIONS[0]]
        kind, light = art["kind"], art["light"]
        ys, xs = np.nonzero(kind == 1)
        mid = (ys.min() + ys.max()) / 2
        self.assertGreater(light[ys[ys < mid], xs[ys < mid]].mean(), light[ys[ys > mid], xs[ys > mid]].mean())
        sy, sx = np.nonzero(kind == 2)
        self.assertGreater(len(sy), 50)
        self.assertGreater(sy.mean(), ys.mean())   # the extrusion hangs below and to the right
        self.assertGreater(sx.mean(), xs.mean() - 2)

    def test_a_vine_runs_underneath(self):
        art = self.art[QUESTIONS[0]]
        self.assertIn("<3", art["rows"][-1])
        self.assertTrue((art["kind"][-1][np.array(list(art["rows"][-1])) != " "] == 3).all())


if __name__ == "__main__":
    unittest.main()
