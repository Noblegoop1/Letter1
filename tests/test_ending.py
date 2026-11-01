import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.art import ending  # noqa: E402

MIRROR = {"/": "\\", "\\": "/", "(": ")", ")": "("}


def frame():
    """A cornered chase frame, like the chase core's: ground, horizon, obstacles, mouse, NO, wall."""
    items = [("_-=~"[c % 4], "g", c * 8, 240) for c in range(40)]
    items += [("=~"[c % 2], "g", c * 8, 252) for c in range(0, 40, 2)]
    items += [(".-"[c % 2], "h", c * 8, 168) for c in range(0, 40, 3)]
    for x, y, s in ((48, 228, ",;."), (96, 228, "o"), (152, 228, "|#|"), (200, 216, "[#]"), (200, 228, "[#]")):
        items += [(ch, "o", x + i * 8, y) for i, ch in enumerate(s)]
    for r, row in enumerate(("()()", "~( '>", "^  ^")):
        items += [(ch, "m", 232 + i * 8, 204 + r * 12) for i, ch in enumerate(row) if ch != " "]
    for r, row in enumerate((".--.", "[NO]", "'--'")):
        items += [(ch, "n", 272 + i * 8, 216 + r * 12) for i, ch in enumerate(row)]
    items += [("|", "w", 312, 156 + r * 12) for r in range(8)]
    return items


ITEMS = frame()
WAVES = (("o",), ("g", "h", "w"), ("m",), ("n",))


def ascii_(s):
    return all(32 <= ord(ch) < 127 for ch in s)


class Tremble(unittest.TestCase):
    def test_e2_amplitude_rises_steadily_with_proximity(self):
        """E2: never rises with distance, strictly rises as the pointer closes in, ~0 far, strong near."""
        amps = [ending.shake_amplitude(d / 2) for d in range(0, 801)]   # 0..400 px in 0.5 px steps
        self.assertTrue(all(a >= b for a, b in zip(amps, amps[1:])))
        for d in range(20, 196, 5):
            self.assertGreater(ending.shake_amplitude(d), ending.shake_amplitude(d + 5))
        self.assertLess(max(amps[400:]), 0.5)                            # beyond 200 px
        self.assertGreaterEqual(min(amps[:41]), 4.0)                     # within 20 px
        self.assertLess(max(a - b for a, b in zip(amps, amps[1:])), 0.05)  # smooth: no jump anywhere

    def test_shake_is_continuous_in_time_and_bounded(self):
        for d in (5, 60, 150, 400):
            a = ending.shake_amplitude(d)
            pts = [ending.proximity_shake(d, i / 1000) for i in range(5000)]
            self.assertTrue(all(abs(x) <= a + 1e-9 and abs(y) <= a + 1e-9 for x, y in pts))
            steps = [max(abs(x1 - x0), abs(y1 - y0)) for (x0, y0), (x1, y1) in zip(pts, pts[1:])]
            self.assertLess(max(steps), 0.5)                                 # at 1 ms: never a jump
            self.assertGreater(max(x for x, _ in pts) - min(x for x, _ in pts), a)   # it really moves

    def test_shake_does_not_repeat_on_a_short_period(self):
        near = [ending.proximity_shake(10, i / 100)[0] for i in range(300)]
        for lag in range(5, 150):
            self.assertGreater(max(abs(a - b) for a, b in zip(near, near[lag:])), 0.5, lag)


