# Spec: "To Esther" — an interactive letter, as a Windows desktop app

Status: **APPROVED v3 (2026-10-31), defaults taken for Q1–Q5. Built through G5 (2026-11-01); G6 release in progress.** Later user changes the same day: the letter world
stays ASCII (envelope, paper, questions, all text); the question banner becomes shaded ASCII lettering; the
envelope tilts visibly and the banner and buttons hover; the flower becomes a sea holly in the user's blue gradients (an ocean glow under the moon); clouds
and a moon fill the night sky as the flower blooms; the fireflies get a richer pass (§9, §10). This is the
single authoritative spec. It replaces
the web-era specs (Part 1 `SPEC.md`, the Part 2 `CAPABILITY-MAP.md` and its `SPEC-<id>.md` files), which
now live in `docs/superseded/web/` for history only. The module index and build gates are in
`CAPABILITY-MAP.md`; the stack decision is `docs/adr/0001-desktop-stack.md`.

---

## 0. What changed, and what carries over

| Topic | Before (web, superseded) | Now (authoritative) |
|---|---|---|
| Runtime | PyScript/MicroPython in a browser, GitHub Pages | Python 3.14 + pygame-ce + NumPy desktop app, PyInstaller portable folder |
| Visual rule | "Every visual is ASCII" | Still ASCII for the envelope, paper, dedication, questions, all text, buttons, effects, dissolves, heart shatter, chase game, glitch and face (user decision, 2026-10-31). The night flower, meadow and fireflies are pointillist particle dots; an optional ASCII rendering of the flower can come later. |
| Envelope writing | `RAHHH` / `SHE OPENED IT` | **To Esther** (fades in on launch) |
| Flower | ASCII placeholder (`site/flower.py`) | Pointillist particle flower after iremcnar/Flowers at 640 × 640 logical (see §10 and open question Q1) |
| Fireflies | 10 fireflies orbiting the flower | 30–60 detailed fireflies travelling the whole night scene; they rise out of the grass, some pass behind it, a few drift close as soft out-of-focus lights |
| Question banner | Pixel-font letters of `#` and `/` | Shaded ASCII lettering: a real typeface cut into cells, each cell the best-fitting mark, lit from the top left, with an extruded side (§9) |
| Flower | Purple and pink pointillist lotus (later in "sunrise" colours) | A pointillist sea holly in the user's blue gradients, glowing like the ocean under the moon (§10.4) |
| Night sky | A static gradient | Stars from the start; as the flower blooms, soft moonlit clouds gather and the moon slowly appears (§10.6) |
| Pace | 10–24 Hz redraws, 4.5 s reveal | 60 fps; durations tuned by one `SPEED` setting (§13) |
| No button | Shakes, letters go wild | A full alternate route: questions, earthquake, swap, heart shatter, chase game, ending (§15–§18) |
| Pause button | On screen | Removed (not part of the game look); the clock pauses itself when the window loses focus |

**Carries over:**
- the phase/clock/easing/hash/Bayer core (`stage.py`);
- the envelope geometry, ideas and heart seal sprite;
- the button big-letter art and hover ripple;
- the dissolve-by-threshold technique and the wind field;
- the yes-route choreography (dissolve → flap → sheet → zoom → night → seed → grow → bloom → fireflies);
- the existing unit tests for those parts.

---

## 1. Objective
A small, polished interactive piece for one person, Esther. It is sent as a downloadable app, and feels
like a tiny indie game rather than a web page:
1. A floating, lamp-lit envelope reads **To Esther**, and asks **"Will you open?"** with YES and NO.
2. **YES**:
   1. the writing crumbles and a sheet slides out;
   2. the view dives into the sheet, which becomes a night meadow;
   3. a seed falls and a pointillist flower grows;
   4. clicking the flower blooms it;
   5. fireflies fill the night.
3. **NO** is a hidden route of escalating refusals:
   1. the letter shakes;
   2. the buttons swap;
   3. the heart shatters;
   4. the NO button escapes into an ASCII chase game;
   5. when caught, the world glitches apart, leaving a face that sheds one tear before going black for
      good.

**Recipient experience:** download a zip, extract it, double-click `LetterToEsther.exe`. The experience
starts at once, offline, with nothing else installed.

## 2. Assumptions (correct any of these)
- **A1 Stack:** Python 3.14 + pygame-ce + NumPy, released with PyInstaller `--onedir --windowed` as a
  portable folder (ADR 0001). New dependencies: `pygame-ce`, `numpy` (runtime) and `pyinstaller` (build
  only).
- **A2 Art direction (user decision, 2026-10-31):** the letter world stays ASCII:
  - the envelope and paper are grids of glyphs, with lighting from per-cell glyph colour and per-cell
    background colour (ANSI style);
  - the dedication, every question and all on-screen text are glyphs (the questions are big italic
    pixel-letter banners made of characters);
  - buttons, dissolves, the heart seal and shatter, the chase game, the glitch and the face are glyphs.

  The night scene's flower, soil, grass and fireflies are pointillist particle dots, following the
  reference. An ASCII rendering mode for the flower (brightness → `. : + * @`) is allowed if it keeps
  the look, as an option rather than the default.
