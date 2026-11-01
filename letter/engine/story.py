"""The narrative state machine for both routes (SPEC §8). Pure: no pygame, unit-tested.

A phase either waits for an event or is timed and hands off on its own. Events count only in the
phases listed for them and only once that phase's input lock has passed, so double clicks and late
clicks can never start anything twice.
"""
from letter import config

YES_ROUTE = ("yes-reveal", "night", "seed", "grown", "bloom", "bloomed")
NO_ROUTE = ("no-1", "no-2", "no-3", "no-4", "chase", "cornered", "glitch", "face", "black")

# timed phases: phase -> next phase (durations come from config.T)
TIMED = {"intro": "letter", "yes-reveal": "night", "night": "seed", "seed": "grown", "bloom": "bloomed",
         "no-4": "chase", "glitch": "face", "face": "black"}
# waiting phases whose first seconds are an animation that must finish before clicks count
LOCKED_START = ("no-1", "no-2", "no-3")
EVENTS = {
    ("letter", "yes"): "yes-reveal", ("no-1", "yes"): "yes-reveal",
    ("no-2", "yes"): "yes-reveal", ("no-3", "yes"): "yes-reveal",
    ("letter", "no"): "no-1", ("no-1", "no"): "no-2", ("no-2", "no"): "no-3", ("no-3", "no"): "no-4",
    ("grown", "flower"): "bloom",
    ("chase", "course-end"): "cornered",
    ("cornered", "catch"): "glitch",
}
EVENT_NAMES = sorted({e for _, e in EVENTS})


def duration(phase):
    """Seconds a timed phase (or a waiting phase's opening lock) lasts at the current SPEED."""
    return config.T[phase] / config.SPEED if phase in config.T else None


def locked(phase, since, t):
    """True while clicks must be ignored: timed phases, and the opening animation of a question."""
    if phase in TIMED or phase == "black":
        return True
    return phase in LOCKED_START and t - since < duration(phase)


def step(phase, since, t, event=None):
    """-> (phase, since). Handles one event, then any timed hand-offs that are due."""
    if event is not None:
        nxt = EVENTS.get((phase, event))
        if nxt is not None and not locked(phase, since, t):
            return nxt, t
        return phase, since
    while phase in TIMED and t - since >= duration(phase):  # a long gap can cross several phases
        phase, since = TIMED[phase], since + duration(phase)
    return phase, since


def route(phase):
    return "yes" if phase in YES_ROUTE else "no" if phase in NO_ROUTE else None
