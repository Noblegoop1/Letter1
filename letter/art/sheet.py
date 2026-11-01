"""The second ASCII sheet pulled from the envelope: cream paper border around an empty dark window.

The window is the night-to-be: once the camera's zoom fills the screen with it, the night begins.
Pure; returns rows, per-cell fg and bg like envelope.colours().
"""
import numpy as np

from letter.engine.timeline import hash32

W, H = 47, 17                       # cells
INSIDE = (3, 2, W - 3, H - 2)       # window: x0, y0, x1, y1 (exclusive)
CREAM_BG = np.array((236, 222, 194), np.float32)
FIBRE = np.array((176, 156, 120), np.float32)
WINDOW = np.array((12, 9, 16), np.uint8)   # same as the page background: the zoom ends seamlessly


def build():
    rows, fg, bg = [], np.zeros((H, W, 3), np.uint8), np.zeros((H, W, 4), np.uint8)
    x0, y0, x1, y1 = INSIDE
    for y in range(H):
        row = []
        lit = 1.06 - 0.22 * y / H                  # lit from above
        for x in range(W):
            if y0 <= y < y1 and x0 <= x < x1:
                row.append(" ")
                bg[y, x] = (*WINDOW, 255)
                continue
            h = hash32(x + 100, y)
            row.append(".'"[h % 2] if h % 7 == 0 else " ")
            edge = 0.9 if x in (0, W - 1) or y in (0, H - 1) else 1.0
            bg[y, x, :3] = np.clip(CREAM_BG * lit * edge * (0.97 + 0.06 * ((h >> 5) % 10) / 10), 0, 255)
            bg[y, x, 3] = 255
            fg[y, x] = np.clip(FIBRE * lit, 0, 255)
        rows.append("".join(row))
    return rows, fg, bg


def cover_scale(box, view_w, view_h):
    """Scale about the centre of box (x0, y0, x1, y1 px) that makes it cover the viewport (1.0 if empty)."""
    x0, y0, x1, y1 = box
    if x1 - x0 < 1 or y1 - y0 < 1:
        return 1.0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return max(2 * max(cx, view_w - cx) / (x1 - x0), 2 * max(cy, view_h - cy) / (y1 - y0)) * 1.05
