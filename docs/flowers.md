# Reference notes: iremcnar/Flowers ("Pointillism Flower")

How `flow.py` works, line by line, and how its techniques map onto an
all-ASCII, browser-hosted love letter.

| | |
|---|---|
| Source | https://github.com/iremcnar/Flowers |
| Commit | `1900a387103e38cf2e9b14262f16e95b3df05fec` (as supplied in our brief; the local copy has no `.git`, so the hash cannot be re-verified from the snapshot itself) |
| Date | 2026-10-15 (the README's screenshot filename carries the same date) |
| Local copy | `part1/reference/flowers/` (`flow.py` 24,488 bytes / 558 lines, `README.md` 1,378 bytes / 19 lines, `.gitattributes` 68 bytes / 2 lines) |
| Licence | **None.** There is no `LICENSE`/`COPYING` file, and `flow.py` has no licence or copyright header (it starts with `import math`, `flow.py:1`). Under default copyright rules we have no granted right to copy, modify or redistribute the code. Treat it as a read-only style reference: study the techniques, write our own implementation, credit the inspiration. (This is a working note, not legal advice.) |
| How it was studied | Read in full. **Never executed** (it opens a Tk window, needs numpy/Pillow, and is downloaded code). The few numbers marked "computed" below come from re-implementing individual formulas in a separate scratch script, not from running `flow.py`. |

**What it draws.** A single-file generative-art program that grows, blooms and
withers one stylised purple/magenta flower over a 45-second timeline, using
nothing but small coloured dots ("splats", pointillism) on a black canvas.
There is a textured brown soil mound; a purple stem that follows a cubic Bezier
curve; four teal-to-violet leaves; 23 petals in four layers (20,620 dots) with
rim highlights, white specks and gold flecks; a cluster of stamens; a glowing
aura made of a halo, seven orbiting rings, six bright nodes and drifting
sparks; and finally a wilt phase where the stem arches over, the head flips
nearly upside-down, and petal dots flutter down onto the soil. Every frame is a
pure function of time `t`: `Plant.render(t)` returns an `(H, W, 3)` `uint8`
array.

---

## 1. What is in the repo, and README errata

The snapshot has exactly three files:

| File | Content |
|---|---|
| `flow.py` | the whole program, 558 lines |
| `README.md` | 19 lines: title, description, screenshot link, feature list, a truncated "How to Run" |
| `.gitattributes` | `* text=auto` (line 2), i.e. LF normalisation only |

No tests, no `requirements.txt`, no `LICENSE`, no package structure.

README problems, all checkable:

* It tells you to run `python flower.py` (`README.md:19`), but the file is
  `flow.py`. The brief flagged the same thing.
* The "How to Run" section is cut off: the code fence opened at `README.md:17`
  is never closed, and only the interactive command is shown. The `--png` and
  `--gif` flags exist only in the source (`flow.py:554-557`) even though the
  feature list (`README.md:13`) mentions "headless flags".
* The feature list says "pulsing stamens" (`README.md:12`). The stamen block in
  `render` (`flow.py:406-417`) contains no time term; stamens only change with
  `bloom`, `size`, `wilt` and the head's overall sway. (Rings and sparks do
  pulse; see section 7.6.)
* The screenshot is a GitHub-hosted attachment (`README.md:5`), not in the
  repo, so we have no reference image to compare against.

---

## 2. How to run

Three modes, selected by a bare `sys.argv` test with no argparse (`flow.py:553-559`):

```text
python flow.py          # interactive Tk viewer   -> App().run()
python flow.py --png    # headless: 5 stage PNGs + a strip   -> save_png()
python flow.py --gif    # headless: animated GIF  -> save_gif()
```

`--png` is tested first, then `--gif`, otherwise the viewer starts. Any other
arguments are ignored. Output files go to the current working directory.

| Mode | Resolution | Output files | Source |
|---|---|---|---|
| Viewer | square, `H = min(0.92 * screen_h, 0.96 * screen_w)`, `W = H` | none unless you press `S` (`flower_frame.png`) | `flow.py:512-515` |
| `--png` | 1000 x 1000 | `flower_1.png` ... `flower_5.png`, plus `flower_stages.png` (five 500 x 500 LANCZOS thumbnails side by side, 2500 x 500) | `flow.py:479-492` |
| `--gif` | 640 x 640, 12 fps, `int(45 * 12) + 1 = 541` frames | `flower.gif`, infinite loop | `flow.py:495-501` |

The PNG stage times are 3, 9, 16, 26 and 41 seconds (`flow.py:482`). Using the
state table in section 4.3 (computed), that is: a tiny sprout, a young bud with
the first aura, half-open, full bloom, and fully withered.

**Dependencies.**

* `numpy` (uses `np.random.default_rng`, so numpy >= 1.17) - `flow.py:5`.
* `Pillow` (`Image`, plus `ImageTk` imported lazily) - `flow.py:6, 507`.
* `tkinter` from the standard library, imported *inside* `App.__init__`
  (`flow.py:506`), so the headless `--png`/`--gif` modes do not need Tk.
* Standard library: `math`, `sys`, `time` (`flow.py:1-3`).

**Keyboard controls** (`flow.py:525-528`):

| Key | Action |
|---|---|
| `Space` | toggle pause (`toggle`, `flow.py:532-533`) |
| `R` | restart: `clock = 0.0` (`restart`, `flow.py:535-536`) |
| `S` | render the current time and save `flower_frame.png` |
| `Esc` | destroy the window |

---

## 3. Architecture map

### 3.1 Layout of `flow.py` (line index)

| Lines | Item | Kind |
|---|---|---|
| 1-6 | imports | |
| 8-12 | `SEED`, `TIME_SCALE`, `TICK_MS`, `WIN_FRAC`, `LOOP` | tuning constants |
| 14-24 | `KEYS`, `T_END` | keyframe matrix, lifecycle length |
| 26-37 | 12 named palettes | colour data |
| 39-48 | `LAYERS` | petal ring definitions |
| 49-54 | `LEAF_DEFS` | leaf definitions |
| 56-59 | `_OFF`, `OFF`, `D2` | precomputed disc stamp offsets |
| 62-64 | `smoothstep` | helper |
| 67-68 | `sinc` | helper |
| 71-72 | `profile` | helper (petal/leaf width profile) |
| 75-80 | `palette_pick` | helper (noisy palette sampling) |
| 83-88 | `area_u` | helper (rejection sampling) |
| 91-95 | `sample_v` | helper (rim-biased sampling) |
| 98-105 | `permute`, `cat` | helpers on dict-of-arrays |
| 108-117 | `splat` | rasteriser: stamp discs into the canvas |
| 120-134 | `Batch` | collects particles, depth-sorts, splats |
| 137-148 | `state` | keyframe interpolation (Catmull-Rom) |
| 151-158 | `bez` | cubic Bezier + derivative |
| 161-162 | `mixcol` | live-to-wilt colour blend |
| 165-178 | `Plant.__init__` | geometry constants + build order |
| 180-183 | `Plant.surface` | soil height function |
| 185-214 | `Plant.build_soil` | static soil image + crumb arrays |
| 216-228 | `Plant.build_stem` | stem particle arrays |
| 230-236 | `Plant.ctrl` | stem Bezier control points |
| 238-265 | `Plant.build_head` | all petal particles |
| 267-278 | `Plant.build_stamens` | stamen particles |
| 280-294 | `Plant.build_leaves` | leaf particles |
| 296-325 | `Plant.build_fx` | halo, rings, sparks, falling petals |
| 327-476 | `Plant.render` | per-frame transform + composite |
| 479-492 | `save_png` | exporter |
| 495-501 | `save_gif` | exporter |
| 504-550 | `App` | Tk viewer, clock, key bindings |
| 553-559 | `__main__` | mode dispatch |

### 3.2 Data flow

```text
SEED = 5
  |
  v
rng = np.random.default_rng(5)                   Plant.__init__  (flow.py:168)
  |   ONE shared stream, consumed in a fixed order:
  |   soil -> stem -> head -> stamens -> leaves -> fx   (flow.py:173-178)
  v
build_*  (run once)                 particle ARRAYS ("structure of arrays")
  soil     -> self.base   static uint8 HxWx3 image, soil splatted once
              self.cr     520 "crumb" particles (animated later)
  stem     -> self.stem   3,600 dots   (s, lat, live, wilt, rn, rad)
  head     -> self.head   20,620 dots  (th, u, v, per-petal params, colours)
  stamens  -> self.st     700 dots on 60 filaments
  leaves   -> self.leaf   3,600 dots   (4 leaves x 900)
  fx       -> self.halo 1,800   self.ring 1,720   self.spark 280   self.fall 260
  |
  |   every array has been run through permute(): random order
  v
render(t)  (every frame, flow.py:327)
  state(t) -> (stem, size, bloom, wilt, leaf, glow)  six numbers in [0,1]
  ctrl()   -> Bezier control points -> bez() -> stem curve, head anchor (hx,hy)
  per system, fully vectorised numpy, using only the FIRST nv entries
  of each array (prefix slice => uniform random subset => "growth"):
      stem / leaves / petals / stamens / halo / rings / sparks / falling dots
        -> Batch.add(x, y, colour, radius, z)
  Batch.draw: concatenate -> argsort(z) -> splat (painter's algorithm)
  nodes splat (6 big dots), crumbs splat (soil hop), on top
  |
  v
(H, W, 3) uint8 array
  -> Tk PhotoImage.paste (viewer)  |  PNG file  |  GIF frame
```

### 3.3 Particle budget (exact, from the source)

| System | Count | Where |
|---|---|---|
| Soil body, baked once | 26,000 | `flow.py:187` |
| Soil pebbles, baked once (radius 2-3) | 170 | `flow.py:199` |
| Soil crumbs (animated) | 520 | `flow.py:205` |
| Stem | 3,600 | `flow.py:217` |
| Leaves | 4 x 900 = 3,600 | `flow.py:282-283` |
| Petals | (8x1150) + (6x950) + (5x760) + (4x480) = 20,620 over 23 petals | `flow.py:40-47` |
| Stamens | 700 (60 filaments) | `flow.py:268` |
| Halo | 1,800 | `flow.py:298` |
| Rings | 700 + 6 x 170 = 1,720 | `flow.py:305-310` |
| Ring nodes | 6 (bigger dots, drawn separately) | `flow.py:440-443` |
| Sparks | 280 | `flow.py:313` |
| Falling petal dots | 260 | `flow.py:318` |

