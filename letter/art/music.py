"""The music, written note by note with NumPy (SPEC §21). No music files ship and no licence applies.

One theme in F major runs through the piece: a music-box waltz on the letter, the same tune in F minor once
she says NO, its first four bars on celesta as the fireflies form the question (stopping unresolved on the
dominant), and its last two bars resolving to F major if she says yes. Everything else (the night pad, the
chase, the drone, the small cues) stays in the same keys, F major and D minor.

Every track is float32 stereo, shape (frames, 2), at RATE: 22.05 kHz holds everything these soft instruments
play (up to 11 kHz) at half the work, and SDL resamples it to the device when it becomes a sound. Loops wrap
their note tails and their reverb around the end, so they repeat without a seam; one-shot cues end on
silence.
"""
import math

import numpy as np

RATE = 22050
_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def midi(name):
    """'Bb4' -> 70."""
    pc = _PC[name[0]] + (-1 if name[1] == "b" else 1 if name[1] == "#" else 0)
    return 12 * (int(name.lstrip("ABCDEFGb#")) + 1) + pc


def hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def _smooth(n):
    """The first length >= n whose only prime factors are 2, 3, 5 and 7, so its FFT is fast."""
    while True:
        m = n
        for p in (2, 3, 5, 7):
            while m % p == 0:
                m //= p
        if m == 1:
            return n
        n += 1


class Score:
    """A stereo buffer that notes are added into. A loop wraps whatever runs past its end back to the start."""

    def __init__(self, seconds, loop, rate=RATE, exact=False):
        n = round(seconds * rate)
        self.rate, self.loop = rate, loop
        self.buf = np.zeros((n if exact or not loop else _smooth(n), 2), np.float32)
        self.cache = {}

    @property
    def seconds(self):
        return len(self.buf) / self.rate

    def add(self, start, sound, pan=0.0, vel=1.0):
        a = (pan + 1) * math.pi / 4   # equal-power pan for a mono sound
        gains = (vel * math.cos(a), vel * math.sin(a)) if sound.ndim == 1 else (vel, vel)
        n, i, done = len(self.buf), round(start * self.rate), 0
        if self.loop:
            i %= n
        while done < len(sound) and i < n:   # a loop wraps the rest back to its start
            k = min(len(sound) - done, n - i)
            for c in (0, 1):
                part = sound[done:done + k] if sound.ndim == 1 else sound[done:done + k, c]
                self.buf[i:i + k, c] += part * np.float32(gains[c])
            done, i = done + k, (0 if self.loop else n)

    def note(self, instrument, start, name, vel=1.0, pan=0.0, **kw):
        """Add one note; each (instrument, pitch, options) is rendered once and reused at any velocity."""
        key = (instrument.__name__, name, tuple(sorted(kw.items())))
        if key not in self.cache:
            self.cache[key] = instrument(midi(name) if isinstance(name, str) else name, rate=self.rate, **kw)
        self.add(start, self.cache[key], pan, vel)


# --- instruments (mono unless noted; unit velocity) ------------------------------------------------------
def _t(seconds, rate):
    return np.arange(round(seconds * rate), dtype=np.float64) / rate


def _partials(f, tau, parts, attack, rate):
    """Sum of decaying sines, parts = [(ratio, amplitude, decay as a fraction of tau)], skipping any above
    Nyquist. The note lasts until its fundamental is 30 dB down, and fades over its last fifth."""
    t = _t(tau * 3.5, rate)
    t32 = t.astype(np.float32)
    y = np.zeros(len(t), np.float32)
    for ratio, amp, k in parts:
        if ratio * f < rate * 0.45:   # the phase in float64 (long notes), the rest in float32 (fast)
            x = ratio * f * t
            phase = (x - np.floor(x)).astype(np.float32)
            y += np.float32(amp) * np.sin(np.float32(2 * np.pi) * phase) * np.exp(t32 / np.float32(-tau * k))
    y *= np.minimum(np.float32(1.0), t32 / np.float32(attack))
    y *= np.minimum(np.float32(1.0), (t32[-1] - t32) / np.float32(tau * 0.7))
    return y


