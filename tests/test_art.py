import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "site"))

import art  # noqa: E402

MIRROR = {"/": "\\", "\\": "/", "`": "'", "'": "`", "(": ")", ")": "("}


def is_rect(rows):
    return len(rows) > 0 and all(len(r) == len(rows[0]) for r in rows)


def is_ascii(rows):
    return all(32 <= ord(ch) < 127 for r in rows for ch in r)


def check_frame(test, frame):
    chars, cls = frame
    test.assertTrue(is_rect(chars), "rows differ in width")
    test.assertEqual([len(r) for r in chars], [len(r) for r in cls])
    test.assertEqual(len(chars), len(cls))
    test.assertTrue(is_ascii(chars), "non-ASCII character")


class BigLetters(unittest.TestCase):
    def test_yes_is_seven_rows_of_two_column_pixels(self):
        mask = art.big_mask("YES")
        self.assertEqual(len(mask), 7)
        self.assertEqual(len(mask[0]), (5 * 3 + 2) * 2)

    def test_headline_layouts_are_rectangular_ascii(self):
        for narrow in (False, True):
            check_frame(self, art.headline(narrow))

    def test_narrow_headline_is_less_than_half_as_wide(self):
        wide = len(art.headline(False)[0][0])
        narrow = len(art.headline(True)[0][0])
        self.assertLess(narrow, wide / 2 + 2)


class Envelope(unittest.TestCase):
    def test_every_flap_depth_gives_same_size_ascii_frame(self):
        sizes = set()
        for d in range(-art.CY, art.CY + 1):
            frame = art.envelope(d)
            check_frame(self, frame)
            sizes.add((len(frame[0]), len(frame[0][0])))
        self.assertEqual(sizes, {(art.HEAD + art.ENV_H, art.ENV_W)})

    def test_closed_envelope_has_heart_seal_on_centre(self):
        chars, cls = art.envelope(art.CY)
        self.assertEqual(cls[art.HEAD + art.CY][art.CX], "h")

    def test_open_envelope_has_no_seal_and_flap_above_body(self):
        chars, cls = art.envelope(-art.CY)
        self.assertNotIn("h", "".join(cls))
        self.assertTrue(chars[0].strip(), "flipped flap should reach the top row")

    def test_closed_envelope_leaves_head_rows_empty(self):
        chars, _ = art.envelope(art.CY)
        self.assertEqual("".join(chars[: art.HEAD]).strip(), "")

    def test_closed_envelope_hides_the_lining(self):
        _, cls = art.envelope(art.CY)
        self.assertNotIn("i", "".join(cls))

    def test_line_spans_reach_both_ends_without_gaps(self):
        for x1, y1 in ((30, 12), (2, 12), (30, 1), (11, 30), (0, 12), (-20, 5)):
            spans = art._line(None, 10, 0, 10 + x1, y1)
            rows = sorted(spans)
            self.assertEqual((rows[0], rows[-1]), (0, y1))
            ends = {spans[0][0], spans[0][1], spans[y1][0], spans[y1][1]}
            self.assertIn(10, ends)
            self.assertIn(10 + x1, ends)
            for a, b in zip(rows, rows[1:]):  # each row starts where the one above stopped
                lo, hi = spans[a]
                self.assertTrue(spans[b][0] <= hi + 1 and spans[b][1] >= lo - 1)

    def test_flap_depth_follows_angle(self):
        self.assertEqual(art.flap_depth(0), art.CY)
        self.assertEqual(art.flap_depth(90), 0)
        self.assertEqual(art.flap_depth(180), -art.CY)

    def test_heart_sprite_is_mirror_symmetric(self):
        for row in art.HEART:
            mirrored = "".join(MIRROR.get(ch, ch) for ch in reversed(row))
            self.assertEqual(row, mirrored)


class Buttons(unittest.TestCase):
    def test_yes_and_no_are_same_size(self):
        yes, no = art.button("YES", 0.0), art.button("NO", 0.0)
        check_frame(self, yes)
        check_frame(self, no)
        self.assertEqual((len(yes[0]), len(yes[0][0])), (len(no[0]), len(no[0][0])))

    def test_churn_keeps_the_letter_shape(self):
        mask = art.big_mask("YES")
        for t in (0.0, 0.37, 5.1):
            rows = art.churn(mask, "#@%&", t)
            self.assertEqual([len(r) for r in rows], [len(r) for r in mask])
            for r, m in zip(rows, mask):
                self.assertEqual([c == " " for c in r], [c == " " for c in m])

    def test_churn_changes_over_time(self):
        mask = art.big_mask("YES")
        self.assertNotEqual(art.churn(mask, "#@%&", 0.0), art.churn(mask, "#@%&", 1.0))


class Html(unittest.TestCase):
    def test_escapes_markup_and_keeps_text(self):
        html = art.to_html(["a<&>b"], ["xxxxx"])
        self.assertEqual(html, '<span class="x">a&lt;&amp;&gt;b</span>')

    def test_blank_cells_are_plain_text(self):
        self.assertEqual(art.to_html([" ab "], [" yy "]), ' <span class="y">ab</span> ')


class Ease(unittest.TestCase):
    def test_ease_clamps_and_hits_ends(self):
        self.assertEqual(art.ease(-1), 0)
        self.assertEqual(art.ease(0), 0)
        self.assertEqual(art.ease(1), 1)
        self.assertEqual(art.ease(2), 1)
        self.assertAlmostEqual(art.ease(0.5), 0.5)


if __name__ == "__main__":
    unittest.main()