- **A3 Flower code:** iremcnar/Flowers has **no licence**, so its code may not be shipped (Q1). Until the
  author grants permission, the flower is a **clean re-implementation of the same techniques**. These
  are documented in `docs/flowers.md` and are standard maths:
  - Catmull-Rom keyframes;
  - Bézier stem;
  - sinc-arc petals;
  - layered palettes;
  - a depth-ordered splat;
  - halo, rings and sparks.

  It is matched visually to the reference image, and nothing is copied from `flow.py`. With permission
  it becomes an adaptation of the original, with attribution.
- **A4 Pace:**
  - "about 3x faster" means everything renders at 60 fps in real time instead of the web's 10–24 Hz
    redraws and the reference's 12 fps GIF;
  - durations live in one timing table with a global `SPEED` setting;
  - the reference's 45 s lifecycle becomes about 6 s of growth plus about 2 s of bloom, with no wilting.
- **A5 Window:**
  - opens at 80% of the screen height with a 16:10 shape, resizable;
  - `F11` or `Alt+Enter` toggles fullscreen and `Esc` leaves fullscreen;
  - no menus or toolbars;
  - closing the window quits;
  - each launch starts fresh.
- **A6 Night scene shape:**
  - the night and flower scene is a 640 × 640 square, scaled to the window height and centred;
  - the side bars are the same night colour, and the grass and soil fade out at the square's edges, so
    it doesn't look boxed;
  - fireflies roam the whole square.
- **A7 Fonts:** one bundled SIL-OFL monospace family, JetBrains Mono (regular, bold, italic), with its
  licence file. It draws every glyph. It was downloaded once at development time into `assets/fonts/`.
- **A8 Sound:** none in this version.
- **A9 Web version:** `site/` moves to `legacy/web/` unchanged, and `.github/workflows/pages.yml` is
  deleted. Nothing in `legacy/` ships.
- **A10 Commits:** none until you ask.
- **A11 Reduced motion:** if Windows "Show animations" is off, the ambient float and sway are calmer,
  the earthquake and glitch are gentler, and there are no flashes. The story itself and the game still
  play.

## 3. Tech stack
- **Runtime:** CPython 3.14 (x64), pygame-ce 2.5.x (SDL 2), NumPy 2.5.x. Versions are pinned in
  `requirements.txt`.
- **Build:** PyInstaller 6.22.x, in `requirements-dev.txt`.
- **Tests:** stdlib `unittest`, plus headless pygame (`SDL_VIDEODRIVER=dummy`) for render and scenario
  tests.
- No network access at runtime, ever.

## 4. Commands (run from the project root in PowerShell or Git Bash)
```
py -m venv .venv                                   # once
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m letter                     # run the app (development)
.venv\Scripts\python -m letter --scene yes-night   # jump straight to a scene while developing
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m letter --selftest          # scripted run of both routes, headless, exit code 0/1
.venv\Scripts\python tools\shots.py                # render reference screenshots to build\shots\ for review
.venv\Scripts\python tools\build.py                # PyInstaller release -> dist\LetterToEsther\ + zip
.venv\Scripts\python tools\build.py --clean        # remove build\ and dist\
```

## 5. Project structure
```
letter/                 the application package (python -m letter)
  __main__.py           entry: DPI awareness, window, main loop, CLI flags
  config.py             SPEED, timing table, quality (particle counts), colours
  engine/
    viewport.py         logical canvases -> window: scale, letterbox, inverse for input (one transform)
    clock.py            stage clock (from stage.py): pause on focus loss, fixed step for physics
    glyphs.py           monospace glyph atlas, ASCII grid drawing, text effects
    particles.py        NumPy splat, glow, dither helpers
    timeline.py         phases, events, guards (from stage.py)
    assets.py           finds bundled files both from source and from the PyInstaller folder
  scenes/
    letter.py           envelope, dedication, question, buttons (shared by both routes)
    yes_reveal.py       dissolve, sheet, zoom
    night.py            lighting shift, soil, grass, wind, seed
    flower.py           pointillist flower (the swap point)
    fireflies.py        waypoint fireflies
    no_route.py         questions, earthquake, swap, heart shatter, escape
    chase.py            320 x 320 ASCII runner
    ending.py           cornered button, glitch, face, tear, black
  art/                  pure geometry/text helpers kept from the web version (buttons, heart, dissolve)
assets/fonts/           bundled OFL fonts + their licence files
tools/                  build.py, shots.py, make_icon.py
tests/                  unit tests (pure logic) + headless scene/scenario tests
docs/                   adr/, flowers.md, loveyou.md, neonbutterfly.md, superseded/web/
legacy/web/             the retired web app (not shipped)
SPEC.md  CAPABILITY-MAP.md  README.md  CLAUDE.md  THIRD_PARTY_NOTICES.md
```

