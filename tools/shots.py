"""Render reference screenshots of the story to build/shots/<WxH>/ for review by eye (SPEC §17).

Usage: .venv\\Scripts\\python tools\\shots.py [WxH ...]   (default: 1280x800 1920x1080)
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from letter.app import App, headless  # noqa: E402

# (story time, action, argument); "shot" saves the frame drawn just before that time
PLAN = [
    (0.3, "shot", "00-fade-up"),
    (1.2, "shot", "01-dedication"),
    (2.6, "shot", "02-letter"),
    (2.7, "move", "yes"),
    (2.8, "shot", "03-hover-yes-scramble"),
    (3.6, "shot", "04-hover-yes-settled"),
    (3.7, "move", "no"),
    (3.8, "shot", "05-hover-no"),
    (9.0, "shot", "06-float-later"),
    (9.1, "click", "yes"),
    (9.4, "shot", "07-yes-dissolve"),
    (9.8, "shot", "08-yes-flap-sheet"),
    (10.6, "shot", "09-yes-sheet-out"),
    (11.2, "shot", "10-yes-zoom"),
    (11.8, "shot", "11-yes-zoom-late"),
    (12.6, "shot", "12-night-dark"),
    (13.4, "shot", "13-night-emerging"),
    (14.6, "shot", "14-seed-falling"),
    (17.0, "shot", "15-growing"),
    (19.0, "shot", "16-bud"),
    (20.6, "shot", "17-bud-glow"),
    (20.7, "move", "flower"),
    (20.8, "click", "flower"),
    (21.8, "shot", "18-blooming"),
    (23.5, "shot", "19-bloomed"),
    (29.0, "shot", "20-fireflies"),
]

# the invitation (SPEC §10.7): wandering, gathering, the formed question and its buttons, then each choice
from letter.engine.story import duration  # noqa: E402

BLOOMED = 20.8 + duration("bloom")
GATHER = BLOOMED + duration("bloomed")
INVITE = GATHER + duration("gather")
CHOICE = INVITE + duration("invite") + 0.5
INVITE_YES = PLAN + [
    (GATHER - 2.0, "shot", "21-wandering"),
    (GATHER + 2.0, "shot", "22-gathering"),
    (GATHER + 4.5, "shot", "23-converging"),
    (INVITE + 0.2, "shot", "24-formed"),
    (CHOICE - 0.6, "move", "date-yes"),
    (CHOICE - 0.1, "shot", "25-invitation-hover-yes"),
    (CHOICE, "click", "date-yes"),
    (CHOICE + 1.2, "shot", "26-yes-scatter"),
    (CHOICE + 3.4, "shot", "27-yes-flower-brightest"),
    (CHOICE + 6.4, "shot", "28-yes-dimming"),
    (CHOICE + duration("farewell") + 1.8, "shot", "29-joy-smile"),
    (CHOICE + duration("farewell") + 4.6, "shot", "30-joy-love-eyes"),
]
INVITE_NO = [step for step in PLAN if step[1] != "shot"] + [
    (CHOICE - 0.6, "move", "date-no"),
    (CHOICE - 0.1, "shot", "31-invitation-hover-no"),
    (CHOICE, "click", "date-no"),
    (CHOICE + 1.2, "shot", "32-no-letgo"),
    (CHOICE + duration("letgo") + 4.6, "shot", "33-no-face-and-tear"),
]

# the NO route: four NOs, the escape, a chase played with one jump, the catch and the ending
SPACE = 32
NO_PLAN = [
    (2.7, "move", "no"),
    (3.0, "click", "no"),
    (3.4, "shot", "n01-are-you-sure"),
    (3.8, "click", "no"),
    (4.0, "shot", "n02-earthquake"),
    (4.6, "shot", "n03-is-this-what"),
    (4.9, "click", "no"),
    (5.3, "shot", "n04-swap"),
    (5.9, "shot", "n05-swapped"),
    (6.0, "click", "no"),
    (6.3, "shot", "n06-tremble"),
    (6.7, "shot", "n07-crack"),
    (7.2, "shot", "n08-shatter"),
    (9.7, "shot", "n09-message"),
    (11.1, "shot", "n10-open"),
    (12.1, "shot", "n11-hop"),
    (13.3, "shot", "n12-dive"),
    (14.6, "shot", "n13-chase-start"),
    (15.5, "key", SPACE),
    (15.75, "shot", "n14-jump"),
    (45.0, "shot", "n15-chase-b"),
    (114.0, "shot", "n16-chase-c"),
    (146.0, "shot", "n17-cornered"),
    (146.2, "move", "no"),
    (146.6, "shot", "n18-cornered-pointer-near"),
    (147.0, "click", "no"),
    (147.2, "shot", "n19-freeze"),
    (148.6, "shot", "n20-glitch"),
    (150.6, "shot", "n21-dissolve"),
    (154.0, "shot", "n22-face"),
    (157.5, "shot", "n23-tear"),
    (165.0, "shot", "n24-black"),
]


def main(sizes):
    import pygame
    headless()
    for size in sizes:
        out = os.path.join(ROOT, "build", "shots", "%dx%d" % size)
        os.makedirs(out, exist_ok=True)
        for plan in (INVITE_YES, INVITE_NO, NO_PLAN):   # each path in a fresh app
            app = App(size=size)
            app.run_script(plan, on_shot=lambda name, screen: pygame.image.save(screen, os.path.join(out, name + ".png")))
        print("saved", out)


if __name__ == "__main__":
    args = sys.argv[1:] or ["1280x800", "1920x1080"]
    main([tuple(int(n) for n in a.split("x")) for a in args])
