# neonButterfly: how `neon.py` works

A close reading of one small generative-art program, written as a style reference for our ASCII love-letter page.

**Citation conventions**

- `neon.py:N`, `README.md:N` are line numbers in the reference copy at `part1/reference/neonbutterfly/`.
- `turtle.py:N` is CPython 3.14.0's stdlib `turtle.py` as installed on this machine (line numbers differ between Python versions).
- **[calc]** marks numbers I recomputed with a stand-alone replica of the formulas (pure `math` / `random`, CPython 3.14.0). `neon.py` itself was never executed, and nothing under `reference/` was modified.
- **[wiki]** marks facts from Wikipedia's "Butterfly curve (transcendental)" page, fetched 2026-10-31.

---

## 1. Header

| Item | Value |
|---|---|
| Source | https://github.com/iremcnar/neonButterfly |
| Author | GitHub user `iremcnar` (from the task brief; the local copy carries no author metadata) |
| Commit | `0aad531904611353ae982f07d78cab602579dbc5`, shallow clone, dated 2026-10-08 (from the brief; the local copy has no `.git`, so I could not check it) |
| Files | `neon.py` (116 lines, 2356 bytes), `README.md` (18 lines, 709 bytes), `.gitattributes` (`* text=auto`, line-ending normalisation only) |
| Licence | **None.** There is no `LICENSE` file, and `README.md` has no licence text either. |
| Dependencies | Python standard library only: `math`, `random`, `turtle` (`neon.py:1-3`) |

