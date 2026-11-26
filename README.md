<p align="center"><img src="docs/pixbot.png" width="128" alt="Pixbot"></p>

<h1 align="center">Pixbot</h1>
<p align="center"><b>A tiny pixel robot that lives on your Windows desktop.</b><br>
He walks along your taskbar, hops onto your windows, plays with your cursor, and has 130+ little animations.</p>

<p align="center"><a href="https://ko-fi.com/c1tribal"><img src="https://img.shields.io/badge/Support%20Pixbot-Ko--fi-FF5E5B?logo=ko-fi&logoColor=white" alt="Support on Ko-fi"></a></p>

![Pixbot animations](docs/animations.png)

## What he does

- **Lives on your screen**: walks the taskbar, climbs window borders, hangs off ledges, swings along the top of the screen, and parachutes back down.
- **Sees what's on screen**: the edges of thumbnails, buttons and rows become platforms he can run and jump across (see *Privacy* below).
- **Reacts to you**: comes over when you're idle, types along when you type, dances or grabs popcorn while you watch a video, plays along when you're in a fullscreen game, notices new windows, copies, low battery, and more.
- **Cursor games**: reach, grab, tag, high-five, hide and seek, slide under it, and even propose to it.
- **130+ animations**: everyday, chill and hobbies, sports and gym, silly ones, arcade fun, movie-style scenes with captions, getting around (skateboard, pogo stick, flying cloud, jetpack, portal blaster, smoke bomb), moves and tricks.
- **Clothes**: 65 hats, face items and outfits, plus 15 ready-made looks.
- **Settings app**: turn every animation on or off, pick favourites and dislikes, set how calm or hyper he is, where he likes to hang out, his colour and size, when he's around, and more.

![Pixbot settings app](docs/settings.png)

## Download

1. Go to the [**Releases**](../../releases) page.
2. Download `Pixbot.exe`.
3. Double-click it. Pixbot appears on your taskbar. Right-click him and pick **Settings...** to open the settings app.

Windows SmartScreen may warn you because the app isn't code-signed (signing certificates cost money). Click **More info → Run anyway**. If you'd rather not, run it from source instead (below). It's the exact same code.

## Run from source (no .exe needed)

You need [Python 3.10+](https://www.python.org/downloads/) on Windows.

```powershell
git clone https://github.com/c1tribal/pixbot.git
cd pixbot
python -m pip install -r requirements.txt
pythonw pixbot.pyw              # starts Pixbot
pythonw pixbot.pyw --settings   # opens the settings app
```

## Privacy and safety: what Pixbot does on your PC

Everything is in this repository and you can read every line. In short:

| | |
|---|---|
| **Internet** | Pixbot never connects to the internet. The only time anything opens a web page is when *you* click a button on the Support page. |
| **Screen** | Every half second he takes a screenshot of the screen he's on, to find edges to stand on. It stays **in memory only**, is never saved to disk and never leaves your PC. You can turn this off: Settings → General → *Let him look at the screen*. |
| **Keyboard and mouse** | He only checks *when* you last used the mouse or keyboard and roughly how fast you type (to type along with you). He never records which keys you press, apart from noticing Backspace and Caps Lock for two small reactions. |
| **Files** | He writes only his own settings to `%APPDATA%\Pixbot`. Nothing else. |
| **Startup** | Only if you tick *Start Pixbot when Windows starts*, he adds one entry under `HKEY_CURRENT_USER\...\Run`. Unticking it removes it. |
| **The .exe** | It's built automatically by GitHub Actions from this exact source code (see [`.github/workflows/build.yml`](.github/workflows/build.yml)). You can also build it yourself with [`build.ps1`](build.ps1). |

**Uninstall:** quit Pixbot (right-click → Quit), untick *Start Pixbot when Windows starts* if you ticked it, delete `Pixbot.exe`, and delete the `%APPDATA%\Pixbot` folder.

## What every file is

| File | What's in it |
|---|---|
| `pixbot.pyw` | The starting point. Runs Pixbot, or the settings app with `--settings`. |
| `pixbot_pet.pyw` | Pixbot himself: movement, physics, deciding what to do next, reacting to you, screens and windows. |
| `pixbot_acts.py` | How he looks and all his animations: poses, props and effects. |
| `pixbot_movies.py` | The movie-style scenes and their caption lines. |
| `pixbot_outfits.py` | The wardrobe: every hat, face item and outfit. |
| `pixbot_app.pyw` | The settings app. |
| `pixbot_catalog.py` | The list of animations, their names and categories, and the default settings. |
| `pixbot_vision.py` | The screen reading: finds edges and pictures in an in-memory screenshot. |
| `pixbot_paths.py` | Where files live (`%APPDATA%\Pixbot`) and how Pixbot starts itself. |
| `pixbot_common.py` | Sizes and colours shared by everything. |
| `pixbot_paint.py` | A tiny drawing helper used by the settings app previews and flying effects. |
| `pixbot_links.json` | The links on the Support page. |
| `build.ps1` | Builds `Pixbot.exe` yourself with PyInstaller. |
| `requirements.txt` | The 4 Python packages Pixbot needs: `numpy`, `pillow`, `comtypes`, `pycaw`. |

## Build the .exe yourself

```powershell
python -m pip install -r requirements.txt pyinstaller
.\build.ps1
```

The result is `dist\Pixbot.exe`.

## Support

Pixbot is free. If he makes your day a little better, you can [buy me a coffee on Ko-fi](https://ko-fi.com/c1tribal). Ideas for new animations are welcome in [Issues](../../issues).

## License

[MIT](LICENSE). Pixbot and all of his art, animations and text are original.
