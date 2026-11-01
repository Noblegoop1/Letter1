"""Browser side of the love letter: one loop walks the stage phases and writes each layer.

All drawing lives in pure modules (art, reveal, night, flower, fireflies); this file reads the clock,
asks them for frames and puts the results into the DOM, writing only what changed.
"""
import math

from pyscript import document, window, when
from pyscript.ffi import create_proxy

import art
import fireflies
import flower
import night
import reveal
import stage
from stage import clamp, ease, ease_in, ease_out, lerp

STEP_HZ = 24        # button ripple redraws per second
GRASS_HZ = 10       # meadow redraws per second (each one is split over two frames)
FLOWER_HZ = 20      # flower redraws per second (the CSS tilt smooths in between)
WILD_S = 0.6        # how long NO's letters go wild
PULL_ROWS = reveal.SHEET_H - 3   # how far the sheet rises out of the pocket
CELL_BUDGET = 4500   # night grid cells: MicroPython measured 10-25x slower than CPython
RESIZE_SETTLE = 0.25  # seconds a new window size must hold before the meadow is rebuilt
BUD_GLOW = 0.25
LEAN_MAX = 0.45      # pointer lean, in flower bend units
LEAN_TAU = 0.35      # seconds for the lean to follow the pointer
TILT_DEG = 2.5       # CSS tilt per unit of bend: smooth sway between character steps
STATUS = {
    "reveal": "The writing crumbles and a sheet of paper slides out of the envelope.",
    "night": "The paper becomes a quiet night meadow.",
    "grown": "A small flower has grown from a seed. Press it to wake it.",
    "bloom": "The flower opens and begins to glow.",
    "bloomed": "Fireflies gather around the glowing flower.",
}

reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
clock = stage.Clock()
s = {"phase": "letter", "since": 0.0, "t": 0.0, "dt": 0.0, "hover": {"yes": None, "no": None},
     "wild_until": 0.0, "pointer": None, "lean": 0.0, "grid": None, "zoom": None, "depth": art.CY,
     "ff": [], "size": None, "pending": None, "resize": None}
last = {}
_els = {}
flaps = {}  # flap depth -> (back, front) HTML, built one per idle frame so the opening never stalls
DEPTHS = range(-art.CY, art.CY + 1)
_proxies = []  # keep event proxies alive


def el(name):
    if name not in _els:  # one JS proxy per element instead of a new one on every call
        _els[name] = document.getElementById(name)
    return _els[name]


def now():
    return window.performance.now() / 1000


def show(name, frame):
    html = frame if isinstance(frame, str) else art.to_html(*frame)
    if last.get(name) != html:  # touch the DOM only when the picture changed
        last[name] = html
        el(name).innerHTML = html


def css(name, prop, value):
    if last.get(name + prop) != value:
        last[name + prop] = value
        el(name).style.setProperty(prop, value)


def flap(d):
    if d not in flaps:
        back, front = art.envelope(d)
        flaps[d] = (art.to_html(*back), art.to_html(*front))
    return flaps[d]


def listen(target, event, fn):
    proxy = create_proxy(fn)
    _proxies.append(proxy)
    target.addEventListener(event, proxy)


# --- phases -----------------------------------------------------------------------------------

def advance(t, event=None):
    old = s["phase"]
    new, s["since"] = stage.step(old, s["since"], t, event, reduced)
    for k in range(stage.PHASES.index(old) + 1, stage.PHASES.index(new) + 1):
        enter(stage.PHASES[k])
    if new != old:
        s["phase"] = new
        document.body.setAttribute("data-phase", new)


def enter(phase):
    if phase in STATUS:
        el("status").textContent = STATUS[phase]
    if phase == "reveal":
        for name in ("title", "choices"):
            el(name).classList.add("gone")
            el(name).setAttribute("inert", "")
    elif phase == "seed":
        el("seed").style.display = "block"
    elif phase == "grown":
        # the seed and puff can be cut short (reduced motion, a hidden tab): never leave them hanging
        el("seed").style.display = "none"
        show("puff", art.puff(-1))
        el("flower").removeAttribute("inert")
        if document.activeElement == document.body or document.activeElement is None:
            el("flower").focus()  # keyboard users land on the one thing they can press
    elif phase == "bloom":
        el("flower").setAttribute("inert", "")
    elif phase == "bloomed":
        make_fireflies()


# --- letter -----------------------------------------------------------------------------------