**Licence status in practice.** With no licence, the code is "all rights reserved" by default. We have no permission to copy or adapt `neon.py`. Treat it as a reference to learn from and re-implement independently. The underlying maths (Fay's curve, linear interpolation, smoothstep) is not the author's to restrict. This is not legal advice. If we ever want to ship anything derived from the code itself, ask the author or credit them.

**Summary.** `neon.py` opens an 800x800 `turtle` window on a near-black background and draws a neon butterfly out of 5600 tiny coloured line segments. A seeded RNG picks 5600 random (angle, scale) pairs. The angle selects a point on Fay's butterfly curve, and the scale blows that curve up from 3 to 92 pixels per unit. This makes nested, similar copies of the butterfly that fill the wings. Pairs are sorted by scale, so the picture grows from the centre outward. Each pair becomes a short stroke that points roughly away from the butterfly's pivot, with a random length (3 to 8 px) and width (0.7 to 1.3 px). The stroke's colour comes from a four-stop gradient (cyan, electric blue, magenta, deep purple) indexed by scale. The strokes come out of a generator, and a self-rescheduling timer callback draws one per tick and repaints. The "glow" is not a real effect. It is a saturated palette plus many thin overlapping lines on a dark ground.

The README (`README.md:1-18`) is a title, a one-sentence description (line 3), a screenshot link (line 6, not fetched), a three-bullet feature list (lines 11-13) and `python neon.py` under "How to Run" (lines 17-18). The code fence opened at line 17 is never closed.

---

## 2. Running it, dependencies, window setup

### Run and dependencies

```bash
python neon.py        # README.md:17-18
```

- It needs a display. A Tk window opens and the program stays alive in the Tk main loop until the window is closed (`neon.py:116`).
- The README lists `tkinter` as a dependency (`README.md:13`), but `neon.py` never imports it. Only `math`, `random` and `turtle` are imported (`neon.py:1-3`). Tk is reached through turtle, which does `import tkinter as TK` (`turtle.py:101`). You still need a Python build that includes Tk. On Debian/Ubuntu that means installing `python3-tk` separately.
- The three module aliases are one letter long: `m` is math, `r` is random, `t` is turtle. `r` is used exactly once, at `neon.py:13`. The file has no comments or docstrings at all (the only `#` characters are inside the two hex-colour strings at `neon.py:7` and `neon.py:27`). The stop names "cyan / electric blue / ..." come from the README, not the code. There is no `if __name__ == "__main__"` guard, so everything runs at import time.

### Window setup (`neon.py:5-13`)

| Line | Code | Effect |
|---|---|---|
| 5 | `s = t.Screen()` | Gets turtle's singleton screen object (`turtle.py:3786-3792`). This creates the Tk root window and a `ScrolledCanvas`. |
| 6 | `s.setup(800, 800)` | Sets the window to 800x800 px, centred on the display (`turtle.py:3817-3855`). |
| 7 | `s.bgcolor("#03030b")` | Canvas background of RGB (3, 3, 11), nearly black with a slight blue cast. |
| 8 | `s.title("Neon Butterfly")` | Window title. |
| 9 | `s.tracer(0)` | Turns off turtle's automatic redraw counter (`turtle.py:1237-1263`). See below. |
| 11 | `cv = s.getcanvas()` | Returns the underlying canvas object so we can draw on it directly. |
| 12 | `OY = -30` | Vertical offset of the butterfly's pivot, in world units (see section 4.5). |
| 13 | `rng = r.Random(12)` | A private, seeded generator. The same seed gives the same picture every run. |

**`tracer(0)` is effectively a no-op here.** It only governs how often turtle redraws *Turtle objects*. The script never creates a `Turtle`, so there is nothing for it to control. The only turtle-side loop in `s.update()` iterates over an empty list of turtles (`turtle.py:1309-1318`). The real repaint control is the manual `s.update()` call (`neon.py:105`). I assume `tracer(0)` is an idiom carried over from typical turtle animation code.

**Raw Tk canvas.** `getcanvas()` returns a `ScrolledCanvas`, a `tkinter.Frame` that wraps a real `tkinter.Canvas`. Canvas methods such as `create_line` are forwarded to the inner canvas (`turtle.py:326-426`). So `cv.create_line(...)` at `neon.py:41` is the ordinary Tk canvas API. Turtle only supplies the window, the event loop and the coordinate setup. Items created this way are plain Tk canvas items. Turtle does not track them and tracer settings do not apply to them.

**Origin and y-axis flip.**

- Turtle configures the canvas scroll region as centred on (0, 0): `scrollregion=(-w//2, -h//2, w//2, h//2)` (`turtle.py:366-372`, re-centred on resize at `turtle.py:392-394`). So raw canvas coordinate (0, 0) is the middle of the visible canvas, and the butterfly's pivot lands near the window centre.
- Tk's y axis grows **downward**, but all the maths in `neon.py` is y-up. Turtle itself negates y when it draws (`turtle.py:509`). The script does the same in exactly one place, `segment`: `cv.create_line(x1, -y1, x2, -y2, ...)` (`neon.py:42`).
- Everything before that call (the curve, the OY offset, the `atan2` direction, the stroke endpoints) is in y-up "world" coordinates. This keeps the maths natural and puts the flip at the drawing boundary. We should do the same when we rasterise to rows of text, where row 0 is the top.

### Constants at a glance

| Constant | Value | Where |
|---|---|---|
| Window | 800x800, bg `#03030b` | 6-7 |
| RNG seed | 12 | 13 |
| Samples | 5600 | 53 |
| Scale range | uniform [3, 92] | 52 |
| Angle range | uniform [0, 2pi) | 52 |
| Direction jitter | +/-0.18 rad (about +/-10.3 deg) | 63 |
| Stroke length | uniform [3, 8] px | 65 |
| Stroke width | uniform [0.7, 1.3] px | 96 |
| Colour bands | scale < 41, < 74, else (up to 92) | 67, 74, 81 |
| Pivot offset `OY` | -30 | 12 |

---

## 3. Architecture and data flow

The program is a pipeline built around one generator and one timer callback.

```
rng = Random(12)                                                  neon.py:13
   |
   |  11 200 draws, all consumed on the FIRST next()              neon.py:50-56
   v
5600 x (angle a ~ U[0, 2pi),  scale s ~ U[3, 92])
   |  sorted by s ascending  -> inner copies first                neon.py:55
   v
for each (a, s) in that order:                                    neon.py:58
   (x, y) = butterfly(a, s)      Fay curve * s, y shifted by OY   neon.py:59
   angle  = atan2(y-OY, x) + U(-0.18, 0.18)   radial + jitter     neon.py:61-64
   length = U(3, 8)                                               neon.py:65
   colour = 3-band gradient of s                                  neon.py:67-89
   width  = U(0.7, 1.3)                                           neon.py:96
   yield (x, y, x2, y2, colour, width)                            neon.py:91-97
   |
   |  consumed one tuple per timer tick
   v
draw_next():  segment(*next(strokes)); s.update(); s.ontimer(draw_next, 0)
   |                                                              neon.py:102-106
   v
cv.create_line(x1, -y1, x2, -y2, fill=hx(colour), width, capstyle="round")
                                                                  neon.py:40-46
```

### Stage by stage

1. **Seeded RNG** (`neon.py:13`). All randomness comes from one `random.Random(12)`. `random` is never used through the module-level functions. The output is fully deterministic: same seed, same picture. Integer seeds produce the same Mersenne Twister stream across CPython 3.x versions.
2. **Sampling** (`neon.py:50-56`). The generator expression produces 5600 `(angle, scale)` tuples. Within each tuple the angle is drawn first, then the scale, because tuple elements are evaluated left to right. `sorted(..., key=lambda point: point[1])` pulls the whole expression to exhaustion before returning, so all 11 200 sampling draws happen here, sorted ascending by scale.
3. **Per-sample stroke** (`neon.py:58-97`).
   - Position `(x, y)` comes from `butterfly(a, scale)`.
   - The direction is the polar angle of the point as seen from the pivot, `atan2(y - OY, x)`, plus a jitter of +/-0.18 rad. So strokes radiate outward from the pivot like fur or sparks. The `- OY` is what puts the pivot back at (0, OY) (see 4.5). For a negative radius (`r < 0`), the position vector points the opposite way from `(sin a, cos a)`, but `atan2` of the actual position handles that, so the stroke still points away from the pivot.
   - The endpoint is `(x + L cos(angle), y + L sin(angle))` with `L ~ U(3, 8)` (`neon.py:93-94`).
   - Colour depends only on `scale` (section 5). Width is drawn last, inside the `yield` expression (`neon.py:96`).
   - Draw order per stroke is therefore: jitter (63), length (65), width (96). Those are 3 draws per stroke, 16 800 after the 11 200 sampling draws, 28 000 total [calc].
4. **Generator** (`neon.py:49, 99`). `artwork()` contains `yield`, so it is a generator function. `strokes = iter(artwork())` (`neon.py:99`) runs **none** of its body. The sampling and sorting happen on the first `next(strokes)`, inside the first timer tick. It is cheap: 5600 samples is trivial work.
5. **Tick** (`neon.py:102-112`). Each tick takes the next stroke tuple, draws it, forces a repaint and schedules itself again (section 6.7).

The tuple layout `(x1, y1, x2, y2, color, width)` matches the parameter order of `segment(x1, y1, x2, y2, color, width)` exactly, which is why `segment(*next(strokes))` works (`neon.py:40, 104`). Colours stay as float tuples inside the generator. They are only converted to a hex string at draw time (`neon.py:43`).

---

## 4. Fay's butterfly curve

### 4.1 The published curve

Temple H. Fay (University of Southern Mississippi) published the curve in 1989 **[wiki]**. Wikipedia gives two forms, which I quote as printed:

```
parametric, 0 <= t <= 12*pi:
  x = sin t * ( e^cos t - 2 cos 4t - sin^5(t/12) )
  y = cos t * ( e^cos t - 2 cos 4t - sin^5(t/12) )

polar:
  r = e^sin(theta) - 2 cos(4*theta) + sin^5((2*theta - pi)/24)
```

Wikipedia is not self-consistent between the two forms. The sign on the `sin^5` term differs, and the parametric form uses `cos` inside the exponential while the polar form uses `sin`. The code follows the parametric form's structure (`cos` in the exponential, `x = r sin`, `y = r cos`) but with the polar form's plus sign on the last term.

### 4.2 The code's version (`neon.py:16-23`)

```python
def butterfly(a, scale):
    radius = (
        m.exp(m.cos(a))
        - 2 * m.cos(4 * a)
        + m.sin(a / 12) ** 5
    ) * scale

    return radius * m.sin(a), radius * m.cos(a) + OY
```

In maths:

```
r(a) = e^cos(a) - 2 cos(4a) + sin^5(a/12)          (the base curve, "unit scale")
x(a, s) =  s * r(a) * sin(a)
y(a, s) =  s * r(a) * cos(a) + OY
```

Because `x = r sin a` and `y = r cos a`, the angle `a` is measured from the +y axis (straight up), clockwise. This is the same convention as the parametric form above.

Differences from the published curve:

| | Published (parametric, **[wiki]**) | `neon.py` |
|---|---|---|
| Parameter range | 0 to 12pi (six laps) | 0 to 2pi (one lap), `neon.py:52` |
| `sin^5(t/12)` term | amplitude up to 1 (t/12 runs 0 to pi) | at most 0.03125 [calc] (a/12 < pi/6, so sin < 0.5) |
| Sign of that term | minus | **plus** (`neon.py:20`) |
| Scale | none (unit curve) | multiplied by `scale` (3 to 92) |
| Pivot | origin | origin shifted by `OY` on y only |

The first two rows are the important ones. In Fay's original, the slow `sin^5(t/12)` term deforms each of the six laps slightly differently. That is what builds the layered, feathered wings. `neon.py` keeps one lap and a term so small it is almost a constant. It then gets the layering a different way: by drawing many scaled copies of the same lap (section 4.4).

### 4.3 What the base curve looks like [calc]

For the code's `r(a)` over `a` in [0, 2pi):

- `r` ranges from -1.631 to 4.077. For example `r(0) = 0.718`, `r(pi/4) = 4.028`, `r(pi/2) = -1.000`, `r(pi) = -1.631`.
- `r` changes sign six times, at `a` of about 1.347, 1.868, 2.798, 3.485, 4.416 and 4.935. A negative `r` means the point is reflected through the pivot, which is how a single closed curve produces the wing and head lobes with inner loops.
- The unit curve (before scaling or `OY`) spans x from -2.918 to 2.906 and y from -1.810 to 3.145. It is almost left-right symmetric, and the tiny `sin^5` term is the only source of asymmetry.
- Its aspect is about 5.82 wide by 4.95 tall (0.85 height-to-width). We will need that number when we pick a character grid (section 8).

### 4.4 Why scale in [3, 92] fills the wings with nested copies

`scale` multiplies the whole radius, so for a fixed `s` the points `(x, y)` trace the unit curve enlarged by `s` about the pivot. Different `s` values give **similar copies of one shape, nested one inside the next**, like a set of Russian dolls.

`neon.py` does not draw any one copy as a line. Each of the 5600 samples picks a random point (`a`) on a random copy (`s`), so the points scatter over the whole region swept by the scaled curves. That region is the "filled" wing.

- The smallest copy, `s = 3`, is about 17 px wide (3 x 5.82). The largest, `s = 92`, spans x from -268.5 to 267.4 and y from -196.5 to 259.3 including `OY` [calc]. It fits comfortably in the 800x800 window.
- Strokes reach a few pixels beyond that. Over all seed-12 strokes the world extents are x in [-270.0, 264.3] and y in [-199.3, 262.6] [calc].
- The lower bound 3 avoids a degenerate dot at the pivot. The upper bound 92 sets the overall size.

The sample density is not uniform. The map `(a, s) -> (x, y)` has Jacobian determinant `s * r(a)^2` (derived by hand and checked numerically [calc]). Points per unit area therefore scale like `1 / (s * r(a)^2)`:

- the middle of the butterfly is much denser than the rim, because density falls off as 1/s;
- directions where `r` is near zero (the six sign changes in 4.3) get extra density near the pivot;
- the outer shells are sparse: 5600 points, spread over a large area.

Together with the colour fade to dark purple, this sparse rim is what gives the soft, glowing falloff.

### 4.5 The `OY` offset

`OY = -30` (`neon.py:12`) is added to every `y` in `butterfly` (`neon.py:23`). That moves the pivot (the butterfly's "body" point) 30 world units down from the canvas origin. The unit curve is vertically lopsided (y from -1.81 to +3.15), so at scale 92 the shape sits mostly above its pivot. Without `OY` the bounding box would span y from -166.5 to 289.3, with its centre about 61 px above the window centre. With `OY` it spans -196.5 to 259.3, centre about 31 px above [calc]. So `OY` re-centres the picture roughly halfway.

`OY` has to be removed again to get the radial direction, which is why `neon.py:62` uses `m.atan2(y - OY, x)`. Without that subtraction the strokes would radiate from the canvas origin instead of the pivot, and the starburst texture would be skewed.

---

## 5. Colour pipeline

### 5.1 The four stops

Colour values are float RGB triples in [0, 1]. They appear as literals in the three branches (`neon.py:69-70, 76-77, 86-87`).

| Stop | Float RGB | x255 | Hex via `hx` [calc] | Appears at |
|---|---|---|---|---|
| Cyan | (0.32, 0.95, 1.0) | 81.6, 242.25, 255 | `#51f2ff` | `neon.py:69` |
| Electric blue | (0.22, 0.42, 1.0) | 56.1, 107.1, 255 | `#386bff` | `neon.py:70, 76` |
| Magenta | (0.88, 0.20, 1.0) | 224.4, 51, 255 | `#e033ff` | `neon.py:77, 86` |
| Deep purple | (0.24, 0.025, 0.42) | 61.2, 6.375, 107.1 | `#3d066b` | `neon.py:87` |

Background for comparison: `#03030b`.

### 5.2 The three bands

Colour depends only on `scale` (`neon.py:67-89`), so colour is constant along each nested copy and the image is a set of colour-coded rings.

| Band | Condition | Blend | Lines |
|---|---|---|---|
| 1 | `scale < 41` | `mix(cyan, blue, scale / 41)` | 67-72 |
| 2 | `41 <= scale < 74` | `mix(blue, magenta, (scale - 41) / 33)` | 74-79 |
| 3 | `74 <= scale <= 92` | `amount = (scale - 74) / 18`, smoothstepped, then `mix(magenta, purple, amount)` | 81-89 |

Band boundaries are 41, 74 and 92. The first band is 38 wide (3 to 41), the second 33 wide, the third 18 wide.

- **Continuity.** At `scale = 41` band 1 gives amount 1 (pure blue) and band 2 gives amount 0 (pure blue). At `scale = 74` band 2 gives magenta and band 3's smoothstep gives 0 (magenta). There are no colour seams.
- **Smoothstep on the last band** (`neon.py:82-83`): `amount = amount * amount * (3 - 2 * amount)`, the Hermite curve 3t^2 - 2t^3. It has zero slope at both ends, so the fade from magenta into purple eases in and out. The first two bands are plain linear.
- **The extreme stops are never quite reached.** Band 1 divides by 41, not by the band width 38, so at the smallest scale (about 3) the blend is 3/41 = 7.3% of the way to blue. The innermost colour is `#4fe8ff`, not the pure cyan `#51f2ff`. At the top, `uniform(3, 92)` gives values below 92, so the seed-12 maximum scale of 91.957 [calc] sits just short of pure `#3d066b`.
- **Expected vs actual sample counts** (5600 samples; scale is uniform):

  | Band | Expected | Seed 12 [calc] | Share of the animation |
  |---|---|---|---|
  | 1 (cyan to blue) | 2391 | 2426 | 43.3% |
  | 2 (blue to magenta) | 2076 | 2028 | 36.2% |
  | 3 (magenta to purple) | 1133 | 1146 | 20.5% |

Sample colours along the scale axis [calc], with contrast ratio against the background `#03030b` (WCAG formula):

| Scale | Hex | Contrast | Scale | Hex | Contrast |
|---|---|---|---|---|---|
| 3 | `#4fe8ff` | 14.0 | 60 | `#994aff` | 4.7 |
| 41 | `#386bff` | 4.6 | 74 | `#e033ff` | 6.0 |
| 50 | `#665bff` | 4.4 | 83 | `#8e1cb5` | 2.9 |
| | | | 92 | `#3d066b` | 1.4 |

The rim is very dark. At `#3d066b` it is barely distinguishable from the background, so the fade to deep purple reads as the glow dying out, not as a visible outline. That is fine for decoration but unusable for readable text.

### 5.3 `mix` and `hx`

- **`mix(first, second, amount)`** (`neon.py:33-37`) is a per-channel linear interpolation: `a + (b - a) * amount` for each channel pair from `zip(first, second)`. It returns a tuple of floats, works for tuples of any length, and does not clamp `amount`.
- **`hx(color)`** (`neon.py:26-30`) turns a float triple into a Tk colour string. For each channel it clamps to [0, 1] with `max(0, min(1, value))`, multiplies by 255 and **truncates** with `int()` (it does not round), then formats as `"#%02x%02x%02x"`. For example `hx((0.32, 0.95, 1.0))` is `"#51f2ff"` [calc]. The clamp is only a safety net here, because every `amount` the three bands pass stays inside [0, 1].

### 5.4 There is no real glow

A Tk canvas has no blur, no alpha and no shadow. The "neon" look comes only from fully saturated colours on a near-black ground, thin (about 1 px) lines with round caps that overlap into brighter clusters near the dense centre, and the density falloff toward the rim (4.4). In the browser we can add a genuine glow with CSS (section 8.3).

---

## 6. Every function

### 6.1 `butterfly(a, scale)` (`neon.py:16-23`)

Pure function of the angle and scale. It returns the world-space point `(x, y)` on the scaled Fay curve with the pivot offset applied, as described in section 4. It reads the global `OY`. It does not touch the RNG or the canvas.

### 6.2 `hx(color)` (`neon.py:26-30`)

Float RGB tuple in, `"#rrggbb"` string out (section 5.3). Called once per stroke, inside `segment`.

### 6.3 `mix(first, second, amount)` (`neon.py:33-37`)

Linear interpolation between two equal-length tuples (section 5.3). Used three times in `artwork`, once per band.

### 6.4 `segment(x1, y1, x2, y2, color, width)` (`neon.py:40-46`)

```python
def segment(x1, y1, x2, y2, color, width):
    cv.create_line(
        x1, -y1, x2, -y2,
        fill=hx(color),
        width=width,
        capstyle="round",
    )
```

The only function that touches the canvas. It flips y (`-y1`, `-y2`), converts the colour with `hx`, and creates one Tk line item. `width` is a float (0.7 to 1.3), which Tk accepts. `capstyle="round"` rounds the line ends, so a 3 to 8 px stroke has soft, slightly bulbous ends. Items are never deleted, so the canvas ends up holding 5600 line items, and later items sit on top of earlier ones in Tk's display list.

### 6.5 `artwork()` (`neon.py:49-97`)

The generator that holds all of the logic. It:

1. builds and sorts the 5600 samples (lines 50-56);
2. loops over them in ascending scale order (line 58);
3. computes position, direction, length, colour and width (lines 59-96);
4. yields a six-element tuple per stroke (lines 91-97).

It is stateful, because it advances the shared `rng`. It must be consumed exactly once, in order, for the picture to match the seed. Because it is a generator, `artwork()` returns immediately and does nothing until `next()` is called (`neon.py:99`).

### 6.6 `strokes = iter(artwork())` (`neon.py:99`)

Module-level iterator over the generator. `iter()` on a generator returns the generator itself, so this line is just a name binding. It is shared by every call of `draw_next`.

### 6.7 `draw_next()` (`neon.py:102-112`)

```python
def draw_next():
    try:
        segment(*next(strokes))
        s.update()
        s.ontimer(draw_next, 0)

    except StopIteration:
        s.update()

    except (t.Terminator, t.TclError):
        return
```

**Normal tick (lines 104-106).**

1. `next(strokes)` pulls one tuple, and `segment(*...)` creates one line item.
2. `s.update()` forces a repaint. It loops over turtle's registered turtles (none) and then calls `cv.update()` (`turtle.py:1309-1318`, `turtle.py:555-558`), which runs Tcl's `update` and processes pending events including the canvas redisplay.
3. `s.ontimer(draw_next, 0)` re-registers the same function. With a delay of exactly 0, turtle uses `cv.after_idle(fun)`, not `cv.after(0, fun)` (`turtle.py:704-710`). So the next stroke runs when Tk next has nothing else to do. There is no fixed frame rate, and the speed depends entirely on how long each repaint takes on the machine. I did not time it.

**Bootstrapping.** `s.ontimer(draw_next, 0)` at `neon.py:115` only queues the first call. Nothing is drawn until `t.done()` (`neon.py:116`) starts the Tk main loop (`turtle.py:792`; `done` is an alias of `mainloop`, `turtle.py:4105`).

**Termination.** After the 5600th stroke, the next call hits an exhausted generator and `next()` raises `StopIteration`. That is caught at line 108, which does one last `s.update()` and does **not** reschedule. The chain of timers ends, and the window stays open on the main loop. In total `draw_next` runs 5601 times and calls `s.update()` 5601 times (`setup` adds one more, `turtle.py:3855`).

**Error handling (lines 111-112) has a latent bug.** The intent is clear: swallow the errors produced when the user closes the window mid-animation. But in Python 3.14.0, the `turtle` module has no `TclError` attribute (`'TclError' in dir(turtle)` is `False` [calc]; turtle only does `import tkinter as TK`, `turtle.py:101`, and uses `TK.TclError` internally). Python evaluates the `except (...)` tuple only when an exception reaches that clause and the earlier `except StopIteration` did not match. So:

- the normal run, ending in `StopIteration`, never evaluates `t.TclError` and works fine;
- if some other exception arrives (most plausibly a `tkinter.TclError` raised because the window was destroyed while a tick was in flight), evaluating `t.TclError` would raise `AttributeError` instead, probably printing a traceback to stderr rather than exiting quietly. This is inferred from the source only. I did not run it.

Also, `t.Terminator` is only raised by turtle's *global wrapper functions* and by Turtle-object drawing (`turtle.py:1300-1304`, `turtle.py:4071-4084`). `draw_next` calls `s.` instance methods and uses no Turtle objects, so in this script it would never fire there. The name is real (`turtle.py:850`), but the catch is dead code. Neither point matters for a browser port, where cancelling the animation frame is the equivalent.

---

## 7. Animation model

**Order is the animation.** There is no explicit "time" or progress variable. The animation is the order in which items are created, and that order comes from `sorted(..., key=lambda point: point[1])` (`neon.py:55`), ascending by scale. So:

- the first strokes are the smallest copy (scale around 3, about 17 px wide), near the pivot, in cyan;
- the picture grows outward as `scale` rises: the n-th stroke has scale of about `3 + 89 * n / 5600` (expected value for sorted uniform samples);
- colour sweeps with time too: the first 43% of strokes are cyan to blue, the next 36% blue to magenta, the last 20% magenta to purple (seed 12 counts, section 5.2).

The overall effect is a butterfly blooming from its body outward, with a cold bright core and a warm fading rim.

**Within one scale shell the order is random.** Angles are not sorted, so while a given scale is being drawn, strokes pop up at random positions around the shell. It reads as sparkling or shimmering, not a pen tracing a line.

**Painter's order.** Tk draws items in creation order, so outer strokes cover inner ones wherever they overlap. Nothing is ever erased or faded.

**Cost of `s.update()` per stroke.** The program calls `s.update()` after every single line, 5601 times in total (`neon.py:105, 109`). That is the right call for a visibly progressive reveal, because the screen is guaranteed to repaint between strokes. It is also the dominant cost. Each call enters the Tcl event loop, handles pending events (including window and input events) and repaints. Tk only has to redraw the small region around the new line, but it must redraw every existing item overlapping that region, so work per tick grows with ink density near the centre. That is my understanding of Tk's behaviour, not something measured here. The cost is paid in event-loop overhead, not in the maths: all of the generator's work (about 28 000 random draws, 5600 curve evaluations and a sort) is trivial next to 5601 repaints.

Also note what is **not** there: no easing, no pause, no speed control, no fixed frame time, no user interaction. The reveal speed is whatever the machine's repaint speed allows. Total ink is about 30 700 px of line length (mean stroke 5.48 px, mean width 1.00 px) [calc].

---

## 8. Porting to ASCII in the browser

These are ideas for our love letter (envelope, heart, buttons, and so on). We should write all of it independently (section 1, licence). The sketch below reuses the reference's constants (seed, 5600, scale range, jitter) for comparison only. Pick our own values in the real implementation.

### 8.1 Rasterise the curve into a character grid

Treat the page as a W x H grid of monospace cells. Characters are roughly **twice as tall as they are wide**, so use a world-units-per-cell of `sx` horizontally and `sy = 2 * sx` vertically, or the butterfly comes out stretched.

Size the grid from the shape's aspect (0.85 height-to-width, section 4.3): rows of about `cols x 0.85 / 2`. So 80 columns need about 34 rows [calc]. Map world to cell with the y-flip happening at the very end, as in the reference:

```
col = cols/2 + x / sx
row = rows/2 - (y - y_centre) / sy        # y_centre = world y that lands on the middle row
```

`y_centre` is a choice. The shape's own vertical centre at scale 92 is about 61 world units above the pivot (section 4.5). The sketch below uses 31, which copies the reference's placement (`OY = -30` pulls the centre down to about 31 above the window centre). That leaves the art tight against the top of the grid with about 5 spare rows at the bottom. For our page, use about 61 to centre it.

Two ways to fill the grid:

- **Sampling** (what the reference does): stamp a glyph for each random `(a, s)` sample into a dict keyed by `(col, row)`. Last writer wins, which mimics the canvas z-order. Seeded `random.Random` keeps it deterministic.
- **Deterministic sweep**: walk a regular `(a, s)` lattice with step sizes small enough to touch every cell on the curves. No randomness, no holes, easier to test. It loses the organic grain that makes the original look alive. A hybrid is to use the lattice but jitter the glyph choice.

Below is a tested sketch (pure `math`/`random`, no UI) and its real output at 80 columns, 40000 samples, in y-up world space with the flip applied only when computing the row. At the reference's 5600 samples a 96x44 grid is too sparse (only 1255 of 4224 cells get a glyph [calc]), so the grid size and the sample count have to be tuned together.

```python
import math, random

def fay(a):  # same maths as neon.py:18-20
    return math.exp(math.cos(a)) - 2*math.cos(4*a) + math.sin(a/12)**5

def glyph(theta):                       # orientation, y-up, folded to [0, pi)
    d = math.degrees(theta) % 180
    if d < 22.5 or d >= 157.5: return "-"
    if d < 67.5:  return "/"
    if d < 112.5: return "|"
    return "\\"

def render(cols, rows, n, seed=12):
    rng = random.Random(seed)
    pts = sorted(((rng.uniform(0, 2*math.pi), rng.uniform(3, 92)) for _ in range(n)),
                 key=lambda p: p[1])
    sx = 560 / cols; sy = 2 * sx        # cells are ~2x taller than wide
    grid = {}
    for a, s in pts:
        r = fay(a) * s
        x, y = r*math.sin(a), r*math.cos(a)
        th = math.atan2(y, x) + rng.uniform(-0.18, 0.18)
        c = int(cols/2 + x/sx); ro = int(rows/2 - (y - 31)/sy)
        if 0 <= c < cols and 0 <= ro < rows:
            grid[(c, ro)] = (glyph(th), s)   # painter's order: last write wins
    return grid
```

Output of `render(80, 38, 40000)` (1287 of 3040 cells inked):

```
      \ \\\\\                                                      //// //
   \\\\\\\\\\\\\\\                                            //////////////
  \\\\\\\\\\\\\\\\\\\                                       //////////////////
 \\\\\\\\\\\\\\\\\\\\\\\                                 /|///////////////////
 \\\\\\\\\\\\\\\\\\\\||\|\                            /|///////////////////////
 \\\\\\\\\\\\\\\\\\||\\|||\\                         |////|///////////////////
  \\\\\\\\\\\\\\\\\\\\\\|\\\\|                     ||/////////////////////////
   \\\\\\\\\\\\\\\\\\\\\\\|\|||                  |||||/|/////////////////////
    \\\\\\\\\\\\\\\\\\\\\|\\|\|\               |||/|/|///////////////////////
    \\\\\\\\\\\\\\\\\\\\\\\||\|\|\             |/|/////////////////////////
     \\\\\\\\\\\\\\\\\\\\\\\\||\\\|   ||||   /||/||///////////////////////
       \\\\\\\\\\\\\\\\\\\\\\|||\|||  ||||| |||||///////////////////////
         \\\\\\\\\\\\\\\\\\\\|\\\||\||||||||||//|//////////////////////
           \\-\\-\\\\\\\\\\\\\\|\\\|||||||||/|//////////////////--///
             \\--\\\\\\\\\\\\\\\\|||||||||||||/|///////////////////
               -\-\-\\-\\\\\\\\\\\\||||||||||////////////////--//
                 \--\\\\\\\\\\\\\\||\|||||||////////////////-/
                    \\\--\\\\\\\\\\\\|||||||///////--/-----/
                        \-\--\--\\\\|\|||/||////////----
                           ----\---\\|\|||//-//--//--
                          --------\----\|--/----------
                          -------------|--------------
                               /---/-|//\|\--\--\
                            ///--///|/|  |\\\\\\--\-
                         --//-///////|    \\|\\\\\-\-\\
                       //-/////////||      |\\\\\\\\\-\\\
                    ///-////////////        ||\\\\\\\\\\\-\
                   ///////////////           |\\\\\\\\\\\\\\\
                  ////////////|//              \|\\\\\\\\\\\\\\
                /////////////|/                  |\\\\\\\\\\\\\\
                /////////////                      \\\\\\\\\\\\\
               /////////////                         \\\\\\\\\\\\
                ////////                               \\\\\\\\\
                   /                                        \\
```

The upper wings are large, the lower wings smaller and the body is a column of `|`. The starburst reads as a butterfly.

### 8.2 Choose stroke glyphs by direction

A line has an orientation but no arrow, so fold the stroke angle into [0, 180 degrees) and bin it into the four octant pairs:

| Orientation (y-up, degrees, modulo 180) | Glyph |
|---|---|
| near 0 | `-` |
| about 45 | `/` |
| near 90 | `\|` |
| about 135 | `\` |

Notes:

- **Flip order matters.** If you compute the angle after flipping to screen coordinates (y down), `/` and `\` swap. Keep angles in y-up space as the reference does, flip only for the row.
- **Calibrate to the font.** On a 1:2 cell, if the glyph spans the cell, `/` and `\` draw at roughly 63 and 117 degrees, not 45 and 135. Bin edges can be moved to match the font, or extra glyphs (`'`, `.`, `,`, `_`, `~`) can be used for in-between angles.
- **Closed-form texture.** In the reference, direction is `atan2(y - OY, x)` plus jitter, which is the polar angle of the position from the pivot. So the whole starburst texture can be computed per cell as `glyph(atan2(cell_y, cell_x) + jitter)`, with no strokes stored at all. In the preview above, the four wing quadrants (upper-left, upper-right, lower-left, lower-right) fall out as `\`, `/`, `/`, `\` automatically.
- **Strokes shorter than a cell.** The reference's 3 to 8 px strokes are well under one cell at typical grid sizes, so one glyph per stroke at its start point is enough. Longer strokes could walk the cells they cross (Bresenham style).
- **Density ramp.** For fill instead of lines (the envelope paper, soft shadows), a count-to-glyph ramp like `" .:-=+*#%@"` gives texture and shading. For paper grain use a sparse seeded scatter of `.` `'` `,`.

### 8.3 Colour bands as CSS spans, with a real neon glow

- Reuse the reference's structure: a function `colour(scale)` that picks a band, interpolates, and eases the last band with smoothstep. Run it once per cell and quantise the result to 16 to 32 steps. Emit CSS classes `.c0 ... .c31`, with colours defined as custom properties on `:root`, instead of an inline `style` on each span.
- Merge consecutive cells with the same class into one `<span class="cN">...</span>` (run-length encoding per row) to keep the DOM small.
- Real glow, which the reference cannot do: `text-shadow: 0 0 4px currentColor, 0 0 12px currentColor`. Thousands of text shadows are expensive, though. A cheaper pattern is two stacked layers: the crisp `<pre>`, plus a copy underneath with `filter: blur(3px)` and `mix-blend-mode: screen` (one filter on one big element).
- Use `font-variant-ligatures: none` and `line-height: 1` so glyph runs stay on a strict grid.
- Keep the background near-black with a hint of blue, like `#03030b` (`neon.py:7`).
- **Contrast.** The outer purples (`#8e1cb5` at 2.9:1, `#3d066b` at 1.4:1, section 5.2) are fine for decoration but must never carry letter text. Any actual words should use the cyan or blue stops (4.6:1 to about 15:1), or plain off-white.
- Honour `prefers-reduced-motion`. Skip the animation and show the final frame.

### 8.4 Progressive reveal sorted by radius (the ASCII draw-in)

The key trick to copy is "the sort is the animation" (`neon.py:55`):

1. Build the finished grid up front.
2. For each cell, record the **scale** of the stroke that owns it. Cells are then ordered by that scale ascending, which is inner to outer.
3. On each animation frame, reveal the next `k` cells from that ordered list, where `k = ceil(total / (fps * seconds))`. That gives a bloom of, say, 1 to 2 seconds instead of 5601 separate ticks.
4. A frontier flourish: cells revealed in the last few frames render as bright hot glyphs (`@`, `#`) in the cyan-white stop, then settle to their final glyph and colour. This echoes the way the reference's cyan core is brightest.
5. Ease the pace (for example, `k` larger in the middle of the animation) if linear feels mechanical. The reference has none, so this is optional.

Since colour is a function of scale and time is a function of scale, the sweep from cyan to purple is automatic, with no separate colour animation.

### 8.5 Reusing the band-gradient approach elsewhere

- **Gradient helper.** A single `gradient(stops, bands, t)` function covers everything: stops as RGB floats, band edges, optional smoothstep per band. The butterfly is just one use of it.
- **Heart.** The same nested-copies trick works for any closed parametric curve. A heart (`x = 16 sin^3 t`, `y = 13 cos t - 5 cos 2t - 2 cos 3t - cos 4t`) scaled over a range, sorted by scale and coloured magenta to purple, would grow in the same way and rhyme visually with the butterfly.
- **Envelope.** Colour by distance from the seal or from the top flap edge, giving a gradient across the paper in ASCII texture.
- **Buttons.** Colour set from the palette, with a small glyph frame (`[ ]`, `< >`). On hover or focus, shift the gradient parameter, increase the glow radius, or change the glyph density. Keep the palette as CSS variables so Python only chooses class indices.
- **Consistency.** Use the same four stops and near-black background everywhere, so the page feels like one piece.

### 8.6 Performance notes for a browser Python runtime (Pyodide, PyScript, Brython and similar)

- **The maths is cheap and the DOM is the cost.** The reference needs about 28 000 random draws and 5600 curve evaluations (section 7), which is trivial. What is slow in a browser is touching the DOM. Do the maths once, keep the grid in Python lists or a dict, and write to the DOM in large batches.
- **One DOM write per frame, or per row.** Build whole-row strings in Python and set `textContent` / `innerHTML` for the rows that changed (at most a few dozen rows). Avoid one element per character. Crossing the Python-to-JS boundary costs per call, so make few, large calls.
- **Drive frames with `requestAnimationFrame`**, not a zero-delay timer. The reference's `after_idle` loop has no frame budget, and a browser needs one. Cancel the loop on page hide and on unload.
- **Determinism.** Pyodide runs CPython, so `random.Random(12)` should reproduce the same samples as the reference. Other runtimes (Brython, MicroPython under PyScript) may have different `random` implementations, and some lack `random.Random`. Check before relying on identical output. If exact reproducibility matters, precompute offline and ship the result as data.
- **Startup.** Loading a WASM Python runtime is a noticeable one-off download and start-up delay. Show a static ASCII placeholder immediately. If the page does not strictly need the runtime at view time, the build could run the Python and emit pre-rendered frames as static JSON or text. Whether that fits "written in Python" is our call.
- **Layout.** Choose `cols` from the viewport width and set `font-size` with `clamp()` so the grid fits phones with no horizontal scroll. Recompute the grid on resize, debounced. Keep `contain: layout paint` and a fixed `<pre>` height to avoid reflow while frames update.
- **Accessibility.** Mark decorative art `aria-hidden="true"`. If the art carries meaning, give it `role="img"` and an `aria-label`. Provide a way to skip or stop the animation.
- **Measure.** I have not benchmarked any of this. Check span counts, paint time and frame time on a mid-range phone.

---

## 9. Key takeaways

1. The whole program is a **generator of stroke tuples plus a one-stroke-per-tick timer**. All the art logic is in `artwork()` (`neon.py:49-97`). The drawing function `segment` is five lines.
2. **The sort is the animation.** Sorting samples by scale (`neon.py:55`) makes the picture bloom from the centre outward, and ties colour, size and time together with one variable.
3. **One lap of Fay's curve, scaled many times** (`scale` in [3, 92], `neon.py:52`), replaces Fay's six-lap structure. Nested copies fill the wings. Sample density falls as 1/(s r^2), so the centre is dense and the rim is soft.
4. **Strokes point radially from the pivot** (`atan2(y - OY, x)` plus a small jitter, `neon.py:61-64`). That gives the fur-like texture, and in a glyph grid it maps directly onto `- / | \`.
5. **Colour is a pure function of scale**: cyan to blue (below 41), blue to magenta (41 to 74), magenta to purple with smoothstep (74 to 92). The extreme stops are never fully reached, and the outermost purple is nearly invisible (1.4:1).
6. **Do the maths in y-up and flip once at the end** (`neon.py:42`).
7. **The "glow" is fake**: saturated thin lines on a dark ground. The browser can do real glow with CSS, so we can beat the reference there.
8. **Latent bugs and oddities to avoid copying:** `t.TclError` does not exist in the `turtle` namespace (`neon.py:111`), `t.Terminator` is dead code here, `tracer(0)` does nothing without Turtle objects, the README lists `tkinter` which the code never imports, and the README's code fence is unclosed.
9. **No licence file**, so we re-implement from understanding and use our own constants and code.
10. For the port: pre-compute the grid, reveal it in batches per animation frame, write the DOM in few large calls, run-length-encode colour spans and keep the palette in CSS variables.
