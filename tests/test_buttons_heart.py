import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.art import buttons, heart  # noqa: E402

MIRROR = {"/": "\\", "\\": "/", "`": "'", "'": "`", "(": ")", ")": "("}


class Buttons(unittest.TestCase):
    def test_yes_and_no_frames_are_the_same_size(self):
        for word in ("YES", "NO"):
            rows, roles = buttons.frame(word)
            self.assertEqual((len(rows[0]), len(rows)), buttons.SIZE)
            self.assertTrue(all(len(r) == buttons.SIZE[0] for r in rows + roles))

    def test_rest_frame_never_changes(self):
        self.assertEqual(buttons.frame("YES"), buttons.frame("YES", hover_e=buttons.SETTLE[1] + 3))

    def test_hover_shifts_then_settles_to_the_exact_label(self):
        rest = buttons.frame("YES")
        self.assertNotEqual(buttons.frame("YES", hover_e=0.05), rest)
        self.assertEqual(buttons.frame("YES", hover_e=buttons.SETTLE[1]), rest)

    def test_scramble_and_tantrum_keep_the_letter_shape_and_width(self):
        mask = buttons.big_mask("YES")
        for rows in (buttons.scramble(mask, 0.05), buttons.scramble(mask, 0.3), buttons.tantrum(mask, 1.7)):
            self.assertEqual([len(r) for r in rows], [len(r) for r in mask])
            for r, m in zip(rows, mask):
                self.assertEqual([c == " " for c in r], [c == " " for c in m])

    def test_characters_settle_at_different_moments(self):
        mask = buttons.big_mask("YES")
        mid = buttons.scramble(mask, 0.35)
        settled = sum(row.count(buttons.REST) for row in mid)
        ink = sum(row.count("#") for row in mask)
        self.assertTrue(0 < settled < ink)


class Heart(unittest.TestCase):
    def test_sprite_is_rectangular_and_mirror_symmetric(self):
        for row in heart.SPRITE:
            self.assertEqual(len(row), heart.SIZE[0])
            self.assertEqual(row, "".join(MIRROR.get(ch, ch) for ch in reversed(row)))

    def test_cells_cover_wax_and_outline(self):
        cells = heart.cells()
        self.assertTrue(any(w for *_, w in cells))
        self.assertTrue(any(not w for *_, w in cells))
        self.assertTrue(all(32 <= ord(ch) < 127 for _, _, ch, _ in cells))


if __name__ == "__main__":
    unittest.main()


class HeartBreaks(unittest.TestCase):
    """SPEC §11 no-4: the heart cracks, then bursts into a varied mist of ASCII fragments (N4)."""

    def test_the_crack_grows_and_the_halves_part(self):
        self.assertFalse([c for c in heart.cracked(0.0) if c[3] == "c"])
        half, full = heart.cracked(0.5), heart.cracked(1.0)
        self.assertLess(sum(c[3] == "c" for c in half), sum(c[3] == "c" for c in full))
        self.assertTrue(any(c[4] < 0 for c in full) and any(c[4] > 0 for c in full))

    def test_fragments_vary_and_are_gone_after_the_burst(self):
        first = heart.shatter(0.02)
        self.assertTrue(150 <= len(first) <= 300, len(first))
        self.assertGreaterEqual(len({g for _, _, g, _, _ in first}), 12)
        later = heart.shatter(0.5)
        moved = [((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 for (x0, y0, *_), (x1, y1, *_) in zip(first, later)]
        self.assertGreater(max(moved) / (sorted(moved)[len(moved) // 2] + 1e-6), 2.0)   # a few fly far, most drift
        cx = sum(x for x, *_ in first) / len(first)
        self.assertTrue(any(x < cx - 40 for x, *_ in later) and any(x > cx + 40 for x, *_ in later))
        self.assertLess(len(heart.shatter(1.0)), len(first))      # lifetimes differ
        self.assertEqual(heart.shatter(1.7), [])
        self.assertEqual(heart.shatter(0.3), heart.shatter(0.3))  # deterministic
