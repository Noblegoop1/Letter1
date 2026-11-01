# Spec: "To Esther" — an interactive letter, as a Windows desktop app

Status: **APPROVED v3 (2026-10-31), defaults taken for Q1–Q5. Built through G5 (2026-11-01); G6 release in progress.
2026-11-01 feature update (user brief): the fireflies form a date invitation with its own YES/NO and two new
endings (§10.7), and the chase game is redesigned as a pointer-vs-floating-button runner (§12) — gate G7, built.** Later user changes the same day: the letter world
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
| Finale (YES route) | The bloomed garden was the end | The fireflies gather into "Will you go on a date with me?" with its own YES/NO: YES → a warm kaomoji ending and the app closes; NO → the crying-face ending (§10.7) |
| Fireflies | 10 fireflies orbiting the flower | 30–60 detailed fireflies travelling the whole night scene; they rise out of the grass, some pass behind it, a few drift close as soft out-of-focus lights |
| Question banner | Pixel-font letters of `#` and `/` | Shaded ASCII lettering: a real typeface cut into cells, each cell the best-fitting mark, lit from the top left, with an extruded side (§9) |
| Flower | Purple and pink pointillist lotus (later in "sunrise" colours) | A pointillist sea holly in the user's blue gradients, glowing like the ocean under the moon (§10.4) |
| Night sky | A static gradient | Stars from the start; as the flower blooms, soft moonlit clouds gather and the moon slowly appears (§10.6) |
| Pace | 10–24 Hz redraws, 4.5 s reveal | 60 fps; durations tuned by one `SPEED` setting (§13) |
| No button | Shakes, letters go wild | A full alternate route: questions, earthquake, swap, heart shatter, chase game, ending (§15–§18) |
| Pause button | On screen | Removed (not part of the game look); the clock pauses itself when the window loses focus |
| Sound | None | Effects, ambience and a procedural music theme, all offline (§21); `M` mutes |

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
- **A8 Sound:** added 2026-11-01 at the user's request: effects, ambience and procedural music, all
  offline (§21).
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
.venv\Scripts\python tools\sounds.py               # cut assets\sounds\ from the packs in reference\audio-sources\ (§21)
.venv\Scripts\python tools\listen.py               # record each path's soundtrack to build\sound\*.wav, check levels
.venv\Scripts\python tools\build.py                # sounds, then PyInstaller release -> dist\LetterToEsther\ + zip
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
    audio.py            sound over pygame.mixer: effects, loops, generated music, the cue sheet (§21)
  scenes/
    letter.py           envelope, dedication, question, buttons (shared by both routes)
    yes_reveal.py       dissolve, sheet, zoom
    night.py            lighting shift, soil, grass, wind, seed
    flower.py           pointillist flower (the swap point)
    fireflies.py        waypoint fireflies
    no_route.py         questions, earthquake, swap, heart shatter, escape
    chase.py            320 x 320 ASCII runner
    ending.py           cornered button, glitch, face, tear, black
  art/                  pure geometry/text helpers kept from the web version (buttons, heart, dissolve),
                        and the procedural music (music.py)
  soundtrack.py         the cue sheet and mix levels (data, §21)
