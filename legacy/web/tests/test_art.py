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


def in_body(x, y):
    return 0 < x < art.ENV_W - 1 and art.TOP < y < art.BOT


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
        self.assertLess(narrow, wide / 2 + 8)

    def test_headline_shadow_sits_one_row_down_two_columns_right(self):
        chars, cls = art.headline()
        for y, row in enumerate(cls):
            for x, k in enumerate(row):
                if k in "tuvx":
                    self.assertIn(cls[y + 1][x + 2], "tuvxz")

    def test_headline_is_brighter_at_the_top(self):
        _, cls = art.headline()
        bands = [min("tuvx".index(k) for k in row if k in "tuvx") for row in cls if any(k in "tuvx" for k in row)]
        self.assertEqual(bands, sorted(bands))


class Envelope(unittest.TestCase):
    def test_every_flap_depth_gives_same_size_ascii_layers(self):
        sizes = set()
        for d in range(-art.CY, art.CY + 1):
            for layer in art.envelope(d):
                check_frame(self, layer)
                sizes.add((len(layer[0]), len(layer[0][0])))
        self.assertEqual(sizes, {(art.HEAD + art.ENV_H, art.ENV_W)})

    def test_closed_envelope_has_heart_seal_on_centre(self):
        _, (chars, cls) = art.envelope(art.CY)
        self.assertEqual(cls[art.TIP][art.CX], "h")

    def test_open_envelope_has_no_seal_and_flap_folds_up_behind(self):
        (bchars, bcls), (fchars, fcls) = art.envelope(-art.CY)
        self.assertNotIn("h", "".join(bcls) + "".join(fcls))
        self.assertTrue(bchars[0].strip(), "folded-up flap should reach the top row of the back layer")

    def test_closed_envelope_leaves_head_rows_empty(self):
        for chars, _ in art.envelope(art.CY):
            self.assertEqual("".join(chars[: art.HEAD]).strip(), "")

    def test_closed_front_is_opaque_below_the_top_edge(self):
        _, (_, cls) = art.envelope(art.CY)
        for y in range(art.TOP + 1, art.BOT + 1):
            self.assertNotIn(" ", cls[y], "row %d has a see-through cell" % y)

    def test_top_edge_is_behind_the_sheet(self):
        (bchars, _), (fchars, _) = art.envelope(art.CY)
        self.assertEqual(bchars[art.TOP].strip()[:3], ".--")
        self.assertEqual(fchars[art.TOP].strip(), "")

    def test_open_front_leaves_the_pocket_see_through(self):
        _, (_, cls) = art.envelope(-art.CY)
        self.assertEqual(cls[art.TOP + 3][art.CX], " ")

    def test_side_flaps_darken_from_top_to_bottom(self):
        shades = [art.shade(2, y) for y in range(art.TOP + 1, art.BOT)]
        self.assertEqual(shades, sorted(shades))
        self.assertGreater(len(set(shades)), 2)

    def test_flap_catches_more_light_than_side_flaps(self):
        y = art.TOP + 3
        self.assertLess(art.shade(art.CX, y), art.shade(2, y + 1))

    def test_writing_sits_inside_the_bottom_flap(self):
        for x, y, ch in art.writing():
            self.assertTrue(in_body(x, y))
            self.assertGreater(y - art.TIP, abs(x - art.CX) * art.CY / art.CX, (x, y, ch))
        self.assertEqual("".join(ch for _, _, ch in art.writing()), "RAHHHSHE OPENED IT")

    def test_flap_depth_follows_angle(self):
        self.assertEqual(art.flap_depth(0), art.CY)
        self.assertEqual(art.flap_depth(90), 0)
        self.assertEqual(art.flap_depth(180), -art.CY)

    def test_heart_sprite_is_mirror_symmetric(self):
        for row in art.HEART:
            mirrored = "".join(MIRROR.get(ch, ch) for ch in reversed(row))
            self.assertEqual(row, mirrored)

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

    def test_shadow_is_rectangular_ascii(self):
        check_frame(self, art.shadow())

    def test_puff_spreads_then_vanishes(self):
        for e in (0.0, 0.2, 0.45):
            check_frame(self, art.puff(e))
            self.assertTrue("".join(art.puff(e)[0]).strip())
        self.assertEqual("".join(art.puff(art.PUFF_S)[0]).strip(), "")


class Buttons(unittest.TestCase):
    def test_yes_and_no_are_same_size(self):
        yes, no = art.button("YES", 0.0), art.button("NO", 0.0)
        check_frame(self, yes)
        check_frame(self, no)
        self.assertEqual((len(yes[0]), len(yes[0][0])), (len(no[0]), len(no[0][0])))

    def test_rest_frame_never_changes(self):
        self.assertEqual(art.button("YES", 0.0), art.button("YES", 9.3))

    def test_hover_ripples_then_settles_back_to_rest(self):
        rest = art.button("YES", 0.0)
        self.assertNotEqual(art.button("YES", 5.1, since=5.0), rest)
        self.assertEqual(art.button("YES", 5.0 + art.RIPPLE, since=5.0), rest)

    def test_ripple_and_tantrum_keep_the_letter_shape(self):
        mask = art.big_mask("YES")
        for rows in (art.ripple(mask, 0.1), art.ripple(mask, 0.4), art.churn(mask, art.WILD, 3.3)):
            self.assertEqual([len(r) for r in rows], [len(r) for r in mask])
            for r, m in zip(rows, mask):
                self.assertEqual([c == " " for c in r], [c == " " for c in m])


class Html(unittest.TestCase):
    def test_escapes_markup_and_keeps_text(self):
        html = art.to_html(["a<&>b"], ["xxxxx"])
        self.assertEqual(html, '<span class="x">a&lt;&amp;&gt;b</span>')

    def test_blank_cells_are_plain_text(self):
        self.assertEqual(art.to_html([" ab "], [" yy "]), ' <span class="y">ab</span> ')

    def test_opaque_space_keeps_its_span(self):
        self.assertEqual(art.to_html([" "], ["A"]), '<span class="A"> </span>')


if __name__ == "__main__":
    unittest.main()
