import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "site"))

import art  # noqa: E402
import reveal  # noqa: E402


def letters(frame):
    """Writing glyphs still visible (class 'w')."""
    chars, cls = frame
    return {(x, y) for y, row in enumerate(cls) for x, k in enumerate(row) if k == "w" and chars[y][x] != " "}


class Writing(unittest.TestCase):
    def test_untouched_writing_shows_every_letter(self):
        cells = {(x, y) for x, y, ch in art.writing() if ch != " "}
        self.assertEqual(letters(reveal.writing(0.0)), cells)

    def test_dissolve_is_monotonic_and_complete(self):
        before = letters(reveal.writing(0.0))
        for i in range(1, 41):
            now = letters(reveal.writing(i / 40))
            self.assertLessEqual(now, before)
            before = now
        self.assertEqual(before, set())

    def test_frame_matches_the_envelope_layers(self):
        chars, cls = reveal.writing(0.5)
        self.assertEqual((len(chars), len(chars[0])), (art.HEAD + art.ENV_H, art.ENV_W))
        self.assertTrue(all(len(r) == art.ENV_W for r in chars + cls))

    def test_particles_appear_mid_dissolve_and_stay_capped(self):
        for i in range(41):
            chars, cls = reveal.writing(i / 40)
            self.assertLessEqual(sum(row.count("m") for row in cls), reveal.MAX_PARTICLES)
        mid = reveal.writing(0.6)[1]
        self.assertGreater(sum(row.count("m") for row in mid), 0)
        end = reveal.writing(1.0)[1]
        self.assertEqual(sum(row.count("m") for row in end), 0)


class Sheet(unittest.TestCase):
    def test_sheet_is_rectangular_ascii_with_an_empty_black_inside(self):
        chars, cls = reveal.sheet()
        self.assertTrue(all(len(r) == reveal.SHEET_W for r in chars + cls))
        self.assertEqual(len(chars), reveal.SHEET_H)
        self.assertTrue(all(32 <= ord(c) < 127 for r in chars for c in r))
        x0, y0, x1, y1 = reveal.INSIDE
        for y in range(y0, y1):
            self.assertEqual(chars[y][x0:x1].strip(), "")
            self.assertEqual(set(cls[y][x0:x1]), {"K"})

    def test_sheet_is_opaque_everywhere(self):
        _, cls = reveal.sheet()
        self.assertNotIn(" ", "".join(cls))

    def test_sheet_fits_inside_the_envelope(self):
        self.assertLess(reveal.SHEET_W, art.ENV_W - 4)
        self.assertLess(reveal.SHEET_H, art.ENV_H)


class Timeline(unittest.TestCase):
    def test_cover_scale_covers_the_viewport_from_an_off_centre_box(self):
        for vw, vh in ((1280, 800), (375, 812), (900, 900), (1920, 1080)):
            for x0, y0 in ((vw * 0.4, vh * 0.2), (10, 10), (vw * 0.6, vh * 0.7)):
                box = (x0, y0, x0 + 120, y0 + 50)
                s = reveal.cover_scale(box, vw, vh)
                cx, cy = x0 + 60, y0 + 25  # scaling about the box centre
                self.assertLessEqual(cx - 60 * s, 0)
                self.assertGreaterEqual(cx + 60 * s, vw)
                self.assertLessEqual(cy - 25 * s, 0)
                self.assertGreaterEqual(cy + 25 * s, vh)

    def test_cover_scale_of_an_empty_box_is_no_zoom(self):
        self.assertEqual(reveal.cover_scale((10, 10, 10, 30), 800, 600), 1.0)

    def test_zoom_starts_after_the_sheet_is_out(self):
        self.assertLessEqual(reveal.PULL[1], reveal.ZOOM[0])
        self.assertLessEqual(reveal.ZOOM[1], 4.5)


if __name__ == "__main__":
    unittest.main()