Sum of plant particles at full bloom, excluding crumbs and the baked soil:
3,600 + 3,600 + 20,620 + 700 + 1,800 + 1,720 + 6 + 280 = 32,326 (the 260
falling dots appear only once wilting starts, and the aura disappears as glow
fades to 0). That is what the README means by "tens of thousands".

---

## 4. Constants

### 4.1 Scalar knobs (`flow.py:8-12`)

| Name | Value | Meaning |
|---|---|---|
| `SEED` | 5 | seed for the one `default_rng` that generates every random number |
| `TIME_SCALE` | 1.0 | animation time = wall-clock time **divided by** this (`flow.py:543`), so a value of 2.0 makes it run at half speed |
| `TICK_MS` | 10 | delay passed to Tk `after()` between frames (`flow.py:547`) |
| `WIN_FRAC` | 0.92 | window height as a fraction of screen height (`flow.py:513`) |
| `LOOP` | `False` | if true, restart once `t > T_END + 4` (`flow.py:544-545`) |

### 4.2 `KEYS`: the keyframe matrix (`flow.py:14-23`)

Eight rows, seven columns. Column 0 is time in seconds; columns 1-6 are six
"state channels" that `state()` interpolates and `render` unpacks in this
exact order (`flow.py:329`: `stem, size, bloom, wilt, leaf, glow = state(t)`).
All channels live in [0, 1].

| Column | Channel | What it drives in `render` |
|---|---|---|
| 0 | time (s) | key times 0, 5, 10, 16, 24, 30, 39, 45; `T_END = 45.0` (`flow.py:24`) |
| 1 | `stem` | stem length `L = Ls * stem` (`flow.py:335`), how many stem dots are shown (`flow.py:341`), stem thickness (`flow.py:345`), sway amplitude (`flow.py:336`), gates leaves (`stem > 0.05`) and the head (`stem > 0.01`) |
| 2 | `size` | flower-head scale `Ls_ = Lf * size` (`flow.py:377`), fraction of petal dots shown (`flow.py:384`), fraction of stamen dots (`flow.py:409`); head is skipped if `size <= 0.05` (`flow.py:373`) |
| 3 | `bloom` | 0 = closed bud, 1 = fully open: interpolates petal opening angle, curvature and width (`flow.py:389, 391, 397`), head tilt (`flow.py:375`), stamen reveal (`flow.py:406`) |
| 4 | `wilt` | 0 = alive, 1 = withered: recolours stem/leaves/petals to the brown "wilt" palettes, bends the stem, flips the head, curls petals, drops petal dots (many sites; section 7) |
| 5 | `leaf` | leaf length, dot count and unfurl angle (`flow.py:353, 359, 362`) |
| 6 | `glow` | the aura: halo/rings/nodes/sparks counts and brightness (`flow.py:419-453`) |

The matrix:

```text
 t(s)  stem  size bloom wilt  leaf  glow
  0.0  0.00  0.00 0.00  0.0   0.00  0.00
  5.0  0.42  0.22 0.00  0.0   0.25  0.00
 10.0  0.62  0.42 0.00  0.0   0.50  0.35
 16.0  0.80  0.68 0.50  0.0   0.72  0.55
 24.0  1.00  1.00 1.00  0.0   1.00  1.00
 30.0  1.00  1.00 1.00  0.0   1.00  1.00
 39.0  0.98  0.85 0.55  1.0   0.92  0.00
 45.0  0.98  0.85 0.55  1.0   0.90  0.00
```

Rows 24 and 30 are identical: that duplicated row is how the author makes a
"hold at full bloom" plateau. Rows 39 and 45 do the same for the withered
state (only `leaf` drifts 0.92 -> 0.90).

### 4.3 Lifecycle timeline

| Seconds | Phase | What the keys say |
|---|---|---|
| 0-5 | Sprout | stem 0 -> 0.42, bud size 0 -> 0.22, leaves 0 -> 0.25, no bloom, no glow. Soil crumbs hop during roughly 0-5.5 s (delay up to 2.5 s plus a 3 s hop, `flow.py:473`). |
| 5-10 | Growth | stem -> 0.62, size -> 0.42, leaves -> 0.5, **aura starts** (glow 0 -> 0.35) |
| 10-16 | Opening begins | bloom 0 -> 0.5, size -> 0.68, glow -> 0.55, leaves -> 0.72 |
| 16-24 | Full bloom | everything ramps to 1.0 |
| 24-30 | Hold | all channels 1.0, wilt 0. Sway, ring rotation and sparks keep moving because they use raw `t`. |
| 30-39 | Wilt | wilt 0 -> 1, glow -> 0, bloom -> 0.55, size -> 0.85, stem 0.98, leaf 0.92. Falling dots start when `wilt > 0.02`. |
| 39-45 | Withered hold | constant (leaf 0.92 -> 0.90) |

Computed values of `state(t)` (Catmull-Rom plus clip, re-implemented in a
scratch script; not produced by running `flow.py`):

```text
  t     stem  size  bloom wilt  leaf  glow     note
  0     0.000 0.000 0.000 0.000 0.000 0.000    only soil
  3     0.248 0.123 0.000 0.000 0.138 0.000    PNG stage 1
  9     0.585 0.376 0.000 0.000 0.452 0.284    PNG stage 2
  16    0.800 0.680 0.500 0.000 0.720 0.550    PNG stage 3
  26    1.000 1.000 1.000 0.000 1.000 1.000    PNG stage 4
  34.5  0.990 0.925 0.775 0.500 0.961 0.500    mid-wilt
  41    0.979 0.839 0.517 1.000 0.908 0.000    PNG stage 5
  45    0.980 0.850 0.550 1.000 0.900 0.000    end
```

### 4.4 Palettes

All colours are `(R, G, B)` in 0-255. Hex is given for CSS reuse. "Used at"
shows where the palette is sampled. Most palettes are indexed by a gradient
value in [0, 1] through `palette_pick` (section 5.4), so the **order of the
entries matters**: index 0 is where the gradient value is 0.

```text
SOIL_PAL   flow.py:26   soil body (195), soil crumbs (212)
  0  (34, 25, 20)    #221914   darkest brown
  1  (50, 36, 28)    #32241C
  2  (68, 50, 37)    #443225
  3  (88, 65, 47)    #58412F
  4  (108, 82, 60)   #6C523C   lightest brown
  5  (64, 58, 52)    #403A34   grey-brown

STEM_PAL   flow.py:27   stem (222-224)
  0  (62, 38, 120)   #3E2678   deep violet   \
  1  (100, 58, 165)  #643AA5                  >  gradient base -> top (first 3)
  2  (140, 84, 200)  #8C54C8   lighter violet /
  3  (60, 160, 140)  #3CA08C   teal-green: random 12% accent dots

STEM_WILT  flow.py:28   stem when withered (227)
  0  (120, 88, 66)   #785842
  1  (96, 66, 52)    #604234
  2  (140, 108, 76)  #8C6C4C

LEAF_PAL   flow.py:29   leaf body, gradient along u (287)
  0  (60, 150, 140)  #3C968C   teal at the base
  1  (80, 120, 175)  #5078AF
  2  (130, 80, 195)  #8250C3
  3  (175, 105, 215) #AF69D7   violet at the tip

LEAF_WILT  flow.py:30   (291)
  0  (130, 100, 70)  #826446
  1  (104, 76, 58)   #684C3A
  2  (146, 116, 84)  #927454

RIB_PAL    flow.py:31   leaf midrib dots (288)
  0  (210, 180, 255) #D2B4FF
  1  (170, 230, 220) #AAE6DC

WILT_PAL   flow.py:32   petal wilt colour (260) and falling dots (324)
  0  (150, 86, 128)  #965680
  1  (116, 64, 108)  #74406C
  2  (88, 52, 88)    #583458
  3  (126, 94, 104)  #7E5E68
  4  (104, 72, 56)   #684838

RIM_PAL    flow.py:33   petal edge dots (250)
  0  (205, 165, 255) #CDA5FF
  1  (255, 190, 250) #FFBEFA
  2  (170, 140, 255) #AA8CFF

HI_PAL     flow.py:34   4% white-ish highlight specks on petals (252)
  0  (235, 215, 255) #EBD7FF
  1  (255, 225, 250) #FFE1FA

GOLD_PAL   flow.py:35   2% gold flecks near petal bases (254)
  0  (255, 214, 110) #FFD66E
  1  (255, 238, 170) #FFEEAA
  2  (255, 184, 90)  #FFB85A

STAMEN_PAL flow.py:36   gradient along the filament (271)
  0  (255, 240, 255) #FFF0FF   near the base
  1  (255, 215, 235) #FFD7EB
  2  (255, 230, 150) #FFE696
  3  (255, 190, 80)  #FFBE50   anther tip

STAMEN_WILT flow.py:37  (277)
  0  (140, 112, 84)  #8C7054
  1  (120, 96, 72)   #786048
```

Petal-layer palettes (the `pal` field of each `LAYERS` entry, `flow.py:41-47`;
index 0 = petal base, last = petal tip):

```text
Layer 0 (outer, 8 petals)         Layer 1 (6 petals)
  0 (210, 80, 225)  #D250E1         0 (255, 150, 235) #FF96EB
  1 (170, 58, 225)  #AA3AE1         1 (245, 92, 218)  #F55CDA
  2 (128, 50, 218)  #8032DA         2 (205, 62, 218)  #CD3EDA
  3 (96, 44, 205)   #602CCD         3 (150, 52, 222)  #9634DE
  4 (78, 42, 185)   #4E2AB9

Layer 2 (5 petals)                Layer 3 (inner, 4 petals)
  0 (255, 205, 245) #FFCDF5         0 (255, 238, 252) #FFEEFC
  1 (255, 135, 232) #FF87E8         1 (255, 185, 242) #FFB9F2
  2 (238, 84, 216)  #EE54D8         2 (255, 125, 228) #FF7DE4
  3 (195, 62, 226)  #C33EE2
```

Inline colours that are not named constants:

