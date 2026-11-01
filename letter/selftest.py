"""The scripted stories the self-test plays: (story time, action, argument), sorted by time.

Both routes, each in a fresh app; it must pass from source and from the packaged exe (SPEC §17).
Times follow the story's durations, so a different SPEED still lines up.
"""
from letter.engine.story import duration

SPACE = 32                                  # pygame.K_SPACE

# --- YES: hover YES, open, wait for the bud, wake it, watch the fireflies arrive ------------------------
YES = 3.0                                   # the reader hovers YES, then clicks it
NIGHT = YES + duration("yes-reveal")
SEED = NIGHT + duration("night")
GROWN = SEED + duration("seed")
TOUCH = GROWN + 0.3                         # the bud is clicked
BLOOMED = TOUCH + duration("bloom")

YES_PLAN = [
    (0.5, "expect", "intro"),
    (duration("intro") + 0.3, "expect", "letter"),
    (YES - 0.4, "move", "yes"),
    (YES, "click", "yes"),
    (YES + 0.1, "expect", "yes-reveal"),
    (NIGHT + 0.2, "expect", "night"),
    (SEED + 0.2, "expect", "seed"),
    (GROWN + 0.2, "expect", "grown"),
    (TOUCH - 0.1, "move", "flower"),
    (TOUCH, "click", "flower"),
    (TOUCH + 0.1, "expect", "bloom"),
    (BLOOMED + 0.2, "expect", "bloomed"),
    (BLOOMED + 4.0, "expect", "bloomed"),   # fireflies arriving
]

# --- the invitation: the fireflies wander, gather into the question, its buttons fade in ------------------
GATHER = BLOOMED + duration("bloomed")
INVITE = GATHER + duration("gather")
CHOICE = INVITE + duration("invite") + 0.5
INVITATION = YES_PLAN + [
    (GATHER - 1.0, "expect", "bloomed"),    # still wandering: the gathering waits for config.WANDER
    (GATHER + 0.2, "expect", "gather"),
    (INVITE + 0.2, "expect", "invite"),
    (INVITE + 0.3, "click", "date-no"),     # its buttons are still fading in: nothing happens yet
    (INVITE + 0.4, "expect", "invite"),
    (CHOICE - 0.3, "move", "date-yes"),
]
JOY = CHOICE + duration("farewell")
DATE_YES = INVITATION + [
    (CHOICE, "click", "date-yes"),
    (CHOICE + 0.1, "expect", "farewell"),
    (CHOICE + 0.2, "click", "date-no"),     # locked: the decision is made
    (CHOICE + 0.3, "expect", "farewell"),
    (JOY + 0.3, "expect", "joy"),
    (JOY + duration("joy") + 0.5, "expect", "exit"),   # the app closes itself (the run stops there)
]
FACE = CHOICE + duration("letgo")
DATE_NO = INVITATION + [
    (CHOICE, "click", "date-no"),
    (CHOICE + 0.1, "expect", "letgo"),
    (FACE + 0.5, "expect", "face"),         # straight to the crying face: no chase, no glitch
    (FACE + duration("face") + 1.0, "expect", "black"),
]

# --- NO: four NOs, the shatter and escape, a chase played with one jump (the course always ends, in
# under 30 s even without jumping), the catch, the ending, and black for good ---------------------------------------------
NO = 3.0
NO_4 = NO + 3.0                             # each NO waits out the previous beat's input lock
CHASE = NO_4 + duration("no-4")
CORNERED = CHASE + 30.0                     # SPEC C2: under 30 s even without jumping
GLITCH = CORNERED + 0.5

NO_PLAN = [
    (duration("intro") + 0.3, "expect", "letter"),
    (NO - 0.3, "move", "no"),
    (NO, "click", "no"),
    (NO + 0.1, "expect", "no-1"),
    (NO + 0.8, "click", "no"),
    (NO + 0.9, "expect", "no-2"),
    (NO + 1.9, "click", "no"),
    (NO + 2.0, "expect", "no-3"),
    (NO_4, "click", "no"),                  # NO now sits in YES's old slot
    (NO_4 + 0.1, "expect", "no-4"),
    (NO_4 + 1.0, "click", "yes"),           # locked to the end of the route: nothing happens
    (NO_4 + 1.1, "expect", "no-4"),
    (CHASE + 0.5, "expect", "chase"),
    (CHASE + 2.0, "key", SPACE),            # one jump, so the controls are exercised
    (CORNERED, "expect", "cornered"),
    (GLITCH, "click", "no"),                # caught
    (GLITCH + 0.1, "expect", "glitch"),
    (GLITCH + duration("glitch") + 0.5, "expect", "face"),
    (GLITCH + duration("glitch") + duration("face") + 1.0, "expect", "black"),
    (GLITCH + duration("glitch") + duration("face") + 2.0, "key", SPACE),   # E4: nothing responds
    (GLITCH + duration("glitch") + duration("face") + 2.5, "expect", "black"),
]

PLANS = {"yes, then yes": DATE_YES, "yes, then no": DATE_NO, "no": NO_PLAN}
