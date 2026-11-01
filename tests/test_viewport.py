import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from letter.engine.viewport import Viewport  # noqa: E402

WINDOWS = ((1280, 800), (1920, 1080), (1366, 768), (800, 1280), (640, 400), (3840, 2160))


class ViewportTests(unittest.TestCase):
    def test_round_trip_maps_input_back_to_the_drawn_point(self):
        for logical in ((1280, 800), (640, 640), (320, 320)):
            for window in WINDOWS:
                v = Viewport(logical, window)
                for x, y in ((0, 0), (17.5, 400), (logical[0], logical[1])):
                    wx, wy = v.to_window(x, y)
                    lx, ly = v.to_logical(wx, wy)
                    self.assertAlmostEqual(lx, x, places=6)
                    self.assertAlmostEqual(ly, y, places=6)

    def test_scene_is_never_stretched_and_always_fits(self):
        for logical in ((1280, 800), (640, 640), (320, 320)):
            for window in WINDOWS:
                v = Viewport(logical, window)
                w, h = v.size
                self.assertLessEqual(w, window[0])
                self.assertLessEqual(h, window[1])
                self.assertAlmostEqual(w / h, logical[0] / logical[1], delta=0.01)
                self.assertTrue(w == window[0] or h == window[1])  # fills one axis

    def test_letterbox_is_centred(self):
        v = Viewport((640, 640), (1280, 800))
        self.assertEqual(v.offset, (240, 0))

    def test_rect_scales_position_and_size(self):
        v = Viewport((1280, 800), (2560, 1600))
        self.assertEqual(v.rect(10, 20, 30, 40), (20, 40, 60, 80))

    def test_resize_updates_the_transform(self):
        v = Viewport((1280, 800), (1280, 800))
        v.resize((640, 400))
        self.assertAlmostEqual(v.scale, 0.5)


if __name__ == "__main__":
    unittest.main()
