# Subway Surfers for your disassembler

> can all web challs have some subway surfers playing in the background pls
>
> pwn should do the same ngl
>
> — overheard on a CTF Discord

This plugin adds a Subway Surfers panel to **IDA Pro**, **Binary Ninja** and **Ghidra**, so you have something to watch while you reverse.

By default the panel shows an **ASCII Subway Surfers lookalike** written in plain Python with no dependencies. It has three tracks, trains, barriers, overhead bars, coins, a score multiplier and a BUSTED screen. An autopilot plays it for you, and arrow keys or WASD let you take over. If you'd rather watch real gameplay, a **video mode** plays your own clip instead.

```
 SCORE 0000300  x1  ● 018
·║═════║  ║═════║ ·║═════║
 ║     ║ ·┌─────┐  ║     ║
 ║══●══║  │▓▒▓▒▓│  ║═════║
·║     ║  │▒▒▒▒▒│ ·║     ║
 ║  ●  ║  │◘   ◘│  ║     ║
 ║══●══║  └┬───┬┘  ║═════║
 ║     ║ ·║     ║  ║     ║
 ║══O══║  ║═════║  ║═════║
·║ /|\ ║  ║     ║ ·║     ║
 ║ / \ ║  ║     ║  ┌─────┐
 AUTO  ←→↑↓ / WASD to play
```

## Layout

| Path | What |
| --- | --- |
| `subway_ascii.py` | The game engine. You can run it in a terminal on its own, or use `--stream` to have it print frames for a host program. |
| `subway_player.py` | Shared PySide6 widgets used by IDA and Binja: the ASCII renderer, plus the cv2 video and Qt GIF players for video mode. |
| `ida/` | The IDA 9.2+ plugin (`subway_surfers.py` and `ida-plugin.json`). |
| `binja/` | The Binary Ninja sidebar plugin. |
| `ghidra/SubwaySurfers.java` | A Ghidra script that runs `subway_ascii.py --stream` and draws the frames in a dockable window. |
| `install.ps1` | Copies everything into the right plugin and script folders on Windows. |

## Installation

### Windows (quick)

```powershell
.\install.ps1                         # all three tools
.\install.ps1 -Ida -Binja             # pick some
.\install.ps1 -Video .\clip.mp4       # also copy a clip for video mode
```

The installer copies files into these folders:

| Tool | Folder |
| --- | --- |
| IDA | `%APPDATA%\Hex-Rays\IDA Pro\plugins\subway_surfers\` |
| Binary Ninja | `%APPDATA%\Binary Ninja\plugins\subway_surfers\` |
| Ghidra | `%USERPROFILE%\ghidra_scripts\` |

### Manual installation, or Linux and macOS

**IDA Pro 9.2+** (uses Qt 6 and PySide6). Create `<IDA user dir>/plugins/subway_surfers/` and put these files in it:

```
ida/subway_surfers.py
ida/ida-plugin.json
subway_player.py
subway_ascii.py
```

The IDA user dir is `%APPDATA%\Hex-Rays\IDA Pro` on Windows and `~/.idapro` elsewhere. Keep the plugin in a folder with its `ida-plugin.json`; IDA 9.4 was seen to skip it as a loose `.py` file.

Restart IDA and open a database. To open the game, use **View → Subway Surfers** or press **Ctrl+Shift+Alt+S**. (Ctrl+Alt+S is already IDA's Stack Trace shortcut.)

**Binary Ninja** (a paid licence is needed; the free edition doesn't load plugins). Create `<Binja user dir>/plugins/subway_surfers/` and put these files in it:

```
binja/__init__.py
subway_player.py
subway_ascii.py
```

Restart Binja, then click the ▶ icon in the right sidebar.

**Ghidra** (tested against 12.1; requires `python` / `python3` on your PATH). Copy `ghidra/SubwaySurfers.java` and `subway_ascii.py` into `~/ghidra_scripts/`. Then open **Window → Script Manager**, find **SubwaySurfers** under the *Fun* category, and run it. If you tick its **In Tool** box, it also gets a **Window → Subway Surfers** menu entry.

### Controls

The game plays itself. To take over, click the panel and use the arrow keys or WASD: left and right change lane, up jumps, down rolls. The autopilot comes back after a few seconds without input. Playback pauses while the panel is hidden.

You can also play in a terminal (`q` quits):

```bash
python subway_ascii.py
```

## Video mode

If you set `SUBWAY_MODE=video` before launching the tool, the plugin plays a real gameplay clip instead of the ASCII game. No video is included in this repo, so you have to provide one. For example, this clip works: <https://www.youtube.com/watch?v=-ZsF8xk3Vy0>. Subway Surfers footage belongs to SYBO, so don't redistribute clips with challenges.

Put the clip next to the plugin and name it after the format:

| Tool | File | Needs |
| --- | --- | --- |
| IDA / Binja | `subway_surfers.mp4`, `.webm` or `.mkv` | `opencv-python-headless` installed in the tool's Python |
| IDA / Binja | `subway_surfers.gif` | nothing extra (Qt ships a GIF decoder) |
| Ghidra | `subway_surfers.gif` | nothing extra (Swing animates GIFs) |

You can also point `SUBWAY_VIDEO` at a file anywhere on disk.

Keep the clip small, because frames are decoded on the UI thread:

```bash
# MP4 for IDA / Binja
ffmpeg -i in.mp4 -vf scale=360:-2 -an subway_surfers.mp4
# GIF for Ghidra (or anything else): 20 s, 12 fps, 200 px wide, about 7 MB
ffmpeg -t 20 -i in.mp4 -vf "fps=12,scale=200:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" -loop 0 subway_surfers.gif
```

Installing cv2 into each tool's Python:

- **IDA:** IDA uses whichever Python `idapyswitch` selected. Run `<that python> -m pip install opencv-python-headless`. Use the `-headless` build, because the regular wheel bundles its own Qt, which can conflict with IDA's.
- **Binja:** Binja bundles its own Python. Use its *Install python3 module* command, or run `pip install --target "%APPDATA%\Binary Ninja\python310\site-packages" --python-version 3.10 --platform win_amd64 --only-binary=:all: opencv-python-headless`.

## Environment variables

| Variable | Effect |
| --- | --- |
| `SUBWAY_MODE` | Set to `video` to play a clip instead of the ASCII game. |
| `SUBWAY_VIDEO` | Path to the clip, overriding the file next to the plugin. |
| `SUBWAY_PYTHON` | Ghidra only: the Python executable used to run the game. |

## Troubleshooting

- **IDA shows nothing.** Check the Output window for a `[subway] loaded: ...` line. If it's missing, force-load the plugin to see the error:
  ```python
  import ida_loader; ida_loader.load_plugin(r"<path>/subway_surfers.py")
  ```
- **Ghidra's window says it couldn't start python.** Set `SUBWAY_PYTHON` to the full path of the Python executable. Any Python traceback is shown inside the window itself.
- **Binja shows no ▶ icon.** Check the Log pane for `[subway] loaded`.

## License

MIT. Subway Surfers is a trademark of SYBO Games; this project isn't affiliated with SYBO. The ASCII game contains no SYBO assets.
