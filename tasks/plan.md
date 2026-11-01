# Implementation Plan: "To Esther" desktop app

Spec: `SPEC.md` v3 (approved 2026-10-31). Modules: `CAPABILITY-MAP.md`. Stack: `docs/adr/0001-desktop-stack.md`.
Progress (2026-11-01): gates G1–G5 built and tested; G6 release in progress (`tasks/todo.md`).

## Approach
- **Gates in order (SPEC §19).** Each gate ends with unit tests, the headless self-test and screenshots
  read by eye. The NO route starts only after G4.
- **The engine comes first:** viewport, clock, glyphs, assets and state machine. Scenes are added onto
  that shared base so both routes reuse it.
- **Parallel work** happens only on pure modules with a fixed interface, each in its own files:
  - the flower and ground pointillism, and the fireflies, in G3;
  - the chase game core, in G5.

  Integration and every scene file stay in this session.
- **Night canvas contract** (shared by the night, flower and firefly code): a NumPy `float32` array of
  shape `(640, 640, 3)`, indexed `[y, x]`, display RGB (no gamma), usually in 0..1. It is clipped once when
  presented. The ground line is at `y = GROUND_Y` (500) and the flower root at `(320, GROUND_Y)`.
- **Reused from the web version:**
  - the `stage.py` core (phases, clock, easing, hash, Bayer) becomes `letter/engine/timeline.py`;
  - the button big letters, hover ripple and heart sprite move to `letter/art/`;
  - the Bayer dissolve idea and the `wind()` shape carry over.

## Risks
| Risk | Mitigation |
|---|---|
| The night scene misses 60 fps | Budgets per part (SPEC §15); quality tiers; glow at half rate; moderngl only with approval |
| Fonts blur when scaled | Render text at physical size (scale-aware atlas), never upscale text surfaces |
| PyInstaller misses data files or the DLL path | `assets.py` resolves through `sys._MEIPASS`; frozen `--selftest` run from a copy outside the repo |
| The flower doesn't match the reference | Screenshot side by side with the user's reference image; tune palettes and densities |
| SmartScreen or antivirus on the unsigned exe | `--onedir`; document "More info → Run anyway" |
