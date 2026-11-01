"""What every scene provides. A scene owns one logical canvas and its viewport."""
from letter.engine.viewport import Viewport


class Scene:
    logical = (1280, 800)
    background = (0, 0, 0)

    def __init__(self, app):
        self.app = app
        self.view = Viewport(self.logical, app.size)

    def resize(self, size):
        self.view.resize(size)

    def enter(self, phase, t):
        """Called when the story moves into one of this scene's phases."""

    def update(self, dt, t, phase, e):
        """Advance animation; e = seconds since the phase began."""

    def draw(self, screen, t, phase, e):
        screen.fill(self.background)

    def on_event(self, ev, phase, e):
        """Input, already routed to this scene."""

    def target(self, name):
        """Window-pixel point of a named clickable thing (used by scripted runs)."""
        raise KeyError(name)

    def logical_pos(self, pos):
        return self.view.to_logical(*pos)
