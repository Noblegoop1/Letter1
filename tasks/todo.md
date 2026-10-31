# Tasks — Part 1

- [x] Task 1: `site/art.py` + `tests/test_art.py` — block font, headline (wide/narrow), envelope frames
      for flap angle 0–180°, heart seal, button art, churn, `to_html`.
  - Acceptance: all art rectangular, 7-bit ASCII, heart mirror-symmetric, churn keeps shape,
    `to_html` escapes `& < >`.
  - Verify: `py -m unittest discover -s tests -v`
  - Files: site/art.py, tests/test_art.py
- [x] Task 2: page shell — `index.html`, `style.css`, `pyscript.toml`, `main.py`; scene renders,
      buttons churn, YES plays open + slide, NO shakes, pause toggle, reduced motion.
  - Acceptance: SPEC success criteria 1–5 visible in the browser.
  - Verify: `py -m http.server 8000 --directory site`, built-in browser at 1280×800 and 375×812,
    screenshots of load / mid-open / end, console clean.
  - Files: site/index.html, site/style.css, site/pyscript.toml, site/main.py
- [x] Checkpoint: tests pass, page works end to end, startup time measured (SPEC criterion 6).
- [x] Task 3: repo — `git init`, `.gitignore` (reference/), Pages workflow uploading `site/`.
  - Verify: `git status` shows no reference/ files; workflow YAML points at `site`.
  - Files: .gitignore, .github/workflows/pages.yml
- [x] Task 4: independent code review; fix findings.
