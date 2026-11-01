> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Spec: `fireflies` — quiet lights around the bloom

Status: **APPROVED 2026-10-31.** Module of `CAPABILITY-MAP.md`. Depends on `flower`.

## Objective
Once the flower has fully bloomed, a few fireflies arrive one by one and drift around it, each with its
own path and pulse, adding depth and quiet magic without stealing focus from the flower.

## Design (phase `bloomed`)
- **Count and arrival:** 10 fireflies, chosen for restraint. They fade in one at a time, about 0.7 s
  apart, starting 0.5 s after the bloom ends.
- **Look:** each is a single ASCII glyph (`*`, or `.` for distant ones) in warm yellow-green, with a soft
  CSS `text-shadow` glow.
- **Pulse:** each has its own CSS blink loop (period 1.6–3.6 s, random delay, peak brightness 0.6–1.0).
  Their blinks never sync.
- **Movement:** Python updates each one's position every frame as a smooth path:
  - its own sum of 2–3 sines per axis, with unrelated frequencies and phases;
  - a slowly breathing distance from the flower, so each sometimes drifts close and then away;
  - its own height range, from grass level up to about 1.5× the flower's height;
  - a small push from `wind()`.
  - There are no jumps, and no two fireflies share a path or loop.
- **Rendering:** each is its own small element moved by a CSS `translate` in pixels, so it moves
  smoothly between character cells. That is about 10 style writes per frame, which is cheap.
- **Depth:** fireflies in "front" (lower on screen) are slightly larger and brighter; those behind the
  flower's line are dimmer.
- **Reduced motion:** they appear at fixed spots and only pulse.
- **Pause:** they freeze.

## Interface (`site/fireflies.py`, pure)
```python
def position(i, t, centre, radius):    # -> (x, y) in px for firefly i at stage time t
```

## Testing
`tests/test_fireflies.py`:
- positions stay inside the allowed region over a long time span;
- the speed between consecutive frames is below a cap (no jumps);
- different `i` give different paths;
- each firefly's distance to the flower varies (both near and far happen within a minute).

## Success criteria
1. After bloom, fireflies appear gradually (not all at once) and drift calmly; over 30 s their blinking
   is never in unison and each one's path looks different.
2. The flower remains the brightest, central element (screenshot check).
3. Fireflies add no more than 1 ms of Python per frame (in-page timing).
