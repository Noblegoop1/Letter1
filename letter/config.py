"""Every tunable in one place: pace, timing, sizes, colours, quality, motion (SPEC §14, §15, A11)."""
import os
import sys


def _animations_off():
    """True when Windows "Show animations in Windows" is off (SPI_GETCLIENTAREAANIMATION)."""
    if sys.platform != "win32":
        return False
    import ctypes
    on = ctypes.c_int(1)
    ok = ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(on), 0)
    return bool(ok) and not on.value


TITLE = "To Esther"
SPEED = 1.0        # global pace: 2.0 plays everything twice as fast
FPS_CAP = 60
QUALITY = 1.0      # scales particle and firefly counts (0.5 for weak machines)
# A11: calmer ambient motion and no glints when the reader has turned animations off (LETTER_CALM=1 forces it)
CALM = os.environ.get("LETTER_CALM") == "1" or _animations_off()
MOTION = 0.35 if CALM else 1.0     # scales the ambient float, hover, wave and wind sway
WANDER = 6.5       # s the fireflies wander after arriving, before gathering into the invitation (in T["bloomed"])

LETTER_SIZE = (1280, 800)   # logical canvases (SPEC §7); the window size is independent
NIGHT_SIZE = (640, 640)
CHASE_SIZE = (320, 320)

# seconds at SPEED 1; scenes read their beats from here
T = {
    "intro": 2.2,           # fade up 0.6, dedication 1.2 (from 0.4), question rise 1.0 (from 1.0)
    "yes-reveal": 3.0,      # dissolve 0-1.0, flap 0.1-0.9, sheet 0.4-1.6, zoom 1.5-3.0
    "night": 2.0,
    "seed": 6.5,            # pause 0.4, fall 0.8, puff 0.3, pause 0.5, growth 4.5
    "bloom": 2.0,
    "bloomed": 6.3 + WANDER,   # the fireflies arrive (6.3, night.ARRIVE), then wander before they gather
    "gather": 7.0,          # they converge and form the invitation
    "invite": 1.2,          # input lock while the invitation's buttons fade in
    "letgo": 2.5,           # NO on the invitation: the message disperses, the night fades
    "farewell": 8.0,        # YES on the invitation: scatter 0-3, brighten 1-3.5, dim 4.5-8
    "joy": 7.5,             # smile .6-2.8, love eyes 3.2-5.6, fade 5.8-7.0, then the app closes
    "no-1": 0.6,            # input lock while the question crossfades
    "no-2": 0.9,            # earthquake
    "no-3": 0.8,            # button swap
    "no-4": 8.1,            # tremble .4 crack .4 shatter 1.6 message 1.5 hold .6 open 1.2 hop .8 zoom 1.6
    "glitch": 4.9,          # freeze .4 glitch 2.0 dissolve 2.5
    "face": 11.8,           # black .8 face in 2.0 hold 1.0 tear forms 1.0 falls 3.5 pause 1.0 fade 2.5
}

# palette (sRGB)
BG = (12, 9, 16)
NIGHT_BG = (7, 10, 20)
PAPER = (236, 224, 199)
INK = (92, 54, 70)
YES = (255, 134, 173)
NO = (180, 176, 214)
CREAM = (244, 231, 204)
