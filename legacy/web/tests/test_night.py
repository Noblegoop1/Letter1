import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "site"))

import night  # noqa: E402

SIZES = ((40, 20), (150, 57), (62, 90))
CLASSES = set(" " + night.HAZE + night.FIBRE + night.LIT + night.WARM)


def grass(frame):
    """Cells showing a grass glyph."""
    chars, cls = frame
    return {(x, y) for y, (r, k) in enumerate(zip(chars, cls)) for x, (ch, c) in enumerate(zip(r, k))
            if ch != " " and c in night.LIT + night.WARM}


def fibres(frame):
    return {(x, y) for y, k in enumerate(frame[1]) for x, c in enumerate(k) if c == night.FIBRE}


def rank(c):
    return len(night.LIT) if c == night.WARM else night.LIT.index(c)


class Frames(unittest.TestCase):
    def test_full_grid_of_printable_ascii_for_several_sizes(self):
        for cols, rows in SIZES:
            for t, e, light in ((0.0, 0.0, None), (2.5, 0.5, None), (9.0, 1.0, None),
                                (9.0, 1.0, (cols // 2, rows - 4, 1.0))):
                chars, cls = night.ground(cols, rows, t, e, light)
                self.assertEqual(len(chars), rows)
                self.assertEqual(len(cls), rows)
                for r, k in zip(chars, cls):
                    self.assertEqual(len(r), cols)
                    self.assertEqual(len(k), cols)
                    self.assertTrue(all(32 <= ord(ch) < 127 for ch in r))
                    self.assertTrue(set(k) <= CLASSES, set(k) - CLASSES)

    def test_horizon_leaves_about_a_third_of_the_grid_to_grass(self):
        for rows in (8, 20, 57, 90, 200):
            top = night.horizon(rows)
            self.assertTrue(0 < top < rows)
            self.assertAlmostEqual((rows - top) / rows, night.BAND, delta=0.1)

    def test_grass_sways_over_time(self):
        a, b = night.ground(150, 57, 3.0, 1.0)[0], night.ground(150, 57, 5.0, 1.0)[0]
        self.assertNotEqual(a, b)


class Emergence(unittest.TestCase):
    def test_starts_as_fibres_only(self):
        cols, rows = 150, 57
        frame = night.ground(cols, rows, 1.0, 0.0)
        self.assertEqual(grass(frame), set())
        self.assertTrue(fibres(frame))
        self.assertTrue(all(y >= night.horizon(rows) for x, y in fibres(frame)))
        self.assertTrue(all(not r.strip() for r in frame[0][:night.horizon(rows)]))  # sky still black

    def test_grass_never_ungrows_and_fibres_never_return(self):
        for cols, rows in SIZES:
            prev_g, prev_f = set(), fibres(night.ground(cols, rows, 4.0, 0.0))
            for i in range(1, 21):
                frame = night.ground(cols, rows, 4.0, i / 20)
                g, f = grass(frame), fibres(frame)
                self.assertTrue(prev_g <= g, (cols, rows, i))
                self.assertTrue(f <= prev_f, (cols, rows, i))
                prev_g, prev_f = g, f

    def test_bottom_comes_in_first(self):
        cols, rows = 150, 57
        g = grass(night.ground(cols, rows, 4.0, 0.3))
        self.assertTrue(g)
        self.assertTrue(all(y > (night.horizon(rows) + rows) // 2 for x, y in g))

    def test_complete_at_one(self):
        for cols, rows in SIZES:
            frame = night.ground(cols, rows, 4.0, 1.0)
            self.assertEqual(fibres(frame), set())
            self.assertTrue(grass(frame))


class Wind(unittest.TestCase):
    def test_stays_in_range(self):
        for t in range(0, 600, 7):
            for x in range(0, 300, 5):
                self.assertLessEqual(abs(night.wind(x, t * 0.37)), 1.0)

    def test_distant_columns_differ_at_the_same_time(self):
        diffs = [abs(night.wind(10, t * 0.5) - night.wind(80, t * 0.5)) for t in range(120)]
        self.assertTrue(all(d > 1e-6 for d in diffs))
        self.assertGreater(sum(diffs) / len(diffs), 0.1)

    def test_changes_over_time_at_one_column(self):
        ws = [night.wind(40, t * 0.5) for t in range(120)]
        self.assertGreater(max(ws) - min(ws), 0.3)


class Light(unittest.TestCase):
    def test_spill_brightens_near_grass_and_leaves_far_cells_alone(self):
        cols, rows = 150, 57
        lx, ly = 75, rows - 8
        dark = night.ground(cols, rows, 6.0, 1.0)
        lit = night.ground(cols, rows, 6.0, 1.0, (lx, ly, 1.0))
        self.assertEqual(dark[0], lit[0])  # light changes colours only
        brighter = 0
        for x, y in grass(dark):
            a, b = dark[1][y][x], lit[1][y][x]
            near = abs(x - lx) <= 4 and abs(y - ly) <= 2
            far = abs(x - lx) > 25 or abs(y - ly) > 12
            self.assertGreaterEqual(rank(b), rank(a))
            if near:
                self.assertGreater(rank(b), rank(a), (x, y))
                brighter += 1
            if far:
                self.assertEqual(a, b, (x, y))
        self.assertGreater(brighter, 0)

    def test_weak_light_has_a_small_radius(self):
        cols, rows = 150, 57
        dark = night.ground(cols, rows, 6.0, 1.0)
        weak = night.ground(cols, rows, 6.0, 1.0, (75, rows - 8, 0.1))
        changed = [(x, y) for y in range(rows) for x in range(cols) if dark[1][y][x] != weak[1][y][x]]
        self.assertTrue(changed)
        self.assertTrue(all(abs(x - 75) <= 6 for x, y in changed))
        self.assertEqual(night.ground(cols, rows, 6.0, 1.0, (75, rows - 8, 0.0)), dark)


if __name__ == "__main__":
    unittest.main()
