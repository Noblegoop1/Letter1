"""Find bundled files the same way from a source checkout and from the PyInstaller folder."""
import os
import sys

# frozen: PyInstaller unpacks data next to the exe in _internal (sys._MEIPASS); source: the repo root
ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def path(*parts):
    return os.path.join(ROOT, "assets", *parts)
