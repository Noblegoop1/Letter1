> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Implementation Plan: Part 2 — letter to night garden

Specs: `CAPABILITY-MAP.md` + `SPEC-<id>.md` (all approved 2026-10-31). Part 1 (`SPEC.md`) is done.

## Architecture Decisions
- **Pure modules, one per capability:**
  - `stage.py`: phases, clock, easing, hash, Bayer.
  - `art.py`: letter, headline, buttons.
  - `reveal.py`, `night.py`, `flower.py`, `fireflies.py`.
  - All return `(chars, cls)` frames or numbers and are tested in CPython.
  - Only `main.py` touches the DOM.
- **Layers:** one element per visual. CSS colour classes are **scoped by layer id** (`#ground .a`), so
  modules can't collide. Each scene module ships its own stylesheet (`night.css`, `flower.css`,
  `fireflies.css`).
- **Movement:**
  - Python sets characters and per-frame transforms (zoom, sheet rise, seed, fireflies, sway).
  - CSS keyframes only for endless ambient loops (float, breathing, blink), paused with `body.paused`.
- **Opaque cells** (ANSI-style backgrounds) on the envelope body, the sheet and the writing, so the
  sheet can rise from behind the envelope.
- **Envelope in three layers:** back (lining + flap once past 90°), sheet, then front (body, side
  flaps, flap while closed, seal). The writing is a small overlay redrawn alone while it dissolves.
- **Night grid:** sized from the viewport (font 10–16 px). The flower uses the same cell size so it
  sits on the grass grid.

## Parallel work
`night.py`, `flower.py` and `fireflies.py` (+ their tests and CSS) are independent and written by agents
against their spec interfaces, importing only `stage.py`. Everything else, including integration, is done
in this session.

## Risks
| Risk | Mitigation |
|---|---|
| MicroPython ~10x slower than CPython | Each module states a CPython time budget; measure in-page; cache static layers |
| Zoom looks blurry or jumps | Scale origin measured at zoom start; the black inside matches the page background |
| Agent modules differ in look | Shared palette notes in briefs; visual pass and tuning at integration |
