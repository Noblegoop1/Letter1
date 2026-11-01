"""The soundtrack (SPEC §21): what plays when, and how loud. Pure data, read by letter.engine.audio.

CUES: phase -> [(seconds into the phase at SPEED 1, action, name, ...)], each fired once as the phase passes it:
- ("play", name[, vol]): a one-shot effect or music cue;
- ("loop", name, vol, fade): start a loop, or ramp it, over `fade` seconds;
- ("fade", name, vol, secs): ramp a loop ("*": every loop); at 0 it stops;
- ("stop",): silence, at once.
vol multiplies the sound's LEVEL. Effect files are loudness-matched by tools/sounds.py and the music by
letter.art.music, so LEVEL alone sets the mix.
"""
LEVEL = {
    # music (letter.art.music)
    "theme": 0.6, "theme_minor": 0.55, "night": 0.55, "chase": 0.4, "tension": 0.45,
    "grow": 0.5, "bloom": 0.6, "motif": 0.75, "joy": 0.75, "letgo": 0.6, "sad": 0.7,
    # ambience
    "crickets": 0.5, "wind": 0.3, "heartbeat": 0.7,
    # effects (assets/sounds)
    "hover": 0.18, "press": 0.35, "bell": 0.35, "pencil_short": 0.3, "pencil": 0.3, "flap": 0.4, "sheet": 0.35,
    "page": 0.45, "quake": 0.55, "swoosh": 0.45, "crack": 0.5, "shatter": 0.5, "hop": 0.3, "land": 0.3,
    "riser": 0.45, "whoosh": 0.35, "wand": 0.3, "poof": 0.3, "fairy": 0.35, "arrive": 0.2, "appear": 0.3,
    "jump": 0.22, "stumble": 0.35, "stinger": 0.35, "glitch": 0.55, "static": 0.3, "powerdown": 0.5,
}
LEVEL = {name: min(1.0, 1.5 * v) for name, v in LEVEL.items()}   # the balance above, 3.5 dB up overall:
# recorded runs (tools/listen.py) peaked at -6 dBFS and sat near -24 dB RMS, quiet beside other apps

CUES = {
    "intro": [(0.0, "loop", "theme", 1.0, 2.0), (0.4, "play", "pencil_short")],
    # YES
    "yes-reveal": [(0.0, "play", "press"), (0.0, "play", "bell"), (0.1, "play", "flap"), (0.4, "play", "sheet"),
                   (0.5, "fade", "theme", 0.0, 2.5), (2.0, "play", "whoosh")],   # the whoosh peaks as night falls
    "night": [(0.0, "loop", "crickets", 1.0, 2.5), (0.0, "loop", "wind", 1.0, 3.0), (0.0, "loop", "night", 1.0, 3.0)],
    "seed": [(0.4, "play", "wand"), (1.2, "play", "poof"), (2.0, "play", "grow")],
    "bloom": [(0.0, "play", "bloom"), (0.0, "play", "fairy")],
    "bloomed": [(0.5, "play", "arrive")],
    "gather": [(0.0, "fade", "night", 0.45, 1.5), (0.2, "play", "motif")],
    "invite": [(0.0, "play", "appear")],
    "farewell": [(0.0, "play", "press"), (0.0, "play", "bell"), (0.1, "play", "whoosh"),
                 (0.3, "fade", "night", 1.0, 2.0), (4.5, "fade", "*", 0.0, 3.5)],
    "joy": [(0.0, "play", "joy")],
    "letgo": [(0.0, "play", "press"), (0.0, "play", "letgo"), (0.0, "fade", "*", 0.0, 2.5)],
    # NO
    "no-1": [(0.0, "play", "press"), (0.0, "play", "page"), (0.0, "fade", "theme", 0.0, 1.5),
             (0.0, "loop", "theme_minor", 1.0, 1.5)],
    "no-2": [(0.0, "play", "press"), (0.0, "play", "quake"), (0.0, "fade", "theme_minor", 0.35, 0.15),
             (0.9, "fade", "theme_minor", 1.0, 1.2)],
    "no-3": [(0.0, "play", "press"), (0.0, "play", "swoosh")],
    "no-4": [(0.0, "play", "press"), (0.0, "fade", "*", 0.0, 0.8), (0.3, "play", "crack"), (0.8, "play", "shatter"),
             (0.85, "play", "poof", 0.6), (2.4, "play", "pencil"), (4.5, "play", "flap"), (4.8, "play", "sheet"),
             (5.7, "play", "hop"), (6.4, "play", "land"), (6.5, "play", "riser")],
    "chase": [(0.0, "loop", "chase", 1.0, 0.6)],
    "cornered": [(0.0, "fade", "chase", 0.0, 1.2), (0.0, "loop", "tension", 1.0, 2.0), (0.0, "play", "stinger")],
    "glitch": [(0.0, "stop"), (0.4, "play", "glitch"), (0.5, "play", "static"), (1.3, "play", "glitch", 0.8),
               (2.4, "play", "powerdown")],
    "face": [(0.0, "play", "sad")],
}


def heartbeat(distance):
    """The cornered heartbeat's vol (times its LEVEL) for a pointer `distance` logical px from the NO button:
    a quiet pulse far away, full when close (the same smooth curve as the button's tremble)."""
    from letter.art import ending
    lo, hi = ending.shake_amplitude(1e9), ending.shake_amplitude(0.0)
    return 0.2 + 0.8 * (ending.shake_amplitude(distance) - lo) / (hi - lo)