def tine(note, rate=RATE):
    """A music-box tine: a ringing sine, a little octave, and the bright metal overtone that dies at once."""
    f = hz(note)
    tau = float(np.clip(1.3 * math.sqrt(440 / f), 0.45, 2.0))
    return _partials(f, tau, [(1, 1.0, 1), (2, 0.16, 0.3), (6.27, 0.28, 0.05 / tau)], 0.002, rate)


def celesta(note, rate=RATE):
    """Soft hammered bars over resonators: nearly harmonic and round."""
    f = hz(note)
    tau = float(np.clip(1.1 * math.sqrt(523 / f), 0.4, 1.8))
    return _partials(f, tau, [(1, 1.0, 1), (2, 0.22, 1 / 2), (3, 0.07, 1 / 3), (4.1, 0.03, 1 / 4)], 0.004, rate)


def glock(note, rate=RATE):
    """A glockenspiel bar: the free bar's inharmonic modes, bright and bell-like."""
    f = hz(note)
    tau = float(np.clip(1.5 * math.sqrt(880 / f), 0.5, 2.4))
    return _partials(f, tau, [(1, 1.0, 1), (2.76, 0.3, 1 / 3), (5.40, 0.12, 1 / 6), (8.93, 0.05, 1 / 9)], 0.001, rate)


_N = 4096


def _table(harmonics):
    k = np.arange(_N) / _N
    return sum(a * np.sin(2 * np.pi * h * k) for h, a in enumerate(harmonics, 1)).astype(np.float32)


_WARM = _table((1.0, 0.35, 0.12, 0.05))
_SQUARE = _table((1.0, 0, 1 / 3, 0, 1 / 5, 0, 1 / 7, 0, 1 / 9))
_DULL = _table((1.0, 0.5, 0.2, 0.08))


def _osc(table, f, t, phase=0.0):
    return table[((f * t + phase) * _N).astype(np.int64) & (_N - 1)]


def pad(notes, hold, attack, release, rate=RATE):
    """A soft chord (stereo): three slightly detuned voices per note spread across the field, so the chord
    breathes; raised-cosine attack and release."""
    t = _t(hold + release, rate)
    env = np.sin(np.pi / 2 * np.minimum(1.0, t / attack)) ** 2
    after = np.clip((t - hold) / release, 0, 1)
    env *= np.cos(np.pi / 2 * after) ** 2
    out = np.zeros((len(t), 2), np.float32)
    for i, note in enumerate(notes):
        f = hz(midi(note) if isinstance(note, str) else note)
        for cents, pan in ((-7, -0.6), (0, 0.0), (7, 0.6)):
            y = _osc(_WARM, f * 2 ** (cents / 1200), t, phase=0.37 * i + 0.21 * cents)
            a = (pan + 1) * math.pi / 4
            out[:, 0] += y * math.cos(a)
            out[:, 1] += y * math.sin(a)
    return out * (env / (3 * len(notes)))[:, None].astype(np.float32)


def sub(note, hold, attack, release, rate=RATE):
    """A pure low sine under the chords."""
    t = _t(hold + release, rate)
    env = np.sin(np.pi / 2 * np.minimum(1.0, t / attack)) ** 2 * np.cos(np.pi / 2 * np.clip((t - hold) / release, 0, 1)) ** 2
    return (np.sin(2 * np.pi * hz(note) * t) * env).astype(np.float32)


def pluck(note, rate=RATE, bright=True, decay=0.12):
    """A plucked chiptune string: a square wave that dulls as it fades."""
    f, t = hz(note), _t(decay * 5, rate)
    w = np.exp(-t / 0.05)
    tone = (_osc(_SQUARE if bright else _DULL, f, t) * w + _osc(_DULL, f, t) * (1 - w))
    return (tone * np.exp(-t / decay) * np.minimum(1.0, t / 0.002)).astype(np.float32)


def thump(note=None, rate=RATE):
    """A soft kick or heartbeat: a low sine that drops in pitch as it dies."""
    t = _t(0.5, rate)
    f = 50 + 45 * np.exp(-t / 0.03)
    return (np.sin(2 * np.pi * np.cumsum(f) / rate) * np.exp(-t / 0.09) * np.minimum(1.0, t / 0.003)).astype(np.float32)


