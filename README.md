# Peaceful

Peaceful reads **PEACE / Equalizer APO** `.txt` presets and builds **Easy Effects** output preset files for **Linux** (PipeWire). It only parses and writes JSON; it is not a full DSP engine.

**Status:** early MVP (0.1.x). Issues and PRs welcome.

## What it does

- Reads `Filter:` / `Preamp:` lines (PK, LS, HS, and similar). Skips what it does not support.
- `import`: print JSON for debugging.
- `apply`: write `peaceful_import.json` (or another name) into Easy Effects' output preset folder.
- `visualize`: optional EQ curve plot (needs extra Python packages).

## What you need

- **Python 3.10+** on the machine where you run Peaceful.
- **Linux + Easy Effects** if you want to use `apply` and hear the EQ. Windows is fine for `import`, generating JSON, and `visualize` if you install the viz extras.

Repo: **https://github.com/holykek/peaceful**

## Install on Linux

**Easiest (recommended):** install [pipx](https://pipx.pypa.io/), then:

```bash
pipx install "git+https://github.com/holykek/peaceful.git"
```

Graphs for `visualize`:

```bash
pipx inject peaceful numpy matplotlib
```

**Without pipx:** use a venv in your home directory:

```bash
python3 -m venv ~/peaceful-env
source ~/peaceful-env/bin/activate
python -m pip install "git+https://github.com/holykek/peaceful.git"
python -m pip install "peaceful[viz] @ git+https://github.com/holykek/peaceful.git"
```

Next time you open a terminal, run `source ~/peaceful-env/bin/activate` before `peaceful`.

**If the command `peaceful` is missing:** run `python3 -m peaceful` with the same arguments (or `python -m peaceful` inside the venv).

Arch / CachyOS example for pipx: `sudo pacman -S python-pipx` then `pipx ensurepath` and restart the terminal.

## Install on Windows

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/). Enable **Add python.exe to PATH** in the installer.
2. Open **PowerShell** or **Command Prompt** and run:

```powershell
py -m pip install --user "git+https://github.com/holykek/peaceful.git"
```

If `py` is not found, try `python` instead of `py`.

**No Git installed?** Use the zip URL instead:

```powershell
py -m pip install --user "https://github.com/holykek/peaceful/archive/refs/heads/main.zip"
```

**Graphs (`visualize`):** after Peaceful is installed, add:

```powershell
py -m pip install --user numpy matplotlib
```

**If `peaceful` is not on PATH:** always use:

```powershell
py -m peaceful import --help
```

## How to use

**1. Test the preset file**

```text
peaceful import "C:\path\to\preset.txt" --pretty -v
```

On Linux use `/home/you/...` paths. Quotes matter if the path has spaces.

**2. On Linux only: write the Easy Effects preset**

```text
peaceful apply "/path/to/preset.txt"
```

Default file: `~/.config/easyeffects/output/peaceful_import.json`

In Easy Effects: **Presets**, **Output**, pick **peaceful_import**.

**Flatpak** Easy Effects often uses:

`~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output/`

Either:

```bash
export PEACEFUL_EASYEFFECTS_OUTPUT="$HOME/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output"
peaceful apply "/path/to/preset.txt"
```

or:

```bash
peaceful apply "/path/to/preset.txt" -o "$HOME/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output"
```

**3. Windows workflow tip:** run `import` or `apply --no-reload` with `-o` pointing to a folder you can copy to your Linux machine (USB, cloud), then drop the `.json` into the Easy Effects `output` folder on Linux.

**4. Optional graph**

```text
peaceful visualize "/path/to/preset.txt"
```

`-w` reloads when the file changes on disk.

**Useful flags for `apply`:** `--name mypreset`, `--no-reload`, `--rlc`, `-o DIR`, `-v`. See `peaceful apply --help`.

## Limitations

- At most **32** EQ bands in Easy Effects.
- Shelves and Q may not match Windows APO exactly. Default band mode is **APO (DR)**; try `--rlc` if needed.
- **OFF** filters in the txt file are ignored.

## Project layout

```text
peaceful/   CLI, parser, Easy Effects converter, optional viz
examples/   sample_peace.txt
```

## License

MIT. See [LICENSE](LICENSE).
