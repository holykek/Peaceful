# Peaceful

Peaceful reads **PEACE / Equalizer APO** `.txt` presets and turns them into something you can use on **Linux** with **PipeWire** and **[Easy Effects](https://github.com/wwmm/easyeffects)**.

It is a **compatibility layer**: it does not implement its own DSP engine. Parsing and preset generation only.

**Status:** early / MVP (0.1.x). Feedback and PRs welcome.

## What it does

- Parses common `Filter:` / `Preamp:` lines (PK, LS, HS, etc.); skips unsupported lines safely.
- Prints a small internal JSON (`import`).
- Writes an Easy Effects **output** preset JSON and optionally asks Easy Effects to load it (`apply`).
- Optional **EQ curve plot** from the parsed bands (`visualize`, extra dependencies).

## Requirements

- **Python 3.10+**
- **Linux** with Easy Effects for the full workflow (parse/convert can be done on other OSes for testing).

## Install

```bash
git clone https://github.com/your-github-user/peaceful.git
cd peaceful
python -m pip install -e .
```

Optional visualization:

```bash
python -m pip install -e ".[viz]"
```

If the `peaceful` command is not on your `PATH`, use `python -m peaceful …` (same arguments).

## Usage

### Parse a preset (debug JSON)

```bash
peaceful import path/to/preset.txt --pretty -v
```

### Convert and install an Easy Effects output preset

```bash
peaceful apply path/to/preset.txt
```

Default output file:

- `~/.config/easyeffects/output/peaceful_import.json`

In Easy Effects: **Presets → Output** → choose **peaceful_import** (the name is the filename without `.json`).

**Flatpak** Easy Effects often uses:

`~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output/`

Point Peaceful there:

```bash
export PEACEFUL_EASYEFFECTS_OUTPUT="$HOME/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output"
peaceful apply path/to/preset.txt
```

Or use `--output-dir` / `-o`.

Useful flags:

| Flag | Meaning |
|------|--------|
| `--name mypreset` | Write `mypreset.json` and try to load `mypreset` |
| `--no-reload` | Only write the file; do not run `easyeffects -l` |
| `--rlc` | Per-band **RLC (BT)** mode instead of **APO (DR)** if something looks off |
| `-v` | Parser warnings on stderr |

Auto-load runs `easyeffects -l <name>` or `flatpak run com.github.wwmm.easyeffects -l <name>`. The Easy Effects **service** should be running; if load fails, the message explains manual steps.

### Plot the theoretical EQ curve

```bash
peaceful visualize path/to/preset.txt
```

With `--watch` / `-w`, the plot refreshes when the preset file changes on disk.

## Limitations

- Easy Effects’ built-in equalizer supports **at most 32 bands**; larger PEACE configs will error until trimmed or split.
- Shelf and Q behavior may differ slightly from Windows APO; **APO (DR)** band mode is used by default to stay close to APO-style math.
- **OFF** filters are ignored (same as not being in the chain).

## Project layout

```text
peaceful/
  cli/           # argparse entrypoint
  parser/      # PEACE / APO text parser
  converters/  # Easy Effects JSON
  integrations/# paths, optional reload helper
  models/      # preset dataclasses
  viz/         # optional matplotlib curve
examples/
  sample_peace.txt
```

## License

MIT — see [LICENSE](LICENSE).
