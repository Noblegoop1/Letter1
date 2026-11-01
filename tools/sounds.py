"""Make assets/sounds/ from the downloaded packs in reference/audio-sources/ (SPEC §21).

Each sound the app uses is cut from its pack, faded, mixed to mono, loudness-matched and written as a 16-bit
WAV. The packs' licences allow sounds built into the app but not the raw files on their own, so neither the
packs nor assets/sounds/ are in git; this script is how a checkout gets them back (build.py runs it).

Usage (project root, with the venv):  .venv\\Scripts\\python tools\\sounds.py
"""
import io
import os
import sys
import wave
import zipfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "reference", "audio-sources")
OUT = os.path.join(ROOT, "assets", "sounds")
PACKS = {
    "ds": ("dailysounds/DailySounds_sampler_v1.zip", "DailySounds - Game Starter Sound Pack (Free)/WAV/"),
    "wl": ("willosuna/free-game-ui-sound-pack.zip", "free_game_ui_sounds/wav/"),
    "mk": ("mixkit", ""),
}
# name -> (pack, file, cut). cut: start/end s, fade in/out s, "loop" s of crossfade for a seamless loop,
# "rms" the loudness target in dBFS (default -16: the loudest 300 ms of an effect; ambience is quieter and
# measured over the whole file)
SOUNDS = {
    # the letter
    "hover": ("ds", "DS_UI_Soft_Tap_01.wav", {}),
    "press": ("mk", "2577-interface-device-click.wav", {"end": 0.25}),
    "bell": ("ds", "DS_UI_Clear_Bell_Ding_01.wav", {}),
    "pencil_short": ("mk", "3194-writing-pencil.wav", {"end": 1.25, "fade_out": 0.25}),
    "pencil": ("mk", "3194-writing-pencil.wav", {"end": 1.65, "fade_out": 0.25}),
    "flap": ("mk", "1530-paper-slide.wav", {"end": 0.6, "fade_out": 0.1}),
    "sheet": ("mk", "2379-papers-being-moved-or-wrinkling.wav", {"start": 0.7, "end": 1.9, "fade_out": 0.3}),
    "page": ("mk", "1104-page-turn-single.wav", {}),
    # the NO route on the letter
    "quake": ("ds", "DS_Cinematic_Deep_Impact_Boom_01.wav", {"rms": -13}),
    "swoosh": ("ds", "DS_Transition_Swift_Swoosh_01.wav", {}),
    "crack": ("wl", "game/block_break.wav", {}),
    "shatter": ("wl", "game/shield_break.wav", {}),
    "hop": ("wl", "game/jump.wav", {}),
    "land": ("wl", "game/land.wav", {}),
    "riser": ("ds", "DS_Transition_Cinematic_Riser_01.wav", {"start": 1.4, "fade_in": 0.1}),
    # the night
    "whoosh": ("mk", "869-fairy-sparkle-whoosh.wav", {"start": 0.4, "end": 4.5, "fade_out": 1.0}),
    "wand": ("mk", "3062-magic-wand-sparkle.wav", {"end": 1.4, "fade_out": 0.3}),
    "poof": ("mk", "3082-magic-sparkle-poof-hit.wav", {"end": 2.0, "fade_out": 0.5}),
    "fairy": ("mk", "871-fairy-magic-sparkle.wav", {"start": 0.15, "end": 1.0, "fade_out": 0.2}),
    "arrive": ("mk", "866-fairy-arcade-sparkle.wav", {"fade_out": 0.3}),
    "appear": ("mk", "2573-interface-option-select.wav", {"end": 0.8, "fade_out": 0.3}),
    "crickets": ("mk", "1789-summer-night-crickets-loop.wav", {"rms": -24}),   # already a loop
    "wind": ("mk", "2658-wind-blowing-ambience.wav", {"start": 10.0, "end": 30.0, "loop": 2.0, "rms": -24}),
    # the chase and the ending
    "jump": ("wl", "game/jump.wav", {}),
    "stumble": ("wl", "game/hurt.wav", {}),
    "stinger": ("ds", "DS_Horror_Horror_Stinger_01.wav", {}),
    "heartbeat": ("ds", "DS_Horror_Fast_Heartbeat_01.wav", {"end": 2.09}),   # three beats, 0.697 s apart: loops
    "glitch": ("ds", "DS_SciFi_Digital_Glitch_01.wav", {}),
    "static": ("ds", "DS_Foley_Taser_Zap.wav", {"start": 0.1, "end": 0.95, "fade_in": 0.02, "fade_out": 0.15}),
    "powerdown": ("ds", "DS_Game_Power_Down_01.wav", {}),
}
LOOPS = ("crickets", "wind", "heartbeat")   # measured over the whole file, not the loudest 300 ms
PEAK = 10 ** (-1 / 20)                       # -1 dBFS
LIMIT = 10 ** (10 / 20)                      # how far a peak may be driven into the soft limiter


