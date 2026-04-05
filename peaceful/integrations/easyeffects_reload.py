from __future__ import annotations

import shutil
import subprocess
from typing import Final

_PRESET_FLAG: Final = "-l"


def try_load_output_preset(basename: str) -> tuple[bool, str]:
    """
    Ask a running EasyEffects instance to load an output preset by name
    (filename without ``.json``), via the app CLI.

    Returns ``(ok, detail)``. ``detail`` is empty on success, or a short reason /
    stderr snippet on failure.
    """
    basename = basename.removesuffix(".json")
    commands: list[list[str]] = []

    ee = shutil.which("easyeffects")
    if ee:
        commands.append([ee, _PRESET_FLAG, basename])

    if shutil.which("flatpak"):
        commands.append(
            ["flatpak", "run", "com.github.wwmm.easyeffects", _PRESET_FLAG, basename]
        )

    if not commands:
        return False, "easyeffects not found in PATH and flatpak not found"

    last_err = ""
    for cmd in commands:
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=45,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            last_err = str(e)
            continue
        if proc.returncode == 0:
            return True, ""
        last_err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"

    return False, last_err or "load failed"
