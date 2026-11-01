# Capability Map: "To Esther" desktop app

Status: **APPROVED (2026-10-31).** This is the module index. Progress (2026-11-01): G1–G5 and G7 (invitation
finale, chase redesign) built and tested; G6 (release) in progress. Per-requirement status is in `tasks/todo.md`.
Each module's requirements and acceptance IDs are the `SPEC.md` section listed; there are no separate
per-module spec files. The web-era map is in `docs/superseded/web/`.

| Module id | Responsibility | Depends on | Spec | Gate |
|---|---|---|---|---|
| `app-shell` | Window, main loop, viewport and DPI, input routing, assets and fonts, clock, narrative state machine, CLI (`--scene`, `--selftest`) | — | §3–§8 | G1 |
| `release` | PyInstaller build, icon, zip, third-party notices, frozen self-test | `app-shell` | §16 | G1 (skeleton), G6 (final) |
| `letter` | Procedural envelope (lighting, grain, shadow, float), heart seal, "To Esther", question typography | `app-shell` | §9 | G2 |
| `buttons` | Slot/identity model, fixed hitboxes, hover glyph shift, swap and escape movement | `app-shell` | §9 | G2 |
| `yes-reveal` | Writing dissolve, flap, sheet emerging, camera zoom | `letter` | §10.1 | G3 |
| `night` | Lighting shift, paper → soil dither, grass, wind, seed and puff; the sky (stars, then clouds and the moon as the flower blooms; `letter/art/sky.py`) | `yes-reveal` | §10.2–§10.3, §10.6 | G3 |
| `flower` | Pointillist sea holly at 640 × 640: growth, bud glow, click to bloom, wind and pointer sway | `night` | §10.4 | G3 |
| `fireflies` | About 40 waypoint fireflies across the whole night: halos, trails, independent pulses, depth bands | `flower` | §10.5 | G3 |
| `quality` | Scaling and DPI matrix, fps budgets, timing polish, quality tiers | `fireflies` | §7, §14, §15 | G4 |
| `no-route` | Three questions, earthquake, swap, heart shatter, message, auto-open, NO escapes | `buttons`, `letter`, `quality` | §11 | G5 |
| `chase` | 320 × 320 ASCII runner: the red mouse pointer, obstacles, scripted fair course, recovery | `no-route` | §12 | G5 |
| `ending` | Cornered button, proximity shake, glitch, dissolve, face, single tear, permanent black | `chase` | §13 | G5 |

Build order: `app-shell` + `release` skeleton → `letter`, `buttons` → `yes-reveal` → `night` → `flower` →
`fireflies` → `quality` → **gate** → `no-route` → `chase` → `ending` → `release` (final).

Rules:
- Arrows point one way.
- `flower` and `chase` never run in each other's route.
- Shared systems (glyph effects, dissolve, camera, particles) live in `letter/engine/` and are owned by
  `app-shell`.