## 6. Code style
- Small, flat modules.
- Pure functions for geometry, timing and text (unit-tested). Scenes own their state and expose
  `update(dt, input)` and `draw(surface, viewport)`.
- Time-based everything: no motion depends on the frame count.
- Comments explain only the "why".

```python
def hover_label(label, e, rng_seed):
    """Per-character scramble that settles left-to-right-ish; width never changes."""
    out = []
    for i, ch in enumerate(label):
        settle = 0.12 + 0.05 * i + 0.04 * (hash32(i, rng_seed) % 5)
        out.append(ch if e >= settle else LOOKALIKE[ch][hash32(i, int(e * 30)) % len(LOOKALIKE[ch])])
    return "".join(out)
```

---

## 7. Rendering architecture
- **Logical canvases:**
  - letter scene: 1280 × 800 (16:10);
  - night and flower scene: 640 × 640;
  - chase game: 320 × 320.

  The physical window size is independent of all three.
- **Viewport:** one transform per scene, `scale = min(W/lw, H/lh)`, centred with bars filled in the
  scene's background colour. Drawing and input use **the same transform**, so mouse coordinates are
  mapped back to logical space before any hit test.
- **Sharpness:**
  - **Letter scene:** drawn directly at the physical scale. Fonts are re-rendered at `size × scale` and
    the glyph atlas is rebuilt on resize, so text never blurs.
  - **Flower scene:** the particle canvas is exactly 640 × 640 as required, smooth-scaled to the
    window.
  - **Chase:** 320 × 320, scaled up with nearest-neighbour for crisp glyph pixels.
- **ASCII:** a cached glyph atlas, one surface per (character, colour), drawn in batches with
  `Surface.fblits`. One character is a deliberate cell: about 10 × 20 logical px in the letter scene and
  6 × 12 in the chase game.
- **Particles:** NumPy arrays built once (geometry, colour, depth order). Each frame computes positions
  in a vectorised way and splats into a reused canvas with a 1–5 px stamp, in painter's order sorted
  once.
- **Glow:** downscale, blur, upscale, then additive blending, at a reduced rate when needed.
- **Dithering:** a 4 × 4 Bayer threshold per cell or pixel (`bayer()`).
- **Camera:** zooms are a scale about a measured origin. They are computed so the target region covers
  the viewport, keeping its aspect ratio.
- **DPI:**
  - the app is per-monitor DPI aware (`SetProcessDpiAwareness(2)` before the window opens), so Windows
    never bitmap-stretches it;
  - all sizes come from the viewport.

## 8. Scene, state and input architecture
- **App:**
  - owns the window, the main loop (vsync, 60 fps target), the viewport, the stage clock and the active
    scene;
  - pauses the clock when the window is minimised or loses focus.
- **Narrative state machine** (pure, unit-tested). The phases are:

  ```
  intro → letter
      YES route: yes-reveal → night → seed → grown → bloom → bloomed
      NO route:  no-1 → no-2 → no-3 → no-4 (shatter, message, auto-open, escape) → chase-a → chase-b → chase-c → cornered → glitch → face → black
  ```

  - **Events:** `yes`, `no`, `flower`, `catch`.
  - **Gating:** each event counts only in the phases that accept it, and only when input is unlocked.
  - **Commitment:** `yes` from any letter phase (letter, no-1, no-2, no-3) commits to the YES route.
    From no-4 onward the NO route is committed and YES is gone.
  - **Single runner:** timed phases hand off on their own, and only one transition can run.
- **Input:** SDL events become logical coordinates through the scene's viewport. They are routed to the
  active scene only.
  - Clicks during locked phases are dropped.
  - Space is used only by the chase game.
  - Keyboard alternatives:
    - `←`/`→` focus YES/NO and `Enter` presses;
    - `Enter` wakes the flower once it is grown;
    - `Enter` catches the cornered button.
- **Shared systems:** text dissolve, paper movement, camera zoom, particles and glyph effects are
  shared by both routes. The flower and the chase game are separate and never run in the other route.

---

## 9. Letter scene (`letter`) — both routes start here
**Layout (1280 × 800 logical):**
- the dedication "To Esther" is written on the envelope's lower flap;
- the question sits above the envelope;
- YES and NO sit below it.

**Envelope (an ASCII grid, about 67 × 27 cells plus flap headroom; ported from the web version):**
- Outlines:
  - `.---.` edges and `|` sides;
  - the X folds drawn with `` `-. `` and `.-'` runs, meeting at the centre;
  - the inside of the pocket shown as a lined pattern.
- Every body cell is opaque (it has a background colour), so the sheet can hide behind it.
- **Lit from directly above:**
  - each cell's glyph colour and background colour come from a continuous light function: bright top
    edge, gradual falloff downward, darker toward the edges like ambient occlusion;
  - per-flap shading: the top flap catches the most light, the side flaps tuck under;
  - a soft ASCII drop shadow (`.:` rows) sits under the envelope.
- **Paper texture:** sparse grain glyphs (`.` `'` `,`) with slight per-cell colour variation, subtle
  enough that the writing stays readable.