```text
soil pebbles   flow.py:202   (58,52,48) #3A3430  (84,74,64) #544A40
                             (104,90,76) #685A4C  (46,38,32) #2E2620
halo           flow.py:427   (150, 70, 240)  #9646F0   scaled by brightness
rings          flow.py:438   (210, 145, 255) #D291FF   scaled by brightness
ring nodes     flow.py:442   (255, 215, 255) #FFD7FF   scaled by glow
sparks         flow.py:451   (255, 215, 255) #FFD7FF  or  (255, 150, 235) #FF96EB
```

Two things to notice. First, the "fantasy" palette is deliberate: violet stem,
teal-to-violet leaves, pink/violet petals; only the soil and wilt palettes are
naturalistic browns. Second, there is no alpha channel anywhere: "fainter" is
done by multiplying RGB toward black (`halo`, `rings`, `sparks`) and by
showing fewer dots.

### 4.5 `LAYERS` (`flow.py:39-48`)

Four dicts, outermost first. Each describes one ring of identical-ish petals.

| Key | Meaning | How it is used |
|---|---|---|
| `n` | number of petals in the ring | azimuth `th = 2*pi*i/n + off + N(0, 0.10)` (`flow.py:244`) |
| `ac` | opening angle when closed (radians from the flower axis) | `A0 = ac + (ao - ac)*bloom + aj` (`flow.py:389`) |
| `ao` | opening angle when fully open | same |
| `kc` | curvature (total extra turn in radians along the petal) when closed | `K = kc + (ko - kc)*bloom + wilt*(...)` (`flow.py:391`) |
| `ko` | curvature when open | same |
| `L` | petal length multiplier (times 0.92-1.08 jitter per petal) | `Lp = Ls_ * L * ...` (`flow.py:259, 392`) |
| `wc` | half-width as a fraction of petal length when closed | `lat = v * (wc + (wo - wc)*bloom) * Lp * sp` (`flow.py:397`) |
| `wo` | same, open | same |
| `d` | number of dots **per petal** | sizes `area_u`/`sample_v` calls (`flow.py:242, 247`) |
| `off` | angular offset of the ring (radians), so layers interleave | `flow.py:244` |
| `pal` | base-to-tip colour ramp | `palette_pick(rng, Ly["pal"], u + N(0, 0.10))` (`flow.py:248`) |

| Layer | n | ac / ao | kc / ko | L | wc / wo | d | off |
|---|---|---|---|---|---|---|---|
| 0 | 8 | 0.60 / 1.00 | -1.20 / 0.45 | 1.00 | 0.20 / 0.34 | 1150 | 0.00 |
| 1 | 6 | 0.48 / 0.68 | -1.05 / 0.15 | 0.88 | 0.19 / 0.31 | 950 | 0.40 |
| 2 | 5 | 0.36 / 0.46 | -0.85 / -0.05 | 0.72 | 0.17 / 0.27 | 760 | 0.20 |
| 3 | 4 | 0.22 / 0.32 | -0.50 / -0.10 | 0.46 | 0.14 / 0.22 | 480 | 0.55 |

The petal's tangent angle (from the flower axis) at the tip is `A0 + K`.
Computed from the table (before jitter): layer 0 goes from -0.60 rad closed
(tips curl past vertical toward the centre, a cup/bud) to +1.45 rad open (tips
flare out toward horizontal); layer 3 only goes from -0.28 to +0.22, so the
inner petals stay upright. The outer layers do most of the opening.

### 4.6 `LEAF_DEFS` (`flow.py:49-54`)

Four tuples `(s, m, lfac, a0, c)`, unpacked by index in `render`
(`flow.py:354-360`):

| Field | Meaning | Used at |
|---|---|---|
| `s` | where on the stem the leaf attaches, as a Bezier parameter 0..1 | `bez(P, sa)` (`flow.py:354-355`) |
| `m` | side: +1 grows right, -1 grows left (a horizontal mirror) | `flow.py:357, 367` |
| `lfac` | length factor | `LL = 0.19*H*lfac*leaf*...` (`flow.py:362`) |
| `a0` | base angle **above horizontal**, radians | `flow.py:359` |
| `c` | total curvature (negative = droops downward) | `flow.py:360` |

```text
 # s     m   lfac a0    c
 (0.10, +1, 1.00, 0.55, -0.80)   low right, longest, fairly flat
 (0.16, -1, 0.90, 0.50, -0.85)   low left
 (0.40, +1, 0.70, 0.95, -0.70)   high right, shorter, steeper
 (0.33, -1, 0.62, 0.90, -0.65)   high left
```

### 4.7 `OFF` and `D2` (`flow.py:56-59`)

```python
_OFF = sorted(((dx, dy) for dy in range(-3, 4) for dx in range(-3, 4) if dx*dx + dy*dy <= 9),
              key=lambda p: (p[0]**2 + p[1]**2, p))
OFF = np.array(_OFF, np.int32)      # (29, 2) pixel offsets
D2  = (OFF ** 2).sum(1)             # squared distance of each offset
```

All 29 integer offsets within radius 3, sorted by squared distance (ties by
`(dx, dy)`). Because of the sort, **a prefix of `OFF` is a disc**:

```text
squared distance   0   1   2   4   5   8   9
offsets at that d  1   4   4   4   8   4   4      (computed; no d=3,6,7 exists)
cumulative         1   5   9  13  21  25  29
```

So `OFF[:13]` is exactly the radius-2 disc (the default `nmax=13`) and
`OFF[:29]` the radius-3 disc. The stamps this yields for the radii the code
uses (`D2 <= rad^2 + 0.01`):

```text
rad 1.0 ( 5 px)   rad 1.5 ( 9 px)   rad 2.0 (13 px)   rad 3.0 (29 px)
   .#.               ###               ..#..             ...#...
   ###               ###               .###.             .#####.
   .#.               ###               #####             .#####.
                                       .###.             #######
                                       ..#..             .#####.
                                                         .#####.
                                                         ...#...
```

---

## 5. Helper functions and the maths

### 5.1 `smoothstep(x, a, b)` (`flow.py:62-64`)

```python
t = clip((x - a) / (b - a), 0, 1)
return t*t*(3 - 2*t)            # 0 below a, 1 above b, S-curve between
```

Used once, to fade the stamens in as the flower opens:
`ss = smoothstep(bloom, 0.30, 0.85)` (`flow.py:406`). It is a general "turn
this master channel into a sub-window" tool, worth borrowing.

### 5.2 `sinc(x)` (`flow.py:67-68`)

```python
return np.sinc(x / np.pi)       # numpy's sinc is sin(pi*y)/(pi*y), so this is sin(x)/x, with sinc(0) = 1
```

It exists to make constant-curvature arcs closed-form and safe at zero
curvature; the derivation is in section 7.4.

### 5.3 `profile(u)` (`flow.py:71-72`)

```python
profile(u) = sin(pi * clip(u,0,1)**0.75) ** 0.85
```

A width envelope along a petal or leaf, 0 at both ends, peaking at 1.0 where
`u**0.75 = 0.5`, i.e. `u = 0.5**(1/0.75) ~ 0.397` (computed). Shape (computed):

```text
u        0    0.05  0.1   0.2   0.3   0.4   0.5   0.6   0.7   0.8   0.9   1.0
profile  0    0.39  0.58  0.83  0.96  1.00  0.96  0.86  0.71  0.52  0.29  0
```

A fast rise from a pinched base, widest at about 40% of the length, then a
slower taper to a point: a teardrop/ovate outline. It is used three ways:

1. as the acceptance probability in `area_u` (point density follows width),
2. as the stored per-dot width multiplier `h["sp"] = profile(h["u"])` for petals (`flow.py:264`),
3. directly in the leaf lateral offset (`flow.py:366`).

### 5.4 `palette_pick(rng, pal, g, spread=0.55, jitter=0.07)` (`flow.py:75-80`)

Noisy gradient lookup that deliberately does **not** blend colours:

```python
x   = clip(g, 0, 1) * (len(pal) - 1) + normal(0, spread, g.shape)   # fractional palette index plus noise
idx = clip(rint(x), 0, len(pal) - 1)                                # snap to a whole palette entry
col = pal[idx] * (1 + normal(0, jitter, (n, 1)))                    # per-dot brightness wobble, same for R,G,B
```

So each dot is a *pure palette colour*, brightness-jittered by about 7%; the
gradient appears as a stippled mix of neighbouring entries whose boundary is
blurred by `spread`. Results are `float32` and may exceed 255; clipping happens
later (`flow.py:133`). `spread=1.0` (soil) gives a very noisy mix, `0.35`
(stamens) a tight one. This is the core of the pointillist look.

### 5.5 `area_u(rng, n)` (`flow.py:83-88`): rejection sampling

```python
out = empty
while out.size < n:
    u = random(3n)                          # candidate positions along the petal, uniform in [0,1]
    keep = random(3n) < profile(u)          # accept with probability = local width
    out = concat(out, u[keep])
return out[:n]
```

Result: `u` is distributed with density proportional to `profile(u)`, so dots
are spread **uniformly per unit area** (wide parts get more dots than the
pinched base and tip). The mean acceptance rate is the integral of `profile`
over [0, 1], about 0.687 (computed), so a 3n batch yields about 2.06n
accepted points and the loop almost always finishes in one round. Truncating
to the first `n` is unbiased because candidates are i.i.d.

### 5.6 `sample_v(rng, n, rim=0.14)` (`flow.py:91-95`): rim bias

```python
v = uniform(-1, 1, n)                         # across the petal: -1 left edge ... +1 right edge
r = random(n) < rim                           # 14% of dots become "edge dots"
v[r] = sign(v[r]) * uniform(0.88, 1.0, ...)   # moved onto the outer 12% of their own side
```

Edge dots give each petal a denser, slightly brighter outline. `build_leaves`
passes `rim=0.10` (`flow.py:284`); the stem does its own version (18%, edge
band 0.85-1.0, `flow.py:220-221`).

### 5.7 `permute(d, rng)` and `cat(parts)` (`flow.py:98-105`)

`permute` takes a dict of equal-length arrays, draws one `rng.permutation(n)`
and applies it to every array, so rows stay aligned. `cat` concatenates a list
of such dicts key by key. After `permute`, **any prefix `arr[:k]` of any
field is a uniform random subset of all dots**. The whole growth system
depends on this (section 10).

### 5.8 `splat(canvas, x, y, col, rad, nmax=13)` (`flow.py:108-117`)

The only rasteriser. It stamps a small disc of one colour at every particle,
all at once:

