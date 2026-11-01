import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from letter.art import flower, invitation as inv  # noqa: E402

SIZE = 640


def inside(xy, rect, pad=0.0):
    x, y, w, h = rect
    return (xy[:, 0] >= x - pad) & (xy[:, 0] <= x + w + pad) & (xy[:, 1] >= y - pad) & (xy[:, 1] <= y + h + pad)


def flower_ink():
    """(y, x) of the bloomed sea holly's lit pixels over its whole sway (bend -1..1)."""
    f = flower.Flower()
    lit = np.zeros((SIZE, SIZE), bool)
    for bend in (-1.0, -0.5, 0.0, 0.5, 1.0):
        c = np.zeros((SIZE, SIZE, 3), np.float32)
        f.render(c, 1.0, 1.0, 1.0, bend, 3.0)
        lit |= c.sum(-1) > 0.1
    return lit


class Message(unittest.TestCase):
    def test_text(self):
        self.assertEqual(" ".join(inv.LINES), inv.MESSAGE)
        self.assertEqual(inv.MESSAGE, "Will you go on a date Tuesday?")

    def test_cells_sit_in_the_box_and_are_cached(self):
        p = inv.cells()
        self.assertEqual(p.dtype, np.float32)
        self.assertTrue(600 <= len(p) <= 1400, len(p))
        self.assertTrue(inside(p, inv.BOX).all())
        self.assertIs(inv.cells(), p)
        self.assertFalse(p.flags.writeable)
        self.assertGreater(len(inv.cells(2.6)), len(p))       # finer spacing, more fireflies
        x, y, w, h = inv.BOX
        self.assertTrue(0 <= x and x + w <= SIZE and 0 <= y and y + h <= 165)   # the upper sky
        c = p.mean(0)
        self.assertAlmostEqual(c[0], SIZE / 2, delta=12)      # centred

    def test_cells_are_spaced_like_fireflies_not_piled(self):
        p = inv.cells()
        d = np.hypot(*(p[:, None] - p[None]).transpose(2, 0, 1))
        np.fill_diagonal(d, np.inf)
        nearest = d.min(1)
        self.assertGreater(nearest.min(), 0.6 * inv.SPACING)
        self.assertLess(np.median(nearest), 1.2 * inv.SPACING)

    def test_every_letter_is_filled_and_the_ink_is_covered(self):
        p = inv.cells()
        ink = inv._ink(inv.LINES, inv.EM)
        x, y, w, h = inv.BOX
        ox, oy = x + (w - ink.shape[1]) / 2, y + (h - ink.shape[0]) / 2
        ys, xs = np.nonzero(ink >= 0.5)
        pts = np.stack([xs + ox, ys + oy], -1)
        # nearly every inked pixel has a firefly close by: filled letters, not outlines
        near = np.array([np.hypot(*(p - q).T).min() for q in pts[::7]])
        self.assertGreater((near <= 0.75 * inv.SPACING + 0.5).mean(), 0.97)
        # and nearly every firefly sits on ink
        on = ink[np.clip(np.round(p[:, 1] - oy).astype(int), 0, ink.shape[0] - 1),
                 np.clip(np.round(p[:, 0] - ox).astype(int), 0, ink.shape[1] - 1)]
        self.assertGreater((on > 0.2).mean(), 0.97)
        # two lines, and the words of each stand apart (a clear gap at each space)
        top = p[:, 1] < (p[:, 1].min() + p[:, 1].max()) / 2
        for line, text in ((top, inv.LINES[0]), (~top, inv.LINES[1])):
            gaps = np.diff(np.sort(p[line, 0]))
            self.assertEqual((gaps > 0.4 * inv.EM).sum(), text.count(" "), text)

    def test_clear_of_the_flower_and_the_moon_only_at_a_line_end(self):
        lit = flower_ink()
        p = np.round(inv.cells()).astype(int)
        grow = np.zeros_like(lit)
        for dy in range(-3, 4):
            for dx in range(-3, 4):
                grow[np.clip(p[:, 1] + dy, 0, SIZE - 1), np.clip(p[:, 0] + dx, 0, SIZE - 1)] = True
        self.assertFalse((grow & lit).any())   # no firefly within 3 px of the flower at any sway
        from letter.art import sky
        mx, my, mr = sky.Sky.moon_pos(1.0)
        q = inv.cells()
        behind = np.hypot(q[:, 0] - mx, q[:, 1] - my) < mr
        self.assertLess(behind.mean(), 0.02)


