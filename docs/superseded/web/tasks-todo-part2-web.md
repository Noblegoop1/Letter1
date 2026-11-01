> **SUPERSEDED (2026-10-31).** Web-era document kept for history only. The project is now a Windows desktop app; the authoritative spec is `SPEC.md` at the project root (see also `docs/adr/0001-desktop-stack.md`).

# Tasks — Part 2 (Part 1 tasks all done; see git history)

- [x] T1 `stage`: `site/stage.py` + `tests/test_stage.py` — phases, events, clock, easing, hash, Bayer.
  - Verify: `py -m unittest discover -s tests -v`
- [x] T2 `night-ground` (agent): `site/night.py`, `site/night.css`, `tests/test_night.py`.
- [x] T3 `flower` (agent): `site/flower.py`, `site/flower.css`, `tests/test_flower.py`.
- [x] T4 `fireflies` (agent): `site/fireflies.py`, `site/fireflies.css`, `tests/test_fireflies.py`.
- [x] T5 `letter-look` + `button-hover`: `site/art.py`, `tests/test_art.py` — shading, opaque layers,
      writing, shadow, italic headline, ripple buttons.
- [x] T6 `paper-reveal`: `site/reveal.py`, `tests/test_reveal.py`.
- [x] T7 Integration: `site/main.py`, `site/index.html`, `site/style.css`, `site/pyscript.toml`.
  - Verify: full journey in the browser at 1280×800 and 375×812, in-page timing, console clean.
- [x] Checkpoint: every SPEC-*.md success criterion checked; review agent; fixes.
