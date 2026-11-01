# Tasks and traceability ("To Esther" desktop)

Status keys:
- `todo` — not started.
- `wip` — in progress.
- `impl` — implemented.
- `tested` — unit or scenario test passes.
- `verified` — checked in the packaged exe.

Acceptance IDs come from `SPEC.md`.

## G1 Desktop foundation (`app-shell`, `release` skeleton)
| Task | Status |
|---|---|
| venv + `requirements.txt` / `requirements-dev.txt` | tested |
| Fonts in `assets/fonts` + OFL licences | verified |
| Retire web: `site/` → `legacy/web/`, delete the Pages workflow | tested (legacy tests still pass) |
| `letter/` package: `__main__`, config, viewport, timeline/clock, glyphs, assets, state machine | tested |
| Unit tests: state machine, viewport round-trip, clock | tested (17) |
| `tools/build.py` + icon → `dist/LetterToEsther/`; frozen `--selftest` from a copy outside the repo | verified (68.6 MB folder, 29.6 MB zip) |

## Acceptance traceability
| ID | What | Module | Test | Status |
|---|---|---|---|---|
| L1 | "To Esther" fades in, old text gone | letter | scene test + shot | tested (shot 01) |
| L2 | Top-down shading, drop shadow | letter | shot | tested (lighting unit tests; shots 02, 06) |
| L3 | Float never visibly loops | letter | unit (no period < 60 s) | tested |
| L4 | Question typography, readable at 1280×800 and 640×400 | letter | shots | tested (shaded ASCII banner v2: mark variety, top-left light, extrusion, vine, one/two-line fit; checked by eye for three questions at 1280×800 and 1920×1080) |
| L5 | Hitboxes fixed during hover | buttons | unit | tested |
| L6 | Hover shift settles to the exact label | buttons | unit | tested |
| L7 | Button colours | buttons | unit | tested |
| Y1 | Full YES chain, no cut or stretch at 3 sizes | yes-reveal/night | selftest + shots | tested (selftest walks the chain; shots at 1280×800, 1920×1080, 1366×768) |
| Y2 | Flower 640×640: a sea holly in the user's blue gradients, recognisable next to the photos | flower | unit + shot | tested (`test_flower`, 16 tests; shots 15–20 at 1280×800 and 1920×1080; bloomed 2.3–2.9 ms, bloom transition up to 6.6 ms, over the 5 ms part budget) |
| Y3 | Bloom only on click, staggered petals | flower | unit | tested (click-only: story tests; stagger checked by eye in shot 18) |
| Y4 | Pointer lean ≤ 6°, wind continues | flower | unit | tested (`test_night_scene`) |
| Y5 | Fireflies cover all quadrants, desynchronised, flower brightest | fireflies | unit + shot | tested (v2: rise from the grass, flash rhythms, far/near/bokeh layers, bloom halos; shots 19–20) |
| Y6 | 60 fps average, no frame over 33 ms | quality | selftest log + real window | wip: real window, YES route, with sky, fireflies v2 and sea holly (2026-11-01, quiet machine): 1280×800 letter 60.3 / night 60.3 fps, one frame 33.1 ms; 1920×1080 letter 56.4 (the YES fade frames) / night 60.0 fps, three frames 35.8–36.1 ms. Frozen exe selftest: YES median 8.6 ms (one 83 ms frame on a cold first run), NO median 0.6 ms |
| Y7 | Sky clear before the bloom; clouds gather and the moon appears after it, clear of the aura | sky | unit + shot | tested (`test_sky`, 14 tests; shots 16–20; budget test scales its 2.5 ms limit by measured machine load) |
| A11 | Windows animations off: calmer float, hover, wave and sway; no glints | quality | subprocess test (`LETTER_CALM=1`) | tested |
| G4-DPI | Letterbox and hit-testing at 1920×1080, 1366×768, 640×400, 1280×800 (letter and night) | quality | scene tests | tested |
| N1–N3 | no-1 question crossfade, no-2 earthquake (peak 10.7 px, settles exactly) + question, no-3 swap with hitboxes and colours following; YES still wins | no-route | scene tests (`NoIntro`) + shots | tested |
| N4–N8 | no-4: tremble, crack, varied shatter (238 fragments, 21 glyphs), message written in full, auto-open, NO hops onto the sheet recognisably, input locked; camera dive into the chase | no-route | unit (`HeartBreaks`, `NoShatterAndEscape`) + selftest + shots n06–n12 | tested |
| C1–C5 | Chase: Space only (core + scene), typical bot 91.6 s / never-jump 107.5 s, stumble recovery, NO always visible, same course at 30/60/144 fps; the player is a red ASCII mouse pointer (user clarification) | chase | unit (`test_chase`, `test_chase_scene`) + selftest + shots n13–n16 | tested |
| E1–E4 | No click before cornered; tremble grows with pointer proximity; glitch, dissolve, kaomoji face (´•ω•`) with one tear, black forever | ending | unit (`test_ending`, `test_chase_scene`) + selftest + shots n17–n24 | tested |
| R1 | The zip, extracted to a new folder outside the repo, launches and plays both routes | release | frozen `--selftest --window` | tested (2026-11-01: both routes PASS in a visible window, scripted input; not yet a hand-played double-click run) |
| R2 | Runs with network access disabled | release | code search | implemented: no network code anywhere in `letter/`; not run with the network actually switched off |
| R3 | Closing and relaunching works | release | manual | verified: launched twice from the extracted zip, closed through the window, exit code 0 both times |
| R4 | `--selftest` passes on the frozen exe | release | frozen selftest | verified (both routes, run from `C:\`, exit 0) |
| R5 | Clean Windows machine without Python | release | manual | not possible here: only the development PC was available |
