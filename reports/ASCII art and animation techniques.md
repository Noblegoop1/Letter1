> **Note (2026-10-31):** the ASCII art and animation techniques here still apply. The parts about running Python in the browser (PyScript/MicroPython, GitHub Pages, DOM rendering) are superseded by the desktop stack in `docs/adr/0001-desktop-stack.md`.

# Hand-draw the sprites, let Python animate them

Build this page as a hybrid. Hand-draw a small set of fixed-width, 7-bit ASCII sprites, or generate them and then tidy them by hand: envelope body, flap, heart seal, button frames and headline. Then animate them with small pure-Python functions of time that stack the layers into fixed-size character grids and write each grid into a `<pre>` once per tick. The classics split the work the same way. The Star Wars ASCIImation is **hand-drawn 67×13 frames played at about 15 fps**, while donut.c and asciimatics recompute the whole grid from maths every frame ([ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html), [asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html)). An envelope that opens and slides away needs both. FIGlet fonts through **pyfiglet 1.0.4** are the standard way to make a huge "Will you open ?" headline. But pyfiglet is a CPython package from PyPI, and the in-browser MicroPython runtime cannot install packages ([pyfiglet on PyPI](https://pypi.org/project/pyfiglet/), [PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/)). So run pyfiglet once while authoring and keep its output as text, or replace it with a small block font. The YES/NO words can change constantly and stay readable as long as each letter's outline never moves. Either re-pick the characters that fill big letters, or swap at most one letter for a look-alike. Do the re-picking at 8–12 Hz, driven by a hash of (cell, integer tick) rather than fresh random numbers every display frame. In the browser, **PyScript 2026.7.3's MicroPython runtime (about 170 KB)** drives `requestAnimationFrame` through a single reused `create_proxy`. All motion is computed from the rAF timestamp, and whole-block moves such as the slide-away are CSS transforms. GitHub Pages serves static files only and cannot send custom headers, and project sites live under `/<repo>/`. That rules out PyScript's worker mode and requires every path to be relative ([GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits), [About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)). The two real unknowns are whether CPython-tested code runs unchanged under MicroPython and what width-to-height ratio the chosen font's cells have. Both are cheap to check early in a real browser.

## Seven-bit glyphs on a measured grid keep the art intact

ASCII art is built from the **95 printable characters of the 1963 ASCII standard**. Line art imitates outlines with `/ \ | _ - ( ) < > =`, and shading uses characters of different visual density such as `$` and `#` ([Wikipedia: ASCII art](https://en.wikipedia.org/wiki/ASCII_art)). Two scene styles exist. "Oldskool" style, from the Amiga scene around 1992, outlines shapes with `_/\-+=.()<>:`. "Newskool" style shades with strings like `$#Xxo`. An envelope with a heart seal belongs in the outline tradition. All of it depends on a **monospaced font**: proportional fonts such as Helvetica or Times distort or ruin the art. Unicode offers far more characters, but few fixed-width fonts cover a large subset of them (same source). Unicode box drawing (U+2500–U+257F, with rounded corners `╭╮╯╰` at U+256D–U+2570) and block elements (U+2580–U+259F, including the shades `░▒▓`) give cleaner joins and solid fills. Their glyphs are designed to connect with their neighbours, so they work only in monospaced fonts, and many fonts include only the IBM PC subset. The newer "Symbols for Legacy Computing" sextants have poor font support and often show up as empty boxes ([Wikipedia: Box-drawing characters](https://en.wikipedia.org/wiki/Box-drawing_characters)). **The position this report takes is a pure 7-bit base for everything**, with box-drawing used only as a deliberate accent and only when a font known to contain it is loaded. There is also a stability reason, covered in the animation section: a glyph that falls back to a different font can have a different width and shift its whole row. `♥` (U+2665) is not ASCII either, so a strictly 7-bit page uses `<3` or a drawn heart.

Glyph geometry inside the cell drives most hand-drawing conventions. The rules in this paragraph follow from how standard monospace glyphs are shaped and do not come from a cited source. `_` sits on the floor of its cell, so the top edge of a box or envelope is drawn as underscores on the row above the shape. `-` sits at mid-height. `.` and `,` round off low corners, `'` and `` ` `` round off high ones, and `.-`, `-.`, `` `- `` and `-'` make soft corners. Cells are roughly twice as tall as they are wide, so a run of `/` that steps one column per row reads as about 63°, not 45°. Shallow diagonals therefore need doubled glyphs (`//`, `_/`). Paul Bourke gives the matching fix for generated art: sample half as often vertically, or match the font's measured aspect exactly ([Paul Bourke](https://paulbourke.net/dataformats/asciiart/)). donut.c applies the same correction by scaling x by 30 and y by 15 ([a1k0n, Donut math](https://www.a1k0n.net/2011/07/20/donut-math.html)).

Choose the font before you draw anything. The ASCIImation author found that Courier New makes his Courier-drawn art look "a little too stretched vertically" ([ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)). On the web, CSS has the right unit for this: **`1ch` is the advance width of the glyph "0"**, which equals one cell in a monospace font. If the browser cannot measure it, it assumes 0.5em ([MDN CSS length](https://developer.mozilla.org/en-US/docs/Web/CSS/length)). A grid of N columns is therefore exactly N ch wide. Size the font from small-viewport units (`svw`), which MDN describes as stable, not from dynamic units (`dvw`), which it says "are not stable" (same source). The CSS below is standard practice rather than something sourced. It makes rows touch and prevents coding-font ligatures from merging `==` or `->`:

```css
pre.ascii { margin: 0; white-space: pre; line-height: 1; letter-spacing: 0;
            font-variant-ligatures: none; contain: layout paint;
            font-family: ui-monospace, "Cascadia Mono", "SF Mono", Menlo, Consolas,
                         "DejaVu Sans Mono", "Liberation Mono", monospace; }
```

For an identical layout on every device, self-host one font such as JetBrains Mono or IBM Plex Mono (both OFL-licensed). Wait for `document.fonts.ready`, then measure the cell, for example by dividing the width of 100 copies of `M` by 100, and set `font-size = viewport_px / (columns × cell_width_per_em)`. The ratio is often near 0.6, but measure it rather than assume it. Phones set a hard limit. At 375 CSS px, a 160-column grid needs roughly a 3.75 px font, which is decoration, not legible text. Compose the envelope scene at about 60–80 columns, or ship a narrower phone version of it.

## Generators draw clean shapes, but the best hearts are hand-tidied

### Density ramps shade, shape matching outlines

Shading by brightness uses a density ramp. Bourke's two ramps (1997) are still the reference points. His 70-character ramp is ordered from dense to sparse. His 10-level ramp, `" .:-=+*#%@"`, which he calls "more convincing", is ordered from sparse to dense. He also warns that different typefaces make the same character look lighter or darker, so grey steps come out uneven ([Paul Bourke](https://paulbourke.net/dataformats/asciiart/)). jp2a ships its own 21-character ramp and Rec.601-style weights for converting RGB to grey (0.2989, 0.5866, 0.1145) ([jp2a man page](https://manpages.debian.org/testing/jp2a/jp2a.1.en.html)). Bourke's convention is for print, where dense means dark. **On a dark page, flip the ramp so that bright areas get dense glyphs.** The most accurate ramp is the one measured from the page's actual font: render each glyph with Pillow, count the inked pixels, and sort by coverage. That calibration step is the researchers' own recommendation; no published per-font coverage table was found. The 10-level ramp suits this page's paper-grain fill better than the 70-character one, whose near-equal glyphs (`b d p q`) add visual noise.

Brightness ramps are good for texture and poor for outlines. Alex Harri's January 2026 analysis shows why. Treating each cell as one pixel ignores glyph shape, so edges come out jagged or blurry. His fix gives every cell **6 staggered sampling circles** and every printable glyph a matching "shape vector" of how much of each circle it covers, then picks the glyph nearest by Euclidean distance. Ten more circles just outside the cell add directional contrast, which removes staircasing. Lookups use k-d trees and a quantised cache because brute-force search is too slow for animation ([Alex Harri](https://alexharri.com/blog/ascii-rendering)). The academic version is Xu, Zhang & Wong's "Structure-based ASCII Art" (SIGGRAPH 2010). It traces an image's main lines using an alignment-insensitive shape-similarity metric plus constrained deformation of the input, and observes that tone-based methods give "halftone-like results" that need high text resolution ([project page](https://ttwong12.github.io/papers/asciiart/asciiart.html)). This page is generated once and contains only about a dozen outline glyphs, so a brute-force miniature of Harri's method is enough. Rasterise `/ \ | _ - ( ) . ' , V` into small coverage grids and pick the nearest glyph for each cell of a high-resolution line drawing. jp2a's `--edges-only` mode is a cheaper middle ground: it draws only the edges, choosing glyphs by edge direction ([jp2a man page](https://manpages.debian.org/testing/jp2a/jp2a.1.en.html)).

### Procedural shapes: heart curves, fills and layers

Shapes drawn from maths cover the heart and the envelope. MathWorld lists the implicit heart `(x²+y²−1)³ − x²y³ = 0` and the parametric heart `x = 16 sin³t, y = 13 cos t − 5 cos 2t − 2 cos 3t − cos 4t` ([Wolfram MathWorld: Heart Curve](https://mathworld.wolfram.com/HeartCurve.html)). The inequality `≤ 0`, tested at each cell centre, gives a filled seal. Map how negative the value is through the ramp to fake depth on the wax. The parametric form gives an outline: choose each glyph from the tangent angle on screen, with dy doubled for the cell aspect. The researchers' working bins are `_` below 22.5°, `/` up to 67.5°, `|` up to 112.5° and `\` beyond. When they generated an outline this way, it showed predictable artefacts: stray backslashes on the lobes and doubled `\\\\` runs. The lesson is that **generated outlines are a first draft, and most good ASCII hearts are hand-tidied**. The rest of the toolkit is standard graphics, not sourced here. Bresenham's algorithm draws straight segments. Scanline polygon fill handles the envelope body and flap triangle. Signed distance fields give borders of constant thickness and rounded button corners almost for free.

Compose everything as layers. Each sprite is a list of equal-width strings, and a sentinel character such as `~` marks transparent cells. The researchers generated the envelope below this way, asserting that every row has the same width. It also shows the conventional idioms: an underscore top edge, `|\` and `/|` corners, diagonals meeting at a seal, and the flap's lower edge drawn as `\_____/`:

```
 ______________________________________
|\                                    /|
| \                                  / |
|  \                                /  |
|   \                              /   |
|    \                            /    |
|     \        .--. .--.         /     |
|      \      (    V    )       /      |
|       \      \       /       /       |
|        \______`.   .'_______/        |
|                 `.'                  |
|                                      |
|______________________________________|
```

Its 11-wide seal sits one cell off-centre on the 40-wide body. Give sprites odd widths so they can centre exactly.

### pyfiglet renders the headline, but only at authoring time

FIGlet is the standard for big text. A FIGfont v2 file starts with a header such as `flf2a$ 6 5 20 15 3 0 143 229`, which gives the signature, the hardblank character, height, baseline, maximum line length, old layout code, number of comment lines, print direction, full layout code and code-tag count. Each line of a character ends with an endmark, usually `@`. Six horizontal "smushing" rules let neighbouring letters overlap: equal character, underscore, hierarchy, opposite pair, big X and hardblank ([FIGfont spec](https://github.com/cmatsuoka/figlet/blob/master/figfont.txt)). In Python, **pyfiglet 1.0.4** (15 Aug 2025, MIT, Python ≥3.9) is current ([PyPI](https://pypi.org/project/pyfiglet/)). `figlet_format(text, font=..., width=...)` returns a plain string, and `width` defaults to 80 ([pyfiglet source](https://raw.githubusercontent.com/pwaller/pyfiglet/main/pyfiglet/__init__.py)). A large font wraps "Will you open ?" unless `width` is raised to something like 200. Font licensing is uneven. The README says the `fonts-standard` set has a clear redistribution licence and the `fonts-contrib` set does not. Other fonts ship on a public-domain belief that the project admits "is not a watertight case" ([pyfiglet GitHub](https://github.com/pwaller/pyfiglet)). Check the comment lines of the chosen font with `pyfiglet -i -f FONT`.

pyfiglet clashes with an in-browser runtime. **MicroPython "cannot install packages" and carries only "a subset of the standard library"** ([PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/)). For a MicroPython page without a build step, the clean split is to run pyfiglet once on desktop CPython while authoring, preview the candidate fonts (`standard`, `big`, `doom`, `slant`, `colossal`, which are names remembered from pyfiglet's font set and not checked this session), and paste the chosen output into the art module as a string constant. The alternative is a hand-rolled block font. Map each letter to a 5×7 bitmap and print each "pixel" as two characters (`##`), which also cancels out the 2:1 cell shape. The block font is the better fit for the button words, because its strokes are exactly the cells that the fill-churn effect described below re-picks. Solid-block FIGlet fonts such as `ansi_shadow` are made of Unicode blocks, not ASCII.

### Authoring tools and signing etiquette

The tools are for making assets, not for running the page:

| Need | Tool (current version found) | Note |
|---|---|---|
| Line-art envelope, borders | ASCIIFlow (web, MIT) | Client-side diagram editor ([GitHub](https://github.com/lewish/asciiflow)) |
| Coloured text-mode art, layers | REXPaint 1.70 (Windows) | `.ans` import/export, GIMP palettes ([itch.io](https://kyzrati.itch.io/rexpaint)) |
| Cross-platform editor | Playscii 9.17.1 (2021) | Slow development ([devlog](https://jp.itch.io/playscii/devlog/214916/playscii-9171)) |
| ANSI/BBS style | Moebius (Apache-2.0) | No current version number found ([GitHub](https://github.com/blocktronics/moebius)) |
| Photo → ASCII, HTML output | jp2a 1.3.x | `--html --colors`, custom `--chars` ramp ([man page](https://manpages.debian.org/testing/jp2a/jp2a.1.en.html)) |
| Unicode mosaics, dithering | chafa 1.18.3 (23 Sep 2026) | Mostly for terminal output ([NEWS](https://raw.githubusercontent.com/hpjansson/chafa/master/NEWS)) |
| Braille, colour, Go library | ascii-image-converter | Custom `--map` ramp ([README](https://github.com/TheZoraiz/ascii-image-converter)) |
| Headlines | pyfiglet 1.0.4 / FIGlet 2.2.5 | ([figlet.org](http://www.figlet.org/)) |

Archive art comes with a strong convention: the artist's initials sit in a corner, and the asciiart.eu FAQ says "DO NOT remove these initials" and to ask permission before reusing someone else's work ([asciiart.eu FAQ](https://www.asciiart.eu/faq)). For a personal love letter, the simplest course is to draw the envelope and heart yourself and sign them, which also marks the art as original.

## Sprites plus procedural motion open the envelope

### Three animation models, and why this page needs the hybrid

There are three ways to store ASCII animation. **Frame-based** is the ASCIImation model. Every frame is hand-drawn, the separator line above each frame is replaced by a hold count in 1/15 s units, and identical consecutive frames are stored once. That reduced 17,357 raw frames to **3,849** ([ASCIImation FAQ](https://asciimation.co.nz/asciimation/ascii_faq.html)). Its author calls editing pans frame by frame "the most painful" part of the work. **Event streams** such as asciinema's asciicast v2 store timed `[time, "o", data]` terminal output after a JSON header. They need a terminal emulator to play back, which makes them a poor fit for a `<pre>` page ([asciicast v2](https://docs.asciinema.org/manual/asciicast/v2/)). **Procedural** engines recompute the grid every frame. asciimatics renders an ordered list of Effects per Scene, foreground last, has Sprites follow scripted Paths, and redraws about 20 times a second ([asciimatics](https://asciimatics.readthedocs.io/en/stable/animation.html)). donut.c clears its framebuffer and z-buffer every frame and lights a rotating torus through the 12-character ramp `.,-~:;=!*#$@` ([a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)). The love letter wants the **hybrid**: a handful of hand-drawn sprites that procedural code moves, squashes and recolours. The art stays editable as plain text, and nobody repaints a pan by hand.

### Three clocks: smooth motion, slow glyph changes, fixed-step simulation

Timing must come from the clock, not from counting frames. `requestAnimationFrame` usually runs at the display's refresh rate (60, 75, 120 or 144 Hz). Its callback receives a high-resolution timestamp, and MDN warns that progress computed any other way "will run faster on high refresh-rate screens". rAF is also paused in most background tabs ([MDN rAF](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)). The popular soulwire TextScramble advances one step per rAF call, so it runs at double speed on a 120 Hz screen ([TextScramble gist](https://gist.github.com/Marty-f13/b1fdcf9d9f92600ce0c6903c57fd1971)). Any port should use seconds instead.

Run three clocks inside one rAF loop. **Motion** (flap angle, slide offset) is sampled from eased elapsed time on every display frame. **Glyph churn** runs on a slow integer tick of 8–20 Hz, which matches the 15 fps of the ASCIImation, the roughly 20 Hz redraw of asciimatics and Baffle's default 50 ms scramble interval ([Baffle](https://github.com/camwiegert/baffle)). **Simulations** such as fire or particles use Glenn Fiedler's accumulator: real time accumulates, the simulation consumes it in fixed steps, and frame time is capped at **0.25 s** so that one huge step does not trigger a "spiral of death" ([Fix Your Timestep!](https://gafferongames.com/post/fix_your_timestep/)). The cap also absorbs the multi-second gap when a background tab comes back. One-shot timelines such as the envelope opening should instead pause their clock on `visibilitychange`.

### Compositing: painter's algorithm with opaque spaces

Each frame, layers are painted back to front into a fresh character array, the painter's algorithm. The one non-obvious rule is that **space must be opaque**. Otherwise the envelope's empty interior shows whatever is behind it. Give each layer its own transparent sentinel instead. The compositor below passed the researchers' CPython self-check. Cells that fall outside the grid are clipped, so sprites can slide off-screen:

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
                if 0 <= xx < w and ch != tr:
                    grid[yy][xx] = ch
    return [''.join(r) for r in grid]
```

A workable z-stack, from back to front, is background, envelope back panel, letter, front pocket, flap, then headline and buttons. The flap drops behind the letter once it has opened past vertical. The browser presents every DOM change made within one rAF callback together. So terminal-style "clear, then draw" flicker cannot happen as long as each frame is built completely and assigned once, which is the browser equivalent of donut.c moving the cursor home with `ESC[H` instead of clearing the screen ([a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)).

### The flap folds in characters, the envelope slides as a block

The research produced two candidate techniques for the flap, and they pull in different directions. CSS can rotate a `<pre>` with `rotateX(180deg)` under `perspective`, with `backface-visibility: hidden` and a second, pre-rotated `<pre>` for the inside of the flap. The alternative is a **character row-squash**. A plane rotating by θ projects to a height of `H·|cos θ|` rows, so source rows are sampled nearest-neighbour into that height. Past 90° the flap is drawn above the hinge, mirrored vertically with `/` and `\` swapped. A slight per-row widening adds perspective, following donut.c's projection `x' = K1·x/(K2+z)` ([a1k0n](https://www.a1k0n.net/2011/07/20/donut-math.html)). **The recommendation is the row-squash** (or, for a small flap of six rows or fewer, three or four hand-drawn keyframes chosen by θ), because every intermediate frame stays real characters on the grid. A CSS rotation instead shows foreshortened, rasterised text. Some browsers may blur 3D-transformed text mid-animation; that was not verified. When the researchers tested the row-squash, a 6-row V flap stepped cleanly through 6, 2, 2 and 6 rows at θ = 0, 1.2, 1.9 and π. Two details sell the effect: draw a single hinge line near 90° so the flap never vanishes for a frame, and switch to a different texture for the flap's inside past π/2.

The slide is the opposite case. Moving a whole block is exactly what the compositor handles best. web.dev says the cheapest version of the rendering pipeline avoids layout and paint entirely, and that **`transform` and `opacity` are the only compositor-only properties**. It also warns against promoting elements to their own layers without need ([web.dev](https://web.dev/articles/stick-to-compositor-only-properties-and-manage-layer-count)). Put the envelope in its own `<pre>` and animate `transform: translate(...)` in `ch` or `vh` units. This gives sub-pixel smooth motion and costs Python nothing per frame. To keep the slide on the grid, round the offset to whole `ch`. Rolling characters across inside the compositor also works, but it moves in cell-sized steps of roughly 6–10 px.

Easing turns these moves into gestures. The formulas below come from the easings.net source ([easingsFunctions.ts](https://raw.githubusercontent.com/ai/easings.net/master/src/easings/easingsFunctions.ts)). The pairings and timings are the researchers' design choices:

| Moment | Easing | Formula | Duration |
|---|---|---|---|
| Headline decodes in | easeOutQuart | `1-(1-x)^4` | ~0.6 s |
| Flap opens (θ: 0→π) | easeInOutCubic | `x<.5 ? 4x³ : 1-(-2x+2)³/2` | 0.8–1.2 s |
| Letter rises out (optional) | easeOutBack | `1 + c3(x-1)³ + c1(x-1)²`, c1 = 1.70158 | ~1.0 s |
| Envelope slides away | easeInCubic | `x³` | ≤ 0.8 s |

An ease-out on an exit looks like the envelope stalls at the screen edge, so the exit accelerates. Bounce and elastic easings make big blocks oscillate. A heart-particle burst at the moment the flap opens finishes the beat. The researchers' recipe is position-velocity points rising 2–5 rows/s, swaying sinusoidally, capped at 20–40, rounded to cells only at draw time and composited at the back. Two alternative exits come from the same toolbox. A dissolve gives every cell a fixed hash threshold and walks its glyph down the ramp until it becomes a space. "Burning letter" fire adapts Fabien Sanglard's Doom fire, which runs 37 heat levels from a bottom source row that never updates ([Doom fire](https://fabiensanglard.net/doom_fire_psx/)). Its decay has to be scaled up on a short ASCII grid. Average cooling is 0.5 levels per row, so 36 levels last about 72 rows, and a 12-row fire never shows tips unless the decay per step is raised to about 6.

### Motion needs an off switch

This page never stops moving, so it needs explicit guardrails. **WCAG 2.3.1 (Level A) forbids content that flashes more than three times in any one-second period** above the general and red flash thresholds. The area threshold is about 341×256 CSS px within a 10° visual field. Fine, balanced patterns such as noise are exempt ([W3C Understanding 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)). Churning `#` and `@` inside letter strokes changes the luminance of each cell only a little and stays well clear of the limit. A full-screen white flash when the envelope opens, or a large glitch that toggles faster than 3 Hz, would break it. `prefers-reduced-motion: reduce` "removes, reduces, or replaces motion-based animations", and MDN names panning large objects as a vestibular trigger ([MDN prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)). That argues for a short, one-directional slide, and for a reduced-motion branch that shows static true words and replaces the flap-and-slide with a cross-fade. WCAG 2.2.2 (Pause, Stop, Hide) very likely requires a pause control for auto-playing motion that lasts longer than 5 seconds, but that page was not fetched. Verify it before relying on it, and add an ASCII `[ || pause ]` toggle regardless.

## YES and NO stay readable when the silhouette never moves

The usual "decode" effect is soulwire's TextScramble. For each character position it picks a random start frame and end frame (each up to 40 frames). Before the start it shows the old character, between start and end it shows random glyphs from `!<>-_\/[]{}—=+*^?#________` (re-rolled with probability 0.28 per frame), and after the end it shows the target character. Phrases are cycled by chaining `setText(...).then(() => setTimeout(next, 800))`. The repeated underscores in the character set bias the noise toward quiet, low glyphs ([TextScramble gist](https://gist.github.com/Marty-f13/b1fdcf9d9f92600ce0c6903c57fd1971), [codepen soulwire/mEMPrK](https://codepen.io/soulwire/pen/mEMPrK)). Baffle.js packages the same idea in about 1.8 KB. By default it never obfuscates spaces, but it has been **archived and read-only since April 2020** ([Baffle](https://github.com/camwiegert/baffle)). Porting the roughly 30-line algorithm into Python is the better route. Measure its windows in seconds, not frames, and pad every string to a fixed width so the border never resizes. The same padded decode handles the case where the button words themselves change (YES → SURE → OF COURSE): the button is as wide as its longest word.

A full scramble is unreadable, so "constantly changing but readable" needs a gentler effect. Two designs work, and neither has been tested for legibility in any published study. **For big block letters, change the fill, not the outline.** The strokes carry the word, so the characters that fill them can be re-picked every tick from `#@%&$` while the word stays perfectly legible. This is the right default for button words drawn in a block font, and for the headline. **For small text, swap at most a third of the letters** (one letter of "YES" or "NO") and only for look-alikes that keep the letter's shape: `y→yYv`, `e→eE3`, `s→sS5$`, `n→nNh`, `o→oO0@`. Both effects take their randomness from a hash of the cell and the integer tick rather than from a random-number generator. That makes the output identical on 60 Hz and 144 Hz screens and stable between ticks. It also avoids MicroPython's reduced `random` module, since code that leans on full standard-library features "may behave differently or fail" there ([PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/)). This version passed an assertion check under CPython 3.14 (output stable within each tick, never more than one letter off, every substitute drawn from its look-alike pool). It has not yet been run under MicroPython:

```python
LOOKALIKE = {'y': 'yYv', 'e': 'eE3', 's': 'sS5$', 'n': 'nNh', 'o': 'oO0@'}
FILL = '#@%&$'

def hash32(*xs):                                   # FNV-1a: same (cell, tick) -> same glyph
    h = 2166136261
    for x in xs:
        h = ((h ^ (x & 0xffffffff)) * 16777619) & 0xffffffff
    return h

def churn(word, t, rate=8, salt=0):                # small text: one look-alike swap per tick
    tick = int(t * rate)
    i = hash32(salt, tick) % len(word)
    pool = LOOKALIKE.get(word[i].lower(), word[i])
    return word[:i] + pool[hash32(salt, tick, i) % len(pool)] + word[i + 1:]

def fill_churn(lines, t, rate=10, stroke='#'):     # big letters: re-pick stroke fill, keep silhouette
    tick = int(t * rate)
    return [''.join(FILL[hash32(x, y, tick) % len(FILL)] if c == stroke else c
                    for x, c in enumerate(row)) for y, row in enumerate(lines)]
```

Over 400 samples it produced variants such as `YE5`, `Y3S`, `vES` and `N0`, `nO`, and the true word kept reappearing. To add life without losing readability, run a short decode burst of about 0.4 s back to the true word every few seconds or when the pointer enters a button.

Shimmer, meaning unwanted glyph flicker, has four common causes, and each has a matching fix. These come from the researchers' engineering reasoning; Harri's article explicitly leaves temporal stability out of scope ([Alex Harri](https://alexharri.com/blog/ascii-rendering)). The first is calling `Math.random()` on every frame; replace it with the hash tick above. The second is a continuous value hovering at a ramp boundary and flipping `:`↔`;`; add hysteresis of about half a ramp step. The third is rounding sub-cell positions separately on each row, which makes rows jitter apart; compute one integer offset per sprite. The fourth is a non-ASCII glyph falling back to a font with a different width; stay 7-bit.

Screen readers must never hear the noise. W3C technique H86 says ASCII art "can be very confusing" to screen-reader users and prescribes **`role="img"` with an `aria-label`** on the element that contains it ([W3C H86](https://www.w3.org/WAI/WCAG21/Techniques/html/H86)). `aria-label` is not allowed on a bare `div` or `span`, which is why the role is required ([32bit.cafe](https://discourse.32bit.cafe/t/making-ascii-art-accessable/4454)). Make YES and NO real `<button>` elements with a stable `aria-label`, put the churning glyphs inside an `aria-hidden="true"` span, never use `aria-live` on churning text, and give the buttons a visible `:focus-visible` outline. Native buttons get Enter and Space activation for free. Put the headline in a visually hidden real `<h1>` next to its `aria-hidden` ASCII `<pre>`.

## PyScript MicroPython on GitHub Pages: one string per element per tick

### Choosing a runtime

GitHub Pages "does not support server-side languages like PHP, Ruby or Python" ([GitHub Docs](https://docs.github.com/de/pages/getting-started-with-github-pages/creating-a-github-pages-site)). Python therefore runs either in the browser or before deployment. The options compare as follows:

| Option | First load | Fit |
|---|---|---|
| **PyScript 2026.7.3 `mpy` (MicroPython)** | ~170 KB compressed, near-instant start | Best "Python in the browser" choice for string-and-maths animation |
| PyScript `py` / plain Pyodide 314.x | Multi-MB; an undated roadmap cites a 6.4 MB download and 4–5 s to initialise | Only if PyPI packages such as numpy are needed |
| Brython 3.15.0 | Transpiler plus standard-library JS (size not measured) | Viable; has a native `request_animation_frame` wrapper |
| Transcrypt 3.9.5 | Tiny compiled JS | Python 3.9 subset, extra toolchain |
| Python build step → frames + small JS player | Frames only | Most robust, but no live Python |

Sources: [PyScript Architecture](https://docs.pyscript.net/2026.7.3/user-guide/architecture/), [Pyodide roadmap](https://pyodide.org/en/stable/project/roadmap.html), [Brython releases](https://github.com/brython-dev/brython/releases), [Brython timer](https://brython.info/static_doc/3.12/en/browser.timer.html), [Transcrypt on PyPI](https://pypi.org/project/Transcrypt/).

PyScript **2026.7.3** (29 Jul 2026) is current. It loads from `https://pyscript.net/releases/2026.7.3/core.js` and `core.css`. Since the breaking 2026.6.1 release it supports only MicroPython and Pyodide (Pyodide now on 314.0.3, the Python 3.14 line) ([PyScript releases](https://github.com/pyscript/pyscript/releases), [Beginning PyScript](https://docs.pyscript.net/2026.7.3/beginning-pyscript/)). MicroPython wins for a page where the first impression is everything, because it has `math`, string operations and enough of `random` for this job. Keep all the art in a pure module that never imports `pyscript`, load it through the config file's `[files]` table, and let only `main.py` touch the DOM. Without `create_proxy`, a Python callback passed to JS "would be garbage collected immediately". Pyodide's own advice is to use `create_proxy` for anything called many times and keep a reference to it ([PyScript FFI](https://docs.pyscript.net/2026.7.3/user-guide/ffi/), [Pyodide type conversions](https://pyodide.org/en/stable/usage/type-conversions.html)). So create one proxy for the frame function and reuse it every frame. This skeleton is assembled from the cited APIs and has not been run:

```python
from pyscript import window, document
from pyscript.ffi import create_proxy
import art                                          # pure, MicroPython-safe, CPython-tested

headline = document.getElementById("headline")
last_tick = -1
def frame(ts):
    global last_tick
    tick = int(ts / 1000 * 10)                      # 10 Hz glyph clock from the rAF timestamp
    if tick != last_tick:                           # redraw only when glyphs would change
        headline.textContent = "\n".join(art.fill_churn(art.HEADLINE, ts / 1000))
        last_tick = tick
    window.requestAnimationFrame(frame_proxy)
frame_proxy = create_proxy(frame)
window.requestAnimationFrame(frame_proxy)
```

Event handlers use `@when("click", "#yes")`, which creates proxies automatically but binds only elements that already exist when it runs ([PyScript Events](https://docs.pyscript.net/2026.7.3/user-guide/events/)). The YES handler should only toggle CSS classes, so the flap row-squash runs on its own short timeline and the slide runs as a CSS transition.

### Performance: cross the Python–JS boundary as little as possible

No head-to-head benchmark of `<pre>.textContent` against canvas for ASCII frames exists. Terminal history ranks the DOM slowest at full-screen throughput: VS Code abandoned DOM rendering for its terminal in 2017, and xterm.js measured its WebGL renderer at "up to 900% faster than canvas" ([VS Code blog](https://code.visualstudio.com/blogs/2017/10/03/terminal-renderer), [xterm.js 4.3.0](https://github.com/xtermjs/xterm.js/releases/tag/4.3.0)). At love-letter scale, the deciding cost is crossings between Python and JS, not the DOM. Writing one string per `<pre>` is one FFI call. Updating a 160×60 grid one span per cell would be **about 9,600 calls per frame**, which MicroPython cannot sustain. So split the scene into a few `<pre>` elements (headline, envelope, each button), rewrite one only when its tick changes, give each fixed dimensions and CSS `contain` so a rewrite cannot reflow the page, and add colour by building run-length-merged `<span>` HTML in one string. Canvas output cannot be selected and is invisible to screen readers, which is one more reason to stay with text.

### GitHub Pages: relative paths, `.nojekyll`, no headers

Pages publishes sites of up to **1 GB**, with a 100 GB/month soft bandwidth limit and a 10-minute deployment timeout ([GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits)). Project sites live at `<owner>.github.io/<repository>` ([About GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/about-github-pages)), so a root-absolute `/main.py` returns 404 and every `src`, `config` and `[files]` path must start with `./`. Jekyll silently drops files that start with `_`, `.` or `#` unless the publishing root contains an empty `.nojekyll` ([About GitHub Pages and Jekyll](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/about-github-pages-and-jekyll)). Deployment either publishes a branch's root or `/docs`, or runs through an Actions workflow with `upload-pages-artifact` and `deploy-pages` ([Configuring a publishing source](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site)). MIME types come from mime-db and cannot be overridden ([GitHub Docs: MIME types](https://docs.github.com/enterprise/2.4/user/articles/mime-types-on-github-pages)). Custom headers are impossible, so the cross-origin isolation (COOP/COEP) that PyScript workers need for `SharedArrayBuffer` is unavailable; keep Python on the main thread ([PyScript API: context](https://docs.pyscript.net/2026.7.3/api/context/)). Responses have been observed with `Cache-Control: max-age=600`, though only in older second-hand sources ([GitLab Pages issue #69](https://gitlab.com/gitlab-org/gitlab-pages/-/issues/69)). Expect friends to see a stale page for about ten minutes after a push, and append `?v=N` to the script and config URLs while iterating.

### Testing: unit-test the pure module, smoke-test the page

Keep every art function pure (`render(t) -> str`, `churn(word, t)`, `flap_rows(theta)`) so CPython tests can assert the invariants that keep a grid stable: every frame has exactly ROWS lines of exactly COLS characters, every character is ASCII, the scramble reaches the target word by its end time, and output is deterministic for each tick. CPython passing does not prove that MicroPython will run the code. f-string edge cases, `str.translate`, `random.Random`, `dataclasses` and runtime `typing` are the usual traps. Close the gap with one Playwright smoke test. PyScript's own test pages add a `done` class in an `mpy:done` listener and wait for it ([pyscript commit d9bf5ca](https://github.com/pyscript/pyscript/commit/d9bf5cae12de6806ce9e04f2455440e7a1b8e157), [Playwright Python events](https://playwright.dev/python/docs/events)). Serve the page over `python -m http.server`, because PyScript fetches its files and cannot work from `file://`. Run the smoke test a second time with `emulate_media(reduced_motion="reduce")`.

## Conclusion

The hard part of an all-ASCII page is not drawing but **stability**. Once the font, the cell aspect, the grid width and the per-tick glyph function are fixed, every effect in this report reduces to a pure function from time to a list of equal-width strings. Those functions can be tested in CPython and run in MicroPython. Stability is also what dissolves the apparent conflict between "constantly changing" and "readable": the eye reads letter outlines, so anything inside the outline may churn as long as it changes on a slow, deterministic tick. The same logic splits the rendering work. Characters change where content changes (the flap fold, the button fill, the headline shimmer), and blocks move where only position changes (the slide), handled by the browser's compositor.

Two practical consequences follow. First, pyfiglet and the image converters belong to authoring time, not to the page: their output is text, and text can be committed. That keeps the MicroPython payload small without giving up FIGlet-quality headlines. Second, the main risks sit in places this research could not settle, namely how MicroPython handles CPython-tested code, the cell ratio of the chosen font on each device, and whether 3D-transformed text stays crisp. Each of these takes about an hour to check in a real browser and would take days to fix late. Before drawing the full envelope, build a throwaway page that loads one `mpy` script, measures the cell and churns the word "YES".
