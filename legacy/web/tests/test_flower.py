import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "site"))

import flower  # noqa: E402

COLS, ROWS = flower.SIZE
STEM = "vw"
HEAD = "dergc"
HALO = "ab"
STEPS = (0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0)


def cells(cls, classes):
    return {(c, r) for r, row in enumerate(cls) for c, k in enumerate(row) if k in classes}


def mean_col(cls, classes):
    cs = [c for c, r in cells(cls, classes)]
    return sum(cs) / len(cs)


class Frames(unittest.TestCase):
    def test_frames_are_rectangular_ascii_with_matching_classes(self):
        for grow in STEPS:
            for bloom in STEPS:
                for bend in (-1.0, -0.4, 0.0, 0.7, 1.0):
                    for glow in (0.0, 0.5, 1.0):
                        chars, cls = flower.frame(grow, bloom, bend, glow)
                        self.assertEqual(len(chars), ROWS)
                        self.assertEqual(len(cls), ROWS)
                        for row, krow in zip(chars, cls):
                            self.assertEqual(len(row), COLS)
                            self.assertEqual(len(krow), COLS)
                            for g, k in zip(row, krow):
                                self.assertTrue(" " <= g <= "~", repr(g))
                                self.assertTrue(k == " " or k.isalpha() and ord(k) < 128, repr(k))
                                self.assertEqual(g == " ", k == " ")   # empty means empty in both

    def test_no_growth_is_an_empty_frame(self):
        chars, cls = flower.frame(0.0, 0.0, 0.0, 1.0)
        self.assertEqual(chars, [" " * COLS] * ROWS)
        self.assertEqual(cls, [" " * COLS] * ROWS)

    def test_growth_only_ever_adds_stem_cells(self):
        for bend in (-1.0, 0.0, 0.6):
            before = set()
            for i in range(101):
                stem = cells(flower.frame(i / 100, 0.0, bend, 0.3)[1], STEM)
                self.assertTrue(before <= stem, (bend, i / 100, before - stem))
                before = stem
        self.assertTrue(before)

    def test_the_stem_starts_at_base(self):
        c, r = flower.BASE
        self.assertTrue(0 <= c < COLS and 0 <= r < ROWS)
        for bloom in (0.0, 1.0):
            for bend in (-1.0, 0.0, 1.0):
                self.assertIn(flower.frame(1.0, bloom, bend, 0.0)[1][r][c], STEM)

    def test_grown_flower_droops_and_blooms_upright(self):
        bud = cells(flower.frame(1.0, 0.0, 0.0, 0.0)[1], HEAD)
        bloom = cells(flower.frame(1.0, 1.0, 0.0, 0.0)[1], HEAD)
        tip = min(r for c, r in cells(flower.frame(1.0, 0.0, 0.0, 0.0)[1], STEM))
        self.assertGreater(min(r for c, r in bud), tip)                      # the bud hangs below the crook
        self.assertLess(min(r for c, r in bloom), min(r for c, r in bud))    # the bloom lifts above it
        self.assertGreater(len(bloom), 2 * len(bud))

    def test_closed_and_open_differ(self):
        self.assertNotEqual(flower.frame(1.0, 0.0, 0.0, 0.5), flower.frame(1.0, 1.0, 0.0, 0.5))

    def test_bend_moves_the_head_toward_its_sign(self):
        for bloom in (0.0, 0.5, 1.0):
            left, mid, right = (mean_col(flower.frame(1.0, bloom, b, 0.0)[1], HEAD) for b in (-1.0, 0.0, 1.0))
            self.assertLess(left, mid - 1.5, bloom)
            self.assertGreater(right, mid + 1.5, bloom)

    def test_halo_follows_glow(self):
        for bloom in (0.0, 1.0):
            self.assertFalse(cells(flower.frame(1.0, bloom, 0.0, 0.0)[1], HALO))
            dim = cells(flower.frame(1.0, bloom, 0.0, 0.3)[1], HALO)
            bright = cells(flower.frame(1.0, bloom, 0.0, 1.0)[1], HALO)
            self.assertTrue(bright)
            self.assertLess(len(dim), len(bright))

    def test_heart_marks_the_open_flowers_centre(self):
        chars, cls = flower.frame(1.0, 1.0, 0.0, 1.0)
        x, y = flower.HEART
        self.assertEqual((chars[y][x], cls[y][x]), ("@", "c"))


if __name__ == "__main__":
    unittest.main()
