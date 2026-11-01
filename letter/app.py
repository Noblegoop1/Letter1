"""The application: window, main loop, story clock, phase -> scene routing, scripted runs.

Story time only advances while the window is active, so minimising or switching away pauses everything.
"""
import os
import time

import pygame

from letter import config
from letter.engine import story

# which scene draws each phase (scenes are created lazily so a scene's big arrays live only when needed)
SCENE_OF = {
    "intro": "letter", "letter": "letter", "yes-reveal": "letter",
    "no-1": "letter", "no-2": "letter", "no-3": "letter", "no-4": "letter",
    "night": "night", "seed": "night", "grown": "night", "bloom": "night", "bloomed": "night",
    "gather": "night", "invite": "night", "letgo": "night", "farewell": "night", "joy": "ending", "exit": "ending",
    "chase": "chase", "cornered": "chase",
    "glitch": "ending", "face": "ending", "black": "ending",
}


def _scene_class(name):
    if name == "letter":
        from letter.scenes.letter import LetterScene
        return LetterScene
    if name == "night":
        from letter.scenes.night import NightScene
        return NightScene
    if name == "chase":
        from letter.scenes.chase import ChaseScene
        return ChaseScene
    from letter.scenes.ending import EndingScene
    return EndingScene


def window_size():
    """80% of the screen height at 16:10, never wider than 90% of the screen."""
    w, h = pygame.display.get_desktop_sizes()[0]
    height = int(h * 0.8)
    width = min(int(height * 1.6), int(w * 0.9))
    return width, int(width / 1.6)


class App:
    def __init__(self, size=None, start="intro"):
        pygame.init()
        pygame.display.set_caption(config.TITLE)
        self.windowed = size or window_size()
        self.screen = pygame.display.set_mode(self.windowed, pygame.RESIZABLE)
        self.size = self.screen.get_size()
        self.phase, self.since, self.t = start, 0.0, 0.0
        self.active = True
        self.scenes = {}
        self.frame_ms = []
        self.running = True
        self.pointer = None  # window pixels, or None when the pointer is outside the window

    # --- story -----------------------------------------------------------------------------------
    def scene(self, phase=None):
        name = SCENE_OF[phase or self.phase]
        if name not in self.scenes:
            self.scenes[name] = _scene_class(name)(self)
        return self.scenes[name]

    def emit(self, event):
        """A scene reports a story event (a click on YES, the chase reaching its end, ...)."""
        self._advance(story.step(self.phase, self.since, self.t, event))

    def _advance(self, nxt):
        old = self.phase
        self.phase, self.since = nxt
        if self.phase == "exit":   # the invitation's YES ending closes the app, normally
            self.running = False
        if self.phase != old:
            if SCENE_OF[old] != SCENE_OF[self.phase]:  # leaving a scene for good: free its arrays
                self.scenes.pop(SCENE_OF[old], None)
            self.scene().enter(self.phase, self.t)

    # --- loop ------------------------------------------------------------------------------------
    def handle(self, ev):
        if ev.type == pygame.QUIT:
            self.running = False
        elif ev.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED):
            self.active = False
        elif ev.type in (pygame.WINDOWFOCUSGAINED, pygame.WINDOWRESTORED):
            self.active = True
        elif ev.type == pygame.WINDOWSIZECHANGED:
            self.resize(self.screen.get_size())
        elif ev.type == pygame.KEYDOWN and (ev.key == pygame.K_F11 or
                                            (ev.key == pygame.K_RETURN and ev.mod & pygame.KMOD_ALT)):
            self.toggle_fullscreen()
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE and self.screen.get_flags() & pygame.FULLSCREEN:
            self.toggle_fullscreen()
        else:
            if ev.type == pygame.MOUSEMOTION:
                self.pointer = ev.pos
            elif ev.type == pygame.WINDOWLEAVE:
                self.pointer = None
            self.scene().on_event(ev, self.phase, self.t - self.since)

    def toggle_fullscreen(self):
        if self.screen.get_flags() & pygame.FULLSCREEN:
            self.screen = pygame.display.set_mode(self.windowed, pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.resize(self.screen.get_size())

    def resize(self, size):
        self.size = size
        for s in self.scenes.values():
            s.resize(size)

    def frame(self, dt):
        """One frame: advance story time (if active), hand off timed phases, update and draw."""
        start = time.perf_counter()   # before the handoff, so building a scene counts against the frame
        if self.active:
            self.t += dt
        self._advance(story.step(self.phase, self.since, self.t))
        scene, e = self.scene(), self.t - self.since
        scene.update(dt if self.active else 0.0, self.t, self.phase, e)
        scene.draw(self.screen, self.t, self.phase, e)
        self.frame_ms.append((time.perf_counter() - start) * 1000)

    def run(self):
        clock = pygame.time.Clock()
        self.scene().enter(self.phase, self.t)
        while self.running:
            for ev in pygame.event.get():
                self.handle(ev)
            self.frame(min(clock.tick(config.FPS_CAP) / 1000, 0.1))
            pygame.display.flip()
        pygame.quit()

    # --- scripted runs (self-test, screenshots) ----------------------------------------------------
    def run_script(self, plan, dt=1 / 60, until=None, on_shot=None):
        """Drive the app with a fixed time step. plan: sorted list of (story_time, action, arg).
        Actions: ("click", target name), ("key", pygame key), ("move", target name or (x, y) window px),
        ("shot", name), ("expect", phase). Returns a list of failures (empty = pass)."""
        failures, queue = [], list(plan)
        visible = os.environ.get("SDL_VIDEODRIVER") != "dummy"
        self.scene().enter(self.phase, self.t)
        end = until if until is not None else (queue[-1][0] + 0.5 if queue else 1.0)
        while self.t < end and self.running:
            while queue and queue[0][0] <= self.t:
                _, action, arg = queue.pop(0)
                if action == "click":
                    pos = self.scene().target(arg)
                    for kind in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                        self.handle(pygame.event.Event(kind, pos=pos, button=1))
                elif action == "key":
                    for kind in (pygame.KEYDOWN, pygame.KEYUP):
                        self.handle(pygame.event.Event(kind, key=arg, mod=0, unicode=" "))
                elif action == "move":
                    pos = arg if isinstance(arg, tuple) else self.scene().target(arg)
                    self.handle(pygame.event.Event(pygame.MOUSEMOTION, pos=pos, rel=(0, 0), buttons=(0, 0, 0)))
                elif action == "shot" and on_shot:
                    on_shot(arg, self.screen)
                elif action == "expect" and self.phase != arg:
                    failures.append("t=%.2f expected %s, was %s" % (self.t, arg, self.phase))
            self.frame(dt)
            if visible:   # a real window (--selftest --window): show each frame and keep the window responsive
                pygame.display.flip()
                pygame.event.pump()
        return failures



def headless():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"