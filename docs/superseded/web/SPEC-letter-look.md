> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Spec: `letter-look` — a lit, floating envelope and a better headline

Status: **APPROVED 2026-10-31.** Module of `CAPABILITY-MAP.md`. Depends on `stage`.

## Objective
Make the envelope read as a physical object under a light from directly above, and make
"Will you open ?" feel romantic and intentional instead of plain block letters, while keeping the Part 1
look: ASCII on a dark page.

## Design
**Envelope (`art.envelope`)**
- **Lit from above.**
  - Paper colour steps through 4 shades from brightest at the top border to dimmest at the bottom.
  - The flap catches the most light. The side and bottom flaps are a step darker. The lining is darkest.
  - The top border gets brighter highlight glyphs and the bottom border darker, heavier ones.
- **Opaque cells.** Envelope cells get a background colour, like ANSI art (each cell has a background
  as well as a foreground colour). Today spaces are see-through. Opaque cells are needed so the sheet
  can hide *behind* the envelope in `paper-reveal`, and they give the paper a soft tone. The tint is
  subtle: near-black warm, lighter at the top.
- **Writing.** Two short lines are drawn in the lower triangle, in an ink colour and italic
  (monospace italics keep cell width). They dissolve on YES. Text (chosen 2026-10-31):
  `RAHHH` / `SHE OPENED IT`. The text is one constant, so it is easy to change.
- **Shadow.** A separate ASCII shadow (a soft ellipse of `.:` in a near-black violet) sits under the
  envelope. It grows wider and fainter as the envelope floats up.
- **Float.** A CSS keyframe loop (about 7 s) bobs the envelope 0.6% of the viewport height and tilts it
  ±0.6°, and the shadow is synced to it. Pause freezes it; reduced motion turns it off.
- **Buttons move below the envelope**, overlapping its bottom edge by about a row, so the writing in
  the lower triangle stays visible. Part 1 had them over the lower half.

**Headline (`art.headline`)**
- **Italic letterforms.** The existing pixel font is slanted one column per row, the same slope as `/`.
- **Pen-stroke edges.** Each stroke is solid `#` with a `/` leading edge, so it reads as one leaning pen
  line. (Changed in build: an outlined version, using `/` `_` and neighbour-picked glyphs, was hard to
  read at this size.) The drop shadow uses soft `:` and `.` rather than copies of the letters.
- **Lit from above.** The fill colour runs as a 4-step vertical gradient from pale pink-white at the top
  to deep rose at the bottom.
- **Depth.** A drop shadow sits one row down and two columns right, in dark plum, behind the letters.
- **Glow and breathing.** A soft pink `text-shadow`, plus a slow CSS breathing loop (about 6 s):
  1–1.5% scale with a glow swell.
- **Flourish.** A thin vine under the text, `~-.,_,.-~ <3 ~-.,_,.-~`, in a dim rose.
- Both layouts stay: one line on wide screens, two lines in portrait.

## Testing
In `tests/test_art.py`:
- headline and shadow frames are rectangular and pure ASCII;
- the shadow sits exactly at (+1 row, +2 cols) from the ink;
- envelope shading is non-increasing from top to bottom row;
- the writing sits inside the lower triangle;
- every envelope cell inside the body is opaque.

Browser: screenshots at 1280×800 and 375×812.

## Success criteria
1. A screenshot shows a clear top-to-bottom light falloff on the envelope and a shadow beneath it.
2. The envelope floats and tilts visibly but gently: no more than 0.6% of viewport height, no more than
   ±0.6°, period at least 6 s.
3. The headline reads as italic, gradient-lit, softly glowing letters with a flourish; it fits without
   horizontal scroll at both sizes.
4. The writing is readable on the envelope, and the buttons don't cover it.

## Decisions (2026-10-31)
1. Writing text: `RAHHH` / `SHE OPENED IT`.
2. Cell background colours (ANSI style) are allowed: they make the envelope opaque so the sheet can hide
   behind it.