def draw_letter(t):
    wt = 0.0 if reduced else t  # reduced motion: NO's tantrum is one still frame
    for name, word in (("yes", "YES"), ("no", "NO")):
        since = s["hover"][name]
        wild = name == "no" and t < s["wild_until"]
        rippling = since is not None and 0 <= t - since < art.RIPPLE
        key = (int(wt * STEP_HZ) if rippling or wild else -1, wild)
        if last.get(name + "key") != key:
            last[name + "key"] = key
            show(name + "-art", art.button(word, wt, since if rippling else None, wild))
    if len(flaps) < len(DEPTHS):
        flap(next(d for d in DEPTHS if d not in flaps))
    elif s["grid"] is None and min(window.innerWidth, window.innerHeight) >= 50:
        # the meadow's first layout is slow; build it while the viewer reads
        s["grid"], s["size"] = build_grid(), (window.innerWidth, window.innerHeight)


def start_ripple(name):
    if s["phase"] == "letter" and not reduced:
        s["hover"][name] = s["t"]


# --- reveal -----------------------------------------------------------------------------------

def start_zoom():
    """Aim the camera at the centre of the sheet's black window; return the scale that fills the screen."""
    r = el("sheet").getBoundingClientRect()
    if r.width < 1:  # not laid out (hidden window): try again next frame
        return None
    cw, ch = r.width / reveal.SHEET_W, r.height / reveal.SHEET_H
    x0, y0, x1, y1 = reveal.INSIDE
    box = (r.left + x0 * cw, r.top + y0 * ch, r.left + x1 * cw, r.top + y1 * ch)
    cam = el("camera").getBoundingClientRect()
    origin = "%.1fpx %.1fpx" % ((box[0] + box[2]) / 2 - cam.left, (box[1] + box[3]) / 2 - cam.top)
    el("camera").style.transformOrigin = origin
    return reveal.cover_scale(box, window.innerWidth, window.innerHeight)


def draw_reveal(e):
    p = round(stage.span(e, reveal.WRITE) * 30) / 30  # ~21 redraws/s: 7 ms each in MicroPython
    if last.get("writingkey") != p:
        last["writingkey"] = p
        show("writing", reveal.writing(p))
    d = art.flap_depth(180 * ease(stage.span(e, reveal.FLAP)))
    if d != s["depth"]:
        s["depth"] = d
        back, front = flap(d)
        show("env-back", back)
        show("env-front", front)
    css("sheet", "transform", "translateY(-%.3fem)" % (ease_out(stage.span(e, reveal.PULL)) * PULL_ROWS))
    z = stage.span(e, reveal.ZOOM)
    if z > 0:
        if s["zoom"] is None:
            s["zoom"] = start_zoom()
        if s["zoom"] is not None:
            css("camera", "transform", "scale(%.4f)" % (s["zoom"] ** ease(z)))  # even-feeling dive


# --- night world ------------------------------------------------------------------------------

def hex_rgb(h):
    h = h.strip().lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def css_colour(var, fallback):
    try:
        return hex_rgb(window.getComputedStyle(document.documentElement).getPropertyValue(var))
    except Exception:  # not a #rrggbb value: use a safe colour instead of failing to start
        return hex_rgb(fallback)


def build_grid():
    """Character grid that covers the viewport, plus where the flower and fireflies live in it."""
    vw, vh = window.innerWidth, window.innerHeight
    # a fixed cell budget keeps the meadow's cost the same on any screen; chunky cells suit the look
    fs = clamp(math.sqrt(vw * vh / (CW * CELL_BUDGET)), 12, 32)
    cell = fs * CW
    cols, rows = max(flower.SIZE[0] + 4, math.ceil(vw / cell)), max(flower.SIZE[1] + 8, math.ceil(vh / fs))
    root = (int(vw / cell / 2), night.horizon(rows) + 2)  # centred on the screen even if the grid is wider
    fx, fy = (root[0] - flower.BASE[0]) * cell, (root[1] - flower.BASE[1]) * fs
    g = {"fs": fs, "cell": cell, "cols": cols, "rows": rows, "root": root,
         "head": (fx + (flower.HEART[0] + 0.5) * cell, fy + (flower.HEART[1] + 0.5) * fs),
         "radius": 0.32 * min(vw, vh)}
    for name in ("ground", "seed", "puff", "flower", "fireflies"):
        css(name, "font-size", "%.2fpx" % fs)
    css("flower", "left", "%.1fpx" % fx)
    css("flower", "top", "%.1fpx" % fy)
    css("flower", "--root-x", "%.1fpx" % ((flower.BASE[0] + 0.5) * cell))
    css("puff", "left", "%.1fpx" % ((root[0] - 7) * cell))
    css("puff", "top", "%.1fpx" % ((root[1] - 2) * fs))
    night.ground(cols, rows, 0.0, 0.0)  # pay the slow first layout for this size now
    last.pop("groundkey", None)
    last.pop("flowerkey", None)
    s["pending"] = None  # a frame built for the old size must not be shown at the new one
    return g


