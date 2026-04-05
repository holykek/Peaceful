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


def _normalize_import_text(text: str) -> str:
    """Peace / Windows editors sometimes use curly quotes or invisible chars."""
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    text = text.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")
    text = text.replace("\ufeff", "")
    return text


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
            if "GraphicEQ" in t or "FilterCurve" in t or "Filter" in t or "Preamp" in t:
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


_FILTER_CURVE_KV = re.compile(r'\b([fv])(\d+)\s*=\s*"([^"]*)"')


def _parse_filter_curve(text: str, default_q: float) -> tuple[list[EqBand], list[str]]:
    """
    Peace GUI text export: FilterCurve:f0="10" ... v0="0.888" ...
    Pairs fN (Hz) with vN (dB) into peaking bands (approximation of the spline curve).
    """
    if "filtercurve" not in text.lower():
        return [], []

    f_hz: dict[int, float] = {}
    gain_db: dict[int, float] = {}
    for m in _FILTER_CURVE_KV.finditer(text):
        kind = m.group(1).lower()
        idx = int(m.group(2))
        raw = m.group(3).strip()
        if not raw:
            continue
        try:
            val = _float_apo(raw)
        except ValueError:
            continue
        if kind == "f":
            f_hz[idx] = val
        elif kind == "v":
            gain_db[idx] = val

    idx_ok = sorted(set(f_hz.keys()) & set(gain_db.keys()))
    bands = [
        EqBand(type="peaking", freq=f_hz[i], gain=gain_db[i], q=default_q)
        for i in idx_ok
    ]
    notes: list[str] = []
    if bands:
        notes.append(
            f"interpreted Peace FilterCurve ({len(bands)} f/v pairs) as peaking bands with Q={default_q}; "
            "this is only an approximation of Peace's spline, not a bit-identical match."
        )
        if len(bands) > 32:
            notes.append(
                f"Easy Effects allows at most 32 bands; you have {len(bands)} (use apply only after trimming or merging)."
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
        text = _normalize_import_text(text)

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
            fc_bands, fc_notes = _parse_filter_curve(text, default_q=math.sqrt(2.0))
            bands.extend(fc_bands)
            warnings.extend(fc_notes)

        if not bands:
            sample = text.strip()[:200].replace("\n", " ")
            msg = (
                "no EQ bands found. Expected: APO 'Filter 1: ON PK Fc ... Hz Gain ... dB Q ...', "
                "'GraphicEQ: ...', or Peace 'FilterCurve:f0=\"...\" v0=\"...\" ...'. "
                f"File starts with: {sample!r}"
            )
            if "filtercurve" in text.lower():
                msg += (
                    " Your file looks like Peace FilterCurve; you are probably running an old Peaceful "
                    "(upgrade: py -m pip install --force-reinstall \"git+https://github.com/holykek/peaceful.git\")."
                )
            warnings.append(msg)

        return ParseResult(
            preset=PeacePreset(preamp=preamp, filters=bands),
            warnings=warnings,
            skipped_lines=skipped,
        )

    def parse_file(self, path: str) -> ParseResult:
        raw = Path(path).expanduser().read_bytes()
        return self.parse_text(_decode_file_bytes(raw))
