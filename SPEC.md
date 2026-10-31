# Spec: ASCII Love Letter — Part 1 ("Will you open ?")

Status: **DRAFT — awaiting approval.** Nothing is built until this is approved.

## Objective

A static web page, hosted on GitHub Pages, that works as a love letter. The page logic is written in
Python and every visual — text, shapes, textures, buttons — is ASCII characters. No images, no icons,
no canvas drawings.

Part 1 is the opening scene only:

1. On load, a massive ASCII headline reads **`Will you open ?`**.
2. Below it sits a massive ASCII envelope modelled on [`reference/envelope.png`](reference/envelope.png):
   a rectangle, two diagonals meeting in the middle (the flap), and a red heart seal where they meet.
   The paper is filled with a light ASCII texture.
3. In front of the envelope are two ASCII rectangles (buttons). One says **YES**, the other **NO**.
   Each word is drawn in big ASCII letters whose characters keep changing (scrambling glyphs) while the
   letter shapes stay readable.
4. Choosing **YES** plays the open sequence: the flap opens, then the envelope slides away off-screen.
   The scene ends on an empty stage that Part 2 will fill.

The person reading it is one specific person on their own phone or laptop; the first impression matters
more than anything else, so the page must load fast and never show a broken or half-loaded state.

## Assumptions (correct any of these)

1. **"In py" means the page runs Python in the browser** via PyScript with the MicroPython runtime
   (small download, fast start). The heavier Pyodide runtime is not used. No JavaScript is written by us
   beyond the PyScript loader tag.
2. **Layout:** headline on top, envelope centred under it, both buttons overlapping the lower part of the
   envelope. Everything is on screen from the first frame; the headline is static (no decode-in).
3. **Look:** dark night background (like the three reference repos), cream envelope, dark-grey outlines,
   red heart — the envelope image's palette translated to coloured characters.
4. **"Changing ASCII words":** the button word is a fixed big-letter shape (a small built-in block font);
   the outline stays put and the characters filling it are re-picked at their own ~12 Hz tick, seeded
   per cell so it flickers gently rather than strobing. Timing uses the `requestAnimationFrame`
   timestamp (not frame counts), so 120/144 Hz screens don't run it faster.
5. **Flap opens in characters:** Python redraws the flap rows each frame, squashed by cos θ past the
   hinge (and mirrored above it after 90°), so every frame is real ASCII. **Slide away** = the whole
   envelope `<pre>` then moves off the bottom of the screen with a CSS transform (smooth, no Python cost).
5b. **Big letters** (headline and YES/NO) come from a small hand-made block font in `art.py` — no
   pyfiglet (MicroPython can't install packages, and it isn't worth a build step).
5c. **Scene width ~72 columns;** font size scales with the viewport, so it is massive on a laptop and
   still fits a 375 px phone.
5d. **A small ASCII `[ pause ]` toggle** in a corner stops the scrambling (WCAG 2.2.2: auto-playing
   motion longer than 5 s needs a pause).
6. **Mobile:** the ASCII scales down to fit the screen width; it is never cut off or wrapped.
7. **Reduced motion:** with `prefers-reduced-motion`, the scramble stops and the sequence jumps to its
   end state.
8. **Reference code stays local:** the three iremcnar repos have no licence file, so `reference/` is kept
   out of the published site (and out of a public repo — see Open Questions).

## Tech Stack