def update_lean(dt, g):
    target, p = 0.0, s["pointer"]
    if p is not None and s["phase"] in ("grown", "bloom", "bloomed"):
        target = stage.lean_target(p[0] - g["head"][0], p[1] - g["head"][1], g["radius"], LEAN_MAX)
    s["lean"] = stage.approach(s["lean"], target, dt, LEAN_TAU) if dt > 0 else s["lean"]


def watch_size(t):
    """Rebuild the meadow only once a new window size has held still (drag-resizes would stutter)."""
    # PyScript's window proxy can't addEventListener ("Illegal invocation"), so poll the size
    size = (window.innerWidth, window.innerHeight)
    if min(size) < 50:  # hidden or mid-resize window reports ~0: keep the last picture until it is real
        return False
    if s["grid"] is None:
        s["grid"], s["size"] = build_grid(), size
    elif size != s["size"]:
        if s["resize"] is None or s["resize"][0] != size:
            s["resize"] = (size, t)
        elif t - s["resize"][1] >= RESIZE_SETTLE:
            s["grid"], s["size"], s["resize"] = build_grid(), size, None
    return True


def draw_world(t, phase, e):
    if not watch_size(t):
        return
    g = s["grid"]
    tw = 0.0 if reduced else t  # reduced motion: the wind holds still
    update_lean(s["dt"], g)
    emerge, grow, bloom, glow = 1.0, 0.0, 0.0, 0.0
    if phase == "night":
        k = clamp(e / stage.NIGHT_FADE)
        rgb = [round(lerp(a, b, k)) for a, b in zip(DAY, NIGHT)]
        css_body("rgb(%d, %d, %d)" % (rgb[0], rgb[1], rgb[2]))
        emerge = stage.span(e, stage.NIGHT_EMERGE)
    elif phase == "seed":
        draw_seed(e, g, tw)
        grow = ease(stage.span(e, stage.SEED_GROW))
        glow = BUD_GLOW * grow
    elif phase == "grown":
        grow, glow = 1.0, BUD_GLOW
    elif phase == "bloom":
        k = 1.0 if reduced else ease(stage.progress(phase, s["since"], t))
        grow, bloom, glow = 1.0, k, lerp(BUD_GLOW, 1.0, k)
    else:
        grow, bloom, glow = 1.0, 1.0, 1.0
        draw_fireflies(e, g, tw)
    if phase != "night":
        css_body("var(--night-bg)")
    # the meadow's light pool lies flat on the ground, so it is centred just above the flower's root
    light = (g["root"][0], g["root"][1] - 1, round(glow, 2)) if glow > 0 else None
    key = (int(tw * GRASS_HZ), round(emerge, 2), light)  # still wind (reduced motion): no needless rebuilds
    busy = True
    if s["pending"] is not None:  # second half of a meadow redraw: HTML and DOM write
        show("ground", s["pending"])
        s["pending"] = None
    elif last.get("groundkey") != key:  # first half: build the frame
        last["groundkey"] = key
        s["pending"] = night.ground(g["cols"], g["rows"], tw, emerge, light)
    else:
        busy = False
    if grow > 0:
        draw_flower(t, tw, g, grow, bloom, glow, busy)


def css_body(value):
    if last.get("bodybg") != value:
        last["bodybg"] = value
        document.body.style.background = value
        document.documentElement.style.background = value  # no old-colour strip in overscroll areas


def draw_seed(e, g, tw):
    f = stage.span(e, stage.SEED_FALL)
    if f < 1:
        x = g["root"][0] * g["cell"] + night.wind(g["root"][0], tw) * 8 * f
        y = lerp(-g["fs"] * 2, (g["root"][1] - 0.6) * g["fs"], ease_in(f))
        css("seed", "transform", "translate(%.1fpx, %.1fpx)" % (x, y))
    else:
        css("seed", "display", "none")
    show("puff", art.puff(e - stage.SEED_FALL[1]))


def draw_flower(t, tw, g, grow, bloom, glow, busy):
    bend = clamp(0.55 * night.wind(g["root"][0], tw) + s["lean"], -1.0, 1.0)
    q = round(bend * 20) / 20
    look, beat = (round(grow, 2), round(bloom, 2), q, round(glow, 2)), int(t * FLOWER_HZ)
    prev = last.get("flowerkey")
    # redraw on change, at most FLOWER_HZ, and avoid frames the meadow already spent unless the flower
    # has waited 0.15 s (a slow device where every frame is busy must still see it grow)
    if prev is None or (look != prev[0] and beat != prev[1] and (not busy or t - prev[2] > 0.15)):
        last["flowerkey"] = (look, beat, t)
        show("flower-art", flower.frame(grow, bloom, q, glow))
    css("flower", "transform", "rotate(%.2fdeg)" % (bend * TILT_DEG))
    css("flower", "--glow", "%.2f" % glow)