```python
xi = rint(x); yi = rint(y)                          # nearest pixel, (n,)
off = OFF[:nmax]                                    # (nmax,2) candidate offsets (a disc by construction)
xs = xi[:,None] + off[None,:,0]                     # (n,nmax) target columns
ys = yi[:,None] + off[None,:,1]                     # (n,nmax) target rows
m  = (D2[None,:nmax] <= (rad*rad)[:,None] + 0.01)   # offset inside THIS dot's radius?
     & in_bounds(xs, ys)
rows = nonzero(m)[0]                                # which particle each True belongs to
canvas[ys[m], xs[m]] = col[rows]                    # one fancy-indexed write for the whole frame
```

* The `+ 0.01` is a small tolerance (our reading): an offset whose squared
  distance equals `rad**2` exactly (1, 4, 9) is kept, and for radius 1.5
  (`2.25 + 0.01`) it keeps squared distances 0, 1 and 2 but not 4.
* Because `OFF` is sorted by distance, `nmax` is a cap on the biggest disc:
  default 13 means radius 2. Radius-3 callers (`pebbles`, ring `nodes`) must
  pass `nmax=29` (`flow.py:204, 470`).
* Painting is **overwrite, not blend**. Two overlapping dots: the later one
  in the flattened `(particle, offset)` order wins. That is why callers sort
  particles back-to-front first. This relies on NumPy writing repeated
  indices in order, i.e. last-wins; in practice it behaves that way, but
  NumPy's indexing docs do not formally guarantee the order for repeated
  advanced indices. Worth knowing before copying the idea.
* Memory is `n * nmax` temporaries per call (a few hundred thousand cells for
  ~30k dots): cheap.

### 5.9 `Batch` (`flow.py:120-134`)

```python
add(x, y, col, rad, z):  if len(x): self.p.append((x, y, col, rad, z))
draw(canvas):
    x, y, col, rad, z = concatenate each of the 5 fields across all added chunks
    o = argsort(z, kind="stable")                  # ascending z: far first
    splat(canvas, x[o], y[o], clip(col[o],0,255).astype(uint8), rad[o])
```

A deferred draw list. Each subsystem adds a vectorised chunk with a constant
or per-dot `z`; `draw` merges everything and does a single global sort, which
is a **painter's algorithm** with the nearest dots painted last. `stable`
keeps equal-z dots in insertion order, so output is deterministic.

The z values in use:

| Dots | z | Line | Effect |
|---|---|---|---|
| halo | -2000 | 428 | behind everything |
| rings | -1500 | 439 | behind stem/leaves/petals |
| stem | -500 | 349 | |
| leaves | -450 | 371 | in front of the stem |
| petals | `zp`, the projected depth | 404 | sorted among themselves; magnitude about the head size `Ls_` |
| stamens | `zp + 3.0` | 417 | tiny bias so they win ties against petals at the same depth |
| falling dots | +500 | 465 | in front of the flower |
| sparks | +2000 | 453 | in front of everything |

Not in the sort: the 6 ring **nodes** go into a separate `Batch` (`nodes`) and
are splatted after `B.draw` with `nmax=29` (`flow.py:468-470`), and the soil
**crumbs** are splatted last of all (`flow.py:472-475`), so both end up on top.
A latent scale dependency (our inference): `zp` scales with `H` while the
constants -500/-450/+500 do not, so the petal-vs-stem/falling ordering holds
at the sizes the code runs at but is not scale-invariant.

### 5.10 `state(t)`: Catmull-Rom through the keyframes (`flow.py:137-148`)

```python
t  = clamp(t, 0, T_END)
i  = clamp(searchsorted(KEYS[:,0], t, side="right") - 1, 0, len(KEYS) - 2)   # segment index
u  = (t - ts[i]) / (ts[i+1] - ts[i])                                          # 0..1 inside the segment
p0 = KEYS[max(i-1, 0), 1:]          # previous key  (first key repeated at the start)
p1 = KEYS[i, 1:]                    # segment start
p2 = KEYS[i+1, 1:]                  # segment end
p3 = KEYS[min(i+2, last), 1:]       # next key      (last key repeated at the end)

v = 0.5 * ( 2*p1
          + (p2 - p0) * u
          + (2*p0 - 5*p1 + 4*p2 - p3) * u**2
          + (3*p1 - p0 - 3*p2 + p3)   * u**3 )
return clip(v, 0, 1)
```

* It is the standard uniform Catmull-Rom spline (tension 0.5). It passes
  through every key: `v(u=0) = p1`, `v(u=1) = p2`, with slope
  `(p2 - p0)/2` at the start and `(p3 - p1)/2` at the end, per unit of `u`.
* It works on all six channels at once (numpy vectors), so one call yields
  the whole `(stem, size, bloom, wilt, leaf, glow)` state.
* `searchsorted(..., "right") - 1` finds the segment; at `t == T_END` it
  would return the last index, so the `len(KEYS) - 2` clamp keeps `i` at the
  last real segment and gives `u = 1`.
* Two properties worth knowing (derived from the formula, computed over the
  whole timeline): the spline is parameterised per **segment**, not per
  second, so with key gaps of 5, 5, 6, 8, 6, 9, 6 s the slope in time jumps at
  keys; and it **overshoots**. The raw channels range from about -0.07 to
  +1.09 before the final `np.clip` (for example `wilt` is about -0.06 at
  27 s, `bloom` about 1.06 around 27 s). The clip turns those overshoots into
  flat plateaus at exactly 0 or 1, which is what makes the "hold" rows work.

### 5.11 `bez(P, s)`: cubic Bezier and its derivative (`flow.py:151-158`)

```python
q = 1 - s
x  = q^3*P0x + 3*q^2*s*P1x + 3*q*s^2*P2x + s^3*P3x          # position
y  = (same with the y components)
dx = 3*q^2*(P1x-P0x) + 6*q*s*(P2x-P1x) + 3*s^2*(P3x-P2x)    # tangent = d(position)/ds
dy = (same with y)
return x, y, dx, dy
```

`s` may be a scalar or a whole array, so one call evaluates every stem dot or
every leaf attachment point. The derivative is used to offset stem dots along
the **normal** `(-dy, dx)/|d|` (`flow.py:344-348`).

### 5.12 `mixcol(live, wilt, w)` (`flow.py:161-162`)

```python
return live + (wilt - live) * w[:, None]       # per-dot linear blend, w in [0,1]
```

Each dot carries both a live colour and a wilt colour (chosen at build time);
`w` is how far that dot has wilted. `w` is deliberately staggered across dots
(see the `wi = ...` lines in 7.2-7.4) so the browning spreads rather than
flipping everywhere at once.

---

## 6. `Plant`: constructing the particles

### 6.1 `__init__` (`flow.py:165-178`)

```python
self.rng = default_rng(SEED)
self.cx  = W/2        # horizontal centre line
self.y0  = H*0.80     # soil baseline (screen y, downward)
self.Ls  = H*0.38     # stem length at stem == 1
self.Lf  = H*0.235    # flower scale at size == 1
build_soil(); build_stem(); build_head(); build_stamens(); build_leaves(); build_fx()
```

Everything is proportional to `H`, so the flower is the same composition at
any resolution. **Not** proportional: the dot radii (always 1-3 px, section
4.7), the ripple wavelengths in `surface` (`sin(x*0.045)`, `sin(x*0.13)`) and
the clump pattern. A 640 px GIF therefore has relatively chunkier dots than the
1000 px PNGs. The build order matters because all systems share one RNG
stream; reorder or add a draw and every later system changes.

### 6.2 `surface(x)` (`flow.py:180-183`)

```text
y_surface(x) = y0
             - 0.022*H * exp(-((x - cx) / (0.2*W))^2)     # Gaussian mound under the plant
             - 0.003*H * sin(0.045*x)                     # two gentle ripples
             - 0.002*H * sin(0.13*x + 1.3)
```

Screen y grows downward, so subtracting makes the soil higher. This function
is reused by soil, pebbles, crumbs and the falling-petal landing spots, so
everything rests on the same ground line.

### 6.3 `build_soil` (`flow.py:185-214`)

1. 26,000 soil dots (`flow.py:187-198`):
   * `x ~ U(0, W)`; depth `d = random**1.5 * 0.14*H` (the 1.5 exponent packs
     dots near the surface); `y = surface(x) + d`.
   * `edge = clip(min(x, W-x) / (0.2*W), 0, 1)**0.8` darkens the left and
     right 20% of the image (a vignette).
   * `clump = 0.5 + 0.5*sin(0.07x + 0.05y) * sin(0.11y - 0.03x)` is a cheap
     low-frequency lumpy pattern.
   * `bright = (1-depth)**0.8 * edge * (0.55 + 0.35*clump + 0.35*random)`:
     brightest near the surface, centre, and in lumps.
   * colour: `palette_pick(SOIL_PAL, random, spread=1.0) * bright`.
   * radius: `choice([1.0, 1.5, 2.0], p=[0.4, 0.4, 0.2])`.
   * splatted onto `self.base = zeros((H, W, 3), uint8)`. This is the static
     background; each frame starts from `base.copy()` (`flow.py:330`).
2. 170 pebbles (`flow.py:199-204`): lighter grey-brown dots of radius 2 or 3
   (3 needs `nmax=29`), scattered up to `0.1*H` below the surface (biased
   toward the top, `random**1.3`), edge-dimmed, also baked into `base`.
3. 520 crumbs (`flow.py:205-214`), kept as arrays in `self.cr`:
   * `x = cx + N(0, 0.03*H)` (clustered around the stem), resting at
     `surface(x) - random*0.006*H`;
   * `amp = 0.05*H * random**2.2` (mostly small hops, a few big ones);
   * `delay ~ U(0, 2.5)`;
   * colour from the *light half* of `SOIL_PAL` (gradient 0.3-1.0) times 0.8, so
     they read as lighter clods against the dark soil.
   Animated in `render` (section 7.8).

### 6.4 `build_stem` (`flow.py:216-228`)

3,600 dots with `s ~ U(0,1)` along the curve and `lat ~ U(-1,1)` across it
(18% pushed to the edge band 0.85-1.0). Colour is
`palette_pick(STEM_PAL[:3], s*0.8 + random*0.2)`, so the stem darkens toward the
base and lightens toward the head; 12% of dots become the teal accent
`STEM_PAL[3]` with 8% brightness noise. `wilt` colours come from `STEM_WILT`.
`rn` is a per-dot random number used to stagger wilting. Then `permute`.

