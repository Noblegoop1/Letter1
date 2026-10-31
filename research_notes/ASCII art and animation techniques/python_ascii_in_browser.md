# Python-driven ASCII art and ASCII animation in a static GitHub Pages site

Research date: 2026-10-31. Release versions below were read from the live releases pages and changelogs on that date. Where a release page showed only day and month, the year comes from the version tag and is noted as such.

## 1. PyScript as of late 2026: version, CDN URLs, runtimes, FFI, animation loop, config

### Takeaway
The current PyScript release is **2026.7.3** (29 Jul 2026). It loads from `https://pyscript.net/releases/2026.7.3/core.js` and `.../core.css`. Since 2026.6.1 it supports only two runtimes: MicroPython (`type="mpy"`, about 170 KB compressed, near-instant start) and Pyodide (`type="py"`, full CPython 3.14 with micropip, several MB and seconds to start). For an animation-only love letter that needs no PyPI packages, MicroPython is the right default. Drive the frame loop by passing one long-lived `create_proxy`'d Python function to `window.requestAnimationFrame`.

### Cited Findings
**Versions and releases**
- Latest PyScript releases, newest first: 2026.7.3 (29 Jul), 2026.7.2 (09 Jul), 2026.7.1 (01 Jul), 2026.6.2 (30 Jun), 2026.6.1 (16 Jun), 2026.3.1 (02 Mar). No release after 2026.7.3 was listed on 2026-10-31. — [pyscript/pyscript releases](https://github.com/pyscript/pyscript/releases)
- 2026.7.3 updates Pyodide to **314.0.3**. Earlier steps: 2026.7.1 moved to 314.0.2, 2026.6.2 to 314.0.1, and 2026.6.1 to Pyodide's Python 3.14 line (314.0.0). — [pyscript/pyscript releases](https://github.com/pyscript/pyscript/releases)
- 2026.6.1 is marked **Breaking**: "Other runtimes have mostly been removed due little interest", which leaves MicroPython and Pyodide. Experimental remote packages are now supported by default. — [pyscript/pyscript releases](https://github.com/pyscript/pyscript/releases)
- 2026.3.1 updated MicroPython, adding `weakref`, template strings, complete `asyncio.Future`, and four wasm variants. — [pyscript/pyscript releases](https://github.com/pyscript/pyscript/releases)
- The newest Pyodide is **314.0.7** (14 Sep 2026). Maintenance releases 0.29.5 and 0.27.8 followed on 15 Sep 2026. The major number tracks the Python version: 314.0.0 moved to Python 3.14.2, 0.28 to 3.13, 0.27 to 3.12. — [Pyodide changelog](https://pyodide.org/en/stable/project/changelog.html)

**CDN URLs and page skeleton**
- CSS: `https://pyscript.net/releases/2026.7.3/core.css`. JS: `https://pyscript.net/releases/2026.7.3/core.js`, loaded as `<script type="module" src="...">`. — [PyScript 2026.7.3 Beginning PyScript](https://docs.pyscript.net/2026.7.3/beginning-pyscript/)
- Script tag form: `<script type="py" src="./main.py" config="./pyscript.json"></script>`. The config "must be either a `json` or `toml` file", and the file name "doesn't matter". — [Beginning PyScript](https://docs.pyscript.net/2026.7.3/beginning-pyscript/)
- "Any static web host will work". The docs name GitHub Pages, S3, Google Cloud and Azure. Local testing uses `python3 -m http.server`. An `offline.zip` release asset bundles Pyodide and MicroPython for self-hosting. — [Beginning PyScript](https://docs.pyscript.net/2026.7.3/beginning-pyscript/)
- Unversioned `docs.pyscript.net/latest/...` URLs redirect to `/2026.7.3/...`, which confirms that 2026.7.3 is the current docs version. — [docs.pyscript.net/latest redirect](https://docs.pyscript.net/latest/beginning-pyscript/)

**MicroPython (`mpy`) vs Pyodide (`py`)**
- MicroPython: "Compressed for delivery, it's only about 170KB". It has "a subset of the standard library" and cannot install packages, but you can add code through `files`. — [PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/)
- Pyodide: "full CPython compatibility", the standard library, and PyPI packages through micropip. The trade-off is a "larger file size" and "slower initial load compared to MicroPython". — [PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/)
- Earlier MicroPython technical preview: about 303 KB, starting in under 100 ms. — [Anaconda blog](https://www.anaconda.com/blog/pyscript-updates-bytecode-alliance-pyodide-and-micropython); [MicroPython tech preview](https://pyscript.net/tech-preview/micropython/about.html)
- Pyodide roadmap: a first load "requires a 6.4 MB download" and environment initialization "takes 4 to 5 seconds". The page names no version, so the figure may be stale. — [Pyodide roadmap](https://pyodide.org/en/stable/project/roadmap.html)
- One documented hybrid pattern starts with a MicroPython UI, which loads fast, while Pyodide loads in the background. — [search summary of spylang/spy issue #311](https://www.goodfirstissue.org/spylang/spy/issues/311)

**FFI**
- Both interpreters "implement almost the same Foreign Function Interface", and `pyscript.ffi` "works consistently across both interpreters". — [PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/)
- `pyscript.ffi` exports `to_js`, `create_proxy`, `is_none` (true for both JS `null` and `undefined`), `assign` (like `Object.assign`), and the worker utilities `direct`, `gather` and `query`. `to_js` turns Python dicts into JS objects, not Maps. Runtime-specific features are in `pyodide.ffi` and `micropython.ffi`, but using them breaks cross-interpreter compatibility. — [PyScript FFI guide](https://docs.pyscript.net/2026.7.3/user-guide/ffi/)
- Why `create_proxy` is needed: without it, "the Python function would be garbage collected immediately". The docs example is `button.addEventListener("click", create_proxy(handle_click))`. With `pyscript.web` and `@when`, "proxies are created automatically". — [PyScript FFI guide](https://docs.pyscript.net/2026.7.3/user-guide/ffi/)
- The `pyscript` context module exports `window` and `document`, each "proxied if in a worker". It also exports `RUNNING_IN_WORKER`, `config`, `sync`, `js_import` (dynamic JS module import), `PyWorker` and `current_target`. On the main thread, `window` and `document` "are available directly". In a worker they are proxied "if SharedArrayBuffer available". — [PyScript API: context](https://docs.pyscript.net/2026.7.3/api/context/)
- `from pyscript import js` gives "anything available in JavaScript's global scope". — [PyScript FFI guide](https://docs.pyscript.net/2026.7.3/user-guide/ffi/)
- Pyodide rule: "If it's only going to be called once use create_once_callable()". "If it's going to be called many times use create_proxy()", and keep a reference to it. "Make sure to destroy PyProxies when you are done with them to avoid memory leaks." — [Pyodide type conversions](https://pyodide.org/en/stable/usage/type-conversions.html)
- Pyodide: strings convert implicitly. Large buffers through `toJs()` copy and "will be extremely slow" for something like 1920x1080x4. Use `getBuffer()` instead. — [Pyodide type conversions](https://pyodide.org/en/stable/usage/type-conversions.html)

**Events and the `when` decorator**
- Signature: `when(event_type, selector=None, **options)`. — [PyScript API: events](https://docs.pyscript.net/2026.7.3/api/events/)
- Usage: `@when("click", "#my-button")`. The target can be a `web.button(...)` element or an `ElementCollection` from `web.page.find(".cls")`. The plain-call form `when("click", el)(handler)` works for elements created later. Options are `once=True`, `capture` and `passive=True`. Handlers can be `async` and can leave out the event argument. A custom `Event()` provides `.trigger(data)`. Warning: the decorator only binds elements that exist when it runs. — [PyScript Events guide](https://docs.pyscript.net/2026.7.3/user-guide/events/)
- DOM helpers: `web.page["#id"]` returns an Element or None. `web.page.find("css")` returns an ElementCollection. Elements have `.innerHTML` and `.textContent`. Classes act like a `set` and styles like a `dict`. The docs recommend `pyscript.web` for most work and the FFI for browser APIs that lack wrappers. The two can be mixed. — [PyScript DOM guide](https://docs.pyscript.net/2026.7.3/user-guide/dom/)
- Lifecycle events: `py:ready` or `mpy:ready` fires per interpreter. `py:done` fires "after every single script referenced from the page has finished", and `mpy:done` is the MicroPython equivalent. — [PyScript 2024.4.1 Architecture (lifecycle)](https://docs.pyscript.net/2024.4.1/user-guide/architecture/); [search summary of 2026.x api/events pages](https://docs.pyscript.net/2026.3.1/api/events/)
- Calling Python from JS: the bridge API (`import bridge from 'https://esm.run/@pyscript/bridge'`) turns Python functions into async JS functions. The donkey API (`import { donkey } from 'https://pyscript.net/releases/2026.7.3/core.js'`) evaluates Python on demand in a worker. — [PyScript from JavaScript](https://docs.pyscript.net/2026.7.3/user-guide/from_javascript/)

**Config (`pyscript.toml` / `config` attribute / `[files]`)**
- `[files]` maps a source URL or path to a destination on the virtual filesystem. TOML example: `"./code.py" = "./subdir/code.py"`. JSON example: `"files": {"./code.py": "./subdir/code.py"}`. An empty destination puts the file at root. A destination ending in `/` keeps the source filename. Placeholders such as `"{FROM}"` and `"{TO}"` (any `{NAME}` in braces) build paths, e.g. `"{FROM}/__init__.py" = "{TO}/__init__.py"`. — [PyScript Configuration](https://docs.pyscript.net/2026.7.3/user-guide/configuration/)
- Inline config: `config='{"packages":["arrr"]}'`. Or one `<py-config>` / `<mpy-config>` tag per interpreter on the page. — [PyScript Configuration](https://docs.pyscript.net/2026.7.3/user-guide/configuration/)
- Interpreter pinning: `interpreter = "0.29.0"` or a full URL such as `https://cdn.jsdelivr.net/pyodide/v0.29.0/full/pyodide.mjs`. For MicroPython, `packages` resolve from a MicroPython repository, not PyPI. — [PyScript Configuration](https://docs.pyscript.net/2026.7.3/user-guide/configuration/)

**requestAnimationFrame semantics (apply whatever the language)**
- The callback gets a `DOMHighResTimeStamp`. Its rate "will generally match the display refresh rate", which may be 60, 75, 120 or 144 Hz. It "paused in most browsers when running in background tabs". Compute progress from the timestamp, or the animation "will run faster on high refresh-rate screens". — [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)

### Inferences
- **Recommended skeleton for the love letter.** Not run in a browser in this research. Assembled from the cited APIs.
  ```html
  <link rel="stylesheet" href="https://pyscript.net/releases/2026.7.3/core.css">
  <script type="module" src="https://pyscript.net/releases/2026.7.3/core.js"></script>
  <pre id="stage" role="img" aria-label="An envelope opens and a letter slides out"></pre>
  <script type="mpy" src="./main.py" config="./pyscript.toml"></script>
  ```
  `pyscript.toml`:
  ```toml
  [files]
  "./ascii/frames.py" = "./ascii/frames.py"
  "./ascii/scramble.py" = "./ascii/scramble.py"
  ```
  `main.py` (rAF loop: one proxy created once, one boundary crossing per frame):
  ```python
  from pyscript import window, document
  from pyscript.ffi import create_proxy
  from ascii.frames import render   # pure function: render(t_ms) -> str

  stage = document.getElementById("stage")
  def tick(ts):
      stage.textContent = render(ts)          # whole frame as ONE string
      window.requestAnimationFrame(tick_proxy)
  tick_proxy = create_proxy(tick)            # reuse; do not create a proxy per frame
  window.requestAnimationFrame(tick_proxy)
  ```
- With Pyodide, a fresh `create_once_callable` per frame would also work. Creating one `create_proxy` and reusing it avoids per-frame proxy churn. That pattern follows from the Pyodide rule "called many times use create_proxy()". It has not been benchmarked.
- Choose MicroPython. A love letter needs `random`, `math` and string work, which MicroPython has. Its about-170 KB payload against Pyodide's multi-MB load decides the first impression. Pyodide only pays off if you need numpy or other PyPI packages.
- Avoid worker mode (`worker` attribute) on GitHub Pages. Workers need SharedArrayBuffer to reach `window` and `document`. That normally requires COOP/COEP response headers, and GitHub Pages does not let you set custom headers (see section 6).
- The constantly changing button words fit `setInterval` (via `window.setInterval(create_proxy(fn), 80)`) or the same rAF loop with time-sliced updates. Words changing at 10-15 Hz are enough and reduce work.

### Gaps
- No official 2026 cold-start numbers for Pyodide 314.x or PyScript MicroPython were found. The 6.4 MB / 4-5 s Pyodide figure is from an undated roadmap. Measure in DevTools on the deployed page.
- Not verified: whether `create_proxy` is strictly needed under MicroPython or is a pass-through there. The FFI guide states the requirement without separating runtimes. Using `pyscript.ffi.create_proxy` is safe on both.
- The current docs pages fetched did not show `py:ready`/`py:done` events. They were confirmed only in the 2024.4.1 docs and in search snippets of 2026.x API pages. An unconfirmed `py:all-done` was also mentioned in a third-party article.
- `type="mpy"` script-tag syntax was not quoted from the 2026.7.3 page itself. It follows the documented `type="py"` pattern and is used in PyScript's own tests (see section 8).

## 2. Alternatives: Brython, plain Pyodide, Transcrypt, and Python as a build step

### Takeaway
- **Brython 3.15.0** (10 Oct): transpiles Python in the browser and has a native `browser.timer.request_animation_frame` wrapper.
- **Plain Pyodide 314.0.7:** the same engine as PyScript `py`, without the PyScript layer.
- **Transcrypt 3.9.5** (20 Jun 2026): compiles a Python 3.9 subset to small JS ahead of time.
- **Build step:** Python pre-generates frames or HTML and a few lines of JS play them. This is the fastest and most robust option for GitHub Pages, with zero runtime download.

### Cited Findings
- Brython releases: 3.15.0 (10 Oct; adds lazy imports, the `frozendict` and `sentinel` builtins, and unpacking in comprehensions), 3.14.3 (19 Jun), 3.14.2 (13 Jun), and 3.14.1 (02 May; major rewrite of built-in types). The page showed no year. — [brython-dev/brython releases](https://github.com/brython-dev/brython/releases)
- Brython `browser.timer.request_animation_frame(function)` wraps the JS `requestAnimationFrame`. It returns an id for `cancel_animation_frame(id)`. — [Brython docs: browser.timer (3.12)](https://brython.info/static_doc/3.12/en/browser.timer.html); [Brython timer (3.11)](https://brython.info/static_doc/3.11/en/timer.html)
- Plain Pyodide: newest 314.0.7 (14 Sep 2026). CDN pattern from PyScript's pin example: `https://cdn.jsdelivr.net/pyodide/v{version}/full/pyodide.mjs`. — [Pyodide changelog](https://pyodide.org/en/stable/project/changelog.html); [PyScript Configuration](https://docs.pyscript.net/2026.7.3/user-guide/configuration/)
- Transcrypt latest is 3.9.5 (Jun 20, 2026). Earlier: 3.9.4 (Jun 1, 2025), 3.9.3 (Jul 28, 2024). It targets "Pure Python 3.9 syntax". — [PyPI Transcrypt](https://pypi.org/project/Transcrypt/)
- Transcrypt compiles "a fairly extensive subset of Python into compact, readable Javascript". — [PyPI Transcrypt 3.5.x page](https://pypi.org/project/Transcrypt/3.5.236/)
- Pages "does not support server-side languages like PHP, Ruby or Python". Any Python must run either in the browser or at build time. — [GitHub Docs (de): Creating a GitHub Pages site](https://docs.github.com/de/pages/getting-started-with-github-pages/creating-a-github-pages-site)

### Inferences
- **Trade-off summary** (from the facts above plus general engineering judgement):

| Option | First-load cost | Python at runtime? | Animation smoothness | Fit for the love letter |
|---|---|---|---|---|
| PyScript `mpy` | ~170 KB + core.js | Yes (MicroPython) | Good if one string is pushed per frame | **Best "Python in browser"** |
| PyScript `py` / plain Pyodide | Multi-MB, seconds | Yes (CPython 3.14) | Good after load; slow start | Only if PyPI is needed |
| Brython 3.15 | Transpiler + stdlib JS (size not measured here) | Transpiled at load | Good; runs as JS | Viable; less maintained ecosystem fit |
| Transcrypt 3.9.5 | Tiny JS | No (compiled) | Native JS speed | Python 3.9 subset only; extra toolchain |
| Python build step -> JSON frames + JS player | Frames only (KB-MB) | No | Best | Most robust; loses "live Python" |

- **Hybrid recommended for robustness.** Write all ASCII logic as pure Python (frames, scramble words, headline FIGlet-style glyphs) so it can run both as a build script and in PyScript `mpy`. Ship PyScript as the "written in Python" showpiece. Optionally pre-render the heavy headline at build time.
- A build-step player can be about 15 lines of JS: fetch `frames.json` and set `pre.textContent = frames[i]` inside rAF.
- Brython's CDN is likely `https://cdn.jsdelivr.net/npm/brython@3.15.0/brython.min.js` plus `brython_stdlib.js`. This is not verified (see Gaps).

### Gaps
- Brython CDN URLs and download sizes were not verified. The release page showed no asset links. The 3.15.0 year is inferred as 2026 from the version sequence.
- No 2026 benchmark comparing Brython, Pyodide and MicroPython speed for string-heavy per-frame work was found.

## 3. Performance of per-frame ASCII updates (textContent vs spans vs rows vs canvas; boundary cost)

### Takeaway
No head-to-head benchmark of `<pre>.textContent` against canvas `fillText` for ASCII frames was found. Terminal-renderer history (VS Code, xterm.js) ranks DOM text slowest for high-throughput full-screen updates, canvas next, and WebGL fastest. For a 160x60 grid (about 9.7 KB per frame) the dominant rule is to cross the Python-to-JS boundary once per frame with one string. Spans and canvas are for colour.

### Cited Findings
- VS Code moved its integrated terminal off DOM rendering in 2017 because of a performance ceiling set by the browser's layout engine. — [VS Code blog: Integrated Terminal Performance Improvements](https://code.visualstudio.com/blogs/2017/10/03/terminal-renderer)
- xterm.js 4.3.0 (2020): its WebGL renderer drew frames "up to 900% faster than canvas" in the project's own benchmark. Canvas remains "still fast compared with the DOM renderer" when no GPU is available. — [xterm.js 4.3.0 release](https://github.com/xtermjs/xterm.js/releases/tag/4.3.0); [xterm.js issue #4574](https://github.com/xtermjs/xterm.js/issues/4574)
- WebGL is faster because canvas makes many separate draw calls, while WebGL batches glyphs into one GPU pass. — [xterm.js PR #1790](https://github.com/xtermjs/xterm.js/pull/1790)
- Canvas glyph caching (pre-render glyphs, then `drawImage`) is a known optimisation over repeated `fillText`. — [gist: fillText vs drawImage](https://gist.github.com/subzey/30d069bf4eb7b537311c7e9a3b2b9c6b)
- MeasureThat warns that canvas text benchmark results "can vary across different devices and browsers". — [MeasureThat fillText/strokeText](https://www.measurethat.net/Benchmarks/Show/34747/1/canvas-filltext-stroketext)
- Pyodide: each Python-to-JS translation "may create a PyProxy". Strings convert implicitly. Large buffer conversions via `toJs()` are slow. — [Pyodide type conversions](https://pyodide.org/en/stable/usage/type-conversions.html)

### Inferences
- **Grid math.** 160x60 is 9,600 cells plus 60 newlines, about 9.7 K characters. One `textContent` write per frame is one FFI call and one string conversion. Even at 60 fps that is about 580 KB/s of string transfer, which is trivial. Setting 9,600 span elements individually means about 9,600 FFI calls per frame. That will not hold 60 fps under MicroPython or Pyodide, so never touch individual cells from Python.
- **Ranking for this project** (cheapest first):
  1. **Single `<pre>`, `textContent = frame`** for monochrome frames. Text-only replacement still triggers layout of that subtree. Give the `<pre>` fixed dimensions and `contain: strict` (or `contain: layout paint`) so it cannot reflow the page.
  2. **Per-row `<div>`s** with a dirty-row diff in Python: send only rows that changed. Good when a small region animates, such as the button words or a sliding letter edge.
  3. **`innerHTML` with run-length-coalesced `<span class="c3">...</span>`** for colour. Build the whole HTML string in Python and assign it once. Cost grows with span count, so merge runs of the same colour.
  4. **Canvas `fillText` per row** (60 calls/frame) or per colour run, for full-frame colour effects such as a rainbow-shimmer headline. Canvas text is not selectable or readable by screen readers, so it needs its own `aria-label`.
- 30 fps is plenty for ASCII. Throttle inside the rAF callback (`if ts - last < 33: return`) to halve Python work on 120/144 Hz displays. Use timestamps for motion, per MDN.
- Separate the static layers (the envelope body) from the animated ones (flap, letter, headline shimmer) so each frame re-renders only the moving layer (see section 5).

### Gaps
- No published 2025-2026 benchmark measured `textContent` vs `innerHTML` spans vs canvas for ASCII grids. No measurement of PyScript per-call FFI overhead (in µs) for MicroPython or Pyodide was found. Profile in Chrome DevTools Performance on a mid-range phone.

## 4. Typography: font stacks, touching rows, measuring cells, fitting N columns, mobile, colour

### Takeaway
Use the `ch` unit. In a monospace font, 1ch equals the cell advance width, so a grid of N columns is exactly N ch wide. Set `line-height` to a fixed value (for example `1` or `1.1`) so rows touch. Derive `font-size` from the viewport (`vw`/`svw`) and a measured ch/em ratio. Colour with spans, `text-shadow` glow, or `background-clip: text` gradients on whole blocks.

### Cited Findings
- `ch` is "the width or, more precisely, the advance measure of the glyph `0`" in the element's font. If it cannot be determined, it is assumed to be `0.5em` wide. — [MDN CSS length](https://developer.mozilla.org/en-US/docs/Web/CSS/length)
- `1vw` is 1% of the viewport width. `vw` equals `lvw`. Small (`svw`) units "are fixed, and therefore stable, unless the viewport itself is resized". Dynamic (`dvw`) units "are not stable". — [MDN CSS length](https://developer.mozilla.org/en-US/docs/Web/CSS/length)
- `cap` is the font's cap height. `ic` is the advance of "水". — [MDN CSS length](https://developer.mozilla.org/en-US/docs/Web/CSS/length)

### Inferences
These rest on standard CSS and DOM behaviour; the specific pages were not fetched this session.
- **Font stack:** `font-family: ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas, "DejaVu Sans Mono", "Liberation Mono", monospace;`. For pixel-identical layout everywhere, self-host one font (for example JetBrains Mono or IBM Plex Mono, both OFL) as WOFF2. Wait for `document.fonts.ready` before measuring.
- **Rows touch:** `line-height: 1;` (or `1.0`-`1.15` for box-drawing art), `margin: 0; white-space: pre; letter-spacing: 0;`, and `font-variant-ligatures: none;` so `==` and `->` do not merge.
- **Measure the cell in JS** (or from Python via FFI, once at start and on resize). Put 100 copies of `M` in a hidden span and read `getBoundingClientRect().width / 100` for cell width, and the height of a one-line span for cell height. Alternatively use canvas `ctx.measureText("M").width` with the same `font` string.
- **Fit N columns:** `font-size = viewportWidthPx / (N * chPerEm)`, where `chPerEm` = measured cell width / font-size. It is often about 0.6 for common monospace fonts but must be measured. A pure-CSS approximation is `font-size: calc(100svw / (160 * 0.6))`. On phones (about 360-430 CSS px), 160 columns gives roughly a 3.75 px font: decorative only. Ship a narrower mobile composition (for example 60-80 columns) chosen by a media query or by Python reading `window.innerWidth`.
- **Colour:**
  - Neon glow: `color:#ff5fa2; text-shadow: 0 0 2px #fff, 0 0 8px #ff5fa2, 0 0 18px #ff2d7a;`. Heavy multi-layer shadows on a large `<pre>` that re-renders every frame are expensive. Put the glow on the static or slowly changing headline, or animate `opacity` of a duplicate glow layer instead.
  - Gradients: `background: linear-gradient(...); -webkit-background-clip: text; background-clip: text; color: transparent;` on the headline `<pre>`. Animate `background-position` for a shimmer. That repaints but needs no text re-render.
  - Per-character colour: spans with a few classes, coalesced into runs (section 3).

### Gaps
- MDN pages for `measureText`, `text-shadow`, `background-clip: text` and `font-variant-ligatures` were not fetched this session. The CSS above is standard but unchecked against 2026 browser-compat tables.
- No source measured the ch/em ratio of system monospace fonts across Windows, macOS, iOS and Android.

## 5. Moving whole ASCII blocks: CSS transforms vs re-rendering characters

### Takeaway
Use CSS `transform` (translate, and `rotateX` under `perspective` for the flap) and `opacity` on separate `<pre>` layers for the envelope opening and the letter sliding out. These run on the compositor without layout or paint and are sub-pixel smooth. Re-render characters only where the content itself changes (the scrambling button words, the headline shimmer).

### Cited Findings
- "The best-performing version of the pixel pipeline avoids both layout and paint, and only requires compositing changes." The compositor-only properties are "`transform`s and `opacity`", on an element that is "on its own compositor layer". Promote it with `will-change: transform`. Every layer "requires memory and management", so "Do not promote elements unnecessarily". — [web.dev: Stick to compositor-only properties](https://web.dev/articles/stick-to-compositor-only-properties-and-manage-layer-count)
- MDN's rAF example animates `element.style.transform = translateX(...)` from the elapsed timestamp. — [MDN requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)

### Inferences
- Re-rendering characters can only move a block in whole-cell steps (about 6-10 px jumps), which looks choppy. A `translateY` transition is continuous and costs Python nothing per frame.
- **Envelope recipe:**
  - A parent `.envelope { perspective: 800px; }` holds three absolutely positioned `<pre>`s: `.back` (body), `.letter` (z between), and `.flap` (top triangle).
  - Set `.flap { transform-origin: top center; transition: transform .8s ease; backface-visibility: hidden; }`. On open, apply `.flap.open { transform: rotateX(180deg); }`.
  - For an ASCII "inside of flap" pattern, use a second `<pre>` pre-rotated by `rotateX(180deg)` with `backface-visibility: hidden` as the back face.
  - Then `.letter { transition: transform 1.2s cubic-bezier(.2,.8,.2,1) .6s; }` and `.letter.out { transform: translateY(-60%); }`. Python only toggles classes (`el.classes.add("open")` via `pyscript.web`), so it makes one FFI call per state change.
- Use `will-change: transform` only on the flap and the letter during the sequence, and remove it afterwards (layer-cost guidance).
- Prefer CSS transitions or `element.animate()` (Web Animations API) for these motions over per-frame Python-driven transforms. They keep running smoothly even when the Python rAF loop is busy rendering the headline.

### Gaps
- No source compared the visual smoothness of transform-animated `<pre>` against character re-rendering directly. The recommendation follows from the compositor guidance.
- Not verified: whether 3D-transformed text stays crisp in every browser. Some browsers rasterise transformed text and may blur it mid-animation. Test in Safari, Chrome and Firefox.

## 6. GitHub Pages: static constraints, deploy modes, .nojekyll, MIME types, limits, caching, project-page paths

### Takeaway
GitHub Pages serves static files only. You cannot set MIME types or custom headers: MIME types come from mime-db, and the cache TTL has been observed as about 10 minutes. Deploy from a branch (root or `/docs`) with a `.nojekyll` file, or through an Actions workflow (`upload-pages-artifact` + `deploy-pages`). Loading PyScript from `pyscript.net` means `.wasm` is served by that CDN, not by Pages. Your repo only serves `.html`, `.py` and `.toml`, and every path must be relative because project pages live under `/<repo>/`.

### Cited Findings
**Limits**
- The published site may be no larger than 1 GB, and deployments time out after 10 minutes. The bandwidth soft limit is 100 GB/month. Builds have a soft limit of 10 per hour, which does not apply to custom Actions workflows. The recommended source repo size is at most 1 GB. Rate limiting returns HTTP `429`. — [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)
- Pages is not for commercial, e-commerce or SaaS sites, or for "sending passwords or credit card numbers". — [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)

**URLs and static-only**
- User sites live at `http(s)://<owner>.github.io` and project sites at `http(s)://<owner>.github.io/<repositoryname>`. Pages takes "HTML, CSS, and JavaScript files straight from a repository". — [About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)
- There is no support for server-side languages, Python included. — [GitHub Docs (de)](https://docs.github.com/de/pages/getting-started-with-github-pages/creating-a-github-pages-site)

**Deploy modes**
- Branch deploy publishes from any branch, from root `/` or `/docs`, with Jekyll as the default build. GitHub Actions deploy uses `actions/checkout`, `actions/upload-pages-artifact` and `actions/deploy-pages` with a `github-pages` environment. Commits pushed with `GITHUB_TOKEN` do not trigger a Pages build. External CI that commits output "typically include a `.nojekyll` file". — [Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)

**Jekyll and .nojekyll**
- By default Jekyll does not build files or folders that "Start with `_`, `.`, or `#`". — [About GitHub Pages and Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll)
- An empty `.nojekyll` in the root of the publishing source bypasses Jekyll. — [GitHub blog 2009: Bypassing Jekyll](https://github.blog/2009-12-29-bypassing-jekyll-on-github-pages); [GitHub Docs (ja), setting up with Jekyll](https://docs.github.com/ja/articles/setting-up-a-github-pages-site-with-jekyll)

**MIME types**
- The MIME list is generated from mime-db, covering more than 750 types. Custom MIME types cannot be set per file or per repo. Changes go through mime-db. — [GitHub Docs: MIME types on GitHub Pages (Enterprise 2.4 archive)](https://docs.github.com/enterprise/2.4/user/articles/mime-types-on-github-pages)
- A community thread reported a `.wasm` MIME failure, and the answer pointed to mime-db. Current status unknown. — [GitHub community discussion #22863](https://github.com/orgs/community/discussions/22863)

**Caching**
- `Cache-Control: max-age=600` has been observed on Pages responses (older, secondhand sources). Claims about longer TTLs for assets conflict. — [GitLab Pages issue #69](https://gitlab.com/gitlab-org/gitlab-pages/-/issues/69); [Stack Overflow mirror: GitHub Pages HTTP headers](https://dev.library.kiwix.org/content/stackoverflow_en_nopic_2021-08/questions/14798589/github-pages-http-headers)

### Inferences
- **Relative paths everywhere.** Use `src="./main.py"`, `config="./pyscript.toml"`, and `[files]` keys like `"./ascii/frames.py"`. A root-absolute `/main.py` resolves to `owner.github.io/main.py` and 404s on a project site.
- **Use `.nojekyll`.** Without it, a folder like `_ascii/` or a file like `_frames.py` disappears silently. Simplest setup: branch deploy from `main` root (or `/docs`) with a `.nojekyll`. Use Actions only if a Python build step generates frames, in which case run `python build.py` in the workflow before `upload-pages-artifact`.
- **MIME concerns are minor here.** `.py` and `.toml` are fetched by PyScript with `fetch()` and read as text, so their exact Content-Type is unlikely to matter. `.wasm` comes from `pyscript.net` or jsDelivr unless you self-host `offline.zip`. If you self-host, verify with `curl -I https://<owner>.github.io/<repo>/.../micropython.wasm` that the type is `application/wasm`. Streaming compilation requires it.
- **No COOP/COEP headers.** Custom headers cannot be set, so cross-origin isolation, and with it SharedArrayBuffer-dependent PyScript worker features, is unavailable without a service-worker shim. Keep everything on the main thread.
- **The 10-minute cache** means friends may see a stale version for up to about 10 minutes after a push. Append `?v=2` query strings to `main.py` and `pyscript.toml` references when iterating.

### Gaps
- The current official English docs.github.com text for `.nojekyll`, and a current list of Pages response headers (Cache-Control, CORS), were not found. Confirm with `curl -I` after the first deploy.
- The 100 MB per-file push limit belongs to GitHub repositories generally, not to the Pages docs fetched. It is irrelevant at this project's scale.
- Not confirmed: whether Pages currently serves `.toml` and `.wasm` with correct types.

## 7. Accessibility: ASCII art and screen readers, real buttons, focus, reduced motion

### Takeaway
Wrap each ASCII picture in an element with `role="img"` and a meaningful `aria-label`, per W3C technique H86. Hide purely decorative or animated character soup with `aria-hidden="true"`. Use real `<button>` elements whose accessible name stays stable while the visible ASCII text scrambles. Honour `prefers-reduced-motion: reduce` by showing static final frames.

### Cited Findings
- ASCII art "can be very confusing to people who are accessing the internet using screen readers". The fix is `role="img"` on the containing element plus `aria-label` as the text alternative. A skip link is helpful if the art is not marked up as an image. — [W3C WCAG Technique H86](https://www.w3.org/WAI/WCAG21/Techniques/html/H86)
- In 2010 VoiceOver testing, `<pre role="img" aria-labelledby=...>` was announced as an image, which the tester found exactly right. This is historical evidence. — [public-html list, 2010](https://lists.w3.org/Archives/Public/public-html/2010Mar/0553.html)
- `aria-label` is prohibited on generic elements (a plain div or span without a role), so pair it with `role="img"`. Decorative art can use `aria-hidden`. — [32bit.cafe discussion: Making ASCII Art Accessible](https://discourse.32bit.cafe/t/making-ascii-art-accessable/4454)
- `prefers-reduced-motion` has two values. `no-preference` evaluates false. `reduce` evaluates true, so `@media (prefers-reduced-motion)` equals `(...: reduce)`. Scaling and panning large objects can trigger vestibular discomfort. OS switches: Windows 11 Settings > Accessibility > Visual Effects > Animation Effects; macOS (Tahoe onwards) Accessibility > Motion > Reduce motion; iOS Settings > Accessibility > Motion; Android 9+ Accessibility > Remove animations. — [MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)

### Inferences
- **Button pattern.** The accessible name comes from `aria-label`, which overrides the content. The scrambling glyphs are hidden from the accessibility tree, so screen readers do not hear constant changes.
  ```html
  <button class="ascii-btn" type="button" aria-label="Open the letter">
    <span aria-hidden="true" id="btn-open-glyphs">[ 0P3N ]</span>
  </button>
  ```
  Never put `aria-live` on the constantly changing text.
- **Focus.** Give ASCII buttons a visible style such as `.ascii-btn:focus-visible { outline: 2px solid currentColor; outline-offset: 4px; }`. Many resets remove the default outline. Native `<button>` gives keyboard activation (Enter/Space) for free, and `@when("click", ...)` handles both.
- **Reduced motion from Python:** `window.matchMedia("(prefers-reduced-motion: reduce)").matches`. If true, render final frames once, skip the rAF loop, set the button words to static readable text, and drop transitions (`transition: none`).
- **The headline.** A huge ASCII headline should be `role="img" aria-label="<the actual words>"`, or a visually hidden `<h1>` with the ASCII `<pre aria-hidden="true">` beside it. This keeps a real heading for screen-reader navigation.
- The letter's prose should be real text, not ASCII art, so it can be read, zoomed and translated.

### Gaps
- No 2025-2026 screen-reader test matrix (NVDA, JAWS, VoiceOver, TalkBack) for `role="img"` on `<pre>` was found. Test with NVDA on Windows and VoiceOver on iOS.

## 8. Testing: pure-Python ASCII logic under pytest; headless PyScript tests with Playwright

### Takeaway
Keep every ASCII function pure (`render(t) -> str`, `scramble(word, seed, t) -> str`, `envelope_frame(progress) -> list[str]`) in modules with no `pyscript` import. They can then run under CPython pytest and load into the page through `[files]`. For end-to-end checks, PyScript's own suite uses Playwright with an `mpy:done` / `py:done` listener that sets a DOM flag to wait on.

### Cited Findings
- PyScript test pages register `addEventListener('mpy:done', () => document.documentElement.classList.add('done'))`. The Playwright test waits for that class before asserting. — [pyscript commit d9bf5ca (search summary)](https://github.com/pyscript/pyscript/commit/d9bf5cae12de6806ce9e04f2455440e7a1b8e157)
- `py:done` fires after every page script finishes. `mpy:done` is the MicroPython counterpart. — [PyScript 2024.4.1 Architecture](https://docs.pyscript.net/2024.4.1/user-guide/architecture/)
- Older PyScript integration tests waited for a runtime console message plus a short fixed delay. A maintainer suggested `customElements.whenDefined('py-script')` for the legacy element API. — [pyscript tests support.py (2023 snapshot)](https://github.com/pyscript/pyscript/blob/b674515d06a936008a13b74d4d8f74e0327eed3c/pyscriptjs/tests/integration/support.py); [discussion #1587](https://github.com/pyscript/pyscript/discussions/1587)
- Playwright for Python documents event waiting such as `wait_for_event` and `expect_console_message`. — [Playwright Python: events](https://playwright.dev/python/docs/events)
- MicroPython includes only a subset of the standard library. Code that relies on full stdlib features "may behave differently or fail" under MicroPython. — [PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/)

### Inferences
- **Layout:**
  ```
  index.html  pyscript.toml  main.py        # main.py: the only file importing pyscript
  ascii/__init__.py  ascii/frames.py  ascii/scramble.py  ascii/font.py
  tests/test_frames.py                      # pytest, plain CPython
  .nojekyll
  ```
- **Unit tests** (CPython): assert every frame has exactly `ROWS` lines of exactly `COLS` characters, which keeps the grid stable. Assert `scramble` converges to the target word at `t >= T_END`. Assert determinism with a seeded RNG. Assert only ASCII, or only an allowed glyph set, so no font fallback breaks monospace alignment.
- **MicroPython compatibility.** CPython-passing code can still fail under MicroPython: f-string edge cases, `str` methods, `random.choices`, `dataclasses`, and `typing` at runtime are all risks. Two options: run the same tests under the unix MicroPython binary (`micropython -m ...`), or keep a small Playwright smoke test that loads the page with `type="mpy"` and asserts no Python error appears.
- **Playwright smoke test** (Python):
  ```python
  page.goto("http://localhost:8000/")
  page.wait_for_function("document.documentElement.classList.contains('done')", timeout=20000)
  assert len(page.locator("#stage").inner_text().splitlines()) == 60
  page.get_by_role("button", name="Open the letter").click()
  ```
  The page must add the `done` class itself in an `mpy:done` listener (pattern above). Serve with `python -m http.server`, because PyScript fetches its files and needs HTTP, not `file://`. Run with `page.emulate_media(reduced_motion="reduce")` too, to check the static fallback.

### Gaps
- The current 2026.7.3 docs did not expose a documented testing guide. The lifecycle-event pattern comes from PyScript's own repo and older docs, so confirm `mpy:done` still fires in 2026.7.3 by trying it once.
- No source documents an official way to run PyScript-dependent Python (code that imports `pyscript`) outside the browser. Hence the advice to keep `pyscript` imports confined to `main.py`.