def make_fireflies():
    box = el("fireflies")
    for i in range(fireflies.COUNT):
        glyph, period, delay, peak, depth = fireflies.style(i)
        span = document.createElement("span")
        span.className = "ff"
        span.textContent = glyph
        span.style.setProperty("--period", "%.2fs" % period)
        span.style.setProperty("--delay", "-%.2fs" % delay)  # negative: already mid-blink, never in step
        span.style.setProperty("--peak", "%.2f" % peak)
        span.style.setProperty("--depth", "%.2f" % depth)
        span.style.opacity = "0"
        box.appendChild(span)
        s["ff"].append([span.style, "", ""])  # style proxy, last opacity, last transform


def draw_fireflies(e, g, tw):
    for i, entry in enumerate(s["ff"]):
        style = entry[0]
        # fade in on the stage clock, not a CSS transition, so pause freezes it too
        opacity = "%.2f" % clamp((e - fireflies.arrival(i)) / 1.2)
        x, y = fireflies.position(i, tw, g["head"], g["radius"])
        x += 10 * night.wind(x / g["cell"], tw)
        move = "translate(%.1fpx, %.1fpx)" % (x, y)
        if opacity != entry[1]:
            entry[1] = style.opacity = opacity
        if move != entry[2]:
            entry[2] = style.transform = move


# --- loop and events --------------------------------------------------------------------------

def tick(ms):
    window.requestAnimationFrame(tick_proxy)  # first, so one bad frame can't stop the loop for good
    t = clock.now(ms / 1000)
    s["dt"], s["t"] = clamp(t - s["t"], 0.0, 0.1), t
    advance(t)
    phase, e = s["phase"], t - s["since"]
    if reduced and phase in stage.DURATIONS:
        e = stage.DURATIONS[phase]  # reduced motion: every timed phase shows its end state
    if phase == "letter":
        draw_letter(t)
    elif phase == "reveal":
        if reduced:  # a short fade instead of crumbling, pulling and diving
            css("camera", "opacity", "%.2f" % (1 - stage.progress("reveal", s["since"], t, True)))
        else:
            draw_reveal(e)
    else:
        draw_world(t, phase, e)


tick_proxy = create_proxy(tick)


@when("click", "#yes")
def open_letter(event):
    advance(s["t"], "yes")


@when("click", "#no")
def refuse(event):
    if s["phase"] != "letter":
        return
    s["wild_until"] = s["t"] + WILD_S
    button = el("no")
    button.classList.remove("shake")
    button.offsetWidth  # force a reflow so the shake animation restarts
    button.classList.add("shake")


@when("click", "#flower")
def wake_flower(event):
    advance(s["t"], "flower")


@when("click", "#pause")
def toggle_pause(event):
    if clock.paused_at is None:
        clock.pause(now())
        document.body.classList.add("paused")
        el("pause").textContent = "[ play ]"
        el("pause").setAttribute("aria-pressed", "true")
    else:
        clock.resume(now())
        document.body.classList.remove("paused")
        el("pause").textContent = "[ pause ]"
        el("pause").setAttribute("aria-pressed", "false")


def on_move(event):
    s["pointer"] = (event.clientX, event.clientY)


def on_leave(event):
    s["pointer"] = None


for _name in ("yes", "no"):
    for _ev in ("pointerenter", "focus", "pointerdown"):
        listen(el(_name), _ev, lambda event, n=_name: start_ripple(n))
listen(document, "pointermove", on_move)
listen(document.documentElement, "pointerleave", on_leave)

# the probe is 10 cells at 100px: its width gives this browser's cell width in em
CW = el("probe").getBoundingClientRect().width / 1000
document.documentElement.style.setProperty("--cw", str(CW))
el("probe").remove()
DAY, NIGHT = css_colour("--bg", "#0c0910"), css_colour("--night-bg", "#070a14")

for name, narrow in (("title-wide", False), ("title-narrow", True)):
    frame = art.headline(narrow)
    css(name, "--cols", str(len(frame[0][0])))
    css(name, "--rows", str(len(frame[0])))
    show(name, frame)
css("letter", "--cols", str(art.ENV_W))
css("letter", "--rows", str(art.ENV_H + 9))   # envelope plus shadow and buttons
css("letter", "--head", str(art.HEAD))
css("sheet", "--sx", str((art.ENV_W - reveal.SHEET_W) // 2))
css("sheet", "--sy", str(art.TOP + 3))
back, front = flap(art.CY)
show("env-back", back)
show("env-front", front)
show("writing", reveal.writing(0.0))
show("sheet", reveal.sheet())
show("shadow", art.shadow())
show("yes-art", art.button("YES", 0))
show("no-art", art.button("NO", 0))
el("loading").remove()
document.body.classList.add("ready")
window.requestAnimationFrame(tick_proxy)