class Face(unittest.TestCase):
    def test_face_is_a_one_line_kaomoji_the_bundled_font_can_draw(self):
        """The user chose emote-style faces; any glyph the font lacks would show as an empty box."""
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        import pygame
        from letter.engine import glyphs
        pygame.init()
        self.assertEqual(len(ending.FACE), 1)
        font = glyphs.font("mono-bold", 40)
        box = pygame.image.tobytes(font.render("", True, (255, 255, 255), (0, 0, 0)), "RGB")
        for ch in ending.FACE[0]:
            self.assertNotEqual(pygame.image.tobytes(font.render(ch, True, (255, 255, 255), (0, 0, 0)), "RGB"), box, ch)

    def test_face_is_mirror_symmetric(self):
        mirror = dict(MIRROR, **{"´": "`", "`": "´"})
        for row in ending.FACE:
            self.assertEqual(row, "".join(mirror.get(ch, ch) for ch in reversed(row)))

    def test_the_tear_wells_just_under_an_eye(self):
        c, r = ending.TEAR_EYE
        self.assertEqual(ending.FACE[0][c], "•")
        self.assertTrue(0 < r < 1)


class Tear(unittest.TestCase):
    END = ending.TEAR_FORM + ending.TEAR_FALL

    def test_exactly_one_tear_at_all_times(self):
        for i in range(700):
            drops = ending.tear(i / 100)
            self.assertEqual(len(drops), 1, i)
            ch, col, row, a = drops[0]
            self.assertTrue(len(ch) == 1 and ascii_(ch) and 0 <= a <= 1)
            self.assertEqual(col, ending.TEAR_EYE[0])

    def test_forms_under_the_eye_then_runs_down_and_fades(self):
        c, r = ending.TEAR_EYE
        self.assertEqual(ending.tear(0)[0][1:3], (c, r))
        self.assertEqual(ending.tear(0)[0][3], 0)
        forming = [ending.tear(i / 100) for i in range(100)]
        self.assertTrue(all(d[0][2] == r for d in forming))                       # stays put while it wells
        self.assertTrue(all(a[0][3] <= b[0][3] for a, b in zip(forming, forming[1:])))
        self.assertEqual(ending.tear(1.0)[0][3], 1)
        rows = [ending.tear(1 + i / 100)[0][2] for i in range(400)]
        self.assertTrue(all(a <= b for a, b in zip(rows, rows[1:])))             # only ever down
        self.assertGreater(rows[-1] - r, 1.5)                                    # runs well below the face
        self.assertLessEqual(rows[-1], ending.TEAR_END)
        self.assertEqual(ending.tear(self.END)[0][3], 0)
        self.assertGreater(ending.tear(2.5)[0][3], 0.9)


class Glitch(unittest.TestCase):
    def run_(self, seed=0, calm=False, step=0.01):
        return [ending.glitch(ITEMS, i * step, seed, calm) for i in range(int(ending.GLITCH_LEN / step))]

    @staticmethod
    def changed(out):
        return len(set(ITEMS) ^ set(out))

    def test_everything_stays_ascii_and_keeps_its_roles(self):
        roles = {r for _, r, _, _ in ITEMS}
        for out, flash in self.run_(seed=3):
            self.assertTrue(0 <= flash <= 1)
            for ch, role, x, y in out:
                self.assertTrue(len(ch) == 1 and ascii_(ch))
                self.assertIn(role, roles)

    def test_at_most_three_short_flashes_in_any_second(self):
        for seed in range(12):
            on = [ending.glitch(ITEMS, i / 1000, seed)[1] > 0 for i in range(2000)]
            starts = [i for i in range(1, 2000) if on[i] and not on[i - 1]]
            for s in starts:
                self.assertLessEqual(sum(1 for t in starts if s <= t < s + 1000), 3, seed)
                run = next((i for i in range(s, 2000) if not on[i]), 2000) - s
                self.assertLessEqual(run, ending.FLASH_LEN * 1000 + 1)
        self.assertTrue(any(f for _, f in self.run_(seed=0, step=0.001)))       # it does flash at all

    def test_intensity_builds(self):
        outs = self.run_(seed=1)
        early = sum(self.changed(o) for o, _ in outs[:50])
        late = sum(self.changed(o) for o, _ in outs[-50:])
        self.assertGreater(late, 2 * early)
        self.assertGreater(early, 0)

    def test_corrupts_ground_mouse_and_button(self):
        orig = {(x, y): ch for ch, _, x, y in ITEMS}
        hit = set()
        for out, _ in self.run_(seed=2):
            hit |= {role for ch, role, x, y in out if orig.get((x, y), ch) != ch}
        self.assertTrue({"g", "m", "n"} <= hit, hit)

    def test_rows_slide_by_whole_cells(self):
        xs = {x for _, _, x, _ in ITEMS}
        moved = [x for out, _ in self.run_(seed=4) for _, _, x, _ in out if x not in xs]
        self.assertTrue(moved)
        self.assertTrue(all(x % ending.CW == 0 for x in moved))

    def test_calm_is_gentler_and_never_flashes(self):
        calm, full = self.run_(seed=5, calm=True, step=0.005), self.run_(seed=5, step=0.005)
        self.assertFalse(any(f for _, f in calm))
        self.assertLess(sum(self.changed(o) for o, _ in calm), sum(self.changed(o) for o, _ in full) / 2)

    def test_deterministic_per_seed_and_time(self):
        self.assertEqual(ending.glitch(ITEMS, 1.37, 9), ending.glitch(ITEMS, 1.37, 9))
        self.assertNotEqual(ending.glitch(ITEMS, 1.37, 9), ending.glitch(ITEMS, 1.37, 10))


