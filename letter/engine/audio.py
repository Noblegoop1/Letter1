"""Sound (SPEC §21): effects, loops and generated music over pygame.mixer, driven by a cue sheet.

The cue sheet (letter.soundtrack) is data: phase -> [(seconds into the phase, action, ...)]. follow() fires each
cue once, in the frame the phase's clock passes it, so the sound lands on the same beat as the picture. Scenes
play only what isn't a story beat (hover, jumps, the cornered heartbeat). Without an audio device, or without
assets/sounds/, nothing here plays, and nothing fails; it still logs what was asked (for the tests).

The music is generated once per process on a worker thread (pure NumPy: no pygame calls off the main thread)
and becomes sounds on the main thread, one track per frame, as each is ready.
"""
import math
import os
import threading

import numpy as np
import pygame

from letter import config
from letter.engine import assets

FORMAT = (44100, -16, 2, 1024)   # mixer rate, sample size, channels, buffer frames (SDL converts for the device)
LOOP_CHANNELS = 8                  # reserved for loops; effects share the rest
EFFECT_CHANNELS = 24


def pre_init():
    """Ask for exactly FORMAT, before pygame.init(): the generated music is written for it."""
    pygame.mixer.pre_init(*FORMAT, allowedchanges=0)


# --- music, made once per process ----------------------------------------------------------------------
_HALF = (np.sinc(np.arange(-15, 16) / 2) * np.blackman(33)[1:-1]).astype(np.float32)   # half-band low-pass
_ready = {}                        # track name -> 16-bit stereo bytes at FORMAT's rate
_lock = threading.Lock()
_worker = None


def upsample(x, loop):
    """Twice the sample rate: zero-stuff, then a half-band filter (wrapping around the seam for a loop)."""
    pad = 8
    x = np.pad(x, ((pad, pad), (0, 0)), mode="wrap" if loop else "constant")
    y = np.zeros((2 * len(x), 2), np.float32)
    y[::2] = x
    y = np.stack([np.convolve(y[:, c], _HALF, mode="same") for c in (0, 1)], axis=1)
    return y[2 * pad: -2 * pad]


def _make_music(tracks, rate):
    for name, (make, loops) in tracks.items():
        data = (np.clip(upsample(make(), loops), -1, 1) * 32767).astype("<i2").tobytes()
        with _lock:
            _ready[name] = data


def wait_for_music():
    """Block until the music is made (the timing tests measure on an otherwise quiet machine)."""
    if _worker is not None:
        _worker.join()


def _start_music(tracks, rate):
    global _worker
    assert rate * 2 == FORMAT[0], "the music is written at half the mixer's rate"
    if _worker is None:
        _worker = threading.Thread(target=_make_music, args=(tracks, rate), name="music", daemon=True)
        _worker.start()


_effects = {}                      # name -> Sound, loaded once per process


def _load_effects():
    folder = assets.path("sounds")
    if not _effects and os.path.isdir(folder):
        for f in sorted(os.listdir(folder)):
            if f.endswith(".wav"):
                try:
                    _effects[f[:-4]] = pygame.mixer.Sound(os.path.join(folder, f))
                except pygame.error:
                    pass
    return _effects