- **Heart seal:** the hand-drawn ASCII heart from the web version, drawn in red glyphs on the flap tip
  with a faint warm glow, integrated like a wax seal. Its glyph cells are kept as separable fragments
  for the NO-route shatter.
- **Float:** gentle vertical drift (about ±7 px), a slight but visible tilt (up to about ±1.1°) and a slow
  wobble. It is the sum of 2–3 slow sines with unrelated periods, so it never visibly loops. The drop
  shadow tracks the height. Everything on the letter hovers: the banner drifts and waves, and each button
  bobs gently on its own phase (visual only, within ±3 logical px; hitboxes stay fixed).

**Dedication "To Esther":**
- On launch the scene fades up from black (0.6 s).
- "To Esther" is written in ASCII on the envelope's bottom flap: italic monospace glyphs in an ink
  colour, larger than the grain.
- It fades in gently after a short delay (ease-out over 1.2 s, with a 2–3 px rise). It replaces
  `RAHHH`/`SHE OPENED IT` everywhere.

**Question "Will you open?" (an ASCII banner):**
- Big lettering built from glyphs: the question is set in the bundled JetBrains Mono Bold, slanted and a
  little heavier, then cut into character cells. Each cell takes the ASCII mark whose shape best matches
  the ink under it, so outlines come out as `/ \ ( ) | _ '` and the like.
- Shaded: inside the strokes a bevel light from the top left picks heavy marks (`@ % #`) where lit and
  lighter ones (`* +`) in shade; colour runs from pale rose-white at the top of each line to deep rose,
  with a near-white sheen on the lit edges.
- Depth: a sparse extruded side (`. : / _`) down and to the right in dark wine, a soft blurred shadow and
  glow, and a small `~-.,_,.-~ <3 ~-.,_,.-~` vine underneath.
- Alive: it appears with a gentle rise and fade, then hovers slowly and waves column by column (about
  2 px, a few seconds per cycle); small `+` glints flare and fade on its lit strokes.
- Other question texts (NO route) use the identical treatment and crossfade in place. A question that
  would be set too small on one line wraps onto two; smaller lettering uses smaller marks, so detail
  stays about the same.

