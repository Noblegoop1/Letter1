# ASCII Love Letter

A love-letter web page for GitHub Pages. Page logic is Python running in the browser (PyScript,
MicroPython runtime); **every visual is ASCII characters** — art, textures, buttons. No images.

Read `SPEC.md` first. Work is spec-gated: specify → plan → tasks → implement, with approval between.

## Commands

```
py -m http.server 8000 --directory site      # serve, then open http://localhost:8000/
py -m unittest discover -s tests -v          # unit tests for site/art.py
```

`python` on this machine is the Microsoft Store alias; use `py` (CPython 3.14). No `gh` CLI.

## Layout

- `site/` — the published page (index.html, style.css, main.py, art.py, pyscript.toml). Only this ships.
- `tests/` — CPython tests for `site/art.py` (pure functions, no browser imports, MicroPython-safe).
- `docs/` — how each reference repo works, plus ASCII technique notes.
- `reference/` — local copies of the reference repos and the envelope design image. Not published.
- `research_notes/`, `reports/` — deep research on ASCII art and animation.

## References

Style references are three small generative-art programs by iremcnar (Python desktop apps: Tk/turtle).
They have **no licence file**: learn from them, re-implement ideas, never copy their code into `site/`,
and never run them (downloaded code that opens GUI windows).

| Repo | Local copy | Doc | What to take from it |
|---|---|---|---|
| https://github.com/iremcnar/Flowers (commit `1900a38`) | `reference/flowers/flow.py` | `docs/flowers.md` | keyframe timeline (Catmull-Rom), smoothstep, particle growth by prefix slices, palettes, wilt/fall |
| https://github.com/iremcnar/loveYou (commit `ee7be9e`) | `reference/loveyou/love.py` | `docs/loveyou.md` | parametric heart, scanline spans to fill a shape with words, ease-out float-in, shimmer |
| https://github.com/iremcnar/neonButterfly (commit `0aad531`) | `reference/neonbutterfly/neon.py` | `docs/neonbutterfly.md` | Fay's butterfly curve, neon colour bands, progressive draw-in by radius |

- Envelope design: `reference/envelope.png` — cream rectangle, dark outline, X diagonals to a red heart seal.
- ASCII art + animation research: `reports/ASCII art and animation techniques.md`
  (notes in `research_notes/ASCII art and animation techniques/`).

## Rules

- Everything visible is pure 7-bit ASCII in `<pre>` blocks (no box-drawing, no emoji); colour via CSS on
  spans. Buttons are real `<button>`s with a fixed `aria-label`; churning glyphs are `aria-hidden`.
- Animation timing uses the `requestAnimationFrame` timestamp; glyph picks are a hash of (cell, tick), not
  `random`. Python moves characters; CSS transforms move whole blocks.
- Keep `site/art.py` pure and MicroPython-safe (no dataclasses, typing, pathlib, numpy); only `main.py`
  touches the DOM.
- Relative paths only, so the site works under `username.github.io/<repo>/`.
- Respect `prefers-reduced-motion` (no scramble, jump to end states).
- Verify visual changes in the browser at desktop (1280×800) and phone (375×812) sizes, with screenshots.
- MicroPython in the page is ~10x slower than CPython (a full envelope frame was 35 ms): build static
  layers once at import, cache per-frame HTML, and time real work in-page before calling it fast.
- If the browser pane is hidden, `requestAnimationFrame` never fires. To test the flow anyway, append a
  `<script type="mpy">` from JS: it shares main.py's globals, so it can call `tick(ms)` / `open_letter(None)`
  and `print` results to the console.
- Ask before: git init / pushing / enabling Pages, adding dependencies, publishing `reference/`.