def noise(note=None, rate=RATE, decay=0.03, seed=0):
    """A hat (short) or a snare-ish brush (longer): bright noise with a fast fade."""
    t = _t(decay * 6, rate)
    x = np.random.default_rng(seed).standard_normal(len(t))
    x = np.diff(x, prepend=0.0)   # tilt it bright
    return (x * np.exp(-t / decay) * 0.5).astype(np.float32)


# --- mixing ------------------------------------------------------------------------------------------------
def reverb(score, seconds, wet, seed=1):
    """A hall: stereo decaying noise as the impulse response, convolved by FFT (circularly for a loop, so the
    tail of the end rings into the start)."""
    buf, rate = score.buf, score.rate
    n = len(buf)
    length = min(n, round(seconds * 1.2 * rate))
    t = np.arange(length) / rate
    ir = np.random.default_rng(seed).standard_normal((length, 2)) * np.exp(-6.9 * t / seconds)[:, None]
    c = np.cumsum(ir, axis=0)   # darken it: a 6-sample running mean
    ir[6:] = (c[6:] - c[:-6]) / 6
    ir[:round(0.015 * rate)] = 0.0      # pre-delay
    ir /= np.sqrt((ir ** 2).sum(axis=0))
    size = n if score.loop else _smooth(n + length)
    spec = np.fft.rfft(buf, size, axis=0) * np.fft.rfft(ir, size, axis=0)
    score.buf = (buf + wet * np.fft.irfft(spec, size, axis=0)[:n]).astype(np.float32)


def master(score, rms_db=-20.0, fade=0.0):
    """Bring the loudest second to rms_db, soft-limit the peaks at -1 dBFS, and fade out the end (cues)."""
    buf = score.buf
    if fade:
        k = round(fade * score.rate)
        buf[-k:] *= (np.cos(np.linspace(0, np.pi / 2, k, dtype=np.float32)) ** 2)[:, None]
    power = (buf ** 2).mean(axis=1)
    c = np.concatenate([[0.0], np.cumsum(power, dtype=np.float64)])
    w = min(len(power), score.rate)
    loud = math.sqrt(max(((c[w:] - c[:-w]) / w).max(), 1e-12))
    ceiling = 10 ** (-1 / 20)
    return np.float32(ceiling) * np.tanh(buf * np.float32(10 ** (rms_db / 20) / loud / ceiling))


# --- the theme ----------------------------------------------------------------------------------------------
# sixteen bars of 3/4 in F major: (note, beats) per bar, None a rest
MELODY = [
    [("A4", 2), ("C5", 1)], [("D5", 2), ("C5", .5), ("A4", .5)], [("Bb4", 1), ("D5", 1), ("F5", 1)],
    [("E5", 2), ("G4", 1)], [("A4", 1), ("C5", 1), ("F5", 1)], [("E5", 2), ("C5", 1)],
    [("D5", 1), ("C5", 1), ("E5", 1)], [("F5", 3)],
    [("F5", 1), ("E5", 1), ("D5", 1)], [("D5", 2), ("Bb4", 1)], [("C5", 1), ("A4", 1), ("C5", 1)],
    [("G4", 1), ("C5", 1), ("E5", 1)], [("F5", 2), ("A5", 1)], [("G5", 1), ("F5", 1), ("D5", 1)],
    [("Bb4", 1), ("C5", 1), ("E5", 1)], [("F5", 2), (None, 1)],
]
# the chord on each beat of each bar (a bar's chord holds until the next one named)
CHORDS = [{0: "F"}, {0: "Dm"}, {0: "Bb"}, {0: "C"}, {0: "F"}, {0: "Am"}, {0: "Bb", 1: "C"}, {0: "F"},
          {0: "Dm"}, {0: "Bb"}, {0: "F"}, {0: "C"}, {0: "Dm"}, {0: "Bb"}, {0: "Gm", 1: "C"}, {0: "F"}]
TRIADS = {"F": "FAC", "Dm": "DFA", "Bb": ("Bb", "D", "F"), "C": "CEG", "Am": "ACE", "Gm": ("G", "Bb", "D")}
MINOR = {"A": "Ab", "D": "Db"}   # F major -> F harmonic minor (E stays: the leading tone)