### 6.5 `ctrl(L, wilt, sway)` (`flow.py:230-236`): the stem curve

```python
P0 = (cx,                                              y0 + 4)           # 4 px below the soil baseline
P1 = (cx - 0.06*L*(1-wilt) + 0.02*L*wilt,              y0 - 0.33*L)
P2 = (cx + 0.05*L*(1-wilt) + 0.08*L*wilt + 0.5*sway,   y0 - L*(0.74 + 0.30*wilt))
P3 = (cx + sway + 0.32*L*wilt,                         y0 - L*(1 - 0.15*wilt))
```

Alive (`wilt = 0`): a slight S-curve, with P1 left and P2 right of centre, ending at
height `L` with `sway` of horizontal wobble. Wilted (`wilt = 1`): P2 rises to
1.04 L (above the endpoint), and P3 slides right by 0.32 L and drops to 0.85 L.
That arch-and-droop is the whole "the flower bows over" effect, and since the
head is anchored at `P3` it carries the head with it. The stem starts inside
the mound (below `y0`), and since the plant is painted on top of `base` with no
occlusion by soil, only the crumbs (drawn last) partly cover its foot.

### 6.6 `build_head` (`flow.py:238-265`): all 23 petals

For every petal of every layer (`flow.py:241-262`):

```python
th = 2*pi*i/n + off + N(0, 0.10)       # azimuth around the flower axis (+ jitter)
aj = N(0, 0.06)                        # opening-angle jitter
lj = U(0.92, 1.08)                     # length jitter
pj = random();  wj = U(-0.5, 0.5)      # per-petal wilt "personality"
u  = area_u(rng, d);  v = sample_v(rng, d)
col = palette_pick(Ly.pal, u + N(0, 0.10))           # base -> tip ramp
rim_dots  : |v| > 0.86 and random < 0.55  -> RIM_PAL  # edge sparkle
highlights: 4% of dots                    -> HI_PAL
gold flecks: 2% of dots with u < 0.55     -> GOLD_PAL # only near the base half
wilt colour = palette_pick(WILT_PAL, 0.4*u + 0.6*random, spread=0.7)
```

Notable design point: each dot stores **its own copy of its petal's
parameters** (`th, aj, pj, wj, ac, ao, kc, ko, L, wc, wo`, broadcast with
`np.full`, `flow.py:255-262`). That wastes memory but lets the render step treat
all 20,620 dots as one flat array with no per-petal loop. After `cat`,
`h["sp"] = profile(h["u"])` is precomputed (`flow.py:264`) and the whole dict
is `permute`d (`flow.py:265`). `rn` (per-dot random) and `rad`
(`choice([1.0, 1.5, 2.0], p=[0.30, 0.45, 0.25])`) are stored too.

### 6.7 `build_stamens` (`flow.py:267-278`)

60 filaments (`nf`), 700 dots. Each dot picks a filament `fid`; each filament
has a random azimuth `th` in [0, 2pi), tilt `beta` in [0.2, 0.85] rad, and
length factor `ell` in [0.30, 0.55]; every dot looks these up by `fid`.
`t = 1 - random**1.6` is the position along the filament, with density rising
toward the tip (exponent `1/1.6 - 1 = -0.375` on `(1-t)`, computed). Colour
comes from `STAMEN_PAL` indexed by `t` (cream base to orange tip, `spread=0.35`).
Dots with `t > 0.88` get radius 2.0 (the anther blobs), others 1.0 or 1.5.

### 6.8 `build_leaves` (`flow.py:280-294`)

For each of the four `LEAF_DEFS` entries, 900 dots: `u = area_u`,
`v = sample_v(rim=0.10)`; 9% of dots become the **midrib** (`v ~ N(0, 0.03)`,
colour from `RIB_PAL`). Colour is `LEAF_PAL` indexed by `u + N(0, 0.1)`, so
leaves go teal at the base to violet at the tip. A `lid` array records which leaf
each dot belongs to. Everything is merged with `cat` and `permute`d.

### 6.9 `build_fx` (`flow.py:296-325`)

* **Halo** (1,800): angle uniform, radius `r = min(|N(0, 0.55)|, 1.6)` (a
  clipped half-normal, dense at the centre), base brightness
  `b = (1 - r/1.6)**1.5 * 0.55`, and a twinkle phase `fl`. `permute`d.
* **Rings** (1,720): seven circles. Circle 0 is the big ring (`cf=0`, `rho=1`,
  700 dots). Circles 1-6 are six small rings (`cf=0.5`, `rho=0.5`, 170 dots
  each, centre-index `cj = 0..5`). `permute`d.
* **Sparks** (280): angle, radial fraction, phase, speed 0.6-1.4, radius
  (1 or 2, 70/30), hue selector. Not permuted (all are always drawn).
* **Falling dots** (260): a start-time threshold `r0`, a start scatter
  `(ox, oy)`, a landing point on the soil `(xl, yl)` with `xl ~ N(cx, 0.12*H)`
  and `yl = surface(xl) - random*0.012*H`, a flutter phase, a `WILT_PAL`
  colour and radius 1.5 or 2. Not permuted (selection is by a mask).

---

## 7. `render(t)`: one frame, step by step (`flow.py:327-476`)

### 7.1 Prologue (`flow.py:327-337`)

```python
stem, size, bloom, wilt, leaf, glow = state(t)
canvas = self.base.copy()                           # soil only
B, nodes = Batch(), Batch()
L    = Ls * stem
sway = 0.012*H * sin(0.9*t) * stem * (1 - 0.6*wilt)   # wind: horizontal wobble of the stem tip
P    = ctrl(L, wilt, sway);   hx, hy = P[3]           # head anchor = stem tip
```

Note `sway` uses the raw `t`, not the clamped state, so it keeps swinging
after `T_END` (and wilting dampens it by 60%).

### 7.2 Stem (`flow.py:339-349`)

```python
nv  = int(3600 * clip(stem, 0.08, 1));  s = S.s[:nv]        # prefix => random subset, count ~ length
x, y, dx, dy = bez(P, s);  nn = hypot(dx, dy) + 1e-6        # position, tangent, tangent length
wst = 0.0085*H * (1 - 0.3*s) * (1 - 0.25*wilt) * clip(0.4 + 1.2*stem, 0.4, 1)   # half-thickness
lat = S.lat[:nv] * wst
pos = (x - dy/nn*lat,  y + dx/nn*lat)                       # nudge each dot sideways along the normal
wi  = clip(wilt * (0.75 + 0.5*s) * (0.7 + 0.5*rn), 0, 1)    # top and noisy dots brown first
B.add(pos, mixcol(live, wilt_col, wi), rad, z=-500)
```

The stem thins by 30% toward the head, by 25% when wilted, and starts thin
while sprouting. Because both the dot count and the length scale with `stem`,
the **dots per pixel of stem stay roughly constant while it grows**.

### 7.3 Leaves (`flow.py:351-371`)

Drawn only if `leaf > 0.02 and stem > 0.05`. Shown count is
`int(3600 * clip(leaf, 0.15, 1))`. For dot j on leaf `lid`:

```python
ax, ay = bez(P, sa)[:2]                    # where each leaf is attached on the CURRENT stem curve
a0 = a0_def + (1 - leaf)*0.8 - 0.6*wilt    # young leaves point more upright; wilting droops them
c  = c_def  - 0.5*wilt                     # more downward curl when wilted
LL = 0.19*H * lfac * leaf * (1 - 0.25*wilt)
am = a0 + c*u*0.5                          # mid-angle of the arc up to u
al = a0 + c*u                              # tangent angle at u
sc = sinc(c*u*0.5)
lat = v * 0.27 * LL * profile(u)           # half-width up to 0.27 * LL at the widest
X    = ax + LL*u*m*cos(am)*sc - lat*sin(al)
Yup  =      LL*u*sin(am)*sc   + lat*m*cos(al)
draw at (X, ay - Yup)                       # screen y is downward
```

It is the same constant-curvature-arc idea as the petals (section 7.4) but
angles are measured from the **horizontal** here (`cos` -> x, `sin` -> up),
and `m = +/-1` mirrors left/right. The last two lines add the width offset
along the arc's normal `(-sin(al), m*cos(al))`. Wilt colour weight is
`wi = clip(wilt*(0.9 + 0.5*u + 0.3*rn) - 0.1, 0, 1)` so tips go brown first.
Note the count scales with `leaf` but area scales with `leaf^2`, so small
leaves are drawn more densely than big ones (arithmetic, not a measured look).
z = -450.

### 7.4 The flower head (`flow.py:373-404`)

Drawn only if `stem > 0.01 and size > 0.05`.

**Head orientation** (`flow.py:374-377`):

```python
phi = wilt*2.75 + 0.035*sin(0.9*t + 1.0)*(1 - wilt)    # in-plane roll: ~0 alive (+/-2 deg wobble),
                                                       # 2.75 rad ~ 157.6 deg when wilted: head flips over
tau = 0.20 + 0.36*bloom - 0.40*wilt                    # pitch toward the viewer: 0.20 rad closed,
                                                       # 0.56 rad open, ~0 when wilted
Ls_ = Lf * size                                        # head scale
```

**Projection** (`flow.py:379-382`), flower-local `(xl, yl, zl)` (our reading of
the axes: right, up along the flower axis, toward the viewer; bigger `zp` is
painted later, i.e. nearer):

```python
yp = yl*cos(tau) - zl*sin(tau)          # pitch about the x axis
zp = yl*sin(tau) + zl*cos(tau)          # depth after pitch  (bigger = nearer; used as the sort key)
X  = hx + xl*cos(phi) + yp*sin(phi)     # then roll in the screen plane about the stem tip
Y  = hy - (-xl*sin(phi) + yp*cos(phi))  # (minus because screen y points down)
return X, Y, zp, yp
```

So the head is a rigid 3D object (pitch tau, roll phi) orthographically
projected, with `zp` kept only for sorting and shading.

**How many dots** (`flow.py:384-387`): `vis = clip(size**2 * 1.15, 0.2, 1.0)` and
`nv = int(20620 * vis)`; the dot count follows the *area* (`size^2`), with a
20% floor so the bud is never empty.

