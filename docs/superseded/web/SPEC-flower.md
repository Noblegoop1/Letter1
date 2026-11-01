> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Spec: `flower` — seed, growth, glow, bloom, sway, pointer

Status: **APPROVED 2026-10-31.** Module of `CAPABILITY-MAP.md`. Depends on `night-ground`.
**Placeholder art:** ported from `docs/flowers.md` §12. It will be replaced by your real flower, so all
flower drawing sits behind the small interface below.

## Objective
The meadow's focal point: a seed falls, a shy drooping bud grows and glows faintly, and a click wakes it
into a glowing bloom that sways in the wind and leans gently towards the viewer's pointer.

## Design
**Seed (stage phase `seed`)**
- One `o`, then `.`, falls from above the screen to the ground centre over about 1.4 s:
  - gravity easing (ease-in);
  - a slight sideways drift from `wind()`;
  - a tiny squash on landing, shown as a glyph swap to `_`.
- **Impact puff:** 4–6 dust glyphs (`.` `,` `` ` ``) hop out and fade within 0.5 s, and the nearest grass
  blades flick.
- Then a 0.8 s pause.

**Growth (rest of `seed`, about 3 s)**
- A keyframe timeline with Catmull-Rom curves and `smoothstep` windows (`docs/flowers.md` §12.3)
  drives stem length, leaf unfurl and bud size.
- **Stem:** a cubic Bézier, revealed from the ground up. Each stem cell's glyph follows the curve's
  direction there: `|` `/` `\` `(` `)`.
- **Bud:** droops: the stem tip hooks over and the closed bud hangs down.
- **Imperfect shape:** a seeded jitter is applied to the control points and leaf sizes.

**Bud glow (phase `grown`)**
- The bud has a faint pulse: a CSS breathing loop of about 3 s on its glow.
- It lights grass within a small radius at low strength, through `night-ground`'s light spill.

**Bloom (click, Enter or Space on the flower; phase `bloom`, about 2.5 s)**
- The flower is a real `<button aria-label="The flower">`.
- **Head:** lifts from drooping to upright.
- **Petals:** 5–7 open outward, layered as in `docs/flowers.md`, each starting at a different moment
  (its own `smoothstep` window), so there is no pop.
- **Glow:**
  - the glow level ramps up;
  - the halo (per-cell shading around the head) and the light-spill radius grow;
  - the centre is the brightest, but the petals stay detailed.

**Sway (bloomed, and gently while grown)**
- The stem bends in Python from `wind(x, t)` at the flower, plus a smoothed **pointer lean**.
- **Lean:** pointer position relative to the flower, with distance falloff, capped at about 6°. It is
  followed by exponential smoothing (time constant about 0.35 s) and returns to rest when the pointer
  leaves.
- The two are **added**, so the wind never stops while the pointer is near.
- A small CSS rotation smooths motion finer than one character cell.

## Interface (`site/flower.py`, pure — the swap point)
```python
SIZE = (cols, rows)        # frame size; BASE = (col, row) of the root inside it
def frame(grow, bloom, bend, glow):    # -> (chars, cls); all inputs 0..1 except bend (-1..1)
```
Seed, puff, glow levels, pointer and wind blending live in `main.py`/`stage`, so a new flower only has to
implement `frame`.

## Testing
`tests/test_flower.py`:
- frames are rectangular ASCII for a grid of inputs;
- `grow=0` is empty;
- more growth never removes stem cells;
- closed (`bloom=0`) and open (`bloom=1`) frames differ;
- `bend` moves the head left or right as signed;
- the pointer-lean smoothing converges and is capped.

## Success criteria
1. The seed falls with visible acceleration and a landing puff. After a pause the flower grows smoothly
   over about 3 s and ends drooping with a dim, slowly pulsing bud.
2. Clicking the flower (or Enter on it) blooms it over about 2.5 s, with petals opening at different
   moments and the glow and grass light-spill clearly brighter. A second click does nothing.
3. With no pointer, it still sways with the wind. Moving the pointer nearby makes it lean subtly
   (≤ 6°) on top of the wind, and it drifts back when the pointer leaves.
4. Per-frame flower work fits the stage budget (in-page timing).
