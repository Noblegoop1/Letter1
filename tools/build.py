"""Build the Windows release: dist/LetterToEsther/ (portable folder: exe + _internal/) and a zip of it.

Usage (project root, with the venv):  .venv\\Scripts\\python tools\\build.py [--clean]
"""
import os
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD, DIST, NAME = os.path.join(ROOT, "build"), os.path.join(ROOT, "dist"), "LetterToEsther"


def make_icon(path):
    """A small rose heart, written as an .ico that wraps a 256 px PNG (no image library needed)."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.init()
    s = pygame.Surface((256, 256), pygame.SRCALPHA)
    rose = (255, 134, 173)
    pygame.draw.circle(s, rose, (88, 100), 60)
    pygame.draw.circle(s, rose, (168, 100), 60)
    pygame.draw.polygon(s, rose, [(32, 120), (224, 120), (128, 228)])
    png = path + ".png"
    pygame.image.save(s, png)
    data = open(png, "rb").read()
    with open(path, "wb") as f:  # ICONDIR + one ICONDIRENTRY (0 = 256 px) + the PNG itself
        f.write(struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", 0, 0, 0, 0, 1, 32, len(data), 22) + data)


def main():
    if "--clean" in sys.argv:
        for d in (BUILD, DIST):
            shutil.rmtree(d, ignore_errors=True)
        print("cleaned build/ and dist/")
        return 0
    os.makedirs(BUILD, exist_ok=True)
    icon = os.path.join(BUILD, "icon.ico")
    make_icon(icon)
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", NAME, "--icon", icon,
        "--add-data", os.path.join(ROOT, "assets") + os.pathsep + "assets",
        "--paths", ROOT, "--exclude-module", "tkinter",
        "--distpath", DIST, "--workpath", os.path.join(BUILD, "pyinstaller"), "--specpath", BUILD,
        os.path.join(ROOT, "letter", "__main__.py"),
    ], check=True)
    out = os.path.join(DIST, NAME)
    shutil.copy(os.path.join(ROOT, "THIRD_PARTY_NOTICES.md"), out)
    archive = os.path.join(DIST, NAME + "-win64.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for folder, _, files in os.walk(out):
            for f in files:
                full = os.path.join(folder, f)
                z.write(full, os.path.relpath(full, DIST))
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(out) for f in fs)
    print("built %s (%.1f MB) and %s (%.1f MB)" % (out, size / 1e6, archive, os.path.getsize(archive) / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
