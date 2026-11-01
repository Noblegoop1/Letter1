"""Record the soundtrack of each self-test path to a WAV, and check its levels (SPEC §21, S5).

Each path plays in real time (about a minute each) in its own process, through SDL's "disk" audio driver,
which writes exactly what the mixer outputs. Then: build/sound/<path>.wav to listen to by ear, and a level
report: the peak, how many samples clip, and the loudest moments.

Usage (project root, with the venv):  .venv\\Scripts\\python tools\\listen.py [path name ...]
"""
import os
import subprocess
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "build", "sound")
RATE = 44100


def record(route, raw):
    """In this process (a child of main()): play one path in real time with the disk driver."""
    os.environ.update(SDL_VIDEODRIVER="dummy", SDL_AUDIODRIVER="disk", SDL_DISKAUDIOFILE=raw)
    sys.path.insert(0, ROOT)
    from letter import selftest
    from letter.app import App
    from letter.engine import audio
    app = App(size=(1280, 800))
    audio.wait_for_music()   # a reader's machine has it long before it's needed; here, start on time
    failures = app.run_script(selftest.PLANS[route], realtime=True)
    print("%s: %s; %d cues, missing: %s" % (route, "PASS" if not failures else failures, len(app.audio.played),
                                            sorted(app.audio.missing) or "none"))


def report(route, raw, wav):
    x = np.frombuffer(open(raw, "rb").read(), "<i2").reshape(-1, 2)
    x = x[max(0, int(np.argmax(np.abs(x).max(axis=1) > 0)) - RATE // 10):]   # from the first sound (the
    # device runs from the app's start, while the recorder still waits for the music)
    with wave.open(wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(x.tobytes())
    os.remove(raw)
    f = x.astype(np.float32) / 32768
    second = f[:len(f) // RATE * RATE].reshape(-1, RATE, 2)
    rms = 20 * np.log10(np.sqrt((second ** 2).mean(axis=(1, 2))) + 1e-9)
    peak = 20 * np.log10(np.abs(second).max(axis=(1, 2)) + 1e-9)
    clipped = int((np.abs(x) >= 32767).sum())
    print("%s: %.1f s, peak %.1f dBFS, %d clipped samples -> %s" % (route, len(f) / RATE, peak.max(), clipped, wav))
    print("  per second, RMS dBFS: " + " ".join("%d" % r for r in rms))
    loud = np.argsort(peak)[-5:][::-1]
    print("  loudest seconds: " + ", ".join("%d s (peak %.1f)" % (i, peak[i]) for i in loud))
    return clipped


def main(argv):
    if argv[:1] == ["--record"]:
        return record(argv[1], argv[2])
    sys.path.insert(0, ROOT)
    from letter import selftest
    os.makedirs(OUT, exist_ok=True)
    clipped = 0
    for route in argv or list(selftest.PLANS):
        name = route.replace(",", "").replace(" ", "-")
        raw = os.path.join(OUT, name + ".raw")
        subprocess.run([sys.executable, os.path.abspath(__file__), "--record", route, raw], check=True, cwd=ROOT)
        clipped += report(route, raw, os.path.join(OUT, name + ".wav"))
    return 1 if clipped else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
