from __future__ import annotations

import os
from pathlib import Path


def easyeffects_output_dir(override: str | os.PathLike[str] | None = None) -> Path:
    """
    Directory for output (playback) presets: ``…/easyeffects/output``.

    Resolution order:

    1. ``override`` if given
    2. ``PEACEFUL_EASYEFFECTS_OUTPUT`` env (full path to directory)
    3. ``$XDG_CONFIG_HOME/easyeffects/output`` or ``~/.config/easyeffects/output``
    """
    if override is not None:
        return Path(override).expanduser().resolve()

    env = os.environ.get("PEACEFUL_EASYEFFECTS_OUTPUT")
    if env:
        return Path(env).expanduser().resolve()

    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return (base / "easyeffects" / "output").resolve()
