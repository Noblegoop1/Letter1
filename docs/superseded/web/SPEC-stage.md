> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Spec: `stage` — loop, phases and layers

Status: **APPROVED 2026-10-31.** Module of `CAPABILITY-MAP.md` (Part 2). Commands, code style and
general boundaries are unchanged from `SPEC.md` (Part 1) and `CLAUDE.md`.

## Objective
One place that decides *what is happening now*, so every later module only draws. Today `main.py` mixes
the loop, a two-state machine and DOM writes. Part 2 has seven phases, timed handoffs between them and
two user events; without a single owner, double clicks or overlapping transitions become likely.

## Design
- **Phases, in order:** `letter` → `reveal` → `night` → `seed` → `grown` → `bloom` → `bloomed`.
  - Events: `yes` (accepted only in `letter`), `flower` (accepted only in `grown`). Everything else is
    ignored, so repeated or late clicks can't start anything twice.
  - Timed phases end on their own: `reveal`, `night`, `seed` and `bloom` each have a fixed duration
    from a `DURATIONS` table.
- **One clock.** The stage clock is the `requestAnimationFrame` time minus paused time. **Pause** freezes
  the clock (so all choreography and ambient motion stop together) and sets `body.paused`, which pauses
  CSS keyframe loops with `animation-play-state`.
- **Layers.** Each visual is its own element, stacked by CSS, and Python writes only the layers that
  changed. `body[data-phase]` tells CSS which layers are visible and fades them.
- **Reduced motion.** Each timed phase plays a short crossfade (≤ 0.4 s) instead of its full animation.
  Ambient loops (float, wind, drift) are off.
- **Who moves what:** Python sets characters and per-frame transforms; CSS keyframes are used only for
  small endless loops (glow breathing, firefly blink).
- **Frame budget (measured in-page under MicroPython, desktop):** average Python work per frame
  ≤ 8 ms in every phase.

## Interface (pure, `site/stage.py`)
```python
PHASES = ("letter", "reveal", "night", "seed", "grown", "bloom", "bloomed")
DURATIONS = {"reveal": 4.5, "night": 3.0, "seed": 5.0, "bloom": 2.5}   # seconds, tuned in build

def step(phase, since, t, event=None):
    """-> (phase, since): handle an event or a timed handoff at stage time t."""

def progress(phase, since, t):
    """0..1 through a timed phase (1 for open-ended phases)."""
```
Easing helpers move here from `art.py` (`ease`, plus `ease_out`, `smoothstep`, `lerp`, `clamp`).
`main.py` keeps the DOM glue: it reads `step`/`progress` and calls each module's draw function.

## Testing
`tests/test_stage.py`: every event is ignored outside its phase; each timed phase hands off exactly at
its duration; a double `yes` changes nothing; progress is clamped to 0..1.

## Success criteria
1. Clicking YES five times quickly starts the reveal once; clicking the flower before it is `grown`
   does nothing.
2. Pause freezes everything on screen, including mid-transition, and resuming continues from the same frame.
3. With reduced motion, the whole journey from YES to the bloomed garden plays with only short fades.
4. Every Part 1 test still passes after the refactor.

## Boundaries
- Always: keep `stage.py` pure and MicroPython-safe.
- Never: start a transition from anywhere but `step`.