- PyScript **2026.7.3** (latest, 29 Jul 2026), MicroPython runtime (`<script type="mpy">`, ~170 KB,
  near-instant start), pinned CDN: `https://pyscript.net/releases/2026.7.3/core.js` + `core.css`.
  Python stays on the main thread (GitHub Pages can't send the COOP/COEP headers worker mode needs).
- Python → DOM crossing once per frame per block (one `textContent` string), callbacks wrapped with
  `pyscript.ffi.create_proxy` once and reused.
- Flap folding is drawn by Python in characters; the slide-away is a CSS `transform` transition on the
  envelope `<pre>` (Python only toggles a class).
- Pure 7-bit ASCII everywhere (no box-drawing or emoji, so no fallback-font width jumps); one locked
  monospace font stack, `line-height: 1`, ligatures off.
- Accessibility: art `<pre>`s get `role="img"` + `aria-label`; YES/NO are real `<button>`s with a fixed
  `aria-label` and their churning glyphs `aria-hidden`; at most 3 flashes per second.
- Plain HTML + CSS for the shell: `<pre>` blocks for ASCII, real `<button>` elements for YES/NO.
- Python 3 (CPython, via the `py` launcher — 3.14 on this machine) only for local tests and serving.
- No npm, no build step, no extra Python packages.

## Commands

```
Serve locally:  py -m http.server 8000 --directory site
Open:           http://localhost:8000/
Test:           py -m unittest discover -s tests -v
Deploy:         GitHub Pages from the site/ folder (GitHub Actions "upload-pages-artifact", path: site)
```

## Project Structure

```
site/                  → everything GitHub Pages serves (and nothing else)
  index.html           → page shell: PyScript tag, <pre> blocks, two <button>s
  style.css            → colours, monospace sizing, slide/flap transitions
  main.py              → browser glue (runs in PyScript): DOM writes, animation loop, click handlers
  art.py               → pure ASCII generators: headline, envelope, buttons, scramble — no browser imports
  pyscript.toml        → loads art.py next to main.py
tests/test_art.py      → CPython unittest for art.py
docs/                  → how the reference repos work + ASCII technique guides
reference/             → local copies of the iremcnar repos + envelope.png (not published)
research_notes/, reports/ → deep-research notes and final report
SPEC.md, CLAUDE.md
```

`art.py` stays importable by both MicroPython and CPython, so the drawing logic is tested without a
browser.

## Code Style

Small, flat, readable Python. Pure functions return lists of strings (one per row); only `main.py`
touches the DOM.

```python
RAMP = " .:-=+*#%@"  # light -> dense


def churn(mask, glyphs, tick):
    """Same shape as mask; each filled cell picks a glyph from a hash of (row, col, tick)."""
    return ["".join(glyphs[(r * 73856093 ^ c * 19349663 ^ tick * 83492791) % len(glyphs)] if ch != " " else " "
                    for c, ch in enumerate(row)) for r, row in enumerate(mask)]
```

Glyph choice is a hash of cell + integer tick, not `random`: same look on 60 and 144 Hz screens, and
it avoids MicroPython's cut-down `random` module.

- snake_case, constants UPPER_CASE, no classes unless state needs one.
- Stick to the MicroPython-safe subset in `art.py`: no `dataclasses`, `typing`, `pathlib`, numpy.
- Comments only for the "why".

## Testing Strategy

- **Unit (CPython `unittest`, `tests/test_art.py`)** for `art.py`:
  - headline, envelope and button art are rectangular (all rows the same width) and fit the target width;
  - the envelope's diagonals meet at the seal and the heart sits on the centre;
  - `churn` keeps the shape: spaces stay spaces, non-spaces stay non-spaces, width unchanged;
  - every flap frame from closed to open has the same width and only ASCII characters;
  - easing helpers hit 0 at t=0 and 1 at t=1.
- **In-browser check (manual + screenshots in the built-in browser)** at 1280×800 and 375×812:
  load state, buttons scrambling, mid-open, end state; console free of errors.
- No coverage target; every non-trivial function in `art.py` has at least one test.

## Boundaries

- **Always:** keep every visual ASCII; run the unit tests before saying a change works; check the page
  in the browser (desktop + mobile size) after visual changes; keep `site/` self-contained with relative
  paths so it works under `username.github.io/repo/`.
- **Ask first:** creating the git repo / GitHub repo, pushing, enabling Pages; adding any dependency;
  publishing anything from `reference/`; changing the agreed look or sequence.
- **Never:** use images or emoji for the art; commit secrets; copy reference code into `site/`
  (re-implement ideas instead); run the downloaded reference programs.

## Success Criteria

1. Opening `site/index.html` through the local server shows `Will you open ?` as a big ASCII banner,
   readable at 1280px and 375px wide, with no horizontal scrollbar.
2. The envelope is entirely characters and matches the reference image's structure (rectangle,
   corner-to-centre diagonals, red heart seal, textured cream paper).
3. Two ASCII-bordered rectangles, YES and NO, sit in front of the envelope; their words scramble
   continuously (~8–15 updates/s) and stay readable; both are real buttons reachable by Tab and Enter.
4. YES → flap opens (~1 s) → envelope slides fully off-screen (~1 s) → empty end stage; YES/NO disappear.
5. With reduced motion enabled, no scrambling and the sequence ends instantly.
6. Python starts and the page is interactive within ~3 s on broadband (measured: 706 KB uncompressed,
   drawn well under 1 s locally); until then an ASCII `. . .` line shows, so the screen is never blank.
   (Changed from "art visible before Python": that needs a build step, not worth it for a sub-second gap.)
7. No console errors; `py -m unittest discover -s tests -v` passes.

## Open Questions (default in bold is used if you just approve)

1. **What does NO do?** **(a) a little shake and its glyphs go wild for a moment, nothing else**;
   (b) NO dodges the cursor; (c) NO turns into a second YES; (d) something else.
2. **Repo / hosting:** your home folder is the git repo right now. **`git init` a new repo in this folder;
   you create the GitHub repo and turn on Pages** (the GitHub CLI isn't installed).
3. **reference/ in the repo:** **gitignored, local only (docs link to upstream)**, or committed.
   Committing unlicensed copies to a public repo isn't ideal.
4. **After the envelope slides away:** **empty stage for Part 2**, or the blank letter paper slides up out
   of the envelope first.
5. **Recipient-specific text** (names, a date) in Part 1: **none**.
6. **The `[ pause ]` toggle** (assumption 5d): **keep it**, or drop it and accept the accessibility gap.