class Dissolve(unittest.TestCase):
    def test_breaks_in_order_obstacles_ground_mouse_button(self):
        gone = []
        for roles in WAVES:
            last = max(i for i in range(1001) if any(r in roles for _, r, *_ in ending.dissolve(ITEMS, i / 1000)))
            gone.append(last)
        self.assertEqual(gone, sorted(gone))
        self.assertEqual(len(set(gone)), 4, gone)
        alone = {r for _, r, *_ in ending.dissolve(ITEMS, 0.75)}
        self.assertEqual(alone, {"n"})                                  # the NO button is last, alone

    def test_whole_at_the_start_and_nothing_left_at_the_end(self):
        for seed in range(6):
            self.assertEqual(ending.dissolve(ITEMS, 1.0, seed), [])
            start = ending.dissolve(ITEMS, 0.0, seed)
            self.assertGreaterEqual(sum(1 for *_, a in start if a == 1), len(ITEMS) - 2)

    def test_fragments_vary_and_stay_ascii(self):
        mid = ending.dissolve(ITEMS, 0.3, 2)
        ground = [f for f in mid if f[1] in "ghw" and f[4] < 1]
        self.assertGreater(len({ch for ch, *_ in ground}), 5)
        self.assertGreater(len({round(x) for _, _, x, _, _ in ground}), 20)
        for ch, _, _, _, a in mid:
            self.assertTrue(len(ch) == 1 and ascii_(ch) and 0 < a <= 1)

    def test_deterministic_per_seed(self):
        self.assertEqual(ending.dissolve(ITEMS, 0.4, 1), ending.dissolve(ITEMS, 0.4, 1))
        self.assertNotEqual(ending.dissolve(ITEMS, 0.4, 1), ending.dissolve(ITEMS, 0.4, 2))


class Budget(unittest.TestCase):
    def test_each_frame_is_cheap(self):
        """A few hundred items: the worst frame of glitch and of dissolve is under 1 ms."""
        items = ITEMS + [(ch, r, x, y - 120) for ch, r, x, y in ITEMS]
        for name, fn in (("glitch", lambda i: ending.glitch(items, i / 10)),
                         ("dissolve", lambda i: ending.dissolve(items, i / 20)),
                         ("tear+shake", lambda i: (ending.tear(i / 4), ending.proximity_shake(30, i / 60)))):
            worst = 0.0
            for i in range(20):
                best = 1.0
                for _ in range(15):
                    start = time.perf_counter()
                    fn(i)
                    best = min(best, time.perf_counter() - start)
                worst = max(worst, best)
            print(f"\n  {name} x{len(items)}: worst frame {worst * 1000:.3f} ms", end="")
            self.assertLess(worst * 1000, 1.0)


if __name__ == "__main__":
    unittest.main()