assets/fonts/           bundled OFL fonts + their licence files
assets/sounds/          sound effects made by tools/sounds.py (shipped; not in git, §21)
tools/                  build.py, shots.py, sounds.py, listen.py, preview tools
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
      YES route: yes-reveal → night → seed → grown → bloom → bloomed (fireflies arrive, then wander)
                 → gather (they converge and form the invitation) → invite (its YES / NO)
                     date-yes → farewell (scatter, flower brightens, dims, black) → joy (smile → love eyes) → exit
                     date-no  → letgo (the message disperses, the night fades) → face → black
      NO route:  no-1 → no-2 → no-3 → no-4 (shatter, message, auto-open, escape) → chase (phases A, B, C
                 inside the game) → cornered → glitch → face → black
  ```

  - **Events:** `yes`, `no`, `flower`, `course-end`, `catch`, `date-yes`, `date-no`.
  - **Three separate decisions:** the envelope's YES/NO (`yes`, `no`), the invitation's YES/NO
    (`date-yes`, `date-no`, accepted only in `invite`), and catching the cornered NO (`catch`, only in
    `cornered`). Each has its own buttons, hitboxes and events; none touches another's state or counters.
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
- **Wandering, then the invitation:** once they have all arrived they wander for a configurable delay
  (`config.WANDER`, default 6.5 s), then gather into the invitation (§10.7).
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

### 10.7 The invitation (`invite`): fireflies form the question, and its two endings
1. **Gathering** (`gather`, about 7 s), gradual and organic, in four overlapping stages:
   - free movement continues at first;
   - attraction: each firefly's target drifts toward its place in the message, at its own moment;
   - convergence: paths become coordinated but never synchronised;
   - formation: they settle, and the lettering becomes readable.

   No teleporting and no snapping. Their pulsing and glow continue throughout.
2. **The message is made of fireflies.** The exact text **"Will you go on a date with me?"** is set in the
   bundled font, rasterised to a bitmap, and sampled into cells; every occupied cell is one firefly.
   - The existing fireflies take some of the places. Extra fireflies, with the same look and behaviour,
     fly in from the grass and the edges of the night until every cell is filled, so the letters are
     filled, not outlined.
   - Layout: two lines ("Will you go on" / "a date with me?"), centred, in the upper sky of the 640 × 640
     scene, clear of the flower's head; the moon may sit behind the end of a line.
   - Once formed, each firefly keeps pulsing and flickering a little and adds a soft halo through the
     bloom pass. The lettering stays pointillist, not a neon sign, and never outshines the flower.
3. **The invitation's buttons** fade in under the message once it has formed. They are a new pair, YES
   and NO:
   - they look unlike the envelope buttons: soft, glowing dot outlines and dot-matrix labels made of the
     same luminous points as the message;
   - hover brightens and lifts them slightly, while the hitboxes stay fixed;
   - they have their own events (`date-yes`, `date-no`) and are accepted only in `invite`.
4. **NO** (`letgo`, about 2.5 s, then the shared ending): the buttons go inactive, the message disperses,
   and the night fades to black. Then the existing face, its single tear and permanent black play (§13).
   There is no chase and no shatter, and nothing counts toward the envelope's NO clicks.
5. **YES** (`farewell`, about 8 s, then `joy`):
   - the buttons go inactive;
   - the message breaks apart: its fireflies leave their places and scatter outward into the night,
     glowing, then fading;
   - meanwhile the flower brightens beyond its bloom glow (detail kept, no wash-out), holds, then dims
     smoothly while the fireflies vanish and the night fades to black;
   - **joy** (about 7.5 s): on black, a centred smiling kaomoji ``(˶ᵔ ᵕ ᵔ˶)`` fades in, then gently changes
     to love eyes ``(♡‿♡)`` (never both at once), holds with a faint pulse and fades;
   - then the app closes normally (exit code 0, no error, no restart).
   - The faces' glyphs come from Windows' own Segoe UI Symbol at runtime (not bundled; every Windows 10/11
     PC has it). If it is missing, ASCII-safe faces in the bundled font are used instead.
6. **Locks:** input is locked through each ending; repeated clicks do nothing; no earlier button comes
   back.

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

**Acceptance (invitation):**
- I1: after the bloom, the fireflies wander for the configured delay before gathering starts.
- I2: gathering is gradual: staggered starts, smooth paths, no teleporting or snapping.
- I3: the exact message is formed only by firefly particles, one per occupied cell of the text bitmap. It
  is readable, sits inside the scene, and stays clear of the flower's head.
- I4: extra fireflies join when needed, looking and moving like the others.
- I5: the invitation buttons appear only once the message has formed. They differ from the envelope
  buttons, have fixed hitboxes and hover feedback, and send only `date-yes` / `date-no`.
- I6: NO plays the message dispersing, the night fading, then the existing face with one tear, then
  permanent black.
- I7: YES plays the scatter, the flower brightening then dimming, black, the smile then love eyes, then a
  normal exit with code 0.
- I8: input is locked through both endings, and no earlier decision's buttons or counters react.

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

## 12. Chase game (`chase`), 320 × 320 logical — redesigned 2026-11-01
The concept: **the player's mouse pointer chases the big floating NO button**, jumping over walls, in a
side-scrolling runner. The layout and readability follow a classic runner (the user's dinosaur-game
reference): a ground line low on the screen, the player lower left, obstacles arriving from the right,
the target ahead. The artwork is our own: ASCII glyphs and the envelope's NO button. No dinosaur, no
cacti.
- **Look:** dark paper; a solid ground line with a scrolling dotted texture below it and a faint slow
  horizon; everything in glyphs, drawn crisp at window resolution (the 320 × 320 canvas is the
  coordinate space, not a bitmap that gets stretched).
- **Player: a mouse pointer.** A red ASCII arrow cursor, much larger than a system cursor, with a clear
  outline and fill. It has no animal features, no legs and no run cycle; it glides, tilting slightly.
  - While the chase is on screen the system cursor is hidden, so only one pointer is visible.
  - Its horizontal position follows the real mouse (window → logical through the viewport), clamped to a
    lane on the left part of the ground.
  - **Space** jumps along a fixed, smooth arc (coyote time and a press buffer for forgiveness), and
    horizontal control continues in the air. Nothing else jumps.
- **Target: the NO button.** It is the envelope's NO button art itself (dashed frame, block letters,
  lavender), drawn crisp and large: about a third of the play width. It is a UI button that escaped, not
  a creature: no legs and no running.
  - It hovers above the ground with a smooth rise-pause-fall float.
  - It drifts away and evades: it pulls ahead, shifts, pauses, resumes. It stays readable and on screen,
    and is always reachable.
- **Obstacles: recognisable, block-built shapes** with collision boxes that match what is drawn:
  - short barrier (`+--+` / `|##|`);
  - wall (several rows of `|####|` under a `+----+` cap);
  - tall wall;
  - stacked blocks;
  - a ground gap (a visible missing section of the ground line);
  - clusters of these.

  All share one consistent style: no stray symbols, no noise.