def _pc(name):
    return _PC[name[0]] + (-1 if len(name) > 1 and name[1] == "b" else 0)


def _in_range(pc, low):
    """The pitch class pc as the MIDI note at or just above low."""
    return low + (pc - low) % 12


def _minor_name(name):
    base = name.rstrip("0123456789")
    return MINOR.get(base, base) + name[len(base):]


def _chord_pcs(chord, minor):
    names = TRIADS[chord]
    return [_pc(MINOR.get(n, n) if minor else n) for n in names]


def theme(minor=False, rate=RATE):
    """The letter's music box: melody over an oom-pah-pah of bass and chord tones, a soft pad beneath."""
    bpm = 66 if minor else 76
    beat = 60 / bpm
    s = Score(48 * beat, loop=True, rate=rate)
    beat = s.seconds / 48   # the loop's exact length sets the tempo
    jitter = np.random.default_rng(5).normal(0, 0.006, 200)
    j = 0
    for bar, (notes, chords) in enumerate(zip(MELODY, CHORDS)):
        t0, b = bar * 3 * beat, 0.0
        for name, beats in notes:
            if name:
                s.note(tine, t0 + b * beat + jitter[j], _minor_name(name) if minor else name, vel=0.9, pan=0.15)
                j += 1
            b += beats
        current = None
        for k in range(3):
            chord = chords.get(k, current)
            pcs = _chord_pcs(chord, minor)
            if chord != current:
                s.note(tine, t0 + k * beat + jitter[j], _in_range(pcs[0], 41), vel=0.55, pan=-0.25)
                hold = (3 - k if k + 1 not in chords else 1) * beat
                s.add(t0 + k * beat, pad([_in_range(p, 53) for p in pcs], hold, 0.35 * beat, 1.2 * beat, rate), vel=0.35)
            else:
                for p in pcs[1:]:
                    s.note(tine, t0 + k * beat + jitter[j], _in_range(p, 57), vel=0.32, pan=-0.25)
            current, j = chord, j + 1
    reverb(s, 2.2, 0.32)
    return master(s, -20)


# --- the night ----------------------------------------------------------------------------------------------
NIGHT = [("F2", ("F3", "C4", "E4", "G4", "A4")), ("D2", ("D3", "A3", "C4", "E4", "F4")),
         ("Bb1", ("Bb2", "F3", "A3", "C4", "D4")), ("C2", ("C3", "G3", "A3", "D4", "E4"))]


def night(rate=RATE):
    """A slow pad, a chord every 8 s, each breathing into the next, with glockenspiel stars on its tones."""
    s = Score(32.0, loop=True, rate=rate)
    span = s.seconds / len(NIGHT)
    rng = np.random.default_rng(11)
    for i, (root, notes) in enumerate(NIGHT):
        t0 = i * span
        s.add(t0, pad(notes, span, 2.5, 3.0, rate), vel=1.0)
        s.add(t0, sub(midi(root), span, 1.0, 2.0, rate), vel=0.16)
        t = t0 + rng.uniform(0.3, 1.2)
        while t < t0 + span:
            pc = _pc(rng.choice(notes).rstrip("0123456789"))
            s.note(glock, t, _in_range(pc, 77 + 12 * int(rng.random() < 0.3)), vel=rng.uniform(0.08, 0.2),
                   pan=rng.uniform(-0.7, 0.7))
            t += rng.exponential(1.7) + 0.35
    reverb(s, 3.5, 0.5)
    return master(s, -20)


# --- the chase ----------------------------------------------------------------------------------------------
CHASE_CHORDS = [("D", "F", "A"), ("D", "F", "A"), ("Bb", "D", "F"), ("Bb", "D", "F"),
                ("G", "Bb", "D"), ("G", "Bb", "D"), ("A", "C#", "E"), ("A", "C#", "E")]