class Audio:
    def __init__(self, cues, levels, tracks, rate):
        self.cues, self.levels, self.tracks = cues, levels, tracks
        self.played = []           # (phase, e, action, name): every cue fired and sound asked for
        self.missing = set()       # names asked for with nothing to play (no file, music not ready yet)
        self.muted = self.paused = False
        self.loops, self.pending, self.shots, self.music = {}, {}, [], {}
        self._phase, self._now, self._last = None, 0.0, 0.0
        try:
            if pygame.mixer.get_init() != FORMAT[:3]:
                pygame.mixer.quit()
                pygame.mixer.init(*FORMAT, allowedchanges=0)
            self.on = pygame.mixer.get_init() == FORMAT[:3]
        except pygame.error:       # no audio device: a silent app, not a broken one
            self.on = False
        self.effects = _load_effects() if self.on else {}
        if self.on:
            pygame.mixer.stop()   # a fresh story starts silent (an earlier App in this process may have left loops)
            pygame.mixer.set_num_channels(LOOP_CHANNELS + EFFECT_CHANNELS)
            pygame.mixer.set_reserved(LOOP_CHANNELS)
            _start_music(tracks, rate)

    # --- the cue sheet ---------------------------------------------------------------------------------
    def follow(self, phase, e):
        """Fire every cue of `phase` whose time e has just passed (all of them from 0 on entering it)."""
        if phase != self._phase:
            self._phase, self._last = phase, -1.0
        self._now = e
        for t, action, *args in self.cues.get(phase, ()):
            if self._last < t / config.SPEED <= e:
                getattr(self, action)(*args)
        self._last = e

    # --- actions ---------------------------------------------------------------------------------------
    def _sound(self, name):
        if name in self.effects:
            return self.effects[name]
        if name not in self.music:
            with _lock:
                data = _ready.get(name)
            if data is None:
                return None
            self.music[name] = pygame.mixer.Sound(buffer=data)
        return self.music[name]

    def _volume(self, v):
        return 0.0 if self.muted else min(1.0, max(0.0, v))

    def _log(self, action, name):
        self.played.append((self._phase, round(self._now, 3), action, name))

    def play(self, name, vol=1.0):
        """A one-shot effect or music cue, at its LEVEL times vol."""
        self._log("play", name)
        sound = self._sound(name) if self.on else None
        if sound is None:
            self.missing.add(name)
            return
        v = self.levels.get(name, 1.0) * vol
        channel = sound.play()
        if channel is not None:
            channel.set_volume(self._volume(v))
            self.shots.append((channel, sound, v))

    def loop(self, name, vol=1.0, fade=0.0, log=True):
        """Start a loop (fading in over `fade` story seconds), or ramp a playing one to LEVEL times vol."""
        if log:
            self._log("loop", name)
        if not self.on:
            return
        entry = self.loops.get(name)
        if entry is None:
            sound = self._sound(name)
            if sound is None:
                if name in self.tracks:   # its music is still being made: start it when it's ready
                    self.pending[name] = (vol, fade)
                else:
                    self.missing.add(name)
                return
            used = {x["index"] for x in self.loops.values()}
            free = [i for i in range(LOOP_CHANNELS) if i not in used]
            if not free:
                return
            channel = pygame.mixer.Channel(free[0])
            channel.set_volume(0.0)
            channel.play(sound, loops=-1)
            entry = self.loops[name] = {"index": free[0], "channel": channel, "v": 0.0}
        self._ramp(entry, self.levels.get(name, 1.0) * vol, fade)

    def _ramp(self, entry, target, secs):
        secs /= config.SPEED
        entry["to"] = target
        entry["speed"] = abs(target - entry["v"]) / secs if secs > 0 else math.inf

    def fade(self, name, vol, secs):
        """Ramp a loop (or every loop, name "*") to LEVEL times vol over secs; at 0 it stops."""
        self._log("fade", name)
        for n in (list(self.loops) + list(self.pending)) if name == "*" else [name]:
            if n in self.pending:
                if vol > 0:
                    self.pending[n] = (vol, secs)
                else:
                    del self.pending[n]
            if n in self.loops:
                self._ramp(self.loops[n], self.levels.get(n, 1.0) * vol, secs)

    def stop(self):
        """Silence, at once."""
        self._log("stop", None)
        self.loops.clear()
        self.pending.clear()
        self.shots.clear()
        if self.on:
            pygame.mixer.stop()

    # --- the app's controls ------------------------------------------------------------------------------
    def pause(self, paused):
        """Every sound waits while the story does (the window lost focus)."""
        if paused != self.paused and self.on:
            (pygame.mixer.pause if paused else pygame.mixer.unpause)()
        self.paused = paused

    def toggle_mute(self):
        self.muted = not self.muted
        for entry in self.loops.values():
            entry["channel"].set_volume(self._volume(entry["v"]))
        for channel, _, v in self.shots:
            channel.set_volume(self._volume(v))

    def update(self, dt):
        """Volume ramps (by story time: dt is 0 while paused), loops whose music has arrived, and at most one
        newly generated track turned into a sound per frame."""
        if not self.on:
            return
        with _lock:
            new = next((n for n in _ready if n not in self.music), None)
        if new is not None:
            self._sound(new)
        for name, (vol, fade) in list(self.pending.items()):
            if self._sound(name) is not None:
                del self.pending[name]
                self.loop(name, vol, fade, log=False)
        for name, entry in list(self.loops.items()):
            if dt > 0 and entry["v"] != entry["to"]:
                step, gap = entry["speed"] * dt, entry["to"] - entry["v"]
                entry["v"] = entry["to"] if abs(gap) <= step else entry["v"] + math.copysign(step, gap)
            if entry["v"] <= 0 and entry["to"] <= 0:
                entry["channel"].stop()
                del self.loops[name]
            else:
                entry["channel"].set_volume(self._volume(entry["v"]))
        self.shots = [s for s in self.shots if s[0].get_sound() is s[1]]
