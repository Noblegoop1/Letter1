# Third-party notices

"To Esther" (LetterToEsther.exe) includes the following third-party software and fonts.

| Component | Licence | Where |
|---|---|---|
| Python 3.14 runtime | Python Software Foundation License | https://docs.python.org/3/license.html |
| pygame-ce 2.5 | GNU LGPL 2.1 — shipped as separate, replaceable libraries in `_internal/` | https://github.com/pygame-community/pygame-ce |
| SDL 2 (and SDL_ttf, FreeType, HarfBuzz bundled with pygame-ce) | zlib / FreeType / MIT-style licences | https://www.libsdl.org/ |
| NumPy 2.5 (and its bundled OpenBLAS) | BSD 3-Clause | https://numpy.org/ |
| PyInstaller bootloader | GPL 2.0 with an exception that allows bundling any program | https://pyinstaller.org/ |
| JetBrains Mono | SIL Open Font License 1.1 (`_internal/assets/fonts/OFL-JetBrainsMono.txt`) | https://github.com/JetBrains/JetBrainsMono |

## Sound

The sound effects in `_internal/assets/sounds/` are edited (cut, mixed to mono, levelled) from:

| Source | Licence | Used for |
|---|---|---|
| Sound effects by Daily Sounds (dailysounds.org), Game Starter Sound Pack (Free) | Daily Sounds Sound Pack License v1: royalty-free use in projects; the files may not be redistributed on their own | the boom, bell, swoosh, riser, heartbeat, stinger, glitch, static, power-down, hover tap |
| Willosuna, Free Game & UI Sound Pack (willosuna.itch.io) | Free for personal and commercial projects; the files may not be resold or redistributed as a pack | the heart's crack and shatter, the hop and landing, the chase's jump and stumble |
| Mixkit (mixkit.co) | Mixkit Sound Effects Free License | paper, pencil, page, clicks, sparkles, crickets, wind |

They are part of this app only. Please don't extract them for other uses; get them from their sources.
The music is original: the app generates it note by note when it starts (`letter/art/music.py`).

## Source code

The pygame-ce source code is available from the link above. Because its libraries ship as separate
files, you can replace them with your own builds.

The night flower, a sea holly, is original code; its pointillist dot technique is inspired by
iremcnar/Flowers (https://github.com/iremcnar/Flowers). No code from that repository is included, and no
photographs are included (the reference photos stay on the developer's machine).
