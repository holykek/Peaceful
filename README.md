# Peaceful

Peaceful reads **PEACE / Equalizer APO** `.txt` presets and turns them into something you can use on **Linux** with **PipeWire** and **[Easy Effects](https://github.com/wwmm/easyeffects)**.

It is a **compatibility layer**: it does not implement its own DSP engine. Parsing and preset generation only.

**Status:** early / MVP (0.1.x). Feedback and PRs welcome.

## What it does

- Parses common `Filter:` / `Preamp:` lines (PK, LS, HS, etc.); skips unsupported lines safely.
- Prints a small internal JSON (`import`).
- Writes an Easy Effects **output** preset JSON and optionally asks Easy Effects to load it (`apply`).
- Optional **EQ curve plot** from the parsed bands (`visualize`, extra dependencies).

---

## What you need

| | |
|--|--|
| **OS** | **Linux** to apply presets in Easy Effects. (You can check parsing on Windows/macOS, but `apply` targets Linux paths.) |
| **Python** | **3.10 or newer** (`python3 --version`) |
| **Audio** | [Easy Effects](https://github.com/wwmm/easyeffects) installed and working with PipeWire |
| **Git** | Only if you install from GitHub (see below). Not needed if you use `pip` from a downloaded wheel/sdist later. |

---

## Install (for end users)

Pick **one** method. Replace **`OWNER`** in the URLs below with the **GitHub username or organization** that hosts this repository (the same name you see in `https://github.com/OWNER/peaceful`).

### Option A — Recommended: `pipx` (isolated CLI, no virtualenv to manage)

[`pipx`](https://pipx.pypa.io/) installs Peaceful in its own environment and puts the `peaceful` command on your PATH.

1. **Install pipx** (if you do not have it), for example on Arch / CachyOS:

   ```bash
   sudo pacman -S python-pipx
   pipx ensurepath
   ```

   Then **log out and back in** (or open a new terminal) so `PATH` updates.

2. **Install Peaceful from GitHub:**

   ```bash
   pipx install "git+https://github.com/OWNER/peaceful.git"
   ```

3. **Optional — EQ plot** (`visualize` needs NumPy and Matplotlib):

   ```bash
   pipx inject peaceful numpy matplotlib
   ```

   Or install everything in one step (if your `pipx` supports PEP 508 extras):

   ```bash
   pipx install "peaceful[viz] @ git+https://github.com/OWNER/peaceful.git"
   ```

4. **Check that it works:**

   ```bash
   peaceful import --help
   ```

   If `peaceful` is not found, run `pipx ensurepath`, restart the terminal, or use:

   ```bash
   pipx run --spec "git+https://github.com/OWNER/peaceful.git" peaceful import --help
   ```

### Option B — Virtual environment (full control)

Good if you prefer not to use `pipx`.

```bash
python3 -m venv ~/peaceful-env
source ~/peaceful-env/bin/activate   # fish: source ~/peaceful-env/bin/activate.fish
python -m pip install --upgrade pip
python -m pip install "git+https://github.com/OWNER/peaceful.git"
```

Optional graphing:

```bash
python -m pip install "peaceful[viz] @ git+https://github.com/OWNER/peaceful.git"
```

Whenever you open a new terminal, activate the venv before running `peaceful`:

```bash
source ~/peaceful-env/bin/activate
```

If `peaceful` is still not on `PATH`, use:

```bash
python -m peaceful import --help
```

### Option C — From PyPI (when published)

If this project is published on PyPI, installation becomes:

```bash
pipx install peaceful
# optional:
pipx inject peaceful numpy matplotlib
```

Until then, use **Option A** or **B**.

### Option D — Contributors: clone and editable install

For people who want to change the code:

```bash
git clone https://github.com/OWNER/peaceful.git
cd peaceful
python -m pip install -e .
python -m pip install -e ".[viz]"   # optional
```

---

## Usage guide (step by step)

### 1. Check that your PEACE file is read correctly

Use the real path to your `.txt` preset (spaces in paths: use quotes).

```bash
peaceful import "/path/to/My EQ.txt" --pretty -v
```

You should see JSON with `preamp` (if present) and a `filters` list. `-v` prints warnings for skipped or unknown lines.

### 2. Install the preset into Easy Effects (Linux)

1. Start **Easy Effects** (and enable processing for your output device if you normally do).
2. Run:

   ```bash
   peaceful apply "/path/to/My EQ.txt"
   ```

3. By default this creates:

   `~/.config/easyeffects/output/peaceful_import.json`

4. In **Easy Effects**: open **Presets** → **Output** (playback chain) → select **peaceful_import** (the label is the filename without `.json`).

5. If the preset **does not appear** and you installed Easy Effects **via Flatpak**, configs often live here instead:

   `~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output/`

   Point Peaceful at that folder once per terminal session (or put it in your shell profile):

   ```bash
   export PEACEFUL_EASYEFFECTS_OUTPUT="$HOME/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output"
   peaceful apply "/path/to/My EQ.txt"
   ```

   Or pass the directory explicitly:

   ```bash
   peaceful apply "/path/to/My EQ.txt" -o "$HOME/.var/app/com.github.wwmm.easyeffects/config/easyeffects/output"
   ```

6. **Auto-load:** `apply` tries `easyeffects -l peaceful_import` (or Flatpak). If that fails, the tool still wrote the JSON; load the preset manually in the app as in step 4.

### 3. Optional: plot the theoretical EQ curve

Requires the **viz** extra (see install options above).

```bash
peaceful visualize "/path/to/My EQ.txt"
```

Add `-w` / `--watch` to refresh the plot when you save changes to the same file.

### Command reference

| Command | Purpose |
|--------|---------|
| `peaceful import FILE` | Print parsed JSON (`--pretty`, `-v` for warnings) |
| `peaceful apply FILE` | Write Easy Effects output preset + try to load it |
| `peaceful visualize FILE` | Open magnitude plot (needs viz dependencies) |

**`peaceful apply` flags**

| Flag | Meaning |
|------|--------|
| `--name mypreset` | Write `mypreset.json` and try to load `mypreset` |
| `--no-reload` | Only write the file; do not run `easyeffects -l` |
| `--rlc` | Use **RLC (BT)** per-band mode instead of **APO (DR)** if the curve sounds wrong |
| `-o DIR` | Output directory for the `.json` file |
| `-v` | Parser warnings on stderr |

---

## Limitations

- Easy Effects’ built-in equalizer supports **at most 32 bands**; larger PEACE configs will error until trimmed or split.
- Shelf and Q behavior may differ slightly from Windows APO; **APO (DR)** band mode is used by default to stay close to APO-style math.
- **OFF** filters are ignored (same as not being in the chain).

## Project layout

```text
peaceful/
  cli/            # argparse entrypoint
  parser/         # PEACE / APO text parser
  converters/     # Easy Effects JSON
  integrations/   # paths, optional reload helper
  models/         # preset dataclasses
  viz/            # optional matplotlib curve
examples/
  sample_peace.txt
```

## License

MIT — see [LICENSE](LICENSE).
