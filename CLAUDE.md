# "To Esther" — interactive letter, Windows desktop app

A small interactive piece sent to one person as a downloadable Windows app: extract the zip, double-click
`LetterToEsther.exe`, play. **It is not a website any more.** Stack (ADR 0001): Python 3.14 +
pygame-ce + NumPy, released with PyInstaller as a portable folder.

**Read `SPEC.md` first.** It is the single authoritative spec, covering both routes (YES: flower and
fireflies; NO: chase game and ending), rendering, timing, testing and release. `CAPABILITY-MAP.md` is the
module index and gate order. `docs/adr/0001-desktop-stack.md` records the stack decision.
`docs/superseded/web/` holds the old web specs for history; never follow them.

Status: SPEC v3 **approved 2026-10-31** (defaults for Q1–Q5; later change, same day: the envelope, paper, dedication, questions and all text stay ASCII in JetBrains Mono; only the night flower, meadow and fireflies are particle dots; further same-day changes are listed in SPEC's status line: shaded ASCII banner, visible tilt and hover, the flower is now a sea holly in blue gradients, clouds and moon; 2026-11-01: the chase player is a mouse *pointer*, the ending face a kaomoji). Gates
G1–G5 are built (both routes play end to end). **G7 (2026-11-01) is built and tested:** the chase is
redesigned as a pointer-vs-floating-NO-button runner (SPEC §12), and the YES route gains the firefly
invitation, "Will you go on a date Tuesday?", with its own YES/NO and two endings (SPEC §10.7). G6's
release checks follow (see `tasks/todo.md` for what is verified). User-facing notes are in `README.md`. Work is spec-gated: specify → plan → tasks → implement,
with approval between. Don't commit unless asked.

## Commands (SPEC §4)

```
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m letter                  # run the app
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python -m letter --selftest       # scripted run of both routes (add --window to watch it)
.venv\Scripts\python tools\shots.py             # screenshots to build\shots\ (look at them)
.venv\Scripts\python tools\build.py             # dist\LetterToEsther\ + zip
```

`python` on this machine is the Microsoft Store alias; use `py` or the venv's python. No `gh` CLI.

## Layout
- `letter/` — the app package (`engine/`, `scenes/`, `art/`).
- `assets/fonts/` — bundled OFL fonts and their licence files.
- `tools/` — build and screenshot tools.
- `tests/` — the unit tests and headless scene tests.
- `legacy/` — `web/`: the retired PyScript site and its tests; `desktop/`: the superseded lotus flower.
  Not shipped; don't extend them.
- `docs/`: `adr/`, the reference-repo docs (`flowers.md`, `loveyou.md`, `neonbutterfly.md`) and
  `superseded/`.
- `reference/` — local copies of the iremcnar repos, the envelope image and the user's sea holly photos.
  Not published, not shipped.

## References
Style references are three generative-art programs by iremcnar.
- **No licence:** they have no licence file (checked again 2026-10-31: GitHub reports `license: null`
  for Flowers). Learn from them and re-implement the ideas; never copy their code into the app; never
  run them.
- **The flower:** a pointillist sea holly (user photos and blue gradients in `reference/sea-holly/`,
  not shipped). Its dot technique follows iremcnar/Flowers (`docs/flowers.md`); shipping that repo's
  actual code needs the author's permission (SPEC Q1). The earlier lotus is in `legacy/desktop/`.

| Repo | Local copy | Doc |
|---|---|---|
| https://github.com/iremcnar/Flowers (commit `1900a38`) | `reference/flowers/flow.py` | `docs/flowers.md` |
| https://github.com/iremcnar/loveYou (commit `ee7be9e`) | `reference/loveyou/love.py` | `docs/loveyou.md` |
| https://github.com/iremcnar/neonButterfly (commit `0aad531`) | `reference/neonbutterfly/neon.py` | `docs/neonbutterfly.md` |

## Rules
- All motion is time-based (never per frame). Physics runs on a fixed step.
- One viewport transform per scene serves both drawing and input.
- Logical canvases: letter 1280 × 800, night and flower 640 × 640, chase 320 × 320.
- Build static geometry, textures and glyph atlases once; reuse buffers per frame. Measure fps before
  calling something fast.
- Verify visuals by rendering screenshots (`tools/shots.py`) and looking at the PNGs, at 1280 × 800 and
  1920 × 1080. The headless self-test covers flows.
- Everything visible is ASCII glyphs except the night's pointillist dots and the kaomoji faces. A
  kaomoji's glyphs must exist in the bundled font (tested), except the joy faces (hearts and similar),
  which come from Windows' Segoe UI Symbol at runtime with a bundled-font fallback.
- Three decisions stay separate: the envelope's YES/NO (`yes`/`no`), the invitation's YES/NO
  (`date-yes`/`date-no`, only in `invite`), and catching the cornered NO (`catch`). They have their own
  buttons, hitboxes, events and state.
- Builds: the app is `dist\LetterToEsther\LetterToEsther.exe` (or the zip). `tools/build.py` deletes
  PyInstaller's work folder, whose half-built exe fails with "Failed to load Python DLL".
- Ask before:
  - adding dependencies beyond pygame-ce, numpy and pyinstaller;
  - adding sound;
  - commits and pushes;
  - shipping any iremcnar code.
- Never: network access at runtime; claiming a test that only read source; contradictory docs.