- **Physics:** fixed 120 Hz steps, frame-rate independent. Collision boxes are slightly smaller than the
  drawn shapes, to be forgiving.
- **Course:** scripted, with seeded variation, and always fair (every gap leaves enough room to land and
  react).
  - **Phases** (a short game, user change 2026-11-01: about 20 s in all):
    - A, about 4.5 s: introduction, a single low obstacle, a `[ SPACE ]` hint once;
    - B, about 8.5 s: walls of several sizes, a gap, a cluster, the NO button pulling ahead;
    - C, about 4.5 s: final approach, the NO button closer;
    - then a short run-out and the stop at the end wall.
  - Total about 20 s for a typical player (15–26 s); under 30 s even for a player who never jumps.
- **Collision:** a short reaction (the pointer flashes at most twice and a few glyphs scatter), a brief
  slowdown, then the course continues. The NO button gains a little lead. No restart and no game over.
- **Cornered** (§13 step 1): scrolling stops and the NO button is trapped against a wall, hovering and
  trembling.
  - The pointer now follows the mouse freely (x and y).
  - The tremble grows with the pointer's proximity: almost none when far, subtle at a medium distance,
    strong when near, intense when very close.
  - Only now can the button be clicked (or Enter).

**Acceptance (chase):**
- C1: Space jumps and nothing else does.
- C2: playtime is about 20 s (15–26 s) for a typical player, and under 30 s even for a player who never
  jumps (scripted test).
- C3: after a collision it recovers and progress continues.
- C4: the NO button is visible for the whole chase.
- C5: the course is reachable at 30, 60 and 144 fps (scripted, frame-rate-independent).
- C6: the player is a pointer arrow (no animal, legs or body), and the system cursor is hidden during the
  chase.
- C7: the pointer's horizontal position follows the real mouse inside its lane, and jumps keep that
  control.
- C8: the NO button is the envelope's NO button art, about a third of the play width; it floats and
  evades and never has legs.
- C9: obstacles are recognisable block shapes (walls, barriers, stacks, gaps, clusters), and each one's
  collision box matches its drawing.
- C10: the composition reads as a runner: ground low, player lower left, obstacles from the right, NO
  ahead.

