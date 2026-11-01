"""Entry point: `python -m letter` in development, LetterToEsther.exe when packaged."""
import argparse
import os
import sys
import tempfile

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def dpi_aware():
    """Per-monitor DPI awareness, so Windows never bitmap-stretches the window."""
    os.environ.setdefault("SDL_WINDOWS_DPI_AWARENESS", "permonitorv2")
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:  # older Windows: SDL's hint above still applies
            pass


def selftest(window=False):
    """Scripted runs of both routes in a hidden (or, with window, a visible) window; exit code 0 when every
    expectation held."""
    from letter.app import App, headless
    from letter import selftest as plan

    if not window:
        headless()
    failures, lines = [], []
    for route, steps in plan.PLANS.items():   # each route in a fresh app, as a reader would play it
        app = App(size=(1280, 800))
        failed = ["%s: %s" % (route, f) for f in app.run_script(steps)]
        failures += failed
        ms = sorted(app.frame_ms[1:])   # the first frame builds the letter's caches behind the launch veil
        lines.append("%s route: %s; startup frame %.0f ms; frames: %d, median %.2f ms, p95 %.2f ms, max %.2f ms,"
                     " over 33 ms: %d" % (route, "PASS" if not failed else "FAIL", app.frame_ms[0], len(ms),
                                          ms[len(ms) // 2], ms[int(len(ms) * 0.95)], ms[-1], sum(m > 33 for m in ms)))
    text = "\n".join(["selftest: %s" % ("PASS" if not failures else "FAIL")] + lines + failures)
    print(text)
    with open(os.path.join(tempfile.gettempdir(), "LetterToEsther-selftest.log"), "w") as f:
        f.write(text + "\n")
    return 0 if not failures else 1


def main(argv=None):
    parser = argparse.ArgumentParser(prog="LetterToEsther")
    parser.add_argument("--selftest", action="store_true", help="scripted headless run; exit 0/1")
    parser.add_argument("--window", action="store_true", help="with --selftest: play it in a visible window")
    parser.add_argument("--scene", default="intro", help="start at a story phase (development)")
    parser.add_argument("--size", help="window size WxH (development)")
    args = parser.parse_args(argv)
    dpi_aware()
    if args.selftest:
        return selftest(window=args.window)
    from letter.app import App
    size = tuple(int(n) for n in args.size.lower().split("x")) if args.size else None
    App(size=size, start=args.scene).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
