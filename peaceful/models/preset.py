from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EqBand:
    """One parametric or shelf band after normalization."""

    type: str  # peaking | low_shelf | high_shelf
    freq: float
    gain: float
    q: float


@dataclass
class PeacePreset:
    """Parsed Equalizer APO / PEACE preset."""

    preamp: float | None = None
    filters: list[EqBand] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "filters": [
                {"type": b.type, "freq": b.freq, "gain": b.gain, "q": b.q}
                for b in self.filters
            ],
        }
        if self.preamp is not None:
            out["preamp"] = self.preamp
        return out
