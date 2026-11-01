"""Draw a grid of glyphs with a colour per cell (and an optional opaque background per cell).

Glyphs are rendered once in white; per-cell colour is applied by multiplying with a colour field
blown up to cell size. So thousands of differently lit cells cost one blend, not thousands of renders.
"""
import numpy as np
import pygame


def _field(arr, cell, size):
    """(H, W, C) uint8 per-cell colours -> a surface where every cell is a solid block."""
    h, w = arr.shape[:2]
    alpha = arr.shape[2] == 4
    small = pygame.Surface((w, h), pygame.SRCALPHA if alpha else 0)
    pygame.surfarray.pixels3d(small)[...] = arr[..., :3].swapaxes(0, 1)
    if alpha:
        pygame.surfarray.pixels_alpha(small)[...] = arr[..., 3].swapaxes(0, 1)
    return pygame.transform.scale(small, size)  # nearest-neighbour: crisp cell blocks


def render(atlas, rows, fg, bg=None, cell=None):
    """Surface of the grid. atlas: glyphs.Atlas; fg (H, W, 3) uint8; bg (H, W, 4) uint8 or None;
    cell: (w, h) px per cell (defaults to the atlas cell)."""
    cw, ch = cell or atlas.cell
    h, w = len(rows), len(rows[0])
    grid = (round(w * cw), round(h * ch))
    # glyph boxes can be taller than a packed row: leave room so the last row isn't clipped
    size = (grid[0], max(grid[1], round((h - 1) * ch) + atlas.font.get_height()))
    ink = pygame.Surface(size, pygame.SRCALPHA)
    white = (255, 255, 255)
    ink.fblits([(atlas.glyph(c, white), (round(x * cw), round(y * ch)))
                for y, row in enumerate(rows) for x, c in enumerate(row) if c != " "])
    colour = np.concatenate([fg, np.full(fg.shape[:2] + (1,), 255, np.uint8)], 2)
    # stretch the last row's colour down into the overflow so its glyph tails keep their colour
    field = pygame.Surface(size, pygame.SRCALPHA)
    field.blit(pygame.transform.scale(_field(colour[-1:], (cw, ch), (grid[0], 1)), (grid[0], size[1])), (0, 0))
    field.blit(_field(colour, (cw, ch), grid), (0, 0))
    ink.blit(field, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    if bg is None:
        return ink
    out = pygame.Surface(size, pygame.SRCALPHA)
    out.blit(_field(bg, (cw, ch), grid), (0, 0))
    out.blit(ink, (0, 0))
    return out