## 13. Endings (`ending`)
The crying-face ending (steps 3–5) is shared by the NO route and by NO on the invitation (§10.7). The
invitation's YES ending is in §10.7.

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
- E5: the invitation's NO reaches the same face and single tear without passing through the chase or
  the glitch; its YES ends with the joy faces and a normal exit.

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
| Wander before the invitation (`config.WANDER`) | 6.5 (after the fireflies' 6.3 s arrival) |
| Gather into the message | 7.0 |
| Invitation buttons fade in (input lock) | 1.2 |
| NO: letgo | 2.5 |
| YES: farewell (scatter 0–3, brighten 1–3.5, dim 4.5–8, black by 8) | 8.0 |
| YES: joy (smile 0.6–2.8, love eyes 3.2–5.6, fade 5.8–7.0) | 7.5 |
| Chase | about 20 |
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
  | Message fireflies (about 1,000, while gathering and formed) | ≤ 3 ms |
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
- **Sounds:** `tools/build.py` first runs `tools/sounds.py`, so the release always carries
  `assets/sounds/` (§21), which is not in git.
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
- **Sound (§21):** `tests/test_sound.py` (names, music, cue timing, silence without a device, pause and
  mute, with SDL's dummy audio driver); `tools/listen.py` records each path in real time for the levels
  and for listening by ear.
- **Screenshots:** `tools/shots.py` renders key frames of both routes at 1280 × 800 and 1920 × 1080 to
  `build/shots/`. They are reviewed by eye at each gate (Claude reads the PNGs). This is the visual
  check.
- **Self-test:** `--selftest` drives every path with scripted input in a hidden window (`--window` shows
  it): YES then the invitation's YES (ending in a normal exit), YES then the invitation's NO, and the NO
  route through the chase. It logs fps and phase timings and exits 0/1, from source and from the frozen
  exe.
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
  - changing the story beats;
  - new sound sources (sound itself was asked for and added on 2026-11-01, §21).
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
7. **G7 Finale and chase redesign (2026-11-01):** first the chase redesign (§12), then the firefly
   invitation and its endings (§10.7); then G6's checks again on the new build.
8. **G8 Sound (2026-11-01):** the sound tool, procedural music, the audio engine and cue sheet (§21);
   then G6's checks again.

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

## 21. Sound (`sound`), added 2026-11-01
User brief (2026-11-01): a complete, choreographed soundtrack (effects, music, ambience, transitions and
musical cues), bundled and fully offline, reusing the existing systems. The brief was cut off after its
list of sources, and the user then asked Claude to design the rest. This section is that design.

**Sources and licences:**
- **Effects and ambience** come from three free packs, downloaded once to `reference/audio-sources/` (not
  in git, not shipped):
  - Daily Sounds "Game Starter Sound Pack (Free)" (dailysounds.org): the boom, heartbeat, glitch, bell,
    swoosh, riser, power-down and stinger;
  - Willosuna "Free Game & UI Sound Pack" (willosuna.itch.io): the chase's jump and stumble, and the
    heart's crack and shatter;
  - Mixkit (mixkit.co, Mixkit Sound Effects Free License): paper, pencil, clicks, sparkles, crickets, wind.
- All three allow their sounds inside a finished app and forbid sharing the raw files on their own, edited
  or not. So `tools/sounds.py` cuts, fades, mixes to mono, matches loudness and writes only the sounds the
  app uses to `assets/sounds/` as 16-bit WAV, and **`assets/sounds/` is not in git** (it is in the build).
  `tools/build.py` regenerates it first. Credits are in `THIRD_PARTY_NOTICES.md` (none is required).
- **Music is original and procedural:** `letter/art/music.py` writes every note with NumPy when the app
  starts (on a worker thread, cached), so there are no music files and no licence questions.

**Architecture** (reusing the story machine and the scenes; no new dependency):
- `letter/engine/audio.py`, `Audio`: a thin wrapper over `pygame.mixer` (SDL_mixer, already in pygame-ce).
  - one-shot effects on free channels;
  - named loops on reserved channels, each with a time-based volume ramp (fade in, duck, fade out);
  - generated music turned into sounds on the main thread when the worker has it; a loop asked for
    before its music is ready starts when it is;
  - silence instead of errors when there is no audio device or a sound file is missing.
- `letter/soundtrack.py`: the cue sheet (`CUES`), mix levels (`LEVEL`) and the music list. It is data:
  `phase -> [(seconds into the phase, action, ...)]`, fired by `Audio.follow(phase, e)` every frame when
  `e` passes each cue's time, so cues land on the same beats as the pictures (at any `SPEED`).
- **Scenes add only what isn't a story beat:** hover on the envelope's and the invitation's buttons, the
  chase's jumps and stumbles (counters on `Chase`), and the cornered heartbeat's loudness, which follows
  the pointer's distance like the shake does.
- **Pause:** when the window loses focus, story time stops and so does every sound; they continue
  together.
- **Mute:** `M` toggles all sound.

**Music** (`letter/art/music.py`; one theme in F major for the whole piece):

| Track | Where | What |
|---|---|---|
| `theme` | intro, letter | A music-box waltz (3/4, 76 bpm, 16 bars, loops) over a soft pad |
| `theme_minor` | no-1 to no-3 | The same tune in F harmonic minor, slower (66 bpm); crossfades in on the first NO |
| `night` | night to farewell | A slow pad (Fmaj9, Dm9, B♭maj9, C6/9, 8 s each) with sparse glockenspiel stars and a low root |
| `chase` | chase | D minor, 120 bpm: plucked bass, a chiptune arpeggio, a light kick and hat |
| `tension` | cornered | A low D drone that swells slowly, under the heartbeat |
| `grow` | seed | A glockenspiel arpeggio climbing as the stem grows (4.5 s) |
| `bloom` | bloom | A warm chord swells as the flower opens, with a celesta run |
| `motif` | gather | The theme's first four bars on celesta as the fireflies form the question. It stops on the dominant, unresolved: the question waits |
| `joy` | joy | The theme's last two bars resolve to F major as she smiles; a two-note chime for the love eyes; one soft heartbeat on the pulse |
| `letgo` | letgo | A falling F-minor celesta line as the message disperses |
| `sad` | face | A few slow music-box notes in F minor under the face; one high note as the tear lets go; it fades with the face |

**Cue sheet** (seconds into the phase at `SPEED = 1`; levels are in `soundtrack.LEVEL`):

| Phase | Sound |
|---|---|
| intro | `theme` fades in (2 s); pencil as "To Esther" writes itself (0.4) |
| letter, no-1 to no-3 | a hover tick on each button the pointer (or the arrow keys) moves onto |
| yes-reveal | click and bell (0); the flap (0.1); the sheet rises (0.4); a sparkle whoosh into the night (2.0), peaking as the night begins; `theme` fades out (0.5 to 3.0) |
| night | crickets and wind fade in; `night` fades in (3 s) |
| seed | the seed falls with a wand sparkle (0.4); puff (1.2); `grow` (2.0) |
| bloom | `bloom` and a fairy sparkle (0) |
| bloomed | a soft sparkle as the fireflies arrive (0.5) |
| gather | `night` ducks; `motif` (0.2) |
| invite | a soft tone as the buttons appear (0); hover ticks |
| farewell | click and bell (0); a sparkle whoosh as they scatter (0.1); `night` comes back up (0.3); everything fades out (4.5 to 8) |
| joy | `joy` (0) |
| letgo | click (0); `letgo` (0); everything else fades out (0 to 2.5) |
| no-1 | click; the page turns; `theme` crossfades to `theme_minor` (1.5 s) |
| no-2 | click; the boom of the earthquake; `theme_minor` ducks under it and comes back (0.9) |
| no-3 | click; a swoosh as the buttons swap |
| no-4 | click (0); the music fades out (0 to 0.8); crack (0.3); shatter and glittering fragments (0.8); the pencil writes the message (2.4); the envelope opens (4.5); the sheet (4.8); the hop (5.7) and its landing (6.4); a riser into the chase (6.5) |
| chase | `chase` fades in with the world (0.6 s); jump and stumble sounds from the game |
| cornered | `chase` fades out; `tension` fades in; a low stinger (0); the heartbeat loop (from the scene), from a quiet pulse when the pointer is far to full when it is close, on the same curve as the tremble |
| glitch | everything stops on the catch (0, the freeze); digital glitches (0.4, 1.3) with electric static (0.5); a power-down as the world dissolves (2.4) |
| face | `sad` (0) |
| black, exit | silence |

**Mix:** the tool matches the effects to one loudness, so `LEVEL` alone sets the balance: the music sits
under the effects, the ambience lower still, and nothing clips (checked on recorded runs).

**Acceptance (sound):**
- S1: every sound the cue sheet, the scenes and `LEVEL` name exists after `tools/sounds.py`, and every
  music track generates: finite, peak below 0 dBFS, the loops seamless (unit tests).
- S2: each cue fires once, at its time, in its phase, and never in another route (headless test with the
  dummy audio driver).
- S3: the app runs silently, without errors, when there is no audio device or `assets/sounds/` is missing.
- S4: losing focus pauses sound with the story; `M` mutes and unmutes.
- S5: recorded runs of all three paths (`tools/listen.py`: SDL's disk audio driver, real time) never clip
  and keep the effects above the music; the WAVs are for listening by ear.
- S6: the release includes `assets/sounds/`, and the frozen self-test passes.
- S7: no network access; nothing in `reference/` ships.