def read_wav(data):
    """bytes of a PCM WAV -> (rate, float32 array of shape (frames, channels) in -1..1)."""
    with wave.open(io.BytesIO(data)) as w:
        rate, ch, width, raw = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.readframes(w.getnframes())
    if width == 3:   # 24-bit: widen each sample to 32 bits, keeping the sign
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        x = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        x = np.where(x >= 1 << 23, x - (1 << 24), x).astype(np.float32) / (1 << 23)
    elif width == 2:
        x = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
    else:
        raise ValueError("unsupported sample width %d" % width)
    return rate, x.reshape(-1, ch)


def write_wav(path, rate, mono):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(mono, -1, 1) * 32767).round().astype("<i2").tobytes())


def source(pack, name):
    """The raw bytes of one file in a pack."""
    path, prefix = PACKS[pack]
    full = os.path.join(SRC, path)
    if full.endswith(".zip"):
        with zipfile.ZipFile(full) as z:
            return z.read(prefix + name)
    with open(os.path.join(full, name), "rb") as f:
        return f.read()


def loudest_rms(x, rate, window=0.3):
    c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    w = min(len(x), int(window * rate))
    return float(np.sqrt(((c[w:] - c[:-w]) / w).max()))


def cut(rate, x, start=0.0, end=None, fade_in=0.0, fade_out=0.0, loop=0.0, rms=-16.0, whole=False):
    """One sound, ready to write: mono, cut, faded (or crossfaded into a loop) and loudness-matched."""
    m = x.mean(axis=1)
    m = m[round(start * rate): None if end is None else round(end * rate)].astype(np.float32)
    if loop:   # blend the tail over the head, so the end runs straight back into the start
        k = round(loop * rate)
        u = np.linspace(0, np.pi / 2, k, dtype=np.float32)
        head = m[:k] * np.sin(u) + m[-k:] * np.cos(u)
        m = np.concatenate([head, m[k:-k]])
    for n, ramp in ((round(fade_in * rate), slice(None, None)), (round(fade_out * rate), slice(None, None, -1))):
        if n:
            m[ramp][:n] *= np.linspace(0, 1, n, dtype=np.float32)
    level = float(np.sqrt(np.mean(m.astype(np.float64) ** 2))) if whole else loudest_rms(m, rate)
    # spiky sounds (paper, clicks) reach the peak long before the loudness: let their peaks push up to
    # 10 dB into a soft limiter instead of leaving them quiet
    gain = min(10 ** (rms / 20) / max(level, 1e-9), LIMIT * PEAK / max(float(np.abs(m).max()), 1e-9))
    return (PEAK * np.tanh(m * gain / PEAK)).astype(np.float32)


def main():
    missing = [p for p, _ in PACKS.values() if not os.path.exists(os.path.join(SRC, p))]
    if missing:
        print("missing sound packs in %s: %s (see SPEC §21 for where they come from)" % (SRC, ", ".join(missing)))
        return 1
    os.makedirs(OUT, exist_ok=True)
    total = 0
    for name, (pack, file, opts) in SOUNDS.items():
        rate, x = read_wav(source(pack, file))
        m = cut(rate, x, whole=name in LOOPS, **opts)
        path = os.path.join(OUT, name + ".wav")
        write_wav(path, rate, m)
        total += os.path.getsize(path)
    print("wrote %d sounds to %s (%.1f MB)" % (len(SOUNDS), OUT, total / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
