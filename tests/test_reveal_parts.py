import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.art import dissolve, envelope as env, sheet  # noqa: E402

TEXT = "To Esther"


class Dissolve(unittest.TestCase):
    def visible(self, p):
        return {i for i, g in dissolve.letters(TEXT, p) if g is not None}

    def test_intact_at_start_and_gone_at_the_end(self):
        self.assertEqual([g for _, g in dissolve.letters(TEXT, 0.0)], [c if c != " " else None for c in TEXT])
        self.assertEqual(self.visible(1.0), set())
        self.assertEqual(dissolve.specks(TEXT, 1.0), [])

    def test_crumbling_is_monotonic(self):
        before = self.visible(0.0)
        for k in range(1, 41):
            now = self.visible(k / 40)
            self.assertLessEqual(now, before)
            before = now

    def test_letters_do_not_all_go_at_once(self):
        counts = {len(self.visible(k / 40)) for k in range(41)}
        self.assertGreater(len(counts), 4)

    def test_specks_rise_and_fade(self):
        mid = dissolve.specks(TEXT, 0.6)
        self.assertTrue(mid)
        for _, dx, dy, glyph, alpha in mid:
            self.assertLess(dy, 0)
            self.assertTrue(0 < alpha <= 1)
            self.assertIn(glyph, ".'`,")


class Sheet(unittest.TestCase):
    def test_sheet_is_opaque_with_an_empty_dark_window(self):
        rows, fg, bg = sheet.build()
        self.assertEqual((len(rows), len(rows[0])), (sheet.H, sheet.W))
        self.assertTrue((bg[..., 3] == 255).all())
        x0, y0, x1, y1 = sheet.INSIDE
        self.assertEqual("".join(r[x0:x1] for r in rows[y0:y1]).strip(), "")
        self.assertTrue((bg[y0:y1, x0:x1, :3] == sheet.WINDOW).all())

    def test_paper_border_is_lit_from_above(self):
        _, _, bg = sheet.build()
        self.assertGreater(bg[0:2, :, :3].mean(), bg[-2:, :, :3].mean())

    def test_sheet_fits_inside_the_envelope(self):
        self.assertLess(sheet.W, env.ENV_W - 4)
        self.assertLess(sheet.H, env.ENV_H)

    def test_cover_scale_covers_the_viewport_from_an_off_centre_box(self):
        for vw, vh in ((1280, 800), (375, 812), (1920, 1080)):
            for x0, y0 in ((vw * 0.4, vh * 0.2), (10, 10), (vw * 0.6, vh * 0.7)):
                s = sheet.cover_scale((x0, y0, x0 + 120, y0 + 50), vw, vh)
                cx, cy = x0 + 60, y0 + 25
                self.assertTrue(cx - 60 * s <= 0 and cx + 60 * s >= vw and cy - 25 * s <= 0 and cy + 25 * s >= vh)
        self.assertEqual(sheet.cover_scale((5, 5, 5, 9), 800, 600), 1.0)


if __name__ == "__main__":
    unittest.main()