def chase(rate=RATE):
    """D minor at 120 bpm: a plucked bass on the eighths, a chiptune arpeggio on the sixteenths, a soft kick
    on one and three, a brush on two and four, and hats between."""
    s = Score(16.0, loop=True, rate=rate)
    beat = s.seconds / 32
    pattern = (0, 1, 2, 3, 2, 1, 0, 1)
    for bar, triad in enumerate(CHASE_CHORDS):
        t0 = bar * 4 * beat
        pcs = [_PC[n[0]] + (-1 if n[1:] == "b" else 1 if n[1:] == "#" else 0) for n in triad]
        root = _in_range(pcs[0], 38)
        for e in range(8):
            s.note(pluck, t0 + e * beat / 2, root + 12 * (e % 2), vel=0.55, bright=False, decay=0.16)
            s.note(noise, t0 + (e + 0.5) * beat / 2, 0, vel=0.12 if e % 2 else 0.08, pan=0.3)
        for k in range(16):
            i = pattern[k % 8]
            note = _in_range(pcs[i % 3], 62) + 12 * (i // 3)
            s.note(pluck, t0 + k * beat / 4, note, vel=0.2, pan=0.25 if k % 2 else -0.25)
        for k in (0, 2):
            s.note(thump, t0 + k * beat, 0, vel=0.9)
        for k in (1, 3):
            s.note(noise, t0 + k * beat, 0, vel=0.35, decay=0.12, seed=3)
    reverb(s, 0.8, 0.12)
    return master(s, -19)


def tension(rate=RATE):
    """Cornered: a low D drone that swells once per loop."""
    s = Score(8.0, loop=True, rate=rate, exact=True)
    n, k = len(s.buf), rate   # its sines don't fit 8 s in whole cycles: one extra second crossfades the seam
    drone = pad(("D2", "A2", "D3"), (n + k) / rate, 0.001, 0.001, rate)[:n + k]
    u = np.linspace(0, np.pi / 2, k, dtype=np.float32)[:, None]
    drone = np.concatenate([drone[:k] * np.sin(u) + drone[n:] * np.cos(u), drone[k:n]])
    t = np.arange(n) / rate
    s.add(0, drone * (0.55 + 0.45 * np.sin(2 * np.pi * t / s.seconds))[:, None].astype(np.float32))
    reverb(s, 2.5, 0.4)
    return master(s, -22)


# --- cues ---------------------------------------------------------------------------------------------------
def grow(rate=RATE):
    """The stem grows (4.5 s): a glockenspiel climbing F major, quickening, over a chord that swells with it."""
    s = Score(7.0, loop=False, rate=rate)
    notes = ("F4", "A4", "C5", "D5", "F5", "G5", "A5", "C6", "D6", "F6", "G6", "A6", "C7")
    for i, name in enumerate(notes):
        u = i / (len(notes) - 1)
        s.note(glock, 4.4 * u ** 0.7, name, vel=0.25 + 0.3 * u, pan=-0.4 + 0.8 * u)
    s.add(0.0, pad(("F3", "A3", "C4", "E4"), 4.5, 4.0, 2.5, rate), vel=0.45)
    reverb(s, 3.0, 0.45)
    return master(s, -19, fade=0.5)


def bloom(rate=RATE):
    """The flower opens: a warm Fmaj9 swells under a quick celesta run and one high bell."""
    s = Score(5.5, loop=False, rate=rate)
    s.add(0.0, pad(("F3", "A3", "C4", "E4", "G4"), 1.5, 0.5, 2.8, rate), vel=1.2)
    s.add(0.0, sub(midi("F2"), 1.5, 0.3, 2.5, rate), vel=0.2)
    for i, name in enumerate(("C5", "E5", "F5", "A5", "C6", "E6", "F6")):
        s.note(celesta, 0.1 * i, name, vel=0.35, pan=-0.5 + i / 6)
    s.note(glock, 0.8, "F6", vel=0.3)
    reverb(s, 3.0, 0.5)
    return master(s, -18, fade=0.6)


def motif(rate=RATE):
    """The fireflies form the question: the theme's first four bars on celesta, ending on the dominant,
    unresolved, while the question waits."""
    s = Score(10.0, loop=False, rate=rate)
    beat = 0.55
    for bar in range(4):
        t0, b = bar * 3 * beat, 0.0
        for name, beats in MELODY[bar]:
            s.note(celesta, t0 + b * beat, name, vel=0.6, pan=0.1)
            s.note(glock, t0 + b * beat, midi(name) + 12, vel=0.08, pan=0.3)
            b += beats
        pcs = _chord_pcs(CHORDS[bar][0], False)
        last = bar == 3
        s.add(t0, pad([_in_range(p, 53) for p in pcs], (6 if last else 3) * beat, 0.4, 1.5 if last else 0.8, rate),
              vel=0.4)
    reverb(s, 3.5, 0.5)
    return master(s, -19, fade=1.0)


def joy(rate=RATE):
    """YES (7.5 s on black): the theme's last two bars resolve to F major as she smiles, a two-note chime as
    the eyes turn to hearts, one soft heartbeat on the pulse; quiet by 7.2 s, when the app closes."""
    s = Score(7.4, loop=False, rate=rate)
    beat = 0.6
    for k, (name, chord) in enumerate((("D5", "Bb"), ("C5", "C"), ("E5", None), ("F5", "F"))):
        t = 0.6 + k * beat
        s.note(tine, t, name, vel=0.85 if k < 3 else 1.0, pan=0.15)
        if chord:
            pcs = _chord_pcs(chord, False)
            s.note(tine, t, _in_range(pcs[0], 41), vel=0.5, pan=-0.25)
            hold = beat if chord != "F" else 3.0
            s.add(t, pad([_in_range(p, 53) for p in pcs], hold, 0.2, 1.4 if chord == "F" else 0.6, rate), vel=0.4)
    for i, name in enumerate(("F5", "A5", "C6", "F6")):
        s.note(celesta, 2.4 + 0.1 * i, name, vel=0.3, pan=-0.3 + 0.2 * i)
    s.note(glock, 3.2, "A5", vel=0.35, pan=-0.2)
    s.note(glock, 3.45, "F6", vel=0.4, pan=0.2)
    s.note(thump, 4.6, 0, vel=0.7)
    s.note(thump, 4.82, 0, vel=0.45)
    reverb(s, 2.5, 0.4)
    return master(s, -19, fade=1.6)


def letgo(rate=RATE):
    """NO on the invitation: a celesta line falls through F minor as the message drifts apart."""
    s = Score(5.0, loop=False, rate=rate)
    for t, name, v in ((0.0, "C6", 0.45), (0.3, "Ab5", 0.4), (0.6, "F5", 0.38), (0.95, "Db5", 0.34), (1.4, "C5", 0.32)):
        s.note(celesta, t, name, vel=v, pan=0.1)
    s.add(0.0, pad(("Db3", "F3", "Ab3"), 1.4, 0.3, 0.8, rate), vel=0.45)
    s.add(1.4, pad(("F3", "Ab3", "C4"), 1.0, 0.6, 2.2, rate), vel=0.45)
    reverb(s, 4.0, 0.55)
    return master(s, -20, fade=1.0)


def sad(rate=RATE):
    """Under the face (11.8 s, from the face phase's start): slow music-box notes in F minor, one high note
    as the tear lets go (4.8 s), the last resolving to F, all fading with the face (9.3 to 11.8 s)."""
    s = Score(11.8, loop=False, rate=rate)
    s.add(0.6, pad(("F2", "C3", "Ab3"), 8.7, 2.0, 2.5, rate), vel=0.45)
    for t, name, v in ((1.0, "Ab4", 0.55), (2.0, "C5", 0.5), (3.0, "Db5", 0.55), (4.0, "C5", 0.45),
                       (4.8, "F6", 0.3), (5.4, "Ab4", 0.45), (6.6, "Bb4", 0.45), (7.4, "G4", 0.4), (8.4, "F4", 0.5)):
        s.note(tine, t, name, vel=v, pan=0.1)
    reverb(s, 4.0, 0.5)
    buf = master(s, -21)
    t = np.arange(len(buf)) / rate
    return (buf * np.cos(np.pi / 2 * np.clip((t - 9.3) / 2.5, 0, 1))[:, None] ** 2).astype(np.float32)


# name -> (make, loops); in the order the app needs them, so the first is ready first
TRACKS = {
    "theme": (theme, True),
    "theme_minor": (lambda rate=RATE: theme(minor=True, rate=rate), True),
    "night": (night, True), "grow": (grow, False), "bloom": (bloom, False), "motif": (motif, False),
    "joy": (joy, False), "letgo": (letgo, False), "sad": (sad, False),
    "chase": (chase, True), "tension": (tension, True),
}