**Petal geometry** (`flow.py:389-398`), per dot, all vectorised. This is the
core of the program:

```python
# 1. opening angle (from the flower axis) and curvature, interpolated by bloom, then wilt-modified
A0 = ac + (ao - ac)*bloom + aj
A0 = A0*(1 - 0.55*wilt) + wilt*wj*0.3
K  = kc + (ko - kc)*bloom + wilt*(0.6 + 0.6*pj)
Lp = Ls_ * L * (1 - 0.28*wilt*pj)                # petal length (shrinks when wilted)

# 2. constant-curvature arc, closed form
am = A0 + K*u*0.5                                # mid-angle of the arc from 0 to u
sc = sinc(K*u*0.5)                               # sin(x)/x, equals 1 when K = 0
rr = Lp * u * sin(am) * sc                       # radial distance from the flower axis
hh = Lp * u * cos(am) * sc                       # height along the flower axis

# 3. width across the petal
lat = v * (wc + (wo - wc)*bloom) * Lp * sp       # sp = profile(u): pinched base, widest ~40%, pointed tip
rr  = rr + 0.025*Ls_ - 0.5*lat*lat/(Lp + 1.0)    # base ring offset, minus a small cup term at the edges

# 4. rotate (rr, lat) about the axis by the petal's azimuth, then project
x_local = cos(th)*rr - sin(th)*lat
z_local = sin(th)*rr + cos(th)*lat
X, Y, zp, yp = project(x_local, hh, z_local)

# 5. depth/height shading, then wilt tint
shade = clip(0.72 + 0.28*clip(zp/Ls_*0.5 + 0.5, 0, 1) + 0.12*(hh/Ls_), 0.5, 1.2)
wi    = clip(wilt*(1.0 + 0.7*u + 0.4*rn) - 0.2, 0, 1)
col   = mixcol(live, wilt_col, wi) * shade
B.add(X, Y, col, rad, zp)
```

Why the `sinc` form is right. Treat the petal centreline as an arc whose
tangent angle from the axis is `alpha(u) = A0 + K*u`, with length `Lp`. Then

```text
radial(u) = Lp * integral_0^u sin(A0 + K*w) dw
          = Lp * (cos(A0) - cos(A0 + K*u)) / K
          = Lp * u * sin(A0 + K*u/2) * [ sin(K*u/2) / (K*u/2) ]
height(u) = Lp * integral_0^u cos(A0 + K*w) dw
          = Lp * u * cos(A0 + K*u/2) * [ sin(K*u/2) / (K*u/2) ]
```

which are exactly `rr` and `hh` above with `am = A0 + K*u/2` and the bracket
equal to `sinc(K*u/2)`. The author gets an exact arc with no integration loop
and no division by zero at `K = 0` (`np.sinc(0) = 1`). Reading the sign
conventions: `K < 0` bends the tip back toward (and past) the axis (a closed
bud); `K > 0` flares it outward.

