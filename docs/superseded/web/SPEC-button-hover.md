> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Spec: `button-hover` — YES/NO that come alive under the pointer

Status: **APPROVED 2026-10-31.** Module of `CAPABILITY-MAP.md`. Depends on `stage`.

## Objective
Buttons feel like part of the letter rather than web buttons: still and readable at rest, and briefly
transformed when you reach for them.

## Design
- **At rest:** the big-letter word is drawn with one settled glyph per cell (a fixed, even texture). It no
  longer churns on its own; Part 1's constant churn goes.
- **Scramble.** Hover, keyboard focus or a finger press starts a scramble at time `since`:
  - each filled cell cycles through look-alike ASCII glyphs at about 30 Hz;
  - each cell settles back after its own delay of 0.25–0.7 s, so the word re-forms in a ripple, not all at once;
  - the letter shape never changes, only the glyphs inside it, so the word stays readable;
  - re-entering restarts the ripple from wherever it is.
- **Feedback:** the frame brightens and glows, and the button lifts 2 px with a CSS transform.
  Transforms only, so nothing else on the page moves.
- **Keeps from Part 1:** NO's shake on click; real `<button>`s with fixed `aria-label`; glyphs `aria-hidden`.
- **Touch:** press shows the ripple; the click goes through as usual.
- **Reduced motion:** no ripple, only the frame highlight.
- **Pause:** the stage clock stops the ripple as well.
- **Cost:** the button is only redrawn while a ripple is running, and never more than 24 times a second.

## Interface (`site/art.py`)
```python
def button(word, t, since=None, wild=False):
    """Framed big-letter word; since = when the scramble started (None = at rest)."""
```

## Testing
In `tests/test_art.py`:
- at rest, the frame is identical over time;
- during a ripple it differs;
- after 0.7 s it equals the rest frame again;
- the shape mask is unchanged at all times;
- YES and NO are the same size.

## Success criteria
1. Hovering YES makes its letters shimmer and settle back in under 0.8 s; the word stays recognisable throughout.
2. No layout shift: neighbouring elements' bounding boxes are identical before, during and after hover.
3. Tab focus triggers the same effect and shows a visible focus ring.
