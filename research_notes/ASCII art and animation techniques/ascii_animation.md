# ASCII art and animation techniques

Scope: how ASCII and text-grid animation is built (frame models, timing, render loop, text effects, transitions, procedural effects, accessibility). The target is a Python-driven web page that renders everything into a monospace `<pre>` grid. First feature: a big ASCII envelope whose flap unfolds before it slides away, two ASCII-bordered "yes"/"no" buttons whose words keep changing but stay readable, and a large "Will you open ?" headline.

Snippet status: every Python snippet below was run and asserted in a scratch self-check under Python 3.14 (`py -I snippets_check.py`), and the output is shown where it helps. The JS snippets were not run. Snippets that are not quoted from a source are my own derivations and sit under **Inferences**.

---

## 1. Frame-based vs procedural vs hybrid ASCII animation, and how classic works were made

### Takeaway
Classic ASCII films are frame-based: hand-drawn text frames, each with a stored hold duration. The Star Wars ASCIImation runs at about 15 fps on a 67x13 grid. Terminal recordings such as asciinema store timed output events, not frames. Procedural ASCII (donut.c, Doom fire, asciimatics effects) recomputes the grid every frame from math or state. For this project, a hybrid is best: hand-drawn sprites (envelope, letter, button frames, FIGlet text) moved, squashed and recoloured by procedural code each frame.

