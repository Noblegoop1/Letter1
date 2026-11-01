# ADR 0001 — Desktop stack: Python + pygame-ce + NumPy, packaged with PyInstaller

Status: **Accepted (2026-10-31).**
Supersedes: the web architecture (PyScript/MicroPython in a browser, GitHub Pages), see
`docs/superseded/web/`.

## Context
The project is now a standalone Windows desktop application. Someone downloads a folder, double-clicks
an `.exe`, and plays, with no browser, server, Python, Node or Godot install. The experience needs:
- a pointillist flower of ~30,000 moving particles at a 640 × 640 logical resolution;
- ASCII glyph effects (hover scrambles, dissolves, a heart shattering, a glitch);
- a 320 × 320 ASCII side-scroller with jump physics;
- smooth 60 fps animation.

The flower reference (iremcnar/Flowers, `flow.py`) is Python + NumPy + Pillow + Tk. All the existing
project code is pure Python.

## Options compared

| Area | Python + pygame-ce + NumPy | Godot 4 | Electron | Tauri |
|---|---|---|---|---|
| Rendering (particles, glow, dither, ASCII) | CPU NumPy splats + SDL blits; measured below | best: GPU particles, shaders | Canvas/WebGL, fast in JS | same as Electron, in WebView2 |
| Animation, transitions | own timeline (exists: `stage.py`) | built-in AnimationPlayer | JS / CSS | JS / CSS |
| Input (mouse, proximity, keys) | SDL events, simple | excellent | DOM events | DOM events |
| Performance with thousands of elements | measured OK (below); GPU fallback possible | excellent | good in JS; our Python runs in MicroPython, measured 10–25x slower | same as Electron |
| Windows desktop app | yes (SDL window) | yes | yes | yes |
| Packaging | PyInstaller `--onedir`: portable folder, ~60–80 MB | one-click export, ~70 MB | ~150 MB+ (bundles Chromium) | ~10 MB, needs WebView2 (built into Windows 11) |
| Maintainability for this repo | one language, existing modules and tests reused | full rewrite in GDScript/shaders | Python logic must be rewritten in JS to be fast | same as Electron |
| Existing code kept | `stage.py`, button/heart/ripple art, dissolve logic, wind, 83 tests | none | the DOM shell, but the Python is too slow there | same |
| Offline | yes | yes | yes | yes |
| Flower reference reuse | same language and libraries (NumPy), techniques port directly | port to GDScript/shaders | port to JS | port to JS |

## Measurements (this PC, CPython 3.14, NumPy 2.5.4, pygame-ce 2.5.8, 2026-10-31)
Spike scripts lived in the session scratchpad and are not part of the project.

| Workload | ms per frame |
|---|---|
| 32,000 moving particles, 5-px stamp, depth order sorted once, splat into 640 × 640 | 3.24 |
| 12,000 moving particles, same | 1.17 |
| Naive splat: 35,000 particles, argsort every frame, 13-px discs | 20.7 (avoid) |
| 640² NumPy canvas → surface → smoothscale to 800 → blit | 3.06 |
| Glow: downscale, gaussian blur, upscale, additive blend | 8.36 (cut by blurring smaller or every other frame) |
| 160 × 50 ASCII grid from a cached glyph atlas (8,000 blits via `fblits`) | 3.99 |

Windows wheels exist for Python 3.14: pygame-ce 2.5.8, numpy 2.5.4, pyinstaller 6.22.3 (checked with
`pip download --only-binary`).

## Decision
**Python 3.14 + pygame-ce + NumPy for the app, PyInstaller 6 (`--onedir --windowed`) for the release.**
- **Language:** this keeps one language. The tested pure modules (`stage.py`, button/heart/ripple art,
  dissolve thresholds, wind) carry over, and the flower techniques port 1:1 because they are already
  NumPy.
- **Speed:** CPython is 10–25x faster than the MicroPython that was holding the web version back.
- **Release:** a portable folder: `LetterToEsther.exe` plus `_internal/` (Python runtime, NumPy, SDL,
  fonts). It is zipped for sending. No installer is needed. An installer (Inno Setup) can be added later
  as an extra.
- **Fallback:** if the flower plus glow can't hold 60 fps on modest hardware, move only the particle
  renderer to the GPU through `moderngl`, which renders into the same pygame window. Everything else
  stays. Adding that dependency needs approval first.

### Rejected, and why
- **Godot:** it is the strongest engine, but it means rewriting everything, flower included, in a
  second language, and dropping the working code and tests. Its advantage would only matter if the CPU
  budget fails, and the GPU fallback above covers that case.
- **Electron/Tauri:** the existing web renderer runs Python in MicroPython, which is too slow. Being fast
  would mean a JavaScript rewrite, the same cost as Godot without the engine. Electron also adds about
  150 MB.

## Consequences
- **Kept:** `stage.py` (phases, clock, easing, hash, Bayer), the button big-letter art and hover ripple,
  the heart seal sprite, the dissolve threshold logic and `wind()`, and their tests.
- **Adapted:** the timeline, which gets new phases for both routes and a speed setting. Input moves from
  DOM events to SDL events. All drawing moves from `<pre>` HTML to surfaces.
- **Rewritten:** the ASCII envelope, banner and dissolve are re-rendered with a glyph atlas instead of HTML. The flower becomes a NumPy
  pointillist renderer. The meadow changes from ASCII cells to drawn blades. Fireflies change to a
  waypoint system. The No route, chase game and ending are new.
- **Retired:**
  - The `site/` web app moves to `legacy/web/` as read-only history.
  - The GitHub Pages workflow is removed.
  - `index.html`, CSS, `pyscript.toml` and `main.py`'s DOM code are not used.
- **Release risk:** unsigned PyInstaller executables can trigger Windows SmartScreen ("unknown
  publisher") and occasionally antivirus false positives. Mitigations:
  - `--onedir` rather than `--onefile`, which reduces false positives;
  - documented "More info → Run anyway" steps for the recipient;
  - code signing is optional and costs money.
- **Licences shipped** in `THIRD_PARTY_NOTICES.md` inside the release folder:
  - pygame-ce (LGPL-2.1, dynamically linked DLLs in the folder);
  - SDL (zlib), NumPy (BSD-3);
  - PyInstaller bootloader (GPL with a bundling exception);
  - bundled fonts (SIL OFL).
