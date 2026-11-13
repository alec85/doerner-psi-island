"""Psi's parameters from ``Param.Dat`` (``ReadParameter`` in ``InitPsi``, UStrukturen.Pas line 2645).

The file has three blocks, each preceded by a header line and separated by an
empty line: memory parameters, need parameters (weight, increment, decrement
per need) and modulator parameters (gain, minimum, maximum). ``ReadParameter``
reads it with ``readln``, i.e. the leading numbers of each line; the rest of
the line (comments) is skipped.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from psi_gw.memory.network import MemoryParams
from psi_gw.motivation.needs import NEEDS, Modulator, ModulatorParams, Motive, NeedParams

ROOT = Path(__file__).resolve().parents[2]
ISLAND_PARAM_DAT = ROOT / "reference" / "delphi-original" / "PsiCode" / "PsiDaten" / "InselIII" / "Param.Dat"
"""Parameter file of the reference runs (``PsiDaten=InselIII``)."""


@dataclass(frozen=True, slots=True)
class PsiParams:
    """All parameters read by ``ReadParameter``."""

    memory: MemoryParams
    needs: dict[Motive, NeedParams]
    modulators: dict[Modulator, ModulatorParams]

    def snapshot(self) -> dict[str, Any]:
        return {
            "memory": asdict(self.memory),
            "needs": {m.name: list(asdict(p).values()) for m, p in self.needs.items()},
            "modulators": {m.name: list(asdict(p).values()) for m, p in self.modulators.items()},
        }

    @classmethod
    def restore(cls, data: dict[str, Any]) -> "PsiParams":
        return cls(
            MemoryParams(**data["memory"]),
            {Motive[k]: NeedParams(*v) for k, v in data["needs"].items()},
            {Modulator[k]: ModulatorParams(*v) for k, v in data["modulators"].items()},
        )


def _numbers(line: str, count: int) -> list[float]:
    tokens = line.split()
    if len(tokens) < count:
        raise ValueError(f"expected {count} numbers in {line!r}")
    # DEVIATION(ADR-0005): Delphi converts text to an 80-bit value and then
    # to a 64-bit real; Python rounds the decimal directly to 64 bit. For all
    # values of the island Param.Dat, rounding first to 64 and then to 53
    # significant bits gives the same double (checked with exact fractions),
    # assuming Delphi's text conversion itself is correctly rounded.
    return [float(t) for t in tokens[:count]]


def read_param_dat(path: Path | str = ISLAND_PARAM_DAT) -> PsiParams:
    """Read a ``Param.Dat`` file (Windows-1252, as all files of the original)."""
    lines = Path(path).read_text(encoding="cp1252").splitlines()
    pos = 1  # readln(f): header
    forgetting, protocol_factor, base = (_numbers(lines[pos + i], 1)[0] for i in range(3))
    pos += 3 + 2  # readln(f); readln(f): empty line and header
    needs = {}
    for motive in NEEDS:
        needs[motive] = NeedParams(*_numbers(lines[pos], 3))
        pos += 1
    pos += 2
    modulators = {}
    for modulator in Modulator:
        modulators[modulator] = ModulatorParams(*_numbers(lines[pos], 3))
        pos += 1
    return PsiParams(MemoryParams(forgetting, protocol_factor, base), needs, modulators)
