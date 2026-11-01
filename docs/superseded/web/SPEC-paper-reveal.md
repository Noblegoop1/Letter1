> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Spec: `paper-reveal` — writing dissolves, a sheet is pulled out, the camera dives in

Status: **APPROVED 2026-10-31.** Module of `CAPABILITY-MAP.md`. Depends on `letter-look`.

## Objective
YES starts one continuous movement: the words on the envelope crumble into particles, the flap opens,
a second sheet slides up out of the envelope in step with the crumbling, and the view zooms into the
sheet's black middle until it fills the screen.

## Design (stage phase `reveal`, about 4.5 s; timings tuned in build)
| Time (s) | What happens |
|---|---|
| 0.0–1.4 | **Writing dissolves.** Each writing cell has a fixed 4×4 Bayer dither threshold. As progress passes it, the glyph steps down a ramp (`#` `+` `:` `.`) and vanishes. About 1 in 4 cells sheds a `.` particle that drifts up and fades; there are never more than 30 particles. |
| 0.2–1.5 | **Flap opens.** Reuses Part 1's character fold; the heart seal rides on its tip. |
| 0.6–2.4 | **Sheet pulled out.** A separate layer, moved by a smooth CSS transform. Ease-out starting at the same moment the writing is half gone, so the two read as cause and effect. |
| 2.2–4.5 | **Camera zoom.** Ease-in-out. |

**The sheet**
- A thin cream paper border around an **empty black inside**, about 31×15 cells, with faint paper fibres.

**Layering, back to front**
- Open flap and lining, then the sheet, then the envelope body (opaque cells from `letter-look`).
- So the sheet rises out of the pocket in front of the opened flap. That is the familiar
  "letter peeking out" picture, chosen over strict physical correctness.

**Camera zoom**
- One wrapper holding all letter layers gets `transform: scale(s)`, with `transform-origin` at the centre
  of the sheet's black inside.
- The final `s` is the "cover" ratio, `max(viewport w / inside w, viewport h / inside h) × 1.05`. It is
  measured from the real element sizes when the zoom starts, so it works at any screen size.
- Scaling is uniform, so nothing is stretched. The headline and buttons have already faded out.
- **Hand-off:** when the black covers the screen, the page background is the same black and the night
  layer takes over underneath. There is no visible cut.

## Interface (`site/reveal.py`, pure)
```python
def writing(progress):            # -> (chars, cls) of the writing layer
def particles(progress, t):       # -> list of (col, row, glyph) drifting dots
def sheet():                      # -> (chars, cls) of the sheet, static
def cover_scale(inner_w, inner_h, view_w, view_h):  # -> float
```

## Testing
`tests/test_reveal.py`:
- dissolution is monotonic (a cell that is gone stays gone);
- everything is gone at progress 1;
- the particle count is within the cap;
- the sheet is rectangular ASCII with an all-black (space) inside;
- `cover_scale` covers both axes for landscape, portrait and square screens.

## Success criteria
1. From YES to a fully black screen takes no more than 5 s, with no visible jump, cut or stretch at
   1280×800, 1920×1080 and 375×812 (screenshots at 4+ points along the way).
2. The words visibly crumble before and while the sheet rises; the sheet clearly emerges from inside the
   envelope, not on top of it.
3. Clicking YES again, or anything else, during the reveal does nothing.
4. Python work stays within the stage budget during the zoom.
