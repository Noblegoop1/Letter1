# loveYou (iremcnar) - how the reference program works

| | |
|---|---|
| Source | https://github.com/iremcnar/loveYou |
| Commit | `ee7be9ecf785be6556fa75a4a58583a6171f6180` (shallow clone, dated 2026-10-09; the README screenshot filename also carries 2026-10-09) |
| Local copy | `reference/loveyou/` - `love.py` (274 lines, CRLF, no trailing newline), `README.md` (18 lines), `.gitattributes` (`* text=auto`). No `.git` directory was kept, so the hash cannot be re-verified from the folder itself. |
| Licence | **None.** The repo has no `LICENSE` file and `love.py`/`README.md` carry no licence or copyright header. Default copyright applies: nobody has been granted the right to copy, modify or redistribute it. See section 7.9 for what that means for us. |
| Dependencies | Python standard library only: `math`, `random`, `turtle`, `tkinter.font` (`love.py:1-4`) |

**Summary.** `love.py` opens an 800x800 dark window and fills a heart silhouette with the words "I love you" in 20
languages, set in bold Arial at four sizes. The silhouette is a parametric heart curve; the text is placed row by
row by intersecting each text row with the curve's scanline spans, packing phrases greedily, then stretching each
row so it ends flush against the right edge. Phrases are coloured from deep wine (centre) to bright crimson
(rim) and spawn over about 10 seconds: first the first/last phrase of every row (which reads as the outline,
clockwise from the top notch), then the interior from the outside in. Each phrase drifts down ~34 px with a cubic
ease-out, gains a soft shadow and halo, and flashes pale pink as it lands. When everything has landed, random
phrases flicker pale pink forever.

**Evidence tags used below.** `love.py:N` = read directly in the source. *[stdlib]* = checked in this machine's
Python 3.14.0 `Lib/turtle.py`. *[replica]* = numbers from my own re-typing of the geometry in a scratch script
(it never imports or runs `love.py`). *[est]* = estimate or general Tk/browser knowledge that is not in the repo.

---

## 1. Files in the repo

