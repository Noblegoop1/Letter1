> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Spec: `night-ground` — the black page becomes a night meadow

Status: **APPROVED 2026-10-31.** Module of `CAPABILITY-MAP.md`. Depends on `paper-reveal`.

## Objective
The black that fills the screen turns into a quiet night: ambient deep blue and muted green on
near-black, and the paper's faint fibres dissolve into grass that grows up and sways in a living wind.

## Design (stage phase `night`, about 3 s, then ongoing)
**The grid**
- A full-viewport ASCII grid sized to a fixed cell budget of about 4,500 cells. The font size is
  √(screen area / (cell width × 4500)), clamped to 12–32 px, so the cost is the same on any screen. Its
  columns and rows come from the measured cell size, so it always covers the screen without stretching.
  - Changed in build from a font of about 1.1% of the larger viewport side (10–16 px). Measured under
    MicroPython, a 156×57 meadow took 32 ms per redraw. At about 110×41 it takes 6.5 ms to build plus
    6.1 ms to turn into HTML, and the two are done in separate frames.
- It is rebuilt after a resize, once the new size has held for 0.25 s.

**Lighting shift**
- The page background eases from black to the darkest night tone over 1.5 s.
- The sky is mostly empty, with an extremely faint blue gradient made of a few dim characters.
- There is no top-down paper light any more.

**Ground dissolution**
- The bottom ~35% starts as faint paper fibres (`.` `'` in dim cream).
- Each cell has a Bayer threshold, biased so the bottom rows go first. As progress passes it, the fibre
  vanishes and a grass cell appears.
- The grass comes in gradually from the bottom up, over about 2.5 s.

**Grass**
- Each column has a blade, 2–5 rows tall, with its own height, phase and stiffness (seeded hash, stable
  across frames).
- The glyph depends on how far the blade leans: `|` upright, `/` and `\` leaning, `'` `` ` `` `,` at the tips,
  `"` `;` near the base.
- Colours are muted greens, darker toward the back and bottom rows.

**Wind**
- `wind(x, t)` is a gust that travels across the field: `A(t) · sin(k·x − ω·t)`.
- The amplitude `A(t)` and direction drift slowly (sums of slow sines with unrelated periods), and each
  blade adds its own offset. The field never moves in lockstep, and it never repeats noticeably within
  a minute.
- The same `wind()` is shared with `flower` and `fireflies`.

**Light spill**
- The renderer takes a light source (x, y, strength). Grass cells inside its radius step up 1–3
  brightness classes, falling off with distance. `flower` drives it.

**Cost**
- Grass is redrawn 10 times a second. Each redraw is split into a build frame and an HTML frame, each
  ≤ 8 ms (measured in-page). The first build at a new size (~130 ms) runs while the letter waits.

## Interface (`site/night.py`, pure)
```python
def wind(x, t):                         # -> lean in about [-1, 1]
def ground(cols, rows, t, emerge, light=None):   # -> (chars, cls); emerge 0..1
```

## Testing
`tests/test_night.py`:
- frames are rectangular ASCII for several grid sizes;
- emergence is monotonic (grass never un-grows) and complete at 1;
- `wind` stays in its range and differs between distant columns at the same time;
- light spill brightens near cells and leaves far cells unchanged.

## Success criteria
1. After the zoom, the meadow builds up from the bottom over 2–3 s with no hard cut; a screenshot
   mid-way shows both fibres and grass.
2. The grass visibly sways, with gusts that change strength and direction over ~10 s of watching;
   neighbouring blades are not in lockstep.
3. It fills 1280×800, 1920×1080 and 375×812 with no stretching, gaps or scrollbars.
4. Grass redraws stay within budget (in-page timing).