**Buttons (`buttons`):**
- Keep the current identity: ASCII-framed `.----.` boxes with big block-letter words; YES in rose
  (#ff86ad), NO in lavender (#b4b0d6).
- **Identity is not position:** two slots (left and right) and two buttons. A button keeps its colour,
  label and action wherever it sits.
- **Hitbox:** a fixed rectangle per slot, the button's rest rectangle. Hover animation moves only the
  visual layer, at most ±3 logical px inside that rectangle. The hitbox moves only when the button
  itself moves (the swap, the escape).
- **Idle:** a very faint breathing of the frame glow.
- **Hover:**
  1. the frame brightens;
  2. the visual drifts a couple of px;
  3. the letters run the ASCII character shift: each glyph cycles through look-alikes (for example
     `Y#S`, `7E$`, `Y3S`) at about 30 Hz, each character settling at its own moment within 0.6 s, then
     the label is exactly `YES` again.
  4. The width never changes. Leaving the button lets the current shift finish and settle.

**Acceptance (letter):**
- L1: "To Esther" fades in on launch and the old text appears nowhere.
- L2: top-down shading and the drop shadow are visible in a screenshot.
- L3: the envelope floats and tilts without visible looping within 60 s.
- L4: the question is an ASCII banner with gradient and shadow, readable at 1280 × 800 and at 640 × 400
  windows. Every NO-route question can be rendered.
- L5: hitboxes are identical before, during and after hover (automated test).
- L6: hover shifts characters and always settles back to the exact label.
- L7: colours are YES #ff86ad and NO #b4b0d6.

---

## 10. YES route (`yes-reveal`, `night`, `flower`, `fireflies`)
YES locks both buttons immediately. Repeated clicks, NO, and hover effects do nothing from then on.

### 10.1 Reveal (about 3.0 s)
1. **Writing dissolves (0.0–1.0 s):** "To Esther" breaks into small glyph and pixel fragments. They are
   sampled from the rendered text and released in a Bayer-ordered pattern. Each drifts up and sideways
   a little and fades. Paper stays visible underneath. It is never a plain opacity fade.
2. **Flap opens (0.1–0.9 s):** the top flap folds up and back, foreshortened, with its shading changing
   as it turns.
3. **Sheet emerges (0.4–1.6 s):**
   - a second ASCII sheet slides up out of the pocket with an ease-out. It has a cream paper border
     (lit from above, grain glyphs) around an empty dark window; the window becomes the night;
   - it tilts very slightly, and its cast shadow lengthens as it lifts;
   - it starts as the writing is half gone, so the two read as cause and effect;
   - the open flap stays behind it and the envelope front in front of it.
4. **Zoom (1.5–3.0 s):**
   - the camera dives into the sheet, keeping its aspect ratio;
   - the scale is computed so the sheet's face covers the window;
   - it is an even-feeling exponential zoom with easing and no cut: once the window's dark covers the
     screen, the night begins.

### 10.2 Night (`night`, about 2.0 s, then ongoing)
- **Lighting shift:** the paper's top-down light fades away and the surface darkens toward deep blue,
  muted green and near-black. A dim ambient light remains.
- **Ground:**
  - the lower part of the paper dithers away (Bayer, bottom first) into soil;
  - the soil is fine particles with slight irregularity, depth shading and colour variation, generated
    once and cached;
  - grass blades appear gradually from the dissolving surface.
- **Grass:** hundreds of blades drawn as tapered polylines, each with its own height, stiffness and
  phase.
  - The wind field is `wind(x, t)`: travelling gusts whose strength and direction drift slowly. It is
    shared with the flower and fireflies.
  - Blades bend with smooth spring-like lag and are never in lockstep.
- **Scene shape:** 640 × 640 logical, centred, with side bars in the same night colour and grass and
  soil fading at the edges (A6).

### 10.3 Seed and growth (`night` seed, `flower`, about 6.5 s)
1. A 0.4 s pause after the ground settles.
2. A small glowing seed falls with ease-in "weight" and a hint of wind drift (0.8 s).
3. It lands with a tiny soil puff (4–8 particles) and a short dip (0.3 s).
4. A 0.5 s pause, then growth (about 4.5 s):
   1. the stem emerges and rises with organic curvature;
   2. leaves unfurl in sequence, each slightly different;
   3. the head forms and settles into a **closed, drooping bud**.
5. The bud's faint cool cyan glow pulses gently and spills very faintly onto nearby grass and soil.
6. The bud waits for a click. It never blooms on its own.

### 10.4 The flower (`flower`), a sea holly, 640 × 640 logical
- **What (user change, 2026-10-31):** a sea holly (*Eryngium*) replaces the earlier pointillist lotus
  (kept for reference in `legacy/desktop/lotus_flower.py`). References: the user's photos in
  `reference/sea-holly/` (not shipped). The pointillist *technique* still follows iremcnar/Flowers
  (`docs/flowers.md`; licence: A3 and Q1); no code from it is used.
- **Shape:** an egg- or cone-shaped head, taller than wide, densely packed with tiny florets in spiral
  rows; beneath it a star-shaped ruff of long, narrow, sharply pointed bracts with spiny edges; a tall
  ribbed stem; deeply lobed, spiny leaves. One or two small side heads may sit on side branches, the main
  head staying the focal point.
- **Colours (the user's blue gradient set, `reference/sea-holly/blue-gradients.png`): an ocean glow under
  the moonlight:** a luminous cyan-to-royal-blue cone with silvery moonlit highlight specks, deepening to
  indigo at its base; violet-periwinkle bracts with a silver-blue sheen on their edges; an indigo stem;
  teal-blue silvery leaves; a soft cyan-violet glow around the head. The light it spills on the grass and
  soil is cool cyan.
- **Particles:** generated once from a fixed seed; positions computed per frame from the animation state
  and splatted depth-ordered into 640 × 640. Budget: about 30,000 animated particles, scaled by quality.
- **Rendering:** pointillist dots are the main look.
- **Bloom (click on the bud, or Enter; about 2.0 s):**
  - the drooping bud (a small cone with its bracts folded up around it) lifts upright;
  - the bracts open outward into the star, each on its own staggered window, with no pop;
  - the cone swells a little and its florets light up in a wave climbing from base to tip; the glow
    rises;
  - it stays open. No wilt. Bloomed, the florets shimmer gently.
- **Composition:** the open head is centred near (320, 230) and the plant stays clear of the moon (upper
  right).
- **Motion:**
  - wind sways the stem, head and leaves, with slight phase differences;
  - a pointer lean is added on top: toward the pointer, falling off with distance, smoothed (time
    constant about 0.35 s), capped at about 6°, and easing back when the pointer leaves;
  - wind never stops while the pointer is near.

### 10.5 Fireflies (`fireflies`)
- **Arrival:** after the bloom completes they rise out of the grass over about 6 s, one at a time.
- **Count:** about 40 by default (configurable 20–80 by quality).
- **Each one has:** a bright core, a soft halo, a size and brightness range, its own pulse cycle
  (period 1.2–4 s, varying peak, some slow and soft, some bright), a faint short glow trail and a tiny
  wing flicker.
- **Movement:** waypoints spread over the **whole** 640 × 640 night.
  - Each firefly picks a target, steers toward it with limited acceleration and turn rate, slows
    sometimes, then picks another target. Paths are smooth and never teleport.
  - Some targets are biased near the flower, so a few occasionally drift close and away. Most wander
    elsewhere.
  - There are three depth bands (far: small and dim; mid; near: larger and brighter). The far band is
    drawn behind the grass and the flower, the rest in front.
  - A few large, soft, out-of-focus fireflies drift close to the camera (bokeh), in front of everything.
  - Each firefly also feeds the bloom pass, so it carries a soft wide halo.
  - The wind adds a slight drift.
- The flower stays the brightest focal point.

### 10.6 Sky: stars, clouds and moon (`night`)
- Inspired by the user's moonflower photo (a deep navy sky, a bright full moon with a soft halo, scattered
  stars, a violet glow low on the horizon); the scene is its own, not a copy.
- From the start of the night: the deep blue gradient with faint twinkling stars.
- As the flower blooms, the sky slowly fills over about 10 s: soft, translucent cloud banks gather and
  drift sideways (moonlit rims, darker undersides, thinner toward the horizon), a violet glow rises at
  the horizon, and the moon slowly appears in the upper right, clear of the flower's aura. Clouds pass
  over the moon now and then; gaps always remain.
- Cloud bodies stay dim so the moon and the flower are the bright points; the moon blooms softly.

**Acceptance (YES):**
- Y1: every step 1–18 of the directive's YES test list plays in order, from one click, with no cut or
  stretch at 1280 × 800, 1920 × 1080 and 1366 × 768.
- Y2: the flower canvas is 640 × 640; the sea holly's cone, star of spiny bracts, stem and leaves are
  recognisable next to the user's photos, and its colours come from the user's blue gradients.
- Y3: the bloom starts only on click, and petal timing visibly differs.
- Y4: the pointer lean is ≤ 6°, the wind continues, and the lean returns to rest.
- Y5: the fireflies cover all four quadrants within 30 s, their pulses are never in unison, and the
  flower stays brightest.
- Y6: 60 fps average and no frame over 33 ms on this PC (logged by `--selftest`).
- Y7: the sky is clear (stars only) before the bloom; clouds gather and the moon appears after it, and the
  moon is not hidden behind the flower's aura.

---

## 11. NO route (`no-route`) — implemented only after Gates 1–4 (§19)
Each NO click is accepted only when input is unlocked. During the questions, YES still works and commits
to the YES route.

1. **no-1 "Are You Sure?"**
   - "Will you open?" fades out and "Are You Sure?" fades in, in the same place and treatment.
   - Buttons and hover are unchanged. Moving the mouse never resets the question.
2. **no-2 earthquake:**
   - the whole scene shakes for about 0.9 s: a decaying sum of horizontal and vertical sines with
     varied frequencies, 10–14 logical px peak, settling back exactly;
   - starting with the shake, "Are You Sure?" gives way to **"Is This What You Really Want?"**
3. **no-3 swap:**
   1. The question returns to "Will you open?"
   2. Input locks.
   3. YES and NO trade slots along gentle arcs (0.8 s). Each keeps its colour and action, and its
      hitbox follows it.
   4. Input unlocks, and hover works in the new slots.
4. **no-4 shatter and escape** (NO, now in YES's old slot, clicked again; input locked to the end of
   the route):
   1. The heart trembles (0.4 s) and cracks: crack glyphs grow across it (0.4 s).
   2. It bursts into a mist of 150–300 ASCII fragments with varied glyphs, directions, speeds,
      lifetimes, spin and fade (about 1.6 s). It is not a uniform explosion.
   3. Where the heart was, **"If you really feel that way, prove it."** is revealed character by
      character in the paper's ink style.
   4. The envelope opens on its own: the flap folds back and the **blank sheet** (the same as the YES
      route's) rises.
   5. The NO button detaches from its slot, hops in an arc onto the sheet and settles there.
   6. The camera zooms into the sheet, with the NO button riding along.
   7. The sheet face becomes the chase game. **No flower and no night.**

**Acceptance (NO intro):** N1–N8 cover each click's effect in order:
- the identities and colours survive the swap;
- hitboxes match the drawn positions after the swap;
- the heart fragments vary;
- the message is fully readable;
- the NO button stays recognisable through the jump.

## 12. Chase game (`chase`), 320 × 320 logical
- **Look:** an ASCII world on dark paper:
  - a ground line of `_ - = ~` patterns, with a parallax horizon row;
  - a **red ASCII mouse pointer**: the computer's arrow cursor (an arrowhead pointing up-left with a short
    stem), not an animal (user clarification, 2026-11-01); it glides with a slight bob and tilt, lifts and
    tilts in a jump, may leave a faint motion trail, and wobbles when it stumbles;
  - the fleeing **NO button**, a small framed `[NO]` box that bobs and hops.

  The cells are crisp because of nearest-neighbour scaling.
- **Controls:**
  - the player runs automatically;
  - **Space** jumps: fixed height and duration, with coyote time and a jump buffer for forgiveness;
  - Space does nothing else anywhere in the app, and clicks do nothing in the game.
- **Physics:** a fixed 120 Hz simulation step; drawing interpolates between steps, independent of fps.
- **Obstacles:** at least 5 kinds, each clearly distinct from the ground:
  - a small rock `o`;
  - low debris `,;.`;
  - a short barrier `|#|`;
  - a tall stack `[#]` (2 rows);
  - a ground gap;
  - plus groups of these.

  They come from a **scripted course** with seeded variation in spacing, so it is always fair: the
  minimum gap is never below a jump's landing distance plus reaction time.
- **Phases (total 60–120 s, target about 90 s):**
  - **A**, about 20 s: tutorial pace, single obstacles, a "SPACE" hint glyph once.
  - **B**, about 45 s: denser, mixed obstacles, slightly faster.
  - **C**, about 25 s: fastest, and the NO button visibly closer.
- **Collision:**
  - a brief stumble (0.6 s): a flash at most twice, and a glyph scatter;
  - the NO button regains a little lead;
  - the course continues. There is no restart or game over, and the ending is always reachable.

**Acceptance (chase):**
- C1: Space jumps and nothing else does.
- C2: playtime is within 60–120 s for a typical player, and under 130 s even for a player who never
  jumps (scripted test).
- C3: after a collision it recovers and progress continues.
- C4: the NO button is visible for the whole chase.
- C5: the course is reachable at 30, 60 and 144 fps (scripted, frame-rate-independent).

## 13. Ending (`ending`)
1. **Cornered:**
   - scrolling stops and the NO button backs into the right-hand wall `|`;
   - its run animation stops and it trembles;
   - the shake grows smoothly with **pointer proximity**: almost none when far, and strong when the
     pointer is very close, smoothed so it never jumps;
   - only now can it be clicked (or Enter).
2. **Caught:**
   1. Everything freezes for about 0.4 s.
   2. **Glitch** (about 2 s): character scrambling, row displacement, short tearing, block dropouts
      and corruption of the ground, pointer and button. At most 3 flashes per second, all character-based,
      with no RGB-TV look.
   3. **Dissolve** (about 2.5 s): the world breaks into ASCII fragments that scatter and fade, in this
      order: obstacles, ground, pointer, button. Then black.
3. **Face:** after a short black hold, a melancholic kaomoji face, `` (´•ω•`) ``, fades in at centre (2 s),
   alone on black, large and crisp (drawn at window size), and holds. User choice (2026-11-01), after
   emote-style faces like `(◕‿◕)` and `¯\_(ツ)_/¯`: it is the one exception to "ASCII only", and uses
   only glyphs the bundled JetBrains Mono contains (a test checks that none would show as an empty box).
4. **Tear:** one tear forms under one eye (1 s) and runs slowly down (about 3.5 s). It is the only one,
   and the expression doesn't change. A pause follows.
5. **Black:** the face fades out (2.5 s) and the screen stays black. No text, buttons or restart. It
   stays until the window is closed. The next launch starts fresh.

**Acceptance (ending):**
- E1: clicking is impossible before the cornered state.
- E2: the shake amplitude rises steadily with proximity (unit test on the mapping).
- E3: the glitch, dissolve, face, exactly one tear and permanent black happen in order.
- E4: no input does anything after black except closing the window.

---

## 14. Timing table (seconds at `SPEED = 1`; edited only in `letter/config.py`)

| Beat | Duration |
|---|---|
| Launch fade-up | 0.6 |
| Dedication fade-in | 1.2 |
| Question rise | 1.0 |
| YES reveal | 3.0 |
| Night | 2.0 |
| Seed and growth | 6.5 |
| Bloom | 2.0 |
| Firefly arrival | about 6 |
| Clouds gather, moon appears (from the bloom) | about 10 |
| no-1 crossfade | 0.6 |
| no-2 shake | 0.9 |
| no-3 swap | 0.8 |
| no-4 tremble, crack, shatter | 0.4 / 0.4 / 1.6 |
| no-4 message | 1.5 |
| no-4 open and rise | 1.2 |
| no-4 hop | 0.8 |
| no-4 zoom | 1.6 |
| Chase | about 90 |
| Ending: freeze, glitch, dissolve | 0.4 / 2.0 / 2.5 |
| Ending: face, tear form, tear fall | 2.0 / 1.0 / 3.5 |
| Final fade | 2.5 |

## 15. Performance budgets
- **Frame rate:** 60 fps target with vsync. All motion is time-based, so a lower fps never changes
  speed. Frame time is logged in `--selftest`.
- **Night scene, per frame on this PC:**

  | Work | Budget |
  |---|---|
  | Flower splat | ≤ 5 ms |
  | Grass | ≤ 3 ms |
  | Fireflies | ≤ 2 ms |
  | Sky (stars, clouds, moon) | ≤ 2.5 ms |
  | Glow | ≤ 4 ms (half-rate if needed) |
  | Scaling and blit | ≤ 3 ms |
  | Total | ≤ 16 ms (measured 2026-10-31 before the sky: about 14 ms bloomed) |

- **Allocations:**
  - static geometry, soil, paper grain, glyph atlases and envelope surfaces are built once per scene
    (or per resize);
  - per-frame work reuses buffers;
  - finished scenes release their arrays.
- **Fallback:** if the night scene misses budget on modest hardware, first lower the quality tier
  (particle and firefly counts, glow rate), then consider the GPU particle path (ADR 0001, needs
  approval).

## 16. Packaging and distribution (`release`)
- **Build:** `tools/build.py` runs PyInstaller `--onedir --windowed --name LetterToEsther` with a
  generated icon. It produces `dist/LetterToEsther/`, containing `LetterToEsther.exe` and
  `_internal/…` (runtime, libraries, fonts). It then zips that folder to `dist/LetterToEsther-win64.zip`.
- **Contents:** the release folder includes `THIRD_PARTY_NOTICES.md` and the font licences.
- **Assets:** loaded through `assets.py`, which resolves from `sys._MEIPASS` when frozen and from the
  repository when not. The app works from any working directory and any folder location.
- **What you send:** the zip. The recipient extracts it and double-clicks `LetterToEsther.exe`.
  - If SmartScreen warns "unknown publisher" (the build is unsigned), they choose **More info → Run
    anyway**.
  - Nothing else to install.
- **Not shipped:** `legacy/`, `docs/`, `tests/` and `reference/`.

**Acceptance (release):**
- R1: the zip extracted to a new folder outside the repository launches by double-click and plays both
  routes.
- R2: it runs with network access disabled.
- R3: closing and relaunching works.
- R4: `--selftest` passes on the frozen exe.
- R5: it has been tested on a clean Windows machine without Python, or the report says plainly that
  this wasn't possible.

## 17. Testing strategy
- **Unit (CPython `unittest`):** the pure logic:
  - the state machine (events, gating, route commitment, no double transitions);
  - timing-table sanity;
  - viewport transform round-trips (draw ↔ input) at several window sizes;
  - hover label settling and hitbox stability;
  - dissolve monotonicity;
  - wind range and variation;
  - flower geometry invariants (stem reaches the root, closed ≠ open, particle counts);
  - firefly steering (bounded speed, coverage of the square, desynchronised pulses);
  - chase physics (jump arc, frame-rate independence, course fairness, guaranteed ending);
  - the proximity-to-shake mapping;
  - the ending order and "exactly one tear".
- **Headless scene tests:** each scene is stepped with a fake clock and scripted input under
  `SDL_VIDEODRIVER=dummy`, checking states and that nothing throws.
- **Screenshots:** `tools/shots.py` renders key frames of both routes at 1280 × 800 and 1920 × 1080 to
  `build/shots/`. They are reviewed by eye at each gate (Claude reads the PNGs). This is the visual
  check.
- **Self-test:** `--selftest` drives both routes with scripted input in a hidden window, logs fps and
  phase timings, and exits 0/1. It runs from source and from the frozen exe.
- **Traceability:** each acceptance ID (L1…R5) maps to its module and test in `tasks/todo.md`, with
  statuses: not started / in progress / implemented / tested / verified in packaged build.

## 18. Boundaries
- **Always:**
  - time-based motion;
  - one viewport transform for drawing and input;
  - run the unit tests and look at the screenshots before marking a gate done;
  - keep `SPEC.md` in step with any change;
  - license notices in the release.
- **Ask first:**
  - any new dependency beyond pygame-ce, numpy and pyinstaller (e.g. moderngl);
  - adding sound;
  - commits and pushes;
  - shipping any iremcnar code;
  - changing the story beats.
- **Never:**
  - network access at runtime;
  - copying `reference/` code without permission;
  - starting the NO route before Gates 1–4 pass;
  - claiming a test that only read source;
  - leaving contradictory docs.

## 19. Gates (build order; details in `CAPABILITY-MAP.md`)
1. **G1 Desktop foundation:** window, loop, viewport/DPI, assets, fonts, clock, state machine, packaging
   skeleton (an empty scene ships as an exe).
2. **G2 Letter:** envelope, lighting, float, dedication, question, buttons, hover, hitboxes.
3. **G3 YES route:** reveal, night, grass and wind, seed, flower, bloom, sway and pointer, fireflies.
4. **G4 Quality and performance:** 640/320 canvases, DPI and resize tests, fps budget, timing polish.
   **Gate: the NO route doesn't start until G1–G4 pass.**
5. **G5 NO route:** questions, earthquake, swap, shatter and escape, chase, ending.
6. **G6 Release:** full verification of both routes and the frozen build, docs, the zip.

## 20. Open questions (the default in bold is used if you approve as is)
1. **Q1 Flower code licence:** iremcnar/Flowers has no licence, so shipping its code in an exe would be
   distributing someone else's work without permission.
   - (a) **Re-implement the same techniques cleanly (A3), so it looks like the reference with no code
     copied.**
   - (b) You ask iremcnar to add a licence or give written permission, then the original is adapted
     with attribution.
   - (c) Ship it anyway: not recommended.
2. **Q2 Stack:** **Python + pygame-ce + NumPy + PyInstaller (ADR 0001)**, or Godot 4 (full rewrite).
3. **Q3 Night scene shape:** **640 × 640 square, centred, night-coloured bars, edges fading (A6)**, or a
   wider night that only keeps the flower itself at 640 × 640.
4. **Q4 Fonts:** resolved 2026-10-31: everything is ASCII in JetBrains Mono (A2, A7). No display font.
5. **Q5 The face:** answered 2026-11-01: an emote (kaomoji) face, `` (´•ω•`) `` (§13).