`love.py` is the whole program (one module, no classes). `README.md` lists the features (20 languages, "exact scanline
boundaries", cubic ease-out, shimmer, zero dependencies; `README.md:3-13`) and links a screenshot. Its run snippet
(`README.md:17-18`) opens a code fence that is never closed. `.gitattributes` only sets `* text=auto`. The README
says "exact" boundaries, but they come from a 720-point polygon of the curve (`love.py:70`).

## 2. How to run, dependencies, window setup

```
python love.py        # README.md:18
```

* Needs a Python 3 with `tkinter` (python.org builds include it; some Linux distros ship it separately) *[est]*.
  `yield from` (`love.py:100`) means Python 3.3 or newer.
* The look assumes the system has **Arial** (`FONT`, `love.py:14`); if not, Tk substitutes a font and every
  measurement in `build()` changes with it *[est]*.
* Everything blocks in Tk's event loop: `t.done()` (`love.py:272`) is turtle's alias of `mainloop`
  *[stdlib: turtle.py:4105, 792-805]*.

Window and canvas setup (`love.py:17-24`):

```python
s = t.Screen()          # turtle singleton screen -> creates the Tk root window
s.setup(800, 800)       # window size in pixels
s.bgcolor(BG)           # "#060208", near-black purple
s.title("Love Heart")
s.tracer(0)             # turtle auto-redraw off
cv = s.getcanvas()      # the raw canvas
rng = r.Random(11)      # ONE seeded RNG shared by layout, colours, drift, shimmer
```

What each piece really does:

* **turtle is only a window factory.** The only turtle names used are `Screen`, `done`, `Terminator`
  (`love.py:17, 272-273`). No `Turtle` object is ever created, so `tracer(0)` is effectively inert here
  *[est: defensive leftover]*. It only governs turtle's own pen drawing.
* **`getcanvas()`** returns turtle's `ScrolledCanvas` *[stdlib: turtle.py:1338-1348]*. That class forwards every
  public `tkinter.Canvas` method to its inner canvas *[stdlib: turtle.py:306-326, 426]*, which is why the script can
  call `cv.create_text`, `cv.itemconfig`, `cv.coords` (and `cv.after`, inherited from Tk's `Frame`) directly.
* **Coordinates.** turtle sets the canvas scroll region to `(-w/2, -h/2, w/2, h/2)` *[stdlib: turtle.py:367, 485]*,
  so canvas (0, 0) is the window centre. Tk's y axis points *down*; turtle flips y itself when it draws
  *[stdlib: turtle.py:509, 540, 722]* but raw canvas calls do not, so the script keeps all layout maths in
  y-up "maths" coordinates and flips exactly once, in `spawn`: `y = -p["y"]` (`love.py:182`).
* **Text is the only primitive.** `create_text` (`love.py:187-189`) is the only drawing call in the file. No lines,
  polygons or images exist; the heart is "drawn" purely by where words sit. This is why it is a good style
  reference for an all-text page. Tk's default text anchor is `center` *[est]*, so every stored `x`/`y` is a word's centre.
* **Fonts** are measured with `tkinter.font.Font` objects created with `root=cv` (`love.py:39-41`) but *drawn* with
  tuple font specs `(FONT, size, "bold")` (`love.py:184-185`). Same family/size/weight, so measured width equals drawn width.

## 3. Architecture map and data flow

```
 constants        window+canvas      heart(a)         POLY (720 pts)      EDGES / YMAX / YMIN / CY
 love.py:6-15 --> love.py:17-24 -->  love.py:45-53 --> love.py:70      --> love.py:71-74
                                                                              |
   +--------------------------------------------------------------------------+
   v
 build()  love.py:103-164  (called once at import time, line 229)
   |  rows: y = YMAX-half, step row_h while y > YMIN+half           (109-110, 148)
   |  per row: intersect(spans(y+half), spans(y-half))               (111; spans 77-83, intersect 86-93)
   |  per span: inset 4 px, jitter <= 8 px, greedy pack (<=10 tries) (113-132)
   |  justify leftover space, flag first/last as "edge"              (137-146)
   |  colour by normalised radius (math_dist 167-168)                (150-158)
   |  edges sorted by angle, inner sorted by radius                  (160-164)
   v
 ORDER (list of dicts) --> items = iter(ORDER), RATE = N / 625       love.py:229-233
   v
 step()  love.py:236-252   every TICK=16 ms
   |  acc += RATE; while acc >= 1: spawn(next(items))                (238-243)
   |  animate() every live word; drop finished ones                  (247)
   v  when spawning is over and nothing is animating
 shimmer()  love.py:262-267  every 140 ms, one random word pale for 260 ms, forever
```

Import-time order (everything above `step` runs before the first frame): constants -> Screen -> RNG -> `PHRASES`
-> helper defs -> `POLY/EDGES/YMAX/YMIN/CY` (70-74) -> `FLASH`, `main_ids`, `active` (171-173) -> `BGC` (228) ->
`ORDER = build()` (229) -> `items`, `RATE`, `acc`, `spawning` (230-233) -> `cv.after(200, step)` + `t.done()` (271-272).
`build` calls `math_dist` (defined later, line 167) and `animate` uses `math_sin`/`BGC`; that works because Python
resolves globals at call time and the first call happens after all definitions.

The per-phrase record is a plain `dict` that grows as it moves through the pipeline:

| Stage | Fields added | Lines |
|---|---|---|
| placement | `x` (centre, px), `y` (row centre, y-up), `text`, `size`, `edge` | 146 |
| colour | `color` (r,g,b floats), `rad` | 157-158 |
| spawn | `shadow`, `halo`, `main` (Tk item ids), `f` (frame counter), `dx` (drift) | 191-192 |

## 4. Constants

| Name | Line | Value | What it controls |
|---|---|---|---|
| `SC` | 6 | 21 | Pixels per curve unit. Heart is 32 units wide -> 672 px wide (x from -336 to +336). |
| `OY` | 7 | 20 | Vertical shift of the whole curve, in px, added in `heart()` (53). |
| `DURATION` | 8 | 10 | Nominal seconds for the spawn phase. Only used in `RATE` (231). |
| `TICK` | 9 | 16 | ms between `step()` calls (252) and the unit for `RATE`. ~62 Hz nominal. |
| `ANIM` | 10 | 42 | Frames each phrase animates (199): 42 x 16 ms = 672 ms nominal. |
| `LIFT` | 11 | 34 | Start offset in px: a phrase begins 34 px higher than its slot (189, 203). |
| `GAP` | 12 | 7 | Minimum px between neighbouring phrases (132). |
| `SIZES` | 13 | (9,10,11,12) | Point sizes picked at random per phrase (123); the tallest sets the row height (105). |
| `FONT` | 14 | "Arial" | Family for measuring and drawing; weight is always bold. |
| `BG` | 15 | "#060208" | Window bg (19), the fill of not-yet-visible items (187-189), and `BGC` (228). |

Other hard-coded magic numbers worth knowing: seed `11` (24), 720 samples (70), min span 14 px (91), row leading
+4 (105), span inset 4 px (114-115), start jitter 0-8 px (116), 10 placement tries (121), ellipse radii
`16*SC` / `14.5*SC` (168), colour mix constants (150-156), sort jitter 0.08 (163), horizontal drift +-10 px (192),
shadow offset (+2,+3) and halo size +1 (185-187), shadow/halo brightness 0.30/0.20 (207-208), flash peak 0.75 and
window 0.55-1.0 (211), shimmer 0.6 / 260 ms / 140 ms (265-267), first frame after 200 ms (271).

Derived values *[replica]*:

| Name | Value | Meaning |
|---|---|---|
| `YMAX` | 270.39 | Lobe tops, at a = +-52 deg (sample indices 104 and 616 of 720), x = +-164.4 |
| `YMIN` | -337.0 | The bottom tip (a = pi) |
| `CY` | -33.31 | Vertical middle of the shape; origin of `math_dist` and of the edge-angle sort |
| Notch (a=0) | (0, 125) | The cleft between the lobes |
| Widest point | (+-336, 104) | a = pi/2 |
| `BGC` | (0.0235, 0.0078, 0.0314) | `BG` as 0-1 floats (228) |
| `RATE` | N / 625 | Spawns per tick (231); N = number of phrases the layout produced |

So the heart is 672 x 607 px inside an 800 x 800 window, and `FLASH = (1.0, 0.78, 0.78)` (171) is the pale pink used by
both the landing flash and the shimmer.

### The phrase list (`love.py:26-32`)

20 distinct strings, all NFC *[checked with `ast.literal_eval` on the PHRASES node, nothing executed]*. 9 are pure ASCII
(marked A), 11 are not. The language names are mine, not in the source; have native speakers check them before the
letter ships.

| # | Phrase | Language | A | Notes |
|--:|---|---|:-:|---|
| 1 | I love you | English | A | |
| 2 | Seni seviyorum | Turkish | A | |
| 3 | Te amo | Spanish | A | also valid Portuguese |
| 4 | Je t'aime | French | A | contains an apostrophe |
| 5 | Ich liebe dich | German | A | |
| 6 | Ti amo | Italian | A | |
| 7 | Eu te amo | Portuguese | A | |
| 8 | Я тебя люблю | Russian | | Cyrillic |
| 9 | 사랑해 | Korean | | 3 Hangul syllables, wide (2 cells each); informal register |
| 10 | 愛してる | Japanese | | 4 chars, wide; casual |
| 11 | 我爱你 | Chinese (Simplified) | | 3 chars, wide |
| 12 | मैं तुमसे प्यार करता हूँ | Hindi | | 24 code points, 9 are combining marks; "करता" is the masculine-speaker form |
| 13 | Σ' αγαπώ | Greek | | |
| 14 | Ik hou van jou | Dutch | A | |
| 15 | Jag älskar dig | Swedish | | `ä` |
| 16 | Kocham cię | Polish | | `ę` |
| 17 | ฉันรักเธอ | Thai | | 9 code points, 2 combining marks |
| 18 | Anh yêu em | Vietnamese | | "anh ... em" is a male-to-younger/female address pair |
| 19 | Aku cinta kamu | Indonesian | A | |
| 20 | Я тебе кохаю | Ukrainian | | |

Average length is 10.25 code points (range 3 to 24).

## 5. Every function

### 5.1 Small helpers

* `font_for(size)` (37-42): memoised `tkinter.font.Font(family="Arial", size=size, weight="bold")` per size in `_fonts`.
  Used only for **measuring** (`metrics("linespace")` line 105, `measure(text)` line 124).
* `hx(c)` (56-59): float RGB -> `"#rrggbb"`. Clamps each channel to [0,1], multiplies by 255 and **truncates** with `int`
  (so 0.9 -> 229 = `e5`, not 230).
* `mix(a, b, k)` (62-63): per-channel lerp `p + (q - p) * k`. `k` is not clamped; all callers stay in range.
* `dim(c, k)` (66-67): scales a colour towards black.
* `clamp(v)` (177-178): `max(0, min(1, v))`.
* `math_sin(v)` (224-225): `sin(pi * v)`, a 0 -> 1 -> 0 bump over v in [0,1] (it is `sin(pi * v)`, not plain `sin(v)`).

### 5.2 `heart(a)` - the parametric curve (45-53)

```
x(a) = 16 * sin(a)^3
y(a) = 13 cos a - 5 cos 2a - 2 cos 3a - cos 4a
returns ( x * SC , y * SC + OY )          # y-up, pixels
```

Landmarks *[replica]*: a=0 -> (0, 125) the notch (13-5-2-1 = 5 units); a=pi/2 -> (336, 104) widest; a=pi -> (0, -337)
the tip (-13-5+2-1 = -17 units); lobe tops at about (+-164.4, 270.4). The curve is a simple closed loop, symmetric
about x = 0, so the even-odd rule below is safe.

### 5.3 Polygon sampling (70-74)

```
POLY  = [ heart(2*pi*i/720) for i in 0..719 ]          # 0.5 degree steps
EDGES = pairs (POLY[i], POLY[i+1]) with the last wrapping to POLY[0]   # 720 edges
YMAX, YMIN = max / min of POLY y ;  CY = (YMAX + YMIN) / 2
```

A closed polygon of 720 straight edges stands in for the curve, so a scanline test is a loop over plain segments.
`YMAX`/`YMIN` are the max/min of the *samples*, which matters in `build()` (see 5.7).

### 5.4 `spans(y)` - scanline fill via even-odd crossings (77-83)

```
for each edge (x1,y1)->(x2,y2):
    if  y1 <= y < y2   or   y2 <= y < y1:            # half-open: [low, high)
        xs.append( x1 + (y - y1) * (x2 - x1) / (y2 - y1) )   # linear interpolation
sort(xs)
return [ (xs[0],xs[1]), (xs[2],xs[3]), ... ]          # pair them up
```

* The half-open test `low <= y < high` counts a shared vertex once where the curve passes through it, and zero or
  two times at a local peak/trough, so crossings stay paired. A horizontal edge can never satisfy it, so the
  division by `y2 - y1` never sees zero.
* Sorted crossings alternate "enter, leave, enter, leave", hence pairs `xs[0::2]`, `xs[1::2]` (83) are the inside
  intervals. At most two intervals exist here: one below the notch, two above it.
* *[replica]* `spans(0)` -> `[(-302.8, 302.8)]`; just above the notch (y = 135) -> `[(-332.9, -1.2), (1.2, 332.9)]`;
  at exactly `YMAX` -> `[]`, because the peak vertices fail `y < y2`.

```
 y = 135      (-332.9 .. -1.2)   (1.2 .. 332.9)      two spans: left lobe, right lobe
 y = 125      ----- notch vertex: spans merge -----
 y =   0              (-302.8 .. 302.8)               one span
```

### 5.5 `intersect(A, B)` (86-93)

```
for a in A, for b in B:
    lo = max(a.lo, b.lo) ;  hi = min(a.hi, b.hi)
    keep (lo, hi) if hi - lo > 14
```

`build()` calls it with the spans at the **top** and the **bottom** of a text row (`y + half`, `y - half`, line 111).
A word may only sit where both lines are inside the heart, so the text box's corners stay inside the silhouette.

* Across the notch: top line has two spans, bottom line has one -> two results (one per lobe); the V-shaped notch is
  widest at the top line, so the result never pokes into the cleft.
* Only two heights are sampled; if the outline bulged inward between them the box could clip, but with ~22 px rows on
  this smooth curve the error is small *[est]*.
* The 14 px threshold is only an early filter: after the 4 px insets (114-115) a 14 px span leaves 6 px, and the
  narrowest phrase is far wider, so such spans end up empty anyway (134-135).

### 5.6 `phrase_cycle()` (96-100)

```python
while True:
    order = PHRASES[:]; rng.shuffle(order); yield from order
```

An infinite generator: shuffle all 20, hand them out one by one, reshuffle. Seeded by `Random(11)`, so the order is
reproducible. **Quirk:** `build()` pulls from this generator even for candidates that then fail to fit, and a failed
candidate is *dropped*, not returned (see 5.7). The "each language once per pass" guarantee therefore holds for draws,
not for what ends up on screen.

### 5.7 `build()` - rows, packing, justification (103-164)

**Row height (105-106).** `row_h = max(linespace of each size in SIZES) + 4`, `half = row_h / 2`. Every row uses the
same height (the 12 pt metric plus 4 px). I did not measure it; at 96 dpi it is probably about 22-23 px *[est]*.

**Row loop (109-110, 148).** The first row centre is `YMAX - half` (its top edge exactly on `YMAX`) and the loop
steps `y -= row_h` while `y > YMIN + half`. *[replica]* With `row_h` = 22 that is 27 rows (31 text spans), with 24 it
is 25 rows (29 spans). Because `spans(YMAX)` is empty (5.4) the **first row is always empty**.

**Per span (113-117).** `lo += 4; hi -= 4` insets both ends. `cur = lo + rng.uniform(0, 8)` is a random left start so
rows do not share a left margin. `line = []` collects `[centre_x, text, size, width]`.

**Greedy packing (119-132).**

```python
while True:
    fit = None
    for _ in range(10):                      # up to 10 candidates
        text = next(cycle); size = rng.choice(SIZES); w = font_for(size).measure(text)
        if cur + w <= hi: fit = (text, size, w); break
    if not fit: break                        # 10 misses in a row -> row is done
    line.append([cur + w/2, text, size, w])
    cur += w + GAP
```

Each attempt draws a **new phrase and a new random size**, so a long phrase that does not fit is not retried at a
smaller size. The last iteration of every span *always* ends in 10 misses (it is the only way out of `while True`),
so at least 10 draws are thrown away per span. *[replica + est]* About 30 spans -> 300+ discarded draws against
roughly 100-130 placed phrases. The result is biased towards short phrases ("Te amo", "Ti amo", "我爱你") because
those are what fit into the small leftover at line ends. If no phrase fits at all, `line` is empty and the span is
skipped (134-135).

**Justification (137-142).**

```
left = hi - (right edge of last item)            # >= 0 because every item satisfied cur + w <= hi
item_i.x += left * i / (n - 1)                   # first item stays, last moves by `left`, others linearly
```

The last item's right edge lands exactly on `hi`; the gaps become `GAP + left/(n-1)`. A one-item span is centred
instead: `x = (lo + hi) / 2` (142). The left edge keeps the 0-8 px jitter, the right edge is flush.

**Edge flag (144-146).** The first and last item of every span get `edge=True`. That is up to two per span (one if
the span holds a single phrase), so roughly half of all phrases are "edge" phrases *[est: ~4 phrases per span]*;
they are not a thin outline but the left and right end of every row.

**Colour grading (150-158).**

```
wine    = (0.58, 0.00, 0.09)     crimson = (0.90, 0.05, 0.14)     blood = (0.98, 0.10, 0.16)
rad  = min(1, hypot( x / (16*SC) , (y - CY) / (14.5*SC) ))          # math_dist, 167-168
base = mix(wine, crimson, 0.25 + 0.75 * rad)
k    = uniform(0, 0.35) + (0.30 if edge else 0)
color = clamp01( mix(base, blood, k) )
```

* `math_dist` is a normalised **ellipse radius** centred on `(0, CY)` with semi-axes 336 px and 304.5 px. These match
  the heart's half-width (336) and half-height (303.7) *[replica]*. 0 at the middle, 1 on the ellipse through the
  widest point and the top/bottom of the bounding box, then clamped at 1. Outline points reach 1.19 (lobes),
  1.10 (widest), 1.0 (tip) and only 0.52 (the notch) *[replica]*, so notch-side words stay darker.
* Resulting hex *[replica, using `hx`]*: an inner phrase at the centre is `#a8031a` to `#c40a1f`; an edge phrase on the
  rim (`rad` 1) is `#eb1025` to `#f21527`. Dark wine in the middle, glowing crimson on the rim, random sparkle on top.
  The colour RNG calls happen in placement order after all layout draws, so changing the layout changes the colours too.

**Draw order (160-164).**

```python
edges = [p for p in placed if p["edge"]];  inner = the rest
edges.sort(key = atan2(x, y - CY) mod 2*pi)      # angle from straight-up, clockwise
inner.sort(key = -rad + uniform(0, 0.08))        # biggest radius first, with jitter
return edges + inner
```

`atan2(x, y - CY)` has x as its first argument, so the angle is 0 straight up, pi/2 to the right, pi at the bottom,
3pi/2 to the left *[replica: 0.017, 1.571, 3.142, 4.712]*; the `% 2*pi` wraps negatives. Edges therefore appear
sweeping **clockwise from the top notch**, then the interior fills **outside-in** (`-rad` ascending = rad descending;
the jitter shuffles near-equal radii, and every phrase with `rad` clamped to 1.0 is tied until the jitter breaks it).
`key=` is evaluated once per element, so the jitter is fixed during the sort.

### 5.8 `spawn(p)` (181-194)

```python
x, y = p["x"], -p["y"]                               # flip to canvas coords (y down)
shadow = cv.create_text(x + 2, y + 3,    text, font=(FONT, size,   "bold"), fill=BG)
halo   = cv.create_text(x,     y,        text, font=(FONT, size+1, "bold"), fill=BG)
main   = cv.create_text(x,     y - LIFT, text, font=(FONT, size,   "bold"), fill=BG)
p.update(shadow=shadow, halo=halo, main=main, f=0, dx=rng.uniform(-10, 10))
main_ids.append((main, c));  active.append(p)
```

* Three Tk text items per phrase, all initially filled with the background colour (invisible).
* Z-order is creation order: shadow under halo under main. Later phrases are created later, so on any overlap a newer
  phrase's shadow/halo sits above an older phrase's main text.
* `main` starts at `y - LIFT`: in canvas coordinates that is **34 px higher on screen**, so phrases *settle downward*
  (the README calls it a "float-in"; it is a downward settle). `dx` is a random +-10 px sideways offset that also decays.
* `main_ids` keeps `(item id, final colour)` forever; shimmer picks from it.

### 5.9 `animate(p)` (197-221)

Called once per tick for each live phrase; returns `True` to stay active, `False` when done.

```
f += 1 ;  u = clamp(f / ANIM)                 # progress 0..1 over 42 frames
e = 1 - (1 - u)^3                             # cubic ease-out
px = x + dx * (1 - e)    ;   py = y - (1 - e) * LIFT          # canvas coords, y down
shadow.fill = mix(BGC, 0.30*c, e)             # fades in; NOT moved - it waits at (x+2, y+3)
halo.fill   = mix(BGC, 0.20*c, e*e)           # fades in slower; moves with the word
flash       = 0.75 * sin(pi * clamp((u - 0.55) / 0.45))      # zero until u=0.55, peak at u=0.775
main.fill   = mix( mix(BGC, c, e^1.5), FLASH, flash )
main/halo.coords = (px, py)
if u >= 1: snap halo & main to (x, y); main.fill = c; return False
```

*[replica]* values over the 42 frames:

| frame f | e (position/ease) | hover left (px) | drift left | main brightness e^1.5 | flash |
|--:|--:|--:|--:|--:|--:|
| 1 | 0.070 | 31.6 | 0.93 | 0.02 | 0 |
| 7 | 0.421 | 19.7 | 0.58 | 0.27 | 0 |
| 14 | 0.704 | 10.1 | 0.30 | 0.59 | 0 |
| 21 | 0.875 | 4.2 | 0.12 | 0.82 | 0 |
| 28 | 0.963 | 1.3 | 0.04 | 0.95 | 0.55 |
| 32 | 0.987 | 0.5 | 0.01 | 0.98 | 0.75 (peak) |
| 35 | 0.995 | 0.2 | 0.00 | 0.99 | 0.69 |
| 42 | 1.000 | 0 | 0 | 1.00 | 0 |

Reading it: cubic ease-out is fast then slow, 70% of the travel is done by frame 14 of 42. The pale-pink flash
begins after the word has nearly stopped (frame ~24) and fades by frame 42, so each phrase "lands, then glints".
Brightness uses `e^1.5` (slower than position), halo uses `e^2` (slower still), which staggers the layers.
Spawn (243) and the first `animate` (247) run in the same `step()` call, so the halo's creation position is probably
never painted, because Tk redraws only after the callback returns *[est]*.

### 5.10 The scheduler: `RATE`, `acc`, `step` (229-252)

```python
ORDER = build();  items = iter(ORDER)
RATE  = len(ORDER) / (DURATION * 1000 / TICK)       # N / 625 spawns per tick
acc   = 0.0

def step():
    global spawning, acc
    if spawning:
        acc += RATE
        try:
            while acc >= 1: acc -= 1; spawn(next(items))
        except StopIteration: spawning = False
    active[:] = [p for p in active if animate(p)]    # in-place, so no `global active` needed
    if not spawning and not active: shimmer(); return
    cv.after(TICK, step)
```

* The accumulator turns a fractional rate into whole spawns (see section 6).
* `StopIteration` is the "out of words" signal, caught inside a normal function so it is safe. It fires only when
  `acc` next reaches 1 *after* all words are out, i.e. up to `1/RATE` ticks (about 5 for N = 120) after the last spawn.
* `step` re-arms itself with `cv.after(TICK, step)` *after* its work (252); when the show is complete it hands over
  to `shimmer()` and does not re-arm.

### 5.11 `shimmer()` and `_safe` (255-267)

```python
def shimmer():
    for _ in range(1):                               # vestigial loop: runs once
        i, c = rng.choice(main_ids)                  # uniform over ALL phrases
        _safe(i, mix(c, FLASH, 0.6))                 # snap 60% towards pale pink (no easing)
        cv.after(260, lambda i=i, c=c: _safe(i, c))  # restore base colour 260 ms later
    cv.after(140, shimmer)                           # next glint in 140 ms
```

* One new glint every 140 ms (~7/s), each lasting 260 ms, so ~1.9 phrases glow at once on average (260/140).
* Only `main` items are touched, not halo or shadow. If the same phrase is picked twice within 260 ms the first
  restore cuts the second glint short; harmless.
* `lambda i=i, c=c:` binds the loop values immediately (avoids the late-binding closure bug).
* `_safe` (255-259) wraps `itemconfig` in `try/except Exception: pass`, presumably a guard against `TclError` if the
  canvas is gone when a pending timer fires *[est]*.

### 5.12 Start and shutdown (270-274)

```python
try:
    cv.after(200, step)      # first frame after 200 ms
    t.done()                 # mainloop; returns when the window closes
except (t.Terminator, Exception):
    pass
```

`Terminator` is itself an `Exception` subclass *[stdlib: turtle.py:850]*, so listing both is redundant: every error
raised by these two statements (typically a Tcl error when the window is closed) is swallowed. It does not cover the
callbacks: Tkinter reports exceptions inside `after` callbacks itself *[est]*. `ORDER = build()` (229) is outside this `try`.

## 6. Animation and timing model

Timeline for N phrases (illustration with N = 120; real N depends on font metrics, probably ~100-130 *[est]*):

```
t=0.0 s    ORDER is already built (229); first step() runs at 0.2 s (271)
0..625 tk  spawn: row-end phrases clockwise from the top notch, then interior outside -> in
           one phrase every 1/RATE = 5.2 ticks (~83 ms), ~8 animating at any moment (42 x 0.192)
~667 tk    last phrase lands (~10.7 s after the first step), then shimmer() forever
```

**Why the accumulator gives an even rate.** After `k` ticks `acc` has received `k * RATE` in total and given back one
unit per spawn, so

```
spawned(k) = floor(k * RATE)            (up to float rounding)
=> | spawned(k) - k * RATE | < 1         for every k   (never more than one phrase off a straight line)
=> spawned(625) = N                      all phrases are out after 625 ticks = DURATION
```

* Per tick the spawn count is `floor(RATE)` or `ceil(RATE)`: usually 0 or 1, and if N > 625 several (the `while`
  handles it). The spacing between spawns is as even as integers allow, with no randomness and no drift.
* `DURATION` fixes the *length* of the show, not the density: more phrases means a higher rate, not a longer show.
* Float rounding means tick 625 may emit N-1 and the last one lands a tick later; invisible.
* **It counts ticks, not time.** `step` re-arms *after* its work (252), so the real period is `TICK` + work + Tk timer
  granularity. "10 seconds" is therefore nominal and stretches on a slow machine. In a browser use elapsed time
  instead (7.7).
* Evenness is in the spawn *schedule*, not in the visual: since edges spawn first and sit on the rim, the picture
  grows from outline to centre rather than uniformly.

## 7. Porting to ASCII in the browser

What carries over: the geometry (curve -> polygon -> spans), word packing, colour by radius, the staggered spawn with
ease-out, the flash and the shimmer. What changes: no pixel measurement, no proportional fonts, no Tk item moves. We
work on a grid of character cells.

### 7.1 Rasterising the heart into a character grid (same scanline spans)

A cell is about twice as tall as wide, so scale x by an aspect factor, then reuse `spans`/`intersect` unchanged in
cell units (minimum span ~3 cells instead of 14 px). This is my own sketch, run in a scratch script, not repo code:

```python
import math, unicodedata

def cells(s):                              # display width of a string in monospace cells
    return sum(0 if unicodedata.category(c) in ("Mn", "Me", "Cf") else
               2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in s)

def heart_poly(rows, aspect=2.0, n=720):   # curve units -> (columns, rows)
    sy = rows / 28.92                      # curve is 11.92 - (-17) = 28.92 units tall
    sx = sy * aspect                       # cells are ~2x taller than wide
    return [(16*math.sin(a)**3 * sx,
             (13*math.cos(a) - 5*math.cos(2*a) - 2*math.cos(3*a) - math.cos(4*a)) * sy)
            for a in (2*math.pi*i/n for i in range(n))]
# row r: yc = ymax - (r + 0.5);  spans = intersect(spans(yc + 0.45), spans(yc - 0.45))
# per span: lo = ceil(lo) + 1; hi = floor(hi) - 1; pack words using cells(w) + 1 gap
```

Output for `rows = 22` (51 cells wide), seeded `Random(11)`, Hindi and Thai left out; first 12 of 17 filled rows:

```
        Σ' αγαπώ                I love you
     Ti amo  Σ' αγαπώ         Ti amo  Σ' αγαπώ
    Ich liebe dich          Я тебя люблю Ti amo
   Σ' αγαπώ       Ti amo   I love you   Σ' αγαπώ
  Ich liebe dich  Te amo   Ti amo 愛してる 사랑해
  Ik hou van jou  Я тебе кохаю  Eu te amo  Te amo
   Я тебя люблю   Kocham cię   Ti amo  Je t'aime
    Eu te amo  Ich liebe dich 我爱你 I love you
     Kocham cię Ti amo Aku cinta kamu 愛してる
      Ti amo Ich liebe dich Te amo I love you
        Я тебя люблю   Я тебе кохаю  我爱你
          Ich liebe dich Eu te amo 사랑해
   ... (5 more filled rows narrowing to the tip, then 5 blank rows)
```

Lessons: (1) the twin lobes and the taper fall out of the same maths; (2) the bottom ~5 rows come out blank because the
tip is narrower than the shortest phrase (6 cells), so narrow spans need a filler (short words, `<3`, repeated
fragments) or a taller grid; (3) CJK rows look ragged in many viewers, which is the width pitfall of 7.6, not a
rasteriser bug. Size the grid from the viewport and measure `aspect` from the real font (cell height / cell width)
rather than hard-coding 2.0.

### 7.2 Words as texture (heart, seal, letter body)

`spans` works for any closed polygon: the heart, a wax-seal circle (720 points of a circle) or the letter body can all
be filled with words, with a different word list per region. Keep the readable letter text as real, selectable text on
top of (or beside) the decorative fill.

### 7.3 Packing with cell widths

* Integer widths (`cells(w)`) make packing, `GAP` and justification exact integer maths: spread the leftover as whole
  spaces (`extra // gaps`, plus 1 on the first `extra % gaps` gaps).
* No `measure()` calls, so layout is identical on every machine and the seed is truly reproducible (the original's
  layout depends on the local Arial metrics, `love.py:105, 124`).
* Do not copy the discard-and-bias loop (5.7): put a non-fitting phrase back (`deque.appendleft`) and try the shortest
  remaining one, so all languages appear about equally often.
* The four `SIZES` become brightness/weight classes (dim, normal, bold); a character grid has one font size.

### 7.4 Per-character colour by radius

Keep `math_dist` (167-168) in cell units and quantise: `bucket = round(rad * 7)`, one CSS class per bucket
(`.c0` ... `.c7`) for the wine -> crimson ramp and a second set for the edge boost; the random 0-0.35 sparkle can pick a
neighbouring bucket. Emit one `<span>` per run of equal class (usually per word), not per character. 8-16 colours is
visually close to the continuous mix and keeps the DOM small.

### 7.5 Float-in, flash and shimmer

* **Order and start times:** reuse the draw order (outline clockwise, then interior outside-in); phrase `i` starts at
  `i / N * DURATION`.
* **Ease-out drop:** `u = clamp((t - start) / ANIM_SECONDS)`, `e = 1 - (1 - u)**3`. A grid has no sub-cell movement, so
  quantise: `row_offset = round((1 - e) * LIFT_ROWS)` (2-3 rows) and `col_offset = round(dx * (1 - e))`. If each phrase
  is an absolutely positioned `<span>`, CSS `transform: translate()` gives a smooth drop and the characters stay ASCII.
* **Fade-in without relying on colour:** dissolve through a glyph ramp: each character shows `.`, then `:`, then `+`,
  then its real glyph as `e` crosses its own random threshold (the ASCII analogue of `mix(BGC, c, e^1.5)`).
* **Shadow/halo:** a dim copy one cell right and down on a lower layer (only where the cell is empty). CSS `text-shadow`
  is simpler but is not an ASCII visual; decide whether the "all visuals are ASCII" rule covers styling.
* **Landing flash:** the same `sin(pi * v)` bump (peak 0.75) towards pale pink for `u` in 0.55-1, or a `.flash` class;
  pure ASCII: bracket the word with `*` for a few frames.
* **Shimmer:** keep `{word_index: ends_at}`; every ~140 ms pick a random word, light it for 260 ms, drop expired
  entries and re-render only those spans. ASCII variants: swap a letter for `*`/`+` briefly, or twinkle the gap cells
  (`.` -> `+` -> `*` -> `+` -> `.`). Honour `prefers-reduced-motion` (show the finished picture, no shimmer).

### 7.6 Multilingual text on a monospace grid - the wide-glyph pitfall

A string's `len()` is not its width in cells *[table computed with `unicodedata`]*:

| Phrase | Code points | Cells | Hazard |
|---|--:|--:|---|
| 사랑해 (Korean) | 3 | 6 | Hangul syllables are East Asian Wide (2 cells). NFD would give 7 jamo, so normalise to NFC. |
| 愛してる (Japanese) | 4 | 8 | Wide kanji and kana |
| 我爱你 (Chinese) | 3 | 6 | Wide |
| ฉันรักเธอ (Thai) | 9 | 7 base | Combining vowel/tone marks occupy no cell |
| मैं तुमसे प्यार करता हूँ (Hindi) | 24 | font-dependent | 9 combining marks plus conjunct shaping: glyph count differs from code-point count |
| Cyrillic, Greek, Vietnamese `ê` | 1 each | 1 | Unicode "Ambiguous" width: 1 cell in browsers, but 2 in some CJK-locale terminals |

These cell counts are right for terminals. In a browser the trap is different: CJK, Thai and Devanagari glyphs come
from **fallback fonts** whose advance is not exactly 2x (or 1x) the Latin monospace advance *[est]*, so a "2-cell"
glyph makes the rest of the line drift and columns stop lining up. Options, least to most work:

1. **Treat each phrase as an unbreakable inline box** (closest to the original, which measures and positions per
   word). Compute its width once, in cells, rounded up, and give the `<span>` `display: inline-block; width: Nch;`
   with the glyphs centred/clipped inside. Every other word stays aligned; an odd glyph can only hurt itself.
2. **A CJK-aware monospace webfont**, subset to the ~60 distinct characters of the 20 phrases (a few KB), so wide is
   exactly 2 cells by design. Check the font's licence.
3. **Paint to a `<canvas>`** with `fillText` at `col * cellW` per glyph: no drift, but the text is not selectable.
4. **Transliterate** the 11 non-ASCII phrases (9 are already pure ASCII; see the `A` column in section 4). If "ASCII"
   in our brief means strict 7-bit this is the only option; keep the native script in an `aria-label`/`title`.

Python has no grapheme segmentation in the stdlib. The 20 phrases are fixed, so precompute each cell width offline,
ship it as data and skip the runtime `unicodedata` dependency. For a personal letter, also check the speaker/addressee
forms (Hindi masculine speaker, Vietnamese anh/em) before including them.

### 7.7 Timing: elapsed time instead of ticks

Replace the accumulator with `target = int(min(1, elapsed / DURATION) * N)` and spawn until `spawned == target`. That
is the same even ramp (`floor(k * RATE)`), but the 10 s is now real, dropped frames do not stretch the show, and a
hidden tab that resumes just catches up (clamp `dt` for the animation, not for the schedule). Drive it from
`requestAnimationFrame`, not a fixed 16 ms timer.

### 7.8 Performance in a browser Python runtime (Pyodide / PyScript / Brython)

General guidance, not measured on this project *[est]*:

* **Compute once, animate cheaply.** Sampling, spans, packing and colouring are tiny (about 30 spans x 2 scans x 720
  edges plus a few hundred placements); run them once. Per frame only ~8 phrases are mid-animation (42 x RATE) plus the
  shimmer words.
* **Cross the Python <-> JS boundary rarely.** Each DOM call from Python goes through a proxy: build the HTML string
  for dirty rows in Python and assign it once per frame, rather than touching hundreds of nodes.
* **Few DOM nodes:** one container, one `<span>` per word run (hundreds, not one per cell); toggle classes rather than
  writing inline styles.
* **Create the `requestAnimationFrame` callback proxy once** and reuse it; a new proxy per frame leaks memory.
* **Startup is the real cost.** A Python runtime download is multi-megabyte: show an ASCII spinner while it loads, and
  consider baking the layout (grid and timings) to JSON offline, with Python only running the animation, if load time
  matters more than "Python all the way".
* **Determinism:** `random.Random(seed)` is reproducible in CPython-compatible runtimes; on Brython verify that
  `shuffle`/`uniform` give the same sequence, or ship the precomputed order.
* **Accessibility:** the art is decoration: `aria-hidden="true"` on it, with the real letter as plain text.

### 7.9 Licence

With no `LICENSE` the code is all-rights-reserved by default (not legal advice). Do not paste from `love.py`. The
ideas used here (a published parametric heart curve, scanline even-odd filling, greedy packing, a fractional
accumulator, cubic ease-out) are standard techniques, so a clean re-implementation from the descriptions in this
document is the safe route. Credit iremcnar as inspiration on the page, or ask them to add a licence. The short
excerpts in this document are for analysis and should not be shipped.

## 8. Key takeaways

1. The whole piece is **text placed by geometry**: a 720-point polygon of the heart curve, scanline spans per row,
   the intersection of the top and bottom spans so a row's box stays inside the outline.
2. Packing is **greedy with retries**, then **right-justified** by spreading leftover space over the gaps; it produces the
   dense, even texture. It silently **discards** candidates (bias to short phrases) - fix it in our port.
3. Colour is a **function of normalised ellipse radius** (wine at the centre, crimson on the rim) plus random sparkle
   and an extra boost for the first/last word of each row.
4. **Draw order tells the story**: outline clockwise from the top notch, then interior from the outside in.
5. The spawn schedule is a **fractional accumulator** (`acc += N / 625`): an even ramp with at most one phrase of
   error and a fixed show length, independent of N. But it counts ticks, not seconds; use elapsed time on the web.
6. Each phrase gets three Tk items (shadow, halo, main) and a 42-frame **cubic ease-out drop** of 34 px with sideways
   drift, a pale-pink landing flash and a dim-to-bright colour fade; the shadow never moves.
7. **Shimmer** = one random phrase snapped 60% to pale pink for 260 ms, every 140 ms, forever.
8. Layout depends on local font metrics, so it is **not identical across machines** despite the fixed seed. A
   cell grid makes it deterministic.
9. For us the main risks are **wide/combining glyphs** on a monospace grid, **runtime load size**, and the
   **missing licence** (re-implement, do not copy).

## Appendix A - quirks and dead code in the original

* Dead or redundant: `tick_no = 0` (174) is never used; `for _ in range(1)` (263) runs once; `(t.Terminator, Exception)`
  (273) is redundant; `s.tracer(0)` (21) has no effect on raw canvas items.
* The first text row is always empty (`spans(YMAX)` is empty because of the half-open rule); the 14 px span threshold is
  shadowed by the real limit (narrowest phrase plus insets).
* The shadow item is never repositioned after creation (207 sets only its fill).
* `_safe` swallows every exception from `itemconfig`, real bugs included, and the closing `try/except` swallows
  whatever `mainloop` raises; the window is a fixed 800 x 800 and nothing reacts to resizing.

## Appendix B - how this was checked

`love.py` and `README.md` were read in full and nothing from the repo was executed (no Tk window opened). Numbers tagged
*[replica]* come from a separate scratch script that re-types `heart`, `spans`, `intersect`, `math_dist`, the colour
mixes and the animation formulas; the PHRASES list was read with `ast.parse` + `ast.literal_eval` only. Turtle facts
come from this machine's Python 3.14.0 `Lib/turtle.py`. Values that depend on Tk font metrics (`row_h`, N, phrase
widths) cannot be known without running the program and are marked as estimates.