Wilt acts on the same parameters. `A0` shrinks by 55% (petals start more upright), `K` gains
0.6-1.2 rad (tips curl outward, scaled by the petal's `pj`), lengths shrink by
up to 28%, and the colour weight `wi` is biggest at the tips (`0.7*u`). Combined
with `phi = 2.75` the whole head hangs, faded.

The shading line (`flow.py:401`) brightens dots that are nearer the viewer
(`zp`) and higher on the flower (`hh`), within [0.5, 1.2]. Values above 1.0
push already-bright palette entries past 255, which the later clip turns into
near-white highlights.

### 7.5 Stamens (`flow.py:406-417`)

```python
ss   = smoothstep(bloom, 0.30, 0.85)            # fade in while the flower opens
nv2  = int(700 * clip(size**2, 0.25, 1))
ell  = Ls_ * ss * ell_i                         # filament length grows with ss
beta = beta_i*(0.6 + 0.4*bloom) + wilt*0.3      # filaments splay outward as it opens
r    = ell*t*sin(beta) + 0.02*Ls_               # radial distance
yl   = 0.05*Ls_ + ell*t*cos(beta)               # height
project(cos(th)*r, yl, sin(th)*r)  ->  z = zp + 3.0
colour = mixcol(live, wilt_col, wilt)           # uniform wilt weight, no stagger
```

Straight tilted line segments (not arcs), drawn in front of petals at equal
depth. At the withered end state `bloom = 0.55` so `ss` is about 0.43
(computed: `t = 0.25/0.55`, then `t*t*(3 - 2*t)`) and the stamens are still
partly visible.

### 7.6 The aura: halo, rings, nodes, sparks (`flow.py:419-453`)

Inside `if glow > 0.02`. All of it is centred on the flower:

```python
axis = (sin(phi), -cos(phi))                       # flower axis in screen space
ccx, ccy = hx + axis.x*0.5*Ls_, hy + axis.y*0.5*Ls_    # aura centre: half a head up the axis
```

* **Halo** (`flow.py:422-428`): `nh = int(1800*glow)` dots at radius
  `r * Ls_ * 1.1` around the centre, colour `(150,70,240) * br` with
  `br = b * glow * (0.85 + 0.3*sin(1.3*t + fl*6.28))`: each dot twinkles with its own
  phase. Dense and bright in the middle, fading to black at `r = 1.6`.
  Radius 1, z = -2000.
* **Rings** (`flow.py:430-439`): `Rs = Ls_*1.25`. A dot's position is
  `centre + Rs*(cf*(cos cang, sin cang) + rho*(cos a, sin a))`, with
  `cang = 2*pi*cj/6 + 0.15*t` (the small rings' centres orbit) and
  `a = a0 + 0.05*t` (dots creep around each ring). The big ring has `cf = 0`.
  Each small ring has radius `0.5*Rs` and its centre sits `0.5*Rs` out, so it
  passes through the aura centre and touches the big ring from inside: a
  six-lobed rosette. Brightness
  `bb = (0.40 + 0.60*glow) * (0.65 + 0.35*sin(2*t + fl*20))`. z = -1500.
* **Nodes** (`flow.py:440-443`): 6 dots of radius 3 at `Rs*(cos ja, sin ja)` with
  `ja = 2*pi*k/6 + 0.15*t` (the same angles as the small-ring centres, so each
  sits at a tangent point on the big ring). Splatted after the main batch.
* **Sparks** (`flow.py:445-453`):

  ```python
  life = (0.10*t*sp + ph) % 1.0                         # each spark loops 0 -> 1 with its own speed/phase
  rho  = (0.25 + 1.15*rho0) * Ls_ * (0.6 + 0.6*life)    # drifts outward as it ages
  y    = ccy + sin(a)*rho - life*0.25*Ls_               # and rises
  fade = sin(pi*life)**0.8 * glow                       # 0 at birth and at death: invisible respawn
  ```

  z = +2000, radius 1 or 2, colour A or B by `hue`.

### 7.7 Falling petals (`flow.py:455-465`)

Inside `if wilt > 0.02`:

```python
fp = clip((wilt*1.05 - r0*0.7) / 0.35, 0, 1)      # per-dot progress; r0 staggers the start times
mk = fp > 0                                       # only dots that have begun falling
sx = hx + ox*0.18*Ls_;   sy = hy + oy*0.18*Ls_ + 0.25*Ls_    # start: scattered near the CURRENT head
x  = sx + (xl - sx)*f + sin(f*6.28 + ph)*0.03*H*(1 - f)      # lerp to landing x + flutter that dies out
y  = sy + (yl - sy)*f*f                                      # quadratic ease-in: accelerates like gravity
add(x, y, colour, rad, z=+500)
```

The constants are tuned so that at `wilt = 1` the latest dot (`r0 = 1`) has
`fp = (1.05 - 0.70)/0.35 = 1`: every dot has landed by the end of the wilt
(computed check). Because `sx, sy` are recomputed from the current head
position every frame, a dot that has just started falling rides the drooping
head and then peels away. The head's own petal dots are not removed; these
260 dots are a separate effect.

### 7.8 Compositing (`flow.py:467-476`)

```python
B.draw(canvas)                                                  # z-sorted splat of everything above
if nodes.p: splat(canvas, nodes..., nmax=29)                    # six big dots on top
e  = clip((t - delay)/3.0, 0, 1)                                # per-crumb progress, 3 s each
sy = crumb_y - amp * sin(pi * e)                                # a single hop: up, down, rest
splat(canvas, crumb_x, sy, crumb_colour, crumb_rad)             # soil crumbs, last of all
return canvas
```

The crumb hop (`delay` in [0, 2.5] s, 3 s long) is the "soil is disturbed as the
shoot emerges" moment. After 5.5 s every `e` is 1, `sin(pi) ~ 0`, and the
crumbs sit still as small light clods around the stem base for the rest of the
animation.

`render` mutates no state; it only reads the precomputed arrays. Any `t` can
be rendered at any time, in any order, which is what lets the exporters and the
`S` key jump straight to a time.

---

## 8. Exporters and `App`

### 8.1 `save_png` (`flow.py:479-492`)

`Plant(1000, 1000)`; renders `[3, 9, 16, 26, 41]` s; saves each as
`flower_{i+1}.png`; resizes each to 500x500 with `Image.LANCZOS`, pastes them
left to right into a 2500x500 strip, saves `flower_stages.png`, prints a
message. (Each frame is converted with `Image.fromarray` twice; harmless.)

### 8.2 `save_gif` (`flow.py:495-501`)

`Plant(640, 640)`; frames for `i in range(int(45*12) + 1)` at `t = i/12`, each
converted with `.convert("P", palette=Image.ADAPTIVE)` (a fresh 256-colour
palette per frame); saved with `duration=int(1000/12) = 83` ms,
`loop=0` (forever), `optimize=False`. All 541 frames are held in memory first:
541 x 640 x 640 bytes of palette indices is about 222 MB (computed), plus
render time. The per-frame adaptive palettes may flicker slightly in colour
(our expectation; we did not render it).

### 8.3 `App` (`flow.py:504-550`)

* Lazy imports `tkinter` and `ImageTk` (`flow.py:506-507`).
* Window: a square sized from the screen (`flow.py:512-515`), black background,
  centred (`+{(sw-W)//2}+{max(0,(sh-H)//2-20)}`), a "preparing..." label while
  `Plant(W, H)` builds (`flow.py:518-521`).
* Renders frame 0 into an `ImageTk.PhotoImage`, places it on a `Canvas`, and
  from then on only calls `self.photo.paste(...)`, so there is a single image
  object and no flicker from re-creating canvas items (`flow.py:522-524, 546`).
* State: `clock = 0.0`, `last = perf_counter()`, `paused = False`
  (`flow.py:529`).
* `tick()` is the frame loop (`flow.py:538-547`); see section 9.

---

## 9. Animation and timing model

```python
def tick(self):
    now = time.perf_counter()
    if not self.paused:
        self.clock += now - self.last          # accumulate REAL elapsed seconds
    self.last = now                            # always updated, so unpausing never jumps
    t = self.clock / TIME_SCALE
    if LOOP and t > T_END + 4:
        self.clock, t = 0.0, 0.0               # loop after 4 s of withered hold
    self.photo.paste(Image.fromarray(self.plant.render(t)))
    self.root.after(TICK_MS, self.tick)        # schedule the next frame 10 ms after this one finished
```

Points:

* **The clock is wall-time**, from `time.perf_counter()` (`flow.py:539`). Speed is
  independent of how long frames take; a slow machine drops frames rather than
  playing slow motion. `TIME_SCALE` divides it, so 2.0 means half speed.
* `TICK_MS = 10` is the gap *between* frames, not a target frame rate. The next
  call is scheduled after the render finishes (`flow.py:547`), so the rate is
  at most about 100 fps and in practice `1 / (render time + 10 ms)`. We did not
  run it, so we cannot say what render time is; everything is vectorised, so
  we would expect the cost to be dominated by ~30k-dot numpy operations and
  one `argsort`.
* **Pause** only freezes `clock`; `tick` still re-renders the same `t` every
  10 ms (wasted work, but it keeps the loop trivially simple).
* **Restart** (`R`) sets `clock = 0`; the scene reverts to bare soil.
* **LOOP** is off by default; when on, the cycle is `T_END + 4 = 49 s`.
* Two time bases coexist inside `render`: `state(t)` clamps `t` to [0, 45], but
  the raw `t` keeps feeding `sway`, the ring rotation, spark loops and
  twinkles (and crumb hops), so after 45 s the withered stem still sways
  slightly.
* The exporters ignore the clock: PNG uses a fixed list of times and GIF uses
  `t = frame_index / fps`.

---

## 10. Rendering approach and performance tricks

The program is a tiny **particle renderer with no geometry primitives**: no
polygons, no lines, no alpha blending, no GPU. Every surface is a cloud of
coloured dots whose positions are produced by closed-form formulas.

1. **Precompute once, transform per frame.** All random sampling, colour
   choice and per-dot jitter happen in `build_*`. `render` only evaluates
   deterministic maths on the stored arrays, so the same `t` always gives the
   same picture (seed 5).
2. **Structure of arrays + whole-frame vectorisation.** There is not a single
   Python loop over particles in `render`. Every petal parameter is broadcast
   to a per-dot array so 20,620 dots across 23 petals go through one set of
   numpy expressions.
3. **Permutation so a prefix is a uniform subset.** After `permute`, taking
   `arr[:nv]` is the same as sampling `nv` dots at random. Growth is therefore
   just `nv = int(N * fraction)`: no per-frame resampling, and the shown set
   is always a prefix, so changing the fraction adds or removes dots only at
   the tail of the shuffled order (no popping in and out elsewhere). Counts follow geometry: stem count tracks length
   (`clip(stem, 0.08, 1)`), head and stamens track area (`size^2`), halo/rings
   track `glow`.
4. **One global depth sort per frame.** `Batch` collects every chunk and calls
   a single `argsort(z, kind="stable")`: the painter's algorithm in one shot.
5. **Static background baked once.** The 26,170 soil stamps are drawn into
   `self.base` in the constructor; each frame starts from `base.copy()`
   (a memory copy instead of re-stamping ~26k dots).
6. **Precomputed stamp offsets with prefix property.** `OFF`/`D2` replace
   per-dot disc rasterisation with a small `(n, 13)` mask; `nmax` limits the
   work to radius-2 discs by default.
7. **Radii are tiny and discrete** (1, 1.5, 2, occasionally 3), so a dot is
   at most 13 pixels. That keeps the stamp cost small and gives a consistent,
   chunky texel size: the look comes from quantised radii plus palette
   snapping, not from smooth shading.
8. **Fake transparency.** Dim colour toward black or show fewer dots.
9. **Cheap shortcuts for 3D.** Orthographic projection by two rotations, one
   depth value per dot, a one-line brightness term for depth. No lighting
   model, no normals.
10. **Pure function of time.** `render(t)` has no state to advance, which makes
    pause/restart/scrub/export trivial and removes simulation drift.

---

## 11. Quirks and gotchas worth knowing

* `README.md` names the wrong file (`flower.py`) and is truncated (section 1).
* `TIME_SCALE` is a divisor ("seconds of wall clock per animation second").
* Painter's algorithm relies on last-write-wins for repeated fancy indices in
  `splat` (section 5.8); not formally guaranteed by NumPy.
* Dot sizes and ground ripples are in absolute pixels, not scaled by `H`.
* Fixed z constants (-500, -450, +500) versus a `zp` that scales with `H`
  (section 5.9).
* Catmull-Rom is per-segment, not per-second, and overshoots; the final clip
  hides the overshoot (section 5.10).
* Leaf dot count scales with `leaf`, area with `leaf^2` (section 7.3).
* Pausing keeps re-rendering; `S` writes to the current directory.
* `Image.LANCZOS`/`Image.ADAPTIVE` are module-level Pillow constants
  (`flow.py:487, 497`); fine on the Pillow versions we know, but if a future
  Pillow removes them the exporters break. We did not test.
* Everything shares one RNG stream and one seed; adding or reordering random
  calls changes the flower.

---

## 12. Porting to ASCII in the browser

Everything in this section is **our proposal**, not a claim about the
reference. The target: a GitHub Pages love letter written in Python where every
visual, texture included, is made of characters.

### 12.1 The core mapping

The original paints dots into a pixel canvas; we paint particles into a
character grid. One cell takes the role of a "pixel", a glyph from a ramp
takes the role of a dot's size/density, and CSS colour takes the role of RGB.

| Original technique | ASCII/browser equivalent |
|---|---|
| `splat` stamps a 5-13 px disc per dot | One dot -> one cell (a character cell is already coarse). No stamp; if you want a "fat" dot, also touch the 4 neighbours with dimmer glyphs. |
| Pixel canvas `(H, W, 3)` | Grid of `rows x cols` cells holding `(glyph, colour)`. Use a ~2:1 cell aspect: for a square design space use `cols = 2 * rows` (e.g. 120x60), and map `x -> x/S*cols`, `y -> y/S*rows`. |
| Dot radius 1 / 1.5 / 2 | Per-cell **density** counter plus a **ramp** (below): more overlapping dots -> heavier glyph. |
| Painter's algorithm (`argsort(z)` + last write wins) | **Per-cell z-buffer**: keep `(zbuf, colour)` and replace when `z >= zbuf[cell]`. O(n), no sort, no reliance on NumPy write order. |
| `palette_pick` (snap to palette entry + brightness jitter) | Do it at build time; store the chosen palette *index* per particle. Emit one CSS class per palette entry (a few dozen classes) instead of inline RGB, which shrinks the HTML a lot. |
| `mixcol(live, wilt, w)` | Blend only for the **winning** particle of each cell (after the z-test), not for every particle. |
| Fake alpha (RGB * brightness) | Ramp glyph (`.` `:` `+`) in a dim colour; sparser particles. |
| Per-dot colour jitter (7%) | Pick between 2-3 near shades of a palette entry, or alternate glyphs; keep the "grain". |
| Edge dots (`sample_v` rim) | Edge particles get "outline" glyphs `( ) / \ o O` instead of the ramp. |
| Highlights / gold flecks | Rare `*`, `+`, `@` in HI/GOLD colours, same 4% / 2% rates. |
| Soil texture (26k stamps) | 4-8 rows of **static** text built once: ramp glyphs from the same `bright` formula, dark brown to light brown; vignette at the left/right edge. No particles per frame. |
| Halo | Evaluate `b = (1 - r/1.6)**1.5 * 0.55` **per cell** in the aura's bounding box (about 200-400 cells) and pick a ramp glyph, with an optional per-cell twinkle phase. No particles. |
| Rings | Seven circles, ~40-80 points each, stepped by angle, x stretched by the cell aspect, glyph `.` or `o`; six nodes as `O` or `@`. |
| Sparks | 20-40 particles with the same `life` loop; glyphs `. * +`. |
| Falling petals | 25-50 glyph particles (commas, tildes, apostrophes) using the same staggered `fp` schedule, flutter and quadratic fall. |
| Stem | Pick the glyph by **tangent direction** from the derivative that `bez` returns: a vertical bar near vertical, `/` and `\` on slants, `-` near horizontal, `:` for thick spots. Cheap and reads as a drawn line. |
| Petals | Density ramp, with a few glyph families per layer (outer: `()`, inner: `.:*`) to hint at the layering. |

### 12.2 Density ramp, concretely

A reference ramp for light-on-dark (dark page, bright ink):

```text
RAMP = " .:-=+*#%@"      # index 0 = empty cell, 9 = densest
glyph = RAMP[min(9, int(density * k))]      # k ~ 2-3 for 1-4 particles per cell
```

If the letter page is parchment-coloured (dark ink on light), reverse the ramp
(`"@%#*+=-:. "`). Keep density (how many particles landed) and colour (which
particle won the z test) as two separate channels, exactly like the original
separates "how many dots" from "what colour".

A minimal rasteriser (pure Python, no numpy; smoke-tested on random points):

```python
RAMP = " .:-=+*#%@"

def rasterise(parts, cols, rows, size):
    """parts: iterable of (x, y, z, rgb) in a size x size design space."""
    n = cols * rows
    count, zbuf, rgb = [0] * n, [-1e9] * n, [None] * n
    for x, y, z, c in parts:
        cx, cy = int(x / size * cols), int(y / size * rows)
        if 0 <= cx < cols and 0 <= cy < rows:
            i = cy * cols + cx
            count[i] += 1                      # density channel
            if z >= zbuf[i]:                   # colour/glyph channel: nearest wins
                zbuf[i], rgb[i] = z, c
    return count, rgb
```

### 12.3 Reusing the timeline: `KEYS` + `state()` + `smoothstep`

`state()` is pure scalar maths and ports to plain Python lists unchanged. This
is the same formula as the scratch re-implementation used for the table in
section 4.3 (neither was compared against an actual run of `flow.py`, which we
did not do):

```python
from bisect import bisect_right
TS = [k[0] for k in KEYS]                       # KEYS = [(t, ch1, ch2, ...), ...]

def state(t):
    t = min(max(t, TS[0]), TS[-1])
    i = min(max(bisect_right(TS, t) - 1, 0), len(KEYS) - 2)
    u = (t - TS[i]) / (TS[i + 1] - TS[i])
    p0, p1, p2, p3 = (KEYS[j][1:] for j in (max(i - 1, 0), i, i + 1, min(i + 2, len(KEYS) - 1)))
    return tuple(min(max(0.5 * (2*b + (c - a)*u + (2*a - 5*b + 4*c - d)*u*u
                                + (3*b - a - 3*c + d)*u**3), 0.0), 1.0)
                 for a, b, c, d in zip(p0, p1, p2, p3))
```

Ideas for the letter:

* Replace the six biology channels with **choreography channels** for the
  whole page: `envelope` (flap opening), `paper` (letter rising out), `text`
  (how many characters are revealed), `bloom`, `glow`, `petals` (drift).
  Write the whole scene as one `KEYS` table. Duplicate rows give holds
  (read time for a paragraph); the clip turns spline overshoot into clean
  plateaus.
* Fan one master channel into staggered effects with `smoothstep(x, a, b)`,
  as the original does for stamens: one `open` value drives flap, then paper,
  then flowers with different `(a, b)` windows.
* Keep `render(t)` **pure** (no mutable simulation state). Then `t` can come
  from `requestAnimationFrame` (a wall clock, like `perf_counter` in the
  original), or from **scroll position** or a click, and a reader can scrub
  backward and forward. Pause/restart are free.
* If frame time varies, keep the wall-clock accumulation so speed does not
  depend on frame rate; just cap the redraw rate (about 15-30 fps is plenty for
  text).
* Mind the two quirks: Catmull-Rom here is per segment, not per second (use
  roughly even key spacing, or scale the tangents), and it overshoots (keep
  the clip).

### 12.4 Prefix-slice growth = "drawing in" a flower

Generate every particle once at load, shuffle once with a seeded
`random.Random`, and reveal a prefix:

```python
rng = random.Random(5)
pts = build_all_particles(rng)      # list of (x, y, z, glyph, rgb) at the fully-grown pose
rng.shuffle(pts)                    # any prefix is a uniform random subset
shown = pts[:int(len(pts) * progress)]
```

* The flower appears as stipple that gets denser (like a developing print), and
  existing dots never move.
* The same trick works for **text**: shuffle the indices of the letter's
  characters and reveal a prefix for a "materialising" effect; or sort by `u`
  (distance along the petal) or by row for a deliberate "growing outward" or
  typewriter-like look. Random order is the original's choice; alternatives are
  a one-line change.
* Keep the original's counting rules: **linear** structures (stem) use `n *
  length`; **areas** (head) use `n * size^2`. That keeps density constant while
  the thing grows.

### 12.5 Wilt, fall and drift

* The original's wilt is a handful of linear blends (A0 shrinks, K grows, colour
  blends toward browns, phi rotates). In ASCII you can simplify to: colour
  blend to the wilt palette, petal glyph set swaps to a "tired" one (`. , '`),
  and a stem droop using the same `ctrl()` formulas.
* **Falling petals** are cheap and charming: copy the schedule
  `fp = clip((w*1.05 - r0*0.7)/0.35, 0, 1)`, flutter `sin(6.28*f + ph)*(1-f)`
  and gravity `y = sy + (yl - sy)*f*f`. For a love letter you may not want
  to wilt the flower at all; use the same system as a **petal drift** on
  "open the letter" or when the reader reaches the end, with the head
  unchanged.
* The crumbs hop (`amp * sin(pi*e)`) is a tiny "something is happening here"
  micro-animation for a few soil characters; ~20 are enough.

### 12.6 What is too heavy for a browser Python runtime, and lighter substitutes

We do not know the final runtime (Pyodide/PyScript with CPython compiled to
WebAssembly, Brython, MicroPython, ...). Pyodide can load numpy but it is an
extra multi-megabyte download and a slower start; plain-Python runtimes have
no numpy at all. Budget with that in mind, and **measure on the real runtime**;
the figures below are planning heuristics, not measurements.

| Original | Why it is heavy for us | Lighter substitute |
|---|---|---|
| ~32,000 particles per frame | Pure-Python loops cost microseconds per particle; at 30k that is far too slow, and it is useless anyway: a 120x60 grid has 7,200 cells | Aim for roughly **1 to 3 particles per visible cell: about 1,000-3,000 total**. Counts to try: head ~900 (about 40 per petal), stem ~150, leaves ~60 each, stamens ~40, rings 7 x ~48, sparks ~25, fall ~30 |
| 26,000 soil stamps | Pointless at ASCII resolution | Pre-generate 4-8 text rows once (static); animate only ~20 crumbs |
| `numpy` vectorised maths | Large download or unavailable | Plain lists and `math`; precompute per-petal trig once (23 petals), not per particle; see 12.7 |
| Global `argsort` of ~30k dots | O(n log n) in Python | Per-cell z-buffer (section 12.1), O(n) |
| `splat` with `(n, 13)` masks | Not needed on a coarse grid | One cell per particle (optionally 4 neighbours for fat dots) |
| 1,800-dot halo and 1,720-dot rings | Particles for something smooth | Analytic per-cell shading for the halo; a few dozen points per circle for the rings |
| `Pillow` / `ImageTk` / `tkinter` | Not available in the browser | The DOM: a `<pre>` (or a `<canvas>` with `fillText`) |
| GIF/PNG exporters | Not needed | Drop them |
| 45 s at 10 ms ticks, full repaint | DOM churn | One `innerHTML` assignment per frame (build the whole string in Python, hand it to JS once; avoid per-cell calls across the Python/JS boundary), 15-30 fps, skip frames when `t` has not changed |

Rendering the output cheaply:

* **Run-length merge** neighbouring cells with the same colour class into one
  `<span class="cNN">...</span>`. With palette-index classes the span count
  stays in the low hundreds per frame, versus thousands for per-cell spans.
* Escape `<`, `>` and `&` if those glyphs ever appear in the ramp.
* Set `font-family: monospace; line-height: 1` and size the `<pre>` so one
  cell is about twice as tall as it is wide; this is the aspect factor used above.
* **Bake instead of compute.** Because the site is built from Python, a build
  step (for example a GitHub Action) can run the full original-style
  CPython + numpy pipeline offline and ship pre-rendered text frames. Size
  warning (arithmetic): 541 frames (45 s at 12 fps) x 7,200 cells is about 3.9 million
  cells before compression, so bake **keyframes only** and tween, or
  delta/run-length encode, or bake only the heavy parts (soil texture, flower
  at several bloom levels) and animate the cheap ones live.

### 12.7 A cheaper petal evaluator (idea)

Per frame, for each of the 23 petals compute the centreline once at a handful
of `u` stops (say 16): `rr_k, hh_k` from the `sinc` formulas, plus its tangent
angle for width orientation. Each particle then stores `(petal_id, k, frac, v)`
and reads two table entries with a lerp instead of calling `sin`, `cos` and
`sinc` itself. The per-petal rotation by `th` and the shared projection can also be
folded into a few per-petal constants computed once per frame. The cost drops
from `particles x (trig-heavy)` to `petals x stops x (trig-heavy)` plus a
few multiplies per particle.

### 12.8 Letting the text be the pigment

Since everything is characters anyway, the ramp does not have to be
punctuation. A fun, readable option: build the petal and leaf density ramps out
of **letters of the message** (light letters for sparse cells, `M`, `W`, `@`
for dense ones), so the flower literally contains the words. Keep the
background soil to symbols so the real letter text stays legible against it.

### 12.9 Licence-safe workflow

Because the reference has no licence (header table), implement from the
**ideas** (standard maths: smoothstep, Catmull-Rom, cubic Bezier, circular-arc
closed form, painter's algorithm, prefix-subset growth), not from the
source text; credit `iremcnar/Flowers` as inspiration; and if we ever want to
reuse real code or its colour tables verbatim, ask the author to add a licence
first.

---

## 13. Key takeaways

1. **The whole program is one pure function `render(t)`** over precomputed
   particle arrays. No simulation state; scrubbing, export and pause are free.
2. **Pointillism comes from three cheap choices:** tiny discrete dot radii,
   *snapped* palette colours with a little brightness noise
   (`palette_pick`), and overwrite-only painting; no blending.
3. **Growth is a prefix slice of a shuffled array.** `nv = int(N * f)` is
   random-subset growth for free; use `size^2` for areas and linear for
   lengths.
4. **One keyframe matrix drives everything.** Six channels
   (stem, size, bloom, wilt, leaf, glow) interpolated by Catmull-Rom and
   clipped; duplicate rows make holds; `smoothstep` carves sub-windows out of a
   channel.
5. **Petals are closed-form arcs.** Opening angle `A0` and curvature `K`
   interpolated by `bloom`, positioned with `sinc`, widened by a teardrop
   `profile`, then pitched/rolled and depth-shaded: a convincing 3D bloom with
   no 3D engine.
6. **Wilt = the same parameters pushed further** (smaller `A0`, bigger `K`,
   shorter petals, brown colour blend, head roll `phi = 2.75`, stem Bezier
   arching), plus an independent falling-dots effect with a staggered
   schedule.
7. **Depth is one number per dot** and a single global sort (painter's
   algorithm); for a coarse text grid, replace it with a per-cell z-buffer.
8. **The aura is dim dots plus time-varying maths**: a half-normal halo, a
   rosette of seven circles, six nodes and looping sparks. All cheap to turn into
   a few dozen glyphs.
9. **Do not copy the particle counts.** ~32,000 dots make sense on a ~800x800
   canvas; a 120x60 character grid wants 1,000-3,000. Keep the structure
   (build once, transform per frame, density ramp plus z-buffer) and shrink the
   numbers.
10. **No licence:** use the techniques, write our own code, credit the source.
