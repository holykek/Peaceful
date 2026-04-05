"""
EasyEffects output preset shape (native Equalizer plugin, not LSP).

Top-level keys mirror community presets and EasyEffects' own save format::

    {
      "output": {
        "blocklist": [],
        "equalizer": {
          "bypass": false,
          "input-gain": <float>,   # dB — maps from PEACE Preamp
          "output-gain": 0.0,
          "mode": "IIR",
          "num-bands": <int>,
          "split-channels": false,
          "balance": 0.0,
          "pitch-left": 0.0,
          "pitch-right": 0.0,
          "left": { "band0": { ... }, ... },
          "right": { ... same as left ... },
        },
        "plugins_order": ["equalizer"]
      }
    }

Per-band keys (see easyeffects_db_equalizer_channel.kcfg)::

    {
      "type": "Bell" | "Lo-shelf" | "Hi-shelf",
      "mode": "APO (DR)",        # closest to Equalizer APO / Peace source
      "slope": "x1",
      "frequency": <Hz>,
      "gain": <dB>,
      "q": <float>,
      "mute": false,
      "solo": false
    }

Band type strings must match EasyEffects enums exactly (hyphenated shelf names).
"""

from __future__ import annotations

from typing import Any

from peaceful.models.preset import EqBand, PeacePreset

EE_MAX_BANDS = 32

# easyeffects_db_equalizer_channel.kcfg enum order for band types
_TYPE_PEAKING = "Bell"
_TYPE_LOW_SHELF = "Lo-shelf"
_TYPE_HIGH_SHELF = "Hi-shelf"

# APO (DR) aligns biquad math with Equalizer APO; Peace presets originate there.
_DEFAULT_BAND_MODE = "APO (DR)"
_DEFAULT_SLOPE = "x1"


def _band_dict(band: EqBand, band_mode: str) -> dict[str, Any]:
    if band.type == "peaking":
        t = _TYPE_PEAKING
    elif band.type == "low_shelf":
        t = _TYPE_LOW_SHELF
    elif band.type == "high_shelf":
        t = _TYPE_HIGH_SHELF
    else:
        t = _TYPE_PEAKING

    return {
        "type": t,
        "mode": band_mode,
        "slope": _DEFAULT_SLOPE,
        "frequency": float(band.freq),
        "gain": float(band.gain),
        "q": float(band.q),
        "mute": False,
        "solo": False,
    }


def _channel_dict(bands: list[EqBand], band_mode: str) -> dict[str, Any]:
    return {f"band{i}": _band_dict(b, band_mode) for i, b in enumerate(bands)}


def peace_to_easyeffects_dict(preset: PeacePreset, *, band_mode: str | None = None) -> dict[str, Any]:
    """
    Build the JSON object EasyEffects expects for an output preset.

    ``band_mode`` defaults to APO (DR); pass ``RLC (BT)`` if an older EE build
    rejects APO mode for some band types.
    """
    mode = band_mode or _DEFAULT_BAND_MODE
    bands = list(preset.filters)
    if len(bands) > EE_MAX_BANDS:
        raise ValueError(
            f"EasyEffects equalizer supports at most {EE_MAX_BANDS} bands; "
            f"this preset has {len(bands)}"
        )

    if not bands:
        raise ValueError("preset has no EQ bands to export (PEACE file had no supported ON filters)")

    pre = float(preset.preamp) if preset.preamp is not None else 0.0

    ch = _channel_dict(bands, mode)

    eq: dict[str, Any] = {
        "bypass": False,
        "input-gain": pre,
        "output-gain": 0.0,
        "mode": "IIR",
        "num-bands": len(bands),
        "split-channels": False,
        "balance": 0.0,
        "pitch-left": 0.0,
        "pitch-right": 0.0,
        "left": ch,
        "right": {k: dict(v) for k, v in ch.items()},
    }

    return {
        "output": {
            "blocklist": [],
            "equalizer": eq,
            "plugins_order": ["equalizer"],
        }
    }