class Buttons(unittest.TestCase):
    def test_rects_sit_in_the_night_clear_of_the_message_and_the_flower(self):
        lit = flower_ink()
        rects = [inv.BUTTONS[k] for k in ("yes", "no")]
        x0, y0, w0, h0 = inv.BOX
        for x, y, w, h in rects:
            self.assertTrue(0 <= x and x + w <= SIZE and 0 <= y and y + h <= SIZE)
            self.assertGreaterEqual(y, y0 + h0)                     # under the message
            self.assertFalse(lit[y:y + h, x:x + w].any())          # clear of the flower
        (ax, _, aw, _), (bx, _, _, _) = rects
        self.assertLess(ax + aw, bx)                                # YES left, NO right
        self.assertAlmostEqual((ax + bx + aw) / 2, SIZE / 2, delta=2)   # symmetric about the flower

    def test_dots_draw_the_button_inside_its_rect(self):
        for name in ("yes", "no"):
            xy, rgb, b = inv.button(name)
            self.assertEqual((xy.dtype, rgb.dtype, b.dtype), (np.float32,) * 3)
            self.assertEqual((rgb.shape, b.shape), ((len(xy), 3), (len(xy),)))
            self.assertTrue(inside(xy, inv.BUTTONS[name]).all(), name)
            g = inv._geometry(name)
            label = xy[g["ring"]:]
            self.assertGreater(len(label), 40)                     # a dot-matrix label
            x, y, w, h = inv.BUTTONS[name]
            self.assertTrue(inside(label, (x + inv.INSET + 4, y + inv.INSET + 4, w - 2 * inv.INSET - 8,
                                           h - 2 * inv.INSET - 8)).all(), name)   # within the outline
            self.assertTrue(((b > 0) & (b < 1.6)).all())
            self.assertTrue(((rgb >= 0) & (rgb <= 1)).all())

    def test_deterministic(self):
        for name in ("yes", "no"):
            a, b = inv.button(name, 0.3, 2.0), inv.button(name, 0.3, 2.0)
            for u, v in zip(a, b):
                np.testing.assert_array_equal(u, v)

    def test_hover_brightens_and_lifts_but_the_rect_stays(self):
        rect = dict(inv.BUTTONS)
        for name in ("yes", "no"):
            xy0, _, b0 = inv.button(name, 0.0, 1.0)
            xy1, _, b1 = inv.button(name, 1.0, 1.0)
            self.assertTrue((b1 > b0).all())
            self.assertGreater(b1.mean(), 1.3 * b0.mean())
            lift = xy0[:, 1] - xy1[:, 1]
            np.testing.assert_allclose(lift, inv.LIFT, atol=1e-5)
            np.testing.assert_array_equal(xy0[:, 0], xy1[:, 0])
            self.assertEqual(inv.BUTTONS, rect)

    def test_shimmer_and_colours(self):
        _, rgb_y, a = inv.button("yes", 0.0, 0.0)
        _, _, b = inv.button("yes", 0.0, 0.7)
        self.assertGreater(np.abs(a - b).max(), 0.05)          # dots shimmer over time
        self.assertLess(np.abs(a - b).mean(), 0.3)             # subtly
        _, rgb_n, _ = inv.button("no")
        self.assertGreater(rgb_y[0, 0], rgb_y[0, 2])           # YES warm gold
        self.assertGreater(rgb_n[0, 2], rgb_n[0, 0])           # NO pale lavender

    def test_draw_adds_light_only_around_the_button(self):
        for name in ("yes", "no"):
            c = np.full((SIZE, SIZE, 3), 0.02, np.float32)
            inv.draw(c, name, 0.5, 1.0)
            x, y, w, h = inv.BUTTONS[name]
            self.assertTrue((c >= 0.02).all())
            lit = np.argwhere(c.sum(-1) > 0.0601)
            self.assertGreater(len(lit), 200)
            self.assertTrue(((lit[:, 1] >= x - 2) & (lit[:, 1] <= x + w + 2)).all())
            self.assertTrue(((lit[:, 0] >= y - inv.LIFT - 3) & (lit[:, 0] <= y + h + 2)).all())
            d = np.full((SIZE, SIZE, 3), 0.02, np.float32)
            inv.draw(d, name, 0.5, 1.0, alpha=0.0)
            self.assertTrue((d == 0.02).all())


if __name__ == "__main__":
    unittest.main()
