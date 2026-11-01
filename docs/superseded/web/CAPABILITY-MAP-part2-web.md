> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Capability Map: Part 2 — letter to night garden

Status: **APPROVED 2026-10-31** (assumptions accepted; answers below). Module specs: `SPEC-<id>.md`.

The journey: interactive letter → writing disintegrates → paper pulled out → zoom into the paper →
night grass → seed falls → flower grows → click to bloom → fireflies. Builds on Part 1 (`SPEC.md`);
each module below gets its own `SPEC-<id>.md` after this map is approved.

| Module id | Responsibility | Depends on | Lives in |
|---|---|---|---|
| `stage` | One animation loop and a phase state machine (letter → reveal → night → seed → grown → bloomed); stacked ASCII layers; shared easing/timing; pause + reduced motion; guards so no transition can fire twice or overlap | — | `site/main.py` (refactor), `site/stage.py` |
| `letter-look` | Envelope lit from above (density + colour shading, soft ASCII shadow below), handwritten-style writing on it, gentle float/tilt; redesigned "Will you open ?" headline (more expressive letterforms, colour gradient, glow, slow breathing, small flourish) | `stage` | `site/art.py` |
| `button-hover` | YES/NO calm and readable at rest; on hover/focus/press the glyphs scramble fast and settle back; frame lights up; no layout shift | `stage` | `site/art.py`, `site/main.py` |
| `paper-reveal` | On YES: writing dithers away, flap opens, a separate sheet is pulled out in sync, camera zooms until the sheet fills the screen without stretching | `letter-look` | `site/reveal.py` |
| `night-ground` | Sheet's light fades to deep blue/green/near-black; the paper surface dithers away into grass that emerges gradually; wind field (varying strength/direction, per-blade offsets) drives grass sway | `paper-reveal` | `site/night.py` |
| `flower` | Seed falls with weight and lands with a small dust puff; pause; droopy bud grows (stem, leaves, bud); faint pulsing glow lighting nearby grass; click to bloom (staggered petals, brighter glow, light spill); sway = wind + pointer lean blended. **Swappable**: ported from `docs/flowers.md` for now, behind a small interface so the real flower can replace it | `night-ground` | `site/flower.py` |
| `fireflies` | After full bloom, fireflies fade in one by one: own drifting paths around the flower, own pulse cycles, occasionally drift close and away | `flower` | `site/fireflies.py` |

Build order: `stage` → `letter-look`, `button-hover` → `paper-reveal` → `night-ground` → `flower` → `fireflies` → polish pass.
(Matches the requested order: letter, hover, dissolve, zoom, grass/seed/growth, bloom/glow, pointer, fireflies, polish.)

## Assumptions (correct any of these)

1. **Still 100% ASCII.** Lighting, shadows, gradients and glow come from glyph density, per-character
   colour and CSS `text-shadow`. Float, zoom and sway are CSS transforms on ASCII blocks. No canvas,
   WebGL, SVG or images, and no new dependencies.
2. **Python stays the engine** (PyScript/MicroPython). It is ~10x slower than desktop Python, so the
   night scene is split into layers: grass redrawn ~12–15 times a second, the flower as its own small
   block, fireflies as individually moved single characters. The envelope's flap opening from Part 1 is
   kept as the start of the YES sequence; the "slide away" is replaced by the pull-out and zoom.
3. **Buttons change behaviour:** Part 1's constant churn goes; at rest the words are still, and the
   scramble plays on hover, keyboard focus or a finger press, then settles.
4. **The flower** follows `docs/flowers.md` §12 (Bézier stem, layered petals in its purple/pink palette,
   stamens, halo, sparks, growth by revealing particles) as a placeholder until you swap in the real one.
5. **Reduced motion:** zoom and dissolves become short crossfades; no float, wind or firefly drift
   (fireflies glow in place); bloom happens instantly on click.
6. **The page ends on the living night garden**; nothing comes after the fireflies yet.

## Answers (2026-10-31)

1. **Letter body:** "empty space like black, so when the screen zooms into it we can just expand."
   Read as: the pulled-out sheet's inside is empty black, and the zoom expands it into the night.
   (The envelope face still carries short placeholder writing that dissolves on YES — see answer 2.)
2. **Writing on the envelope's face:** yes; the sheet pulled out is a second paper.
3. **Words on the pulled-out sheet:** none; it becomes the night world.
