# Implementation Plan: ASCII Love Letter — Part 1

## Overview
Build the opening scene from `SPEC.md` (approved with defaults on 2026-10-31): massive ASCII headline,
ASCII envelope with a heart seal, two churning YES/NO buttons in front, YES opens the flap in characters
and slides the envelope away, NO shakes. Static site in `site/`, Python via PyScript/MicroPython.

## Architecture Decisions
- `site/art.py` is pure: every function returns `(chars, cls)` — two lists of equal-width strings, the
  characters and a per-cell colour class. `to_html` turns that into `<span>` runs. Tested in CPython.
- `site/main.py` owns the DOM and one `requestAnimationFrame` loop; it only writes a `<pre>` when its
  HTML changed.
- Sizes live in `art.py` constants; `main.py` copies them into CSS variables so CSS can scale each
  `<pre>` to the viewport (cols × measured char ratio) without Python on resize.
- Two headline layouts (one line wide, two lines for portrait) switched by a CSS media query.
- Flap: drawn per frame with a general line rasteriser (`` `-. `` / `.-'` runs), heart seal rides on
  the flap tip and hides past 90°. Slide-away and fades are CSS transitions.
- Deploy: GitHub Actions uploads `site/` only, so `reference/`, docs and research never ship.

## Task List
See `tasks/todo.md`.

## Risks and Mitigations
| Risk | Impact | Mitigation |
|---|---|---|
| CPython-tested code fails under MicroPython | High | Build the browser shell first and smoke-test `art.py` in PyScript before polishing art |
| Font cell ratio differs per OS (Consolas 0.55 vs Menlo 0.60) | Med | CSS default 0.62 so nothing overflows before Python measures |
| Hand-drawn art drifts out of shape | Low | Tests: rectangular rows, ASCII-only, mirror symmetry |
| PyScript startup leaves a blank screen | Med | Measure; if slow, show an ASCII loading line in the HTML |
