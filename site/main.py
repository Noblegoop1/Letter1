"""Browser side of the love letter: DOM writes, the animation loop and the buttons. Art lives in art.py."""
from pyscript import document, window, when
from pyscript.ffi import create_proxy

import art

OPEN_S = 1.3    # flap swing
HOLD_S = 0.25   # beat with the flap open before the envelope slides away
WILD_S = 0.6    # how long NO's letters go wild

STEP_HZ = 24    # button redraw rate; the glyphs themselves churn at art.button's own rate

reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
state = {"paused": reduced, "opened": None, "wild_until": 0.0, "drawn": None, "depth": art.CY}
last = {}
flaps = {}  # flap depth -> envelope HTML; built one per frame while waiting so the opening never stalls
DEPTHS = range(-art.CY, art.CY + 1)


def el(name):
    return document.getElementById(name)


def now():
    return window.performance.now() / 1000


def flap(d):
    if d not in flaps:
        flaps[d] = art.to_html(*art.envelope(d))
    return flaps[d]


def show(name, frame):
    html = frame if isinstance(frame, str) else art.to_html(*frame)
    if last.get(name) != html:  # touch the DOM only when the picture changed
        last[name] = html
        el(name).innerHTML = html


def size(name, cols, rows, head=0):
    style = el(name).style
    style.setProperty("--cols", str(cols))
    style.setProperty("--rows", str(rows))
    style.setProperty("--head", str(head))


def tick(ms):
    t = ms / 1000
    # paused: time stands still, but NO still flips to a static wild frame as a non-moving cue
    key = (0 if state["paused"] else int(t * STEP_HZ), t < state["wild_until"])
    if state["opened"] is None and key != state["drawn"]:
        state["drawn"] = key
        show("yes-art", art.button("YES", key[0] / STEP_HZ))
        show("no-art", art.button("NO", key[0] / STEP_HZ, key[1]))
    elif state["opened"] is None and len(flaps) < len(DEPTHS):
        flap(next(d for d in DEPTHS if d not in flaps))
    if state["opened"] is not None:
        k = (t - state["opened"]) / OPEN_S
        d = art.flap_depth(180 * art.ease(k))
        if d != state["depth"]:
            state["depth"] = d
            show("envelope", flap(d))
        if k > 1 + HOLD_S / OPEN_S:
            el("letter").classList.add("away")
            el("letter").setAttribute("inert", "")  # gone for screen readers too
            return  # the scene is over; stop the loop
    window.requestAnimationFrame(tick_proxy)


tick_proxy = create_proxy(tick)


@when("click", "#yes")
def open_letter(event):
    if state["opened"] is not None:
        return
    for name in ("title", "choices", "pause"):
        el(name).classList.add("gone")
        el(name).setAttribute("inert", "")
    el("status").textContent = "The envelope opens and slides away."
    # reduced motion: start the clock in the past so the next frame is the end state
    state["opened"] = now() - (10 if reduced else 0)


@when("click", "#no")
def refuse(event):
    state["wild_until"] = now() + WILD_S
    button = el("no")
    button.classList.remove("shake")
    button.offsetWidth  # force a reflow so the shake animation restarts
    button.classList.add("shake")


@when("click", "#pause")
def toggle_pause(event):
    state["paused"] = not state["paused"]
    el("pause").textContent = "[ play ]" if state["paused"] else "[ pause ]"


# the probe is 10 cells at 100px: its width gives this browser's cell width in em
document.documentElement.style.setProperty("--cw", str(el("probe").getBoundingClientRect().width / 1000))
el("probe").remove()
for name, narrow in (("title-wide", False), ("title-narrow", True)):
    frame = art.headline(narrow)
    size(name, len(frame[0][0]), len(frame[0]))
    show(name, frame)
size("letter", art.ENV_W, art.ENV_H, art.HEAD)
show("envelope", flap(art.CY))
show("yes-art", art.button("YES", 0))
show("no-art", art.button("NO", 0))
if reduced:
    el("pause").textContent = "[ play ]"
el("loading").remove()
document.body.classList.add("ready")
window.requestAnimationFrame(tick_proxy)
