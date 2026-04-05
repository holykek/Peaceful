from __future__ import annotations

import numpy as np

from peaceful.models.preset import EqBand, PeacePreset


def _biquad_h(
    f_hz: np.ndarray,
    fs: float,
    b0: float,
    b1: float,
    b2: float,
    a0: float,
    a1: float,
    a2: float,
) -> np.ndarray:
    z = np.exp(1j * 2.0 * np.pi * f_hz / fs)
    z_inv = 1.0 / z
    z_inv2 = z_inv * z_inv
    num = b0 + b1 * z_inv + b2 * z_inv2
    den = a0 + a1 * z_inv + a2 * z_inv2
    return num / den


def _norm_a0(b0: float, b1: float, b2: float, a0: float, a1: float, a2: float) -> tuple[float, ...]:
    return (b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0)


def _coeffs_peaking(f0: float, gain_db: float, q: float, fs: float) -> tuple[float, ...]:
    # RBJ Audio EQ Cookbook — peaking EQ; APO/EasyEffects-style visualization.
    a_lin = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * f0 / fs
    cw0 = np.cos(w0)
    sw0 = np.sin(w0)
    alpha = sw0 / (2.0 * q)
    b0 = 1.0 + alpha * a_lin
    b1 = -2.0 * cw0
    b2 = 1.0 - alpha * a_lin
    a0 = 1.0 + alpha / a_lin
    a1 = -2.0 * cw0
    a2 = 1.0 - alpha / a_lin
    return _norm_a0(b0, b1, b2, a0, a1, a2)


def _coeffs_low_shelf(f0: float, gain_db: float, q: float, fs: float) -> tuple[float, ...]:
    # Web Audio / MDN-style lowshelf with Q (approximation vs every APO variant).
    a_mag = np.sqrt(10.0 ** (gain_db / 20.0))
    w0 = 2.0 * np.pi * f0 / fs
    sw0 = np.sin(w0)
    cw0 = np.cos(w0)
    alpha = (sw0 / 2.0) * np.sqrt((a_mag + 1.0 / a_mag) * (1.0 / q - 1.0) + 2.0)
    sq = np.sqrt(a_mag)
    b0 = a_mag * ((a_mag + 1.0) - (a_mag - 1.0) * cw0 + sq * alpha)
    b1 = 2.0 * a_mag * ((a_mag - 1.0) - (a_mag + 1.0) * cw0)
    b2 = a_mag * ((a_mag + 1.0) - (a_mag - 1.0) * cw0 - sq * alpha)
    a0 = (a_mag + 1.0) + (a_mag - 1.0) * cw0 + sq * alpha
    a1 = -2.0 * ((a_mag - 1.0) + (a_mag + 1.0) * cw0)
    a2 = (a_mag + 1.0) + (a_mag - 1.0) * cw0 - sq * alpha
    return _norm_a0(b0, b1, b2, a0, a1, a2)


def _coeffs_high_shelf(f0: float, gain_db: float, q: float, fs: float) -> tuple[float, ...]:
    # High shelf: map to lowshelf at (fs/2 - f0) trick is messy; use MDN highshelf symmetry.
    a_mag = np.sqrt(10.0 ** (gain_db / 20.0))
    w0 = 2.0 * np.pi * f0 / fs
    sw0 = np.sin(w0)
    cw0 = np.cos(w0)
    alpha = (sw0 / 2.0) * np.sqrt((a_mag + 1.0 / a_mag) * (1.0 / q - 1.0) + 2.0)
    sq = np.sqrt(a_mag)
    b0 = a_mag * ((a_mag + 1.0) + (a_mag - 1.0) * cw0 + sq * alpha)
    b1 = -2.0 * a_mag * ((a_mag - 1.0) + (a_mag + 1.0) * cw0)
    b2 = a_mag * ((a_mag + 1.0) + (a_mag - 1.0) * cw0 - sq * alpha)
    a0 = (a_mag + 1.0) - (a_mag - 1.0) * cw0 + sq * alpha
    a1 = 2.0 * ((a_mag - 1.0) - (a_mag + 1.0) * cw0)
    a2 = (a_mag + 1.0) - (a_mag - 1.0) * cw0 - sq * alpha
    return _norm_a0(b0, b1, b2, a0, a1, a2)


def _band_h(f_hz: np.ndarray, fs: float, band: EqBand) -> np.ndarray:
    if band.type == "peaking":
        c = _coeffs_peaking(band.freq, band.gain, band.q, fs)
    elif band.type == "low_shelf":
        c = _coeffs_low_shelf(band.freq, band.gain, band.q, fs)
    elif band.type == "high_shelf":
        c = _coeffs_high_shelf(band.freq, band.gain, band.q, fs)
    else:
        return np.ones_like(f_hz, dtype=np.complex128)
    b0, b1, b2, a0, a1, a2 = c
    return _biquad_h(f_hz, fs, b0, b1, b2, a0, a1, a2)


def per_band_responses(
    f_hz: np.ndarray,
    preset: PeacePreset,
    fs: float = 48_000.0,
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Return (combined_mag_db, list of per-band complex H) for plotting."""
    bands_h: list[np.ndarray] = []
    prod = np.ones_like(f_hz, dtype=np.complex128)
    for b in preset.filters:
        h = _band_h(f_hz, fs, b)
        bands_h.append(h)
        prod *= h
    pre = preset.preamp if preset.preamp is not None else 0.0
    prod *= 10.0 ** (pre / 20.0)
    mag_db = 20.0 * np.log10(np.maximum(np.abs(prod), 1e-20))
    return mag_db, bands_h


def combined_response(
    f_hz: np.ndarray,
    preset: PeacePreset,
    fs: float = 48_000.0,
) -> np.ndarray:
    m, _ = per_band_responses(f_hz, preset, fs)
    return m
