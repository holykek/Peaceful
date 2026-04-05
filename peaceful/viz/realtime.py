from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np

from peaceful.models.preset import PeacePreset
from peaceful.parser.peace import PeacePresetParser
from peaceful.viz.response import per_band_responses


def _load_preset(path: str) -> tuple[PeacePreset, list[str]]:
    p = PeacePresetParser().parse_file(path)
    return p.preset, p.warnings


def run_visualizer(
    preset_path: str,
    *,
    fs: float = 48_000.0,
    f_min: float = 20.0,
    f_max: float = 20_000.0,
    n_points: int = 512,
    watch: bool = False,
    interval_ms: int = 200,
    show_bands: bool = False,
) -> None:
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    path = str(Path(preset_path).resolve())
    f_hz = np.logspace(np.log10(f_min), np.log10(min(f_max, fs * 0.45)), n_points)

    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    ax.set_xscale("log")
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude (dB)")
    ax.set_title("Peaceful — EQ curve (theoretical cascade)")
    ax.axhline(0.0, color="0.5", linewidth=0.8, linestyle="--")
    ax.grid(True, which="both", alpha=0.35)

    (line_combined,) = ax.plot(f_hz, np.zeros_like(f_hz), color="#2d6cdf", linewidth=2.0, label="Combined")
    band_lines: list = []
    if show_bands:
        colors = plt.cm.viridis(np.linspace(0.15, 0.85, 32))
        for i in range(32):
            (ln,) = ax.plot(
                f_hz,
                np.zeros_like(f_hz),
                color=colors[i % len(colors)],
                alpha=0.45,
                linewidth=1.0,
            )
            band_lines.append(ln)

    status = fig.text(0.02, 0.02, "", transform=fig.transFigure, fontsize=9, color="0.35")

    def _apply_preset(preset: PeacePreset) -> None:
        mag, per_h = per_band_responses(f_hz, preset, fs=fs)
        line_combined.set_ydata(mag)
        if show_bands and per_h:
            for i, ln in enumerate(band_lines):
                if i < len(per_h):
                    db = 20.0 * np.log10(np.maximum(np.abs(per_h[i]), 1e-20))
                    ln.set_ydata(db)
                    ln.set_visible(True)
                else:
                    ln.set_visible(False)
        pad = 3.0
        y0 = float(np.min(mag)) - pad
        y1 = float(np.max(mag)) + pad
        if y1 - y0 < 12.0:
            mid = 0.5 * (y0 + y1)
            y0, y1 = mid - 6.0, mid + 6.0
        ax.set_ylim(y0, y1)

    preset0, warns0 = _load_preset(path)
    _apply_preset(preset0)
    ax.legend(loc="upper right")
    mtime0 = os.path.getmtime(path)
    status.set_text(
        f"{Path(path).name}  ·  {len(preset0.filters)} bands  ·  "
        f"preamp {preset0.preamp if preset0.preamp is not None else 0.0:.1f} dB"
    )

    def on_frame(_frame: int) -> None:
        nonlocal mtime0, preset0
        try:
            mt = os.path.getmtime(path)
            if mt != mtime0:
                mtime0 = mt
                preset0, w = _load_preset(path)
                _apply_preset(preset0)
                status.set_text(
                    f"{Path(path).name}  ·  {len(preset0.filters)} bands  ·  "
                    f"updated {time.strftime('%H:%M:%S')}  ·  "
                    f"{len(w)} parse notes"
                )
        except OSError:
            pass

    if watch:
        _animation = FuncAnimation(fig, on_frame, interval=interval_ms, blit=False, cache_frame_data=False)
    plt.show()
