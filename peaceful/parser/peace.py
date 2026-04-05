from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from peaceful.models.preset import EqBand, PeacePreset

# Equalizer APO type tokens → internal EQ type (EasyEffects / common naming)
_TYPE_MAP: dict[str, str] = {
    "pk": "peaking",
    "peaking": "peaking",
    "peq": "peaking",
    "ls": "low_shelf",
    "lsc": "low_shelf",
    "lowshelf": "low_shelf",
    "low_shelf": "low_shelf",
    "hs": "high_shelf",
    "hsc": "high_shelf",
    "highshelf": "high_shelf",
    "high_shelf": "high_shelf",
}

_FILTER_LINE = re.compile(
    r"^Filter\s*:\s*(?P<on>ON|OFF)\s+(?P<raw_type>\S+)",
    re.IGNORECASE,
)
# "Filter 1:" and "Filter1:" (Peace / hand-edited APO files)
_FILTER_NUM_LINE = re.compile(
    r"^Filter\s*(?P<num>\d+)\s*:\s*(?P<on>ON|OFF)\s+(?P<raw_type>\S+)",
    re.IGNORECASE,
)
_PREAMP = re.compile(
    r"^Preamp\s*:\s*(?P<db>[-+]?\d*[.,]?\d+(?:[eE][-+]?\d+)?)\s*dB",
    re.IGNORECASE,
)
_NUM = r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?"
_FC = re.compile(
    rf"\bFc\s*(?P<hz>{_NUM})\s*(?:Hz)?\b",
    re.IGNORECASE,
)
_GAIN = re.compile(
    rf"\bGain\s*(?P<db>{_NUM})\s*(?:dB)?\b",
    re.IGNORECASE,
)
_Q = re.compile(
    rf"\bQ\s*(?P<q>{_NUM})\b",
    re.IGNORECASE,
)
_GRAPHIC_EQ = re.compile(r"GraphicEQ\s*:\s*([^\n\r]+)", re.IGNORECASE)


def _float_apo(s: str) -> float:
    return float(s.strip().replace(",", "."))


def _decode_file_bytes(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe"):
        return raw.decode("utf-16-le")
    if raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16-be")
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig")
    nul_ratio = raw.count(b"\x00") / max(len(raw), 1)
    if nul_ratio > 0.01 and len(raw) % 2 == 0:
        try:
            t = raw.decode("utf-16-le")
            if "GraphicEQ" in t or "Filter" in t or "Preamp" in t:
                return t
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def _parse_graphic_eq(text: str, default_q: float) -> tuple[list[EqBand], list[str]]:
    """Equalizer APO GraphicEQ line(s): semicolon-separated 'Hz dB' pairs (AutoEq, some Peace exports)."""
    bands: list[EqBand] = []
    notes: list[str] = []
    for m in _GRAPHIC_EQ.finditer(text):
        chunk = m.group(1).strip()
        for part in chunk.split(";"):
            part = part.strip()
            if not part:
                continue
            tokens = part.replace(",", ".").split()
            if len(tokens) < 2:
                continue
            try:
                f_hz = float(tokens[0])
                gain_db = float(tokens[1])
            except ValueError:
                continue
            bands.append(EqBand(type="peaking", freq=f_hz, gain=gain_db, q=default_q))
    if bands:
        notes.append(
            f"interpreted {len(bands)} GraphicEQ points as peaking bands (Q={default_q}); "
            "this approximates the APO graphic curve, not identical to GraphicEQ in APO."
        )
    return bands, notes


@dataclass
class ParseResult:
    preset: PeacePreset
    warnings: list[str] = field(default_factory=list)
    skipped_lines: list[int] = field(default_factory=list)


class PeacePresetParser:
    """Parse Equalizer APO / PEACE .txt preset files."""

    def __init__(self, default_q: float = 0.707) -> None:
        self._default_q = default_q

    def parse_text(self, text: str) -> ParseResult:
        if text.startswith("\ufeff"):
            text = text[1:]

        warnings: list[str] = []
        skipped: list[int] = []
        preamp: float | None = None
        bands: list[EqBand] = []

        for lineno, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            pm = _PREAMP.match(line)
            if pm:
                preamp = _float_apo(pm.group("db"))
                continue

            m = _FILTER_NUM_LINE.match(line) or _FILTER_LINE.match(line)
            if not m:
                continue

            if m.group("on").upper() == "OFF":
                continue

            raw_type = m.group("raw_type")
            key = raw_type.lower().rstrip(":,")
            eq_type = _TYPE_MAP.get(key)
            if eq_type is None:
                warnings.append(
                    f"line {lineno}: unsupported filter type {raw_type!r}, skipped"
                )
                skipped.append(lineno)
                continue

            fcm = _FC.search(line)
            gm = _GAIN.search(line)
            qm = _Q.search(line)

            if not fcm or not gm:
                warnings.append(
                    f"line {lineno}: missing Fc/Gain, skipped ({raw_type})"
                )
                skipped.append(lineno)
                continue

            freq = _float_apo(fcm.group("hz"))
            gain = _float_apo(gm.group("db"))
            q = _float_apo(qm.group("q")) if qm else self._default_q
            if not qm and eq_type in ("low_shelf", "high_shelf"):
                warnings.append(
                    f"line {lineno}: no Q; using default {self._default_q} for {raw_type}"
                )

            bands.append(EqBand(type=eq_type, freq=freq, gain=gain, q=q))

        if not bands:
            gq_bands, gq_notes = _parse_graphic_eq(text, default_q=math.sqrt(2.0))
            bands.extend(gq_bands)
            warnings.extend(gq_notes)

        if not bands:
            sample = text.strip()[:200].replace("\n", " ")
            warnings.append(
                "no EQ bands found. Expected lines like "
                "'Filter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1.0' or a 'GraphicEQ: f g; ...' line. "
                "Peace '.peace' GUI files are not read yet; export or copy the Equalizer APO config text. "
                f"File starts with: {sample!r}"
            )

        return ParseResult(
            preset=PeacePreset(preamp=preamp, filters=bands),
            warnings=warnings,
            skipped_lines=skipped,
        )

    def parse_file(self, path: str) -> ParseResult:
        raw = Path(path).expanduser().read_bytes()
        return self.parse_text(_decode_file_bytes(raw))