### Cited Findings
- **ASCIImation frame model.** Frames of ASCII text are shown one after another at a given rate. Each frame has a fixed width and height chosen before drawing starts, and the film is organised into shots, each a run of frames. — [Star Wars Asciimation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
- Frame size is **67 characters wide x 13 lines high**, not counting the separator line. The drawing section of the same FAQ says "67 columns by 14 rows", which is probably the 13 art rows plus the timing line. — [ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
- Playback is **15 fps**, which the author calls "really just an estimate". Pauses are multiples of 1/15 s, and processing time is not counted. — [ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
- **Duration encoding.** Identical consecutive frames are stored once, and the separator line above each frame is replaced by a number giving its on-screen duration ("The 1 in the first frame means it will appear on screen for 1 * 1/15 of a second"). The raw text had 242,984 lines and 17,357 frames, which encoded down to **3,849 frames**. — [ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
- **Tools and workflow.** Frames were drawn in Notepad, then in an IDE's text editor (Microsoft Development Studio). The author used three methods:
  - copy the frame, make a small change, repeat;
  - copy frames in bulk and replay recorded keystrokes across them;
  - edit each frame individually for pans and explosions, which he calls "the most painful".
  He also removed trailing whitespace to shrink the file. — [ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
- **Player history.** The original player was a Java 1.1 applet that buffered frames, showed each one and waited the stored duration. It is now PHP serving compressed pages plus "simple JavaScript" playing the file, because browsers dropped applets between 2015 and 2017. — [ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
- **Font sensitivity.** The author says Courier New makes the animation look "a little too stretched vertically", and that the art was drawn for Courier. — [ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
- Simon Jansen started the remake in **1997** and is credited with coining "asciimation". It is unfinished, and its last frame was added in January 2015. This comes from a search-result summary; the page itself was not fetched. — [Tedium](https://tedium.co/2018/06/21/star-wars-ascii-remake/)
- **asciinema (asciicast v2) is an event stream, not frames.**
  - The file is newline-delimited JSON. Line 1 is a header (`version: 2`, `width`, `height`, plus optional `timestamp`, `duration`, `idle_time_limit`, `command`, `title`, `env`, `theme`).
  - Every later line is `[time, code, data]`, with `time` a float in seconds. Codes are `o` (output), `i` (input), `m` (marker) and `r` (resize, `"COLSxROWS"`). Players should ignore unknown codes.
  - `idle_time_limit` caps long pauses. Extension `.cast`, MIME `application/x-asciicast`. The format can be written incrementally, so an interrupted recording is not lost.
  — [asciicast v2 docs](https://docs.asciinema.org/manual/asciicast/v2/)
- **asciimatics (Python) is a procedural/scene engine.**
  - A `Scene` holds an ordered list of `Effect`s. Effects render in list order, so foreground effects go last. `Screen.play()` runs scenes in sequence.
  - Each effect's `update(frame_no)` gets the frame number for timing, and `start_frame`/`stop_frame` gate when it is active.
  - Renderers include `FigletText` (large text) and `StaticRenderer(images=[...])` (pre-drawn frames).
  - `Sprite` and `Path` move renderers along scripted paths (`jump_to`, `wait`, `move_straight_to`, `move_round_to`), and `DynamicPath` reacts to program state.
  - `ParticleEffect` contains `ParticleEmitter`s that spawn `Particle`s; for example `StarFirework` = Rocket, then StarExplosion, then StarTrails.
  — [asciimatics animation docs](https://asciimatics.readthedocs.io/en/stable/animation.html)
- **Procedural example: donut.c.** Each frame clears the framebuffer to spaces and the z-buffer to 0, renders every (θ, φ) sample of a torus, then prints rows after moving the cursor home (`ESC[H`). — [a1k0n, Donut math](https://www.a1k0n.net/2011/07/20/donut-math.html)

### Inferences
- **Three models:**

  | Model | Data shipped | Good for | Cost |
  |---|---|---|---|
  | Frame-based (ASCIImation) | list of `(hold_ticks, frame_text)` | hand-crafted character acting, complex shapes | huge authoring effort; every pan is repainted by hand |
  | Event/stream (asciicast) | `[t, "o", ansi_bytes]` | replaying terminal sessions | needs a terminal emulator (xterm-style) to interpret escapes; poor fit for a `<pre>` page |
  | Procedural | code + params | fire, rain, particles, scramble, squash/slide transforms | needs a render loop and care about stability |
  | **Hybrid (recommended)** | small hand-drawn sprites + procedural transforms | envelope, letter, buttons, headline | modest code; art stays editable as plain text |

- **ASCIImation's format suits short pre-baked clips.** One option is to adopt its duration-number-plus-frame format directly. Another is to use an asciicast-like NDJSON file (`{"version":2,"width":W,"height":H}` then `[t, frame_text]` lines) if Python bakes a cut-scene offline and the browser replays it. Dedupe identical consecutive frames the way Jansen did.
- **Pick the font before drawing.** Jansen's Courier vs Courier New remark means cell aspect ratio changes how art reads. Lock the font, `line-height` and `letter-spacing` before drawing the envelope.
- **"Python-driven" can mean three architectures:**
  - (a) Python, e.g. Flask/FastAPI, builds the static art and frame data, and a small JS rAF loop animates in the browser. This gives the lowest latency and is recommended.
  - (b) Python runs in the browser through Pyodide/PyScript and drives the loop itself.
  - (c) Python streams frames over a WebSocket, which adds latency and jitter.
  Per-frame motion should run client-side in (a) or (b). This is my own architectural judgement; none of these were sourced this session.

### Gaps
- ttyrec format details, the asciicast v3 changes, and how asciinema-player interprets ANSI were not researched. The v2 page links to v3 but does not describe the differences.
- The towel.blinkenlights.nl telnet version's origin was not confirmed; the ASCIImation FAQ fetched does not mention it.

---

## 2. Timing: fixed vs variable timestep, delta-time, rAF, target frame rates, easing and keyframe interpolation

### Takeaway
Drive the page with `requestAnimationFrame`, always using its timestamp, never a frame count. Run deterministic simulations (fire, particles) on a fixed-step accumulator with a frame-time cap. Run glyph churn on its own slow clock (8–20 Hz), and drive motion (flap angle, slide offset) from eased elapsed time sampled every display frame.

### Cited Findings
- **rAF timing.**
  - The callback gets a `DOMHighResTimeStamp` for the end of the previous frame's rendering, in ms since time origin. For `Window` it equals `document.timeline.currentTime`. It is similar to `performance.now()` at the start of the callback but "never the same value", and all callbacks in one frame get the same timestamp. — [MDN rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
  - Callbacks usually run at the display refresh rate (60, 75, 120 or 144 Hz). MDN warns to compute progress from the timestamp, "otherwise, the animation will run faster on high refresh-rate screens". — [MDN rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
  - rAF is one-shot (re-request it every frame) and paused in most browsers in background tabs and hidden iframes. `cancelAnimationFrame(id)` cancels a request; IDs can overflow, so avoid `0` as a sentinel. — [MDN rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
  - MDN's canonical pattern: record `start` on the first callback, `elapsed = ts - start`, `shift = Math.min(0.1*elapsed, 200)`, set `element.style.transform = translateX(...)`, and re-request until done. — [MDN rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
- **Glenn Fiedler's timestep progression** — [Fix Your Timestep!](https://gafferongames.com/post/fix_your_timestep/):
  - A fixed dt (e.g. 1/60) only works if the refresh rate matches and updates fit within a frame.
  - A variable dt makes behaviour depend on dt: springs explode and objects tunnel.
  - A semi-fixed timestep (sub-steps ≤ dt plus a remainder) risks the "spiral of death" when a step costs more real time than it simulates. Mitigate with headroom or by clamping steps per frame.
  - The accumulator ("free the physics") lets the renderer produce time and the simulation consume it in fixed-dt chunks, with leftover time carried over. His sample code caps frame time at **0.25 s**.
  - Final touch: `alpha = accumulator / dt`, then render `current*alpha + previous*(1-alpha)` to remove stutter.
  - Exact run-to-run determinism needs a fully fixed dt. Semi-fixed is "good enough" but not identical across runs.
- **Reference frame rates in classic and library practice:**
  - ASCIImation plays at 15 fps. — [ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)
  - asciimatics redraws about 20 times per second, with async drivers calling `draw_next_frame()` about every 0.05 s. — [asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html)
  - Baffle's default `speed` (scramble update interval) is 50 ms, i.e. 20 Hz. — [Baffle](https://github.com/camwiegert/baffle)
  - The soulwire TextScramble advances one "frame" per rAF call, so it is tied to display Hz. — [TextScramble gist](https://gist.github.com/Marty-f13/b1fdcf9d9f92600ce0c6903c57fd1971)
  - donut.c advances A += 0.04 and B += 0.02 per frame, also per-frame rather than per-second. — [a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)
- **Easing formulas from the easings.net source** (x in 0..1; constants `c1=1.70158`, `c2=c1*1.525`, `c3=c1+1`, `c4=2π/3`):
  - `easeOutCubic = 1 - (1-x)^3`
  - `easeInOutCubic = x<0.5 ? 4x^3 : 1 - (-2x+2)^3/2`
  - `easeOutQuart = 1-(1-x)^4`
  - `easeOutQuint = 1-(1-x)^5`
  - `easeOutBack = 1 + c3(x-1)^3 + c1(x-1)^2`
  - `easeOutElastic = x==0?0 : x==1?1 : 2^(-10x)·sin((10x-0.75)·c4)+1`
  - `easeInOutSine = -(cos(πx)-1)/2`
  - `easeOutExpo = x==1?1 : 1-2^(-10x)`
  - `easeOutBounce` is piecewise with `n1=7.5625, d1=2.75`.
  — [easings.net source, easingsFunctions.ts](https://raw.githubusercontent.com/ai/easings.net/master/src/easings/easingsFunctions.ts). The rendered [easings.net](https://easings.net/) page loads its formulas client-side, so a plain fetch shows empty function bodies.

### Inferences
- **Fix soulwire's display-rate bug.** Because TextScramble counts frames, its 40-frame windows last about 0.67 s at 60 Hz but about 0.33 s at 120 Hz, which is exactly the bug MDN warns about. Port it to seconds (see §4).
- **Three clocks in one rAF loop** (JS, not run):
  ```js
  const SIM_DT = 1/30;            // fire/particles: fixed step (deterministic, cheap)
  const GLYPH_HZ = 10;            // scramble/churn re-roll rate: stable, readable
  let last, acc = 0, t0;
  function frame(ts) {
    if (last === undefined) { last = t0 = ts; }
    let ft = Math.min((ts - last) / 1000, 0.25);   // Fiedler's cap; also absorbs background-tab resume
    last = ts; acc += ft;
    while (acc >= SIM_DT) { stepSim(SIM_DT); acc -= SIM_DT; }
    const t = (ts - t0) / 1000;                   // seconds since start
    const glyphTick = Math.floor(t * GLYPH_HZ);   // integer: same tick => same glyphs => no shimmer
    render(t, glyphTick, acc / SIM_DT);           // alpha for interpolation if needed
    rafId = requestAnimationFrame(frame);
  }
  ```
- **Frame-time cap after a hidden tab.** Since rAF pauses in hidden tabs, the first frame after returning can carry a dt of many seconds. The 0.25 s cap stops fire and particles from jumping. For one-shot timelines (envelope opening), either pause the timeline clock on `visibilitychange` or accept that the open completes while hidden.
- **Rate guidance.** Character-grid motion is quantised to whole cells, so even at 60–144 Hz rendering, a slide over 80 columns in 0.8 s only changes position about 100 times per second at most. Render at rAF rate, but keep glyph churn at roughly 8–20 Hz, in line with Baffle's 20 Hz and ASCIImation's 15 fps. Faster churn reads as noise.
- **Easing choices for this feature:**
  - **Flap rotation:** `easeInOutCubic`, so it starts gently and settles gently.
  - **Letter rising out:** `easeOutCubic` or `easeOutBack`; Back gives a small overshoot "pop".
  - **Envelope sliding off-screen:** `easeInCubic` (x³), accelerating away. An ease-out on exit looks like it stalls at the edge.
  - **Headline entrance:** `easeOutQuart` or `easeOutExpo`.
  - **Bounce/Elastic:** avoid on large blocks, since they oscillate and read as more motion (see §7).
- **Keyframe interpolation** (verified in the self-check):
  ```python
  def lerp(a, b, t): return a + (b - a) * t
  def ease_out_cubic(x): return 1 - (1 - x) ** 3
  def ease_in_cubic(x): return x ** 3
  def ease_in_out_cubic(x): return 4*x**3 if x < 0.5 else 1 - (-2*x + 2)**3 / 2
  def ease_out_back(x, c1=1.70158): return 1 + (c1+1)*(x-1)**3 + c1*(x-1)**2

  def sample_track(keys, t, ease=lambda u: u):
      """keys = [(time, value), ...] sorted; per-segment easing."""
      if t <= keys[0][0]: return keys[0][1]
      for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
          if t <= t1: return lerp(v0, v1, ease((t - t0) / (t1 - t0)))
      return keys[-1][1]

  def catmull_rom(p0, p1, p2, p3, t):   # uniform Catmull-Rom, passes through p1 (t=0) and p2 (t=1)
      t2, t3 = t*t, t*t*t
      return 0.5 * (2*p1 + (-p0 + p2)*t + (2*p0 - 5*p1 + 4*p2 - p3)*t2 + (-p0 + 3*p1 - 3*p2 + p3)*t3)

  def sample_spline(keys, t):
      """Smooth path through keyframe values; endpoints duplicated."""
      ts = [k[0] for k in keys]; vs = [k[1] for k in keys]
      if t <= ts[0]: return vs[0]
      if t >= ts[-1]: return vs[-1]
      i = max(j for j in range(len(ts) - 1) if ts[j] <= t)
      p = lambda j: vs[min(max(j, 0), len(vs) - 1)]
      return catmull_rom(p(i-1), p(i), p(i+1), p(i+2), (t - ts[i]) / (ts[i+1] - ts[i]))
  ```
  Use Catmull-Rom for multi-point paths, such as the letter's (x, y) path as it lifts out, arcs and settles, or a floating heart's drift. Interpolate x and y separately, then `round()` to cells as the very last step, never before interpolating. Catmull-Rom can overshoot between keys, which may be unwanted at screen edges.

### Gaps
- The Catmull-Rom formula above is the standard uniform form from general knowledge. It was checked only for passing through its keyframes (asserted `sample_spline(keys, 1) == 10`) and was not cross-checked against a primary source this session.
- The Web Animations API (`element.animate()`) and CSS `steps()` timing were not researched. They are relevant if the slide is done as a CSS transform (§5).

---

## 3. Render loop on a character grid: buffers, clearing, compositing with transparency, z-order, dirty rows, flicker and shimmer

### Takeaway
Treat the `<pre>` as a framebuffer. Each frame, composite layers back-to-front into a fresh 2D char array: the painter's algorithm, with a per-layer transparent sentinel. Build the strings, then write only the rows that changed. Glyph shimmer comes from re-deciding glyphs every frame from noisy or continuous inputs. Make glyph choice a pure function of (cell, integer tick), and add hysteresis on ramps.

### Cited Findings
- **Clear and z-buffer per frame.** donut.c clears the framebuffer to spaces and its z-buffer to 0 every frame. The z-buffer stores `1/z` (`ooz`), so 0 means infinitely far, and a cell is written only when its `ooz` exceeds the stored value. — [a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)
- **Home the cursor instead of clearing.** donut.c moves the cursor home with `ESC[H` and overwrites the whole 80x22 (1,760-cell) frame rather than clearing the screen. — [a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)
- **Character aspect.** The original C code scales x by 30 and y by 15 (`x = 40 + 30·D·…`, `y = 12 + 15·D·…`), compensating for terminal cells being about twice as tall as wide. — [a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)
- **Draw order is z-order.** asciimatics effects render in list order, foreground last. — [asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html)
- **Redraw only when needed.** asciimatics refreshes the Screen only when an effect needs a redraw, and `force_update()` forces a full refresh. — [asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html)
- **innerHTML rebuild.** The soulwire TextScramble rebuilds the element's full `innerHTML` every frame, wrapping scrambled chars in `<span class="dud">` (styled `#757575`). — [TextScramble gist](https://gist.github.com/Marty-f13/b1fdcf9d9f92600ce0c6903c57fd1971)
- **Luminance ramps blur edges; shape matching sharpens them.**
  - Mapping one lightness value per cell to a density-ordered char list is essentially nearest-neighbour downsampling. Character shape is ignored and edges look blurry.
  - Shape-vector rendering samples several circles per cell (six in the final version) and picks the nearest glyph by Euclidean distance.
  - Lookups are made fast with a k-d tree, plus a cache keyed on quantised vector components.
  - "Directional contrast" with external sampling circles removed staircasing.
  - The article covers animated scenes but **does not discuss flicker or temporal stability**.
  — [Alex Harri, ASCII rendering (Jan 17 2026)](https://alexharri.com/blog/ascii-rendering). A Codrops article (Sep 2026) builds the same shape-aware approach in Three.js, sampling 6 points inside the cell and 10 in neighbours across all 95 printable glyphs. This is from the search summary only; the fetch returned 403. — [Codrops](https://tympanus.net/codrops/2026/09/04/beyond-the-luminance-ramp-a-shape-aware-ascii-renderer-in-three-js/)

### Inferences
- **Double buffering in a browser is free if you write once per frame.** DOM changes made inside one rAF callback are presented together. Terminal-style "clear then draw" flicker cannot happen unless you clear in one frame and draw in a later one. Build the whole frame in an array, then assign. This is the browser equivalent of donut.c's cursor-home trick.
- **Make space opaque.** Using space as the transparent char breaks envelopes: the envelope's empty interior must hide the hearts behind it. Give each layer its own transparent sentinel (e.g. `'~'` or `'\0'` in the source art) and treat space as an opaque blank. Verified compositor:
  ```python
  def compose(w, h, layers, bg=' '):
      """layers: (z, x, y, lines, transparent_char). Painter's algorithm, back to front."""
      grid = [[bg] * w for _ in range(h)]
      for z, x, y, lines, tr in sorted(layers, key=lambda L: L[0]):
          for dy, line in enumerate(lines):
              yy = y + dy
              if not 0 <= yy < h: continue
              for dx, ch in enumerate(line):
                  xx = x + dx
                  if 0 <= xx < w and ch != tr:      # off-grid parts are clipped, so sprites can slide off-screen
                      grid[yy][xx] = ch
      return [''.join(r) for r in grid]
  # self-check: compose(10,3,[(0,0,0,['..........']*3,None),(1,2,1,['A~B'],'~')])[1] == '..A.B.....'
  ```
  Suggested z-stack for the envelope: `0` background (hearts/particles), `1` envelope back panel, `2` letter, `3` envelope front pocket (the V-cut front that hides the letter's bottom), `4` flap when closed or folding down (when open and behind, move it to z=0.5), `5` headline and buttons.
- **Dirty-row diffing** (JS, not run). Render one element per row inside the `<pre>` and update only rows whose string changed. Use `textContent`, which is faster than `innerHTML` and immune to HTML injection from `<`, `>`, `&` glyphs, which are common in ASCII art and in soulwire's own charset.
  ```js
  const pre = document.querySelector('pre.screen');
  const rowEls = Array.from({length: H}, () => pre.appendChild(document.createElement('div')));
  let prev = [];
  function present(rows) {
    for (let i = 0; i < rows.length; i++)
      if (rows[i] !== prev[i]) rowEls[i].textContent = rows[i];
    prev = rows;
  }
  ```
  For colour, split a row into runs of `<span>` with the same class. Diff at row granularity anyway, since per-cell span updates usually cost more than they save.
- **Shimmer sources and fixes:**
  1. **Per-frame `Math.random()` on a 60–144 Hz loop.** Replace with deterministic hash noise `hash(x, y, tick)`, where `tick = floor(t * GLYPH_HZ)`. The glyph then changes only when the tick changes, identically across refresh rates.
  2. **Continuous value near a ramp boundary,** e.g. luminance 0.499↔0.501 flipping `:`↔`;`. Add hysteresis: keep the previous glyph unless the new level differs by more than ~0.5 of a ramp step.
  3. **Sub-cell motion rounded independently per row,** which makes rows jitter apart. Compute one integer offset per sprite and apply it to all rows.
  4. **Font fallback width changes.** Non-ASCII glyphs (€, ¥, ♥, Cyrillic) may come from a fallback font with a different advance width and shift the row. Stay pure ASCII, or pick a font that covers every glyph used.
- **Aspect correction.** Monospace cells are roughly 1:2 (w:h). Like donut.c, scale y by about 0.5 relative to x in any procedural geometry (circles, hearts, the flap's projection). In the self-check donut, `yp = H/2 - K1*ooz*y*0.5` gave a round torus.
- **CSS for a stable grid** (general practice, not sourced): `white-space: pre; font-family: <one monospace>; line-height: 1 (or 1.1); letter-spacing: 0; font-variant-ligatures: none; user-select: none` for decorative layers. Ligature-capable coding fonts can merge `<-`, `=>`, `--`, which ruins art.

### Gaps
- No source was found on temporal stability or anti-shimmer in ASCII renderers. One search returned only adjacent NPR and video-quality papers, and Harri explicitly omits it. The hysteresis and hash-tick advice above is my own engineering inference.
- No benchmarks were found for `<pre>` update cost (textContent vs innerHTML vs canvas `fillText`) at specific grid sizes.

---

## 4. Text effects: scramble/decode, typewriter, glitch, wave/jitter, and keeping constantly-changing words readable

### Takeaway
The standard "decode" effect gives each character a random start/end window. Before the window it shows the old char, inside it random glyphs (re-rolled with some probability), and after it the target. For words that must change constantly yet stay readable, never scramble everything: keep most letters correct, substitute only look-alike ASCII glyphs, re-roll at a slow fixed rate, and for big FIGlet letters churn the fill characters while keeping the silhouette fixed.

### Cited Findings
- **Soulwire TextScramble (Justin Windle's CodePen "A little text decoding / scramble effect"):**
  - Charset is `'!<>-_\\/[]{}—=+*^?#________'`. The repeated underscores bias picks toward low, quiet glyphs.
  - `setText(new)` builds one queue entry per position over `max(old.length, new.length)`: `{from, to, start: floor(rand*40), end: start + floor(rand*40)}`. It cancels any running rAF, resets `frame = 0`, and returns a Promise that resolves when every char is done.
  - `update()` per entry: if `frame >= end` output `to`; else if `frame >= start` output a random char, re-rolled when unset or when `Math.random() < 0.28`, wrapped in `<span class="dud">`; else output `from`. Then re-request rAF and `frame++`.
  - The demo cycles phrases by chaining `setText(...).then(() => setTimeout(next, 800))`.
  — [TextScramble gist](https://gist.github.com/Marty-f13/b1fdcf9d9f92600ce0c6903c57fd1971); original pen: [codepen soulwire/mEMPrK](https://codepen.io/soulwire/pen/mEMPrK)
- **Baffle.js:**
  - Dependency-free, about 1.8 KB gzipped. `baffle(selector|NodeList|Node)` has chainable `start()` (obfuscate every `speed` ms), `stop()`, `once()`, `reveal(duration, delay)`, `text(fn)` and `set(options)`.
  - Defaults: `characters` (letters plus symbols), `exclude: [' ']` so spaces are never obfuscated, and `speed: 50` ms.
  - MIT licence. **Archived and read-only since Apr 1, 2020.**
  — [Baffle repo](https://github.com/camwiegert/baffle)

### Inferences
- **Recommendation:** port the soulwire algorithm (about 30 lines) rather than depend on Baffle (archived). Two changes: time-based windows, and padding so the grid width never changes. Verified Python:
  ```python
  GLYPHS = '!<>-_\\/[]{}=+*^?#'
  def hash32(*xs):                       # FNV-1a style; deterministic per (cell, tick)
      h = 2166136261
      for x in xs: h = ((h ^ (x & 0xffffffff)) * 16777619) & 0xffffffff
      return h

  def make_queue(old, new, max_start=0.6, max_dur=0.6, rng=random):
      n = max(len(old), len(new)); q = []
      for i in range(n):
          s = rng.random() * max_start
          q.append((old[i:i+1], new[i:i+1], s, s + rng.random() * max_dur))
      return q

  def decode_frame(q, t, rate=15):        # t = seconds since setText
      tick = int(t * rate)
      out, done = [], 0
      for i, (frm, to, s, e) in enumerate(q):
          if t >= e:   out.append(to or ' '); done += 1
          elif t >= s: out.append(GLYPHS[hash32(i, tick) % len(GLYPHS)])
          else:        out.append(frm or ' ')     # pad: keep grid width fixed
      return ''.join(out), done == len(q)
  ```
  With `max_start=0.6, max_dur=0.6`, every char settles within 1.2 s on any display, matching soulwire's 80 frames at 60 Hz. Exclude spaces as Baffle does (skip positions where `to == ' '`) so word gaps stay visible during the decode, which helps readability a lot.
- **"Always changing but readable" for the yes/no buttons.** Readability rules, which are my own design reasoning (no source tested legibility):
  1. **Cap the off-target share.** At most `max(1, len//3)` letters are wrong at once: 1 of "yes", 1 of "no".
  2. **Look-alike pools only.** Use pure-ASCII glyphs that keep the letter's shape, so the word shape survives: `y→yYv`, `e→eE3`, `s→sS5$`, `n→nNh`, `o→oO0@`.
  3. **Slow, fixed re-roll rate.** 6–10 Hz, seeded by the integer tick, so it is stable between ticks and identical at 60 or 144 Hz.
  4. **Never move the word.** Same cell positions, same length, monospace.
  5. **Accent, not replace.** Optionally dim substituted glyphs in a slightly different colour (soulwire's `.dud` grey).
  Verified:
  ```python
  LOOKALIKE = {'y': 'yYv', 'e': 'eE3', 's': 'sS5$', 'n': 'nNh', 'o': 'oO0@'}
  def churn(word, t, rate=8):
      tick = int(t * rate)
      rng = random.Random(tick * 7919 + len(word))   # same tick -> same output (no shimmer)
      k = max(1, len(word) // 3)
      chars = list(word)
      for i in rng.sample(range(len(word)), k):
          pool = LOOKALIKE.get(word[i].lower())
          if pool: chars[i] = rng.choice(pool)
      return ''.join(chars)
  # self-check: churn('yes', 0.0) -> 'ves'; churn('no', 0.3) -> 'nO'; never >1 letter off; stable within a tick
  ```
  For variety, every few seconds trigger a short full `decode_frame` burst (about 0.4 s) from the current text back to the true word, then return to gentle churn.
- **Fill churn for big letters** (headline, or FIGlet-rendered button words). The word is carried by the silhouette of the strokes, not by which glyph fills them, so the fill characters can cycle every tick while the word stays perfectly readable. Verified:
  ```python
  FILL = '#@%&$'
  def fill_churn(lines, t, rate=10, stroke='#'):
      tick = int(t * rate)
      return [''.join(FILL[hash32(x, y, tick) % len(FILL)] if c == stroke else c
                      for x, c in enumerate(row)) for y, row in enumerate(lines)]
  ```
  Draw or generate the "Will you open ?" headline with a solid-fill FIGlet font (asciimatics' `FigletText` renderer does large text — [asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html); in plain Python the usual library is `pyfiglet`, not verified this session). Then run `fill_churn` on it at about 8–12 Hz, and optionally a one-time `decode_frame` reveal on load.
- **Other text effects (recipes):**
  - **Typewriter:** `n = floor(t * cps)`, showing `text[:n]` plus a cursor glyph (`_` or `█`) that blinks at 1–2 Hz, safely under the 3 flashes/s limit (§7). Use 25–40 chars/s for headlines. Reveal one row at a time for multi-line ASCII art.
  - **Glitch:** for 1–3 frames, shift a random row by ±1–3 columns, swap a few chars for `GLYPHS`, optionally a CSS `text-shadow` red/cyan offset. Trigger rarely (≤ once every 2–3 s) and keep it small in area to respect the flash rules.
  - **Wave/jitter per char:** wrap each char in a `<span>` and set `transform: translateY(A*sin(k*i - ω*t))` in px. This is sub-cell and smooth, and does not disturb the grid. Grid-quantised alternative: `dy = round(A*sin(...))` rows, which only works for single-glyph text on an empty band.
  - **Decode-on-hover:** run `decode_frame` from scrambled to true text when the pointer enters a button, which gives a strong "it's alive" affordance at low cost.

### Gaps
- No legibility study was found on how many scrambled characters a word tolerates. The ⅓ cap and look-alike pools are heuristics and should be tested by eye.
- Codrops' and CSS-Tricks' own scramble tutorials were not fetched separately. The soulwire gist is the code those tutorials are usually based on, but that lineage was not verified.

---

## 5. Transitions for an envelope/letter: flap unfold, slide off-screen, wipe, dissolve, fade

### Takeaway
Do the flap unfold as a **row-squash**: project the flap's rows onto a height of `H·|cos θ|`, sampling source rows nearest-neighbour. Past 90°, draw it above the hinge, vertically mirrored with `/`↔`\` swapped. Add a slight per-row horizontal widen for perspective, using the donut.c projection idea. Do the slide either as a CSS transform on the whole `<pre>` (smooth, cheap) or as integer column offsets in the compositor (authentic and clipped by the grid). Do dissolves with a fixed per-cell random threshold walked down a density ramp.

### Cited Findings
- **Perspective projection.** `x' = K1·x/(K2+z)` and `y' = K1·y/(K2+z)`, with `K2 = 5` (viewer distance). `K1 = screen_width·K2·3/(8·(R1+R2))` puts the object's widest extent at 3/8 of the screen width from centre. — [a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)
- **Moving a whole element per frame.** MDN's rAF example moves an element with `element.style.transform = translateX(${shift}px)`. — [MDN rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
- **Path-based movement.** asciimatics `Sprite` plus `Path.move_straight_to(x, y, steps)` moves a renderer across the grid over a number of frames. — [asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html)
- **Large panning motion is a vestibular trigger** (see §7). — [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)

### Inferences
- **Flap row-squash** (verified; output shown). Rows run from the hinge (row 0) to the tip. θ = 0 is closed (pointing down over the envelope face) and θ = π is fully open (pointing up).
  ```python
  FLIP_V = str.maketrans('/\\^v', '\\/v^')
  def hscale(row, s):                      # nearest-neighbour horizontal scale about centre
      w = len(row); nw = max(1, round(w * s)); off = (w - nw) // 2
      out = [' '] * w
      for i in range(nw):
          xx = off + i
          if 0 <= xx < w: out[xx] = row[min(w - 1, int(i * w / nw))]
      return ''.join(out)

  def flap_rows(flap, theta, persp=0.15):
      """Returns [(dy, row)] relative to hinge: dy>=0 below (closed side), dy<0 above (open side)."""
      H = len(flap)
      h = round(H * abs(math.cos(theta)))   # projected height of a rotating plane
      if h == 0: return []                  # edge-on at 90°: draw just the hinge line
      up = theta > math.pi / 2
      out = []
      for i in range(h):
          src = flap[min(H - 1, int(i * H / h))]
          row = hscale(src, 1 + persp * (i / h) * math.sin(theta))  # far edge nearer viewer -> wider
          if up: row = row.translate(FLIP_V)                        # mirrored: '\' <-> '/'
          out.append((-(i + 1) if up else i, row))
      return out
  ```
  Self-check output for a 6-row V flap:
  ```
  theta=0.00 (closed)      theta=1.20                theta=1.90              theta=3.14 (open)
  +0 \''''''''''/          +0 \''''''''''/           -1 /''''''''''\          -1 /''''''''''\
  +1  \        /           +1    \    /              -2    /    \             -2  /        \
  +2   \      /                                                               -3   /      \
  +3    \    /                                                                -4    /    \
  +4     \  /                                                                 -5     /  \
  +5      \/                                                                  -6      /\
  ```
  Practical notes:
  - Drive θ with `θ = π·easeInOutCubic(p)` over about 0.8–1.2 s.
  - Near 90° (h = 0 or 1), draw a single hinge line (`'-'*w`) so the flap never vanishes for a frame.
  - Use different fill glyphs for the flap's outside (closed) and inside (open), e.g. a `:` paper texture, by keeping two art variants and switching at θ > π/2. This sells the 3D flip more than the geometry does.
  - z-order: while θ < π/2 the flap sits above the letter (z=4). Once open it should be behind the letter (z below 2), so the letter can rise in front of it.
  - Nearest-neighbour row sampling drops rows unevenly. For tiny flaps (H ≤ 6), hand-draw 3–4 intermediate keyframes and pick by θ (the hybrid model) rather than squashing.
- **Full open sequence** (suggested timeline, ~3.5 s total):
  1. 0–0.6 s: headline decodes in. Buttons and envelope fade or decode in.
  2. On "yes" (or on load if desired), 0–1.0 s: flap opens, θ: 0→π, easeInOutCubic.
  3. 0.8–1.8 s: letter rises (y offset 0 → −k rows, easeOutBack), clipped by the front pocket layer.
  4. 1.8–2.6 s: envelope (back, front, flap, but not the letter if it stays) slides off, x: 0 → −(W+envW), easeInCubic. Or the whole envelope with the letter slides away, per the brief.
  5. A light heart-particle burst at the open moment (§6).
- **Slide, option A: whole-element CSS transform** (smooth, compositor-friendly; JS):
  ```js
  const p = Math.min(1, (t - tStart) / dur);
  envPre.style.transform = `translateX(${-(cols * easeInCubic(p))}ch)`;   // ch = one cell width in monospace
  // Quantised "on-grid" look: use Math.round(cols * easeInCubic(p)) + 'ch'
  ```
  Pros: no recompositing, sub-cell smoothness, the envelope is its own `<pre>` layered with CSS `z-index`. Cons: the envelope must live in its own element. (CSS `ch` is the advance width of "0", which equals one cell in a monospace font; general CSS knowledge, not verified this session.)
- **Slide, option B: per-frame character shifting in the compositor.** `x = round(lerp(x0, x1, ease_in_cubic(p)))` passed to `compose()`, which clips off-grid columns automatically. Pros: one grid, true char-level look, natural interaction with other layers (e.g. the envelope passing over hearts). Cons: cell-quantised, so slow slides look steppy. At 80 columns over 0.8 s it is fine.
- **Wipe:** a cell is visible if `x < p·W`, or `x + y·0.5 < p·(W + H·0.5)` for a diagonal wipe. A soft edge puts a 2–3 column band of light ramp glyphs (`.:`) at the boundary.
- **Dissolve via density ramp:**
  - Give each cell a fixed threshold `r = hash32(x, y) / 2³²` (stable, so no shimmer).
  - At progress p, a cell's glyph steps down the ramp `@%#*+=-:. ` by `level = clamp(orig_level - round((p*1.5 - r) * N))` and disappears at `' '`.
  - Run in reverse for "materialise". This reads as paper burning or dust, a good alternative exit for the envelope.
- **Fade via colour:** animate CSS `color` or `opacity` on the layer `<pre>`, e.g. `transition: opacity .4s` or rAF-driven. This is cheaper and smoother than glyph ramps and fine for buttons. Combine with a two-step ramp swap (`#`→`+`→`.`) for an ASCII flavour.

### Gaps
- No published source was found specifically for "row-squash" ASCII flap animation. The algorithm above is derived from the standard cos-θ projection of a rotating plane plus a1k0n's perspective divide.
- CSS `steps()` easing and the Web Animations API, which could quantise a CSS transform slide to whole cells declaratively, were not researched.

---

## 6. Procedural effects: donut.c 3D, plasma, particles, Doom fire, matrix rain, floating hearts

### Takeaway
All of these share one pattern: compute a scalar field or particle state per frame, then map values to a glyph ramp and optionally a colour. donut.c adds a z-buffer and Lambert lighting. Doom fire is a 37-level cellular automaton that needs its decay rescaled for short ASCII grids. Particles (hearts, petals) are position-velocity points rendered as small sprites through the compositor.

### Cited Findings
- **donut.c (a1k0n)** — [Donut math](https://www.a1k0n.net/2011/07/20/donut-math.html):
  - **Geometry:** a torus with tube radius R1 = 1 and centre distance R2 = 2, i.e. the circle `(R2 + R1 cos θ, R1 sin θ, 0)` swept by φ around y, then rotated by A about x and B about z.
  - **Lighting:** the normal `(cos θ, sin θ, 0)` gets the same rotations. Light direction is `(0, 1, −1)`, unnormalised, giving `L = Ny − Nz` in `[−√2, √2]`. Skip L ≤ 0.
  - **Glyphs:** `idx = int(L·8)` into `".,-~:;=!*#$@"`, 12 chars from dim to bright, since 8√2 ≈ 11.3.
  - **Sampling:** θ step 0.07 and φ step 0.02; the original C swaps which loop uses which.
  - **Per frame:** A += 0.04, B += 0.02 on an 80x22 grid.
  - **Canvas demo:** the JS canvas version plots directly without a z-buffer, so it is see-through.
- **Doom PSX fire (Fabien Sanglard)** — [Doom fire](https://fabiensanglard.net/doom_fire_psx/):
  - Values are in [0, 36], i.e. a 37-entry palette from black through red, orange and yellow to white.
  - Init: all zeros except the bottom row = 36. The bottom row is never updated, so it is the heat source.
  - Code (`FIRE_WITH` is his typo for `FIRE_WIDTH`):
    `rand = Math.round(Math.random()*3.0) & 3; to = from - FIRE_WIDTH - rand + 1; firePixels[to] = firePixels[from] - (rand & 1);`
    This is looped over `x` in 0..W, `y` in 1..H.
  - `rand & 1` gives decay of 0 or 1 per step. The `-rand+1` offset moves heat sideways, and he notes that wind can be simulated by changing this propagation.
  - The article gives no frame-rate figure and does not describe extinguishing the fire.
- **asciimatics particle systems:** `ParticleEffect` contains `ParticleEmitter`s that spawn `Particle`s. Fireworks chain Rocket, then StarExplosion, then StarTrails. — [asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html)

### Inferences
- **Doom fire on a short ASCII grid** (verified; Python):
  ```python
  RAMP = ' .:-=+*#%@'
  def fire_init(W, H):
      f = [0] * (W * H)
      for x in range(W): f[(H - 1) * W + x] = 36
      return f
  def fire_step(f, W, H, rng=random, decay=1):
      for x in range(W):
          for y in range(1, H):
              src = y * W + x
              r = rng.randint(0, 3)
              dst = src - W - r + 1
              if 0 <= dst < W * H:              # MUST bounds-check: Python wraps negative indices (JS just sets a junk property)
                  f[dst] = max(0, f[src] - (r & 1) * decay)
  def fire_rows(f, W, H):
      n = len(RAMP) - 1
      return [''.join(RAMP[f[y*W + x] * n // 36] for x in range(W)) for y in range(H)]
  ```
  Things the self-check revealed:
  - **Decay must scale with grid height.** Average cooling is 0.5 levels per row, so 36→0 takes about 72 rows. With `decay=1`, a 12-row ASCII fire stayed almost entirely `%#@` (no flame tips). Use `decay ≈ ceil(72 / H)`, e.g. 6 for 12 rows, or fewer palette levels.
  - **Sanglard's `Math.round(rand*3)&3` is not uniform.** It gives P(0)=P(3)=1/6 and P(1)=P(2)=1/3. The decay chance is still 1/2, but the mean sideways offset is −0.5 columns per row, a slight leftward "wind". `randint(0,3)` gives a uniform version with the same −0.5 mean.
  - **Extinguish:** set the bottom row to 0 (or ramp it down over about 1 s) and the flames die out from the base. This follows from the source-row design but is not in the article.
  - For a love-letter theme, swap the palette for pink/red/white and the ramp for `' .:*+x%#'`, or use it as a "burning letter" exit.
- **donut-style 3D for this project.** The same pipeline (parametric surface → rotate → `ooz = 1/z` z-buffer → `L` → ramp) works for a 3D heart. Use a heart surface or a lathed heart curve, apply the 0.5 y-aspect factor, and keep θ/φ steps proportional to grid size. The Python port in the self-check rendered a correct torus at 80x22 but runs about 9,000 samples per frame in pure Python. Run it in JS, or precompute frames in Python and ship them (the hybrid model).
- **Plasma / sine fields** (unsourced recipe): `v = sin(x*a + t) + sin((y*b + t)*0.5) + sin((x*c + y*d + t)*0.7) + sin(hypot(x - cx, y*2 - cy)*e - t)`, normalised to 0..1, then ramp plus a colour gradient. It is cheap and calm at low speeds, good for a soft background behind the envelope. Keep amplitude and colour contrast low so it does not compete with text.
- **Matrix rain** (unsourced recipe): per column keep `head_y`, `speed` (rows/s) and `length`. The head glyph is random per tick (bright), the trail fades down a ramp or colour, and the column resets when `head_y - length > H`. On a romantic page, use `<3` or letter glyphs from "will you" instead of katakana.
- **Floating hearts and petals** (particles; unsourced recipe):
  ```python
  # particle = dict(x, y, vy, phase, sprite); fixed-step update at SIM_DT
  p['y'] += p['vy'] * dt                         # vy ~ -2..-5 rows/s (rise)
  draw_x = p['x'] + 1.5 * math.sin(t * 1.3 + p['phase'])   # sway, cells
  # sprite by depth/size: '.', '*', '<3', or multi-row:
  #   _  _
  #  ( \/ )
  #   \  /
  #    \/
  # fade by swapping sprite to a lighter ramp version for the last ~20% of life
  ```
  Round only at draw time and pass to `compose()` at z=0. Cap at about 20–40 particles. Spawn from the envelope's mouth as the flap opens for a "burst", then let them drift.

### Gaps
- No primary sources were fetched this session for plasma, matrix rain or ASCII heart particle recipes. These are standard demoscene/folk techniques; the recipes above are mine and untested in the self-check, except for the compositor they would use.
- Doom fire's original frame rate is not stated in the article.

---

## 7. Accessibility and comfort: prefers-reduced-motion, flashing limits, pausing

### Takeaway
The page will be in constant motion (churning buttons, fill-churn headline, particles), so it needs:
- a `prefers-reduced-motion: reduce` branch that shows final static states;
- a visible pause control;
- no flashing above 3 times per second over large areas;
- screen-reader-stable labels for any scrambled text.

### Cited Findings
- **WCAG 2.3.1 Three Flashes or Below Threshold (Level A).** Content must not flash more than three times in any one-second period unless it is below the general and red flash thresholds. — [W3C Understanding 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)
- **General flash:** a pair of opposing changes in relative luminance of ≥10% of maximum, where the darker state is < 0.80. **Red flash:** any opposing pair involving saturated red (R/(R+G+B) ≥ 0.8 and a chromaticity difference > 0.2). — [W3C 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)
- **Area threshold:** concurrent flashing within any 10° visual field must stay ≤ 25%, about 0.006 sr or **341x256 CSS px (87,296 px²)**. Fine balanced patterns, such as white noise or checkerboards with squares under 0.1°, do not count. — [W3C 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)
- **`prefers-reduced-motion` values.** `no-preference` and `reduce`; `@media (prefers-reduced-motion)` equals `reduce`. The setting "removes, reduces, or replaces motion-based animations". Scaling or panning large objects can trigger vestibular disorders. MDN's example swaps a scale pulse for a gentle opacity dissolve. — [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- **OS switches that set `reduce`:**
  - Windows 11: Settings > Accessibility > Visual Effects > Animation Effects (off)
  - Windows 10: Ease of Access > Display > Show animations
  - macOS ≤15: Accessibility > Display > Reduce motion; macOS 26 "Tahoe": Accessibility > Motion
  - iOS: Accessibility > Motion
  - Android 9+: Remove animations
  - GNOME: "Reduced animation"; KDE: Animation speed "Instant"
  - Firefox testing: `about:config` → `ui.prefersReducedMotion = 1`
  — [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion). MDN's text reads "macOS 25 (Tahoe)"; Tahoe is macOS 26, so MDN's number looks off.
- **Background tabs.** rAF is paused in background tabs, so off-screen animation already costs nothing there. — [MDN rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
- **Baffle** excludes spaces from obfuscation by default, a small legibility affordance. — [Baffle](https://github.com/camwiegert/baffle)

### Inferences
- **Reduced-motion branch** (JS, not run):
  ```js
  const rm = matchMedia('(prefers-reduced-motion: reduce)');
  let reduce = rm.matches;
  rm.addEventListener('change', e => { reduce = e.matches; });
  // In render(): if (reduce) -> headline static (no fill churn), buttons show true words,
  // envelope opens with a short cross-fade (opacity) instead of flap-squash + slide, no particles.
  ```
  The `matchMedia` and change-listener pattern is standard. MDN's fetched section did not include it, so the fetch tool's note supplied it from general knowledge.
- **Flash risk in this design.**
  - Glyph churn on dense fills (e.g. `#`↔`@` fill churn) causes only small luminance changes per cell and is closer to a "fine balanced pattern" than a flash. It is low risk.
  - A full-screen colour invert, a white flash when the envelope opens, or a large glitch on a dark background toggling more than 3 times/s would violate 2.3.1. Keep any "flash" to one pulse, and keep big colour changes at ≥ 333 ms per half-cycle.
  - Cursor blink at 1–2 Hz is safe.
- **Pause control.** A small ASCII `[ || pause ]` toggle that stops the rAF loop (or freezes `t`) and stops churn. Persist the choice in `localStorage` inside try/catch.
- **Screen readers and semantics:**
  - Mark decorative ASCII art `aria-hidden="true"`, or wrap the envelope in `role="img" aria-label="An envelope with a love letter"`.
  - Buttons must be real `<button>` elements with `aria-label="Yes"` / `aria-label="No"`. Their scrambled visual `<pre>` should be `aria-hidden="true"` so assistive tech never hears "v-e-s".
  - The headline should be a real `<h1>` with visually hidden text "Will you open?", and its FIGlet `<pre>` `aria-hidden`.
  - Never use `aria-live` on churning text.
- **Comfort.** Keep the envelope slide short (≤ 0.8 s) and one-directional. Avoid elastic or bounce on large blocks, and avoid parallax-style continuous panning of big ASCII layers: MDN names panning large objects as a vestibular trigger.

### Gaps
- **WCAG 2.2.2 Pause, Stop, Hide (Level A)** and **2.3.3 Animation from Interactions (AAA)** were not fetched; the 2.3.1 page does not mention them. From general knowledge, unverified this session:
  - 2.2.2 requires a mechanism to pause, stop or hide auto-starting moving content that lasts more than 5 s and is presented in parallel with other content. The constantly-churning buttons and headline would fall under it, hence the pause control above.
  - 2.3.3 asks that motion triggered by interaction can be disabled.
  Verify both at w3.org/WAI/WCAG22/Understanding before relying on them.
- No research was found on how screen readers handle large `<pre>` ASCII art specifically, beyond the general `aria-hidden` and `role="img"` practice above, which is itself unsourced here.
