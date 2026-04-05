from __future__ import annotations

import re
from dataclasses import dataclass, field

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
_FILTER_NUM_LINE = re.compile(
    r"^Filter\s+(?P<num>\d+)\s*:\s*(?P<on>ON|OFF)\s+(?P<raw_type>\S+)",
    re.IGNORECASE,
)
_PREAMP = re.compile(
    r"^Preamp\s*:\s*(?P<db>[-+]?\d*\.?\d+)\s*dB",
    re.IGNORECASE,
)
_FC = re.compile(
    r"\bFc\s*(?P<hz>[-+]?\d*\.?\d+)\s*Hz\b",
    re.IGNORECASE,
)
_GAIN = re.compile(
    r"\bGain\s*(?P<db>[-+]?\d*\.?\d+)\s*dB\b",
    re.IGNORECASE,
)
_Q = re.compile(
    r"\bQ\s*(?P<q>[-+]?\d*\.?\d+)\b",
    re.IGNORECASE,
)


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
                preamp = float(pm.group("db"))
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

            freq = float(fcm.group("hz"))
            gain = float(gm.group("db"))
            q = float(qm.group("q")) if qm else self._default_q
            if not qm and eq_type in ("low_shelf", "high_shelf"):
                warnings.append(
                    f"line {lineno}: no Q; using default {self._default_q} for {raw_type}"
                )

            bands.append(EqBand(type=eq_type, freq=freq, gain=gain, q=q))

        return ParseResult(
            preset=PeacePreset(preamp=preamp, filters=bands),
            warnings=warnings,
            skipped_lines=skipped,
        )

    def parse_file(self, path: str) -> ParseResult:
        with open(path, encoding="utf-8", errors="replace") as f:
            return self.parse_text(f.read())
