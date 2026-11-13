"""Psi's internal time (ADR 0010).

The original keeps two globals in ``UStrukturen``: ``Age`` (integer, „Alter“)
and ``realtime`` (real), advanced by ``LiftInc`` (UStrukturen.Pas, line 695).
Every cognitive operation costs time; fractional costs accumulate in
``realtime`` until they add up to a full unit of age. Age drives forgetting:
``Decay`` weakens a synapse by an amount proportional to the age since its
last refresh.

``LiftInc`` additionally feeds the EEG display, which may draw random numbers.
That part belongs to the user interface and is not ported (ADR 0010: the UI is
read-only and draws nothing).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction
from typing import Any


def add_real(a: float, b: float) -> float:
    """``a + b`` as Delphi computes it for two reals: in 80 bits, then rounded to 64 bits.

    This double rounding differs from Python's correctly rounded addition only
    when the 80-bit sum lands exactly halfway between two doubles. The fast
    path detects that case from the exact error of the double sum.
    """
    s = a + b
    # exact error of s (TwoSum)
    bb = s - a
    e = (a - (s - bb)) + (b - bb)
    if e == 0 or s == 0:
        return s
    half = math.ulp(s) / 2
    # An error of exactly half an ulp means the exact sum fits in 54 bits, so the
    # 80-bit step is exact and both roundings agree (ties to even). Frequent when
    # an integer is added to a fraction and the exponent grows.
    if abs(e) == half or abs(abs(e) - half) > half / 2048:
        return s
    from psi_gw.body.island.x87 import round_bits  # slow path, rare
    return float(round_bits(round_bits(Fraction(a) + Fraction(b), 64), 53))


@dataclass(slots=True)
class Clock:
    """Age and fractional time of one Psi.

    Attributes:
        age: „Alter“, integer time units since birth.
        realtime: fractional time not yet added to ``age`` (``realtime`` in
            the original), always in [0, 1).
    """

    age: int = 0
    realtime: float = 0.0

    def advance(self, inc: float) -> None:
        """Advance time by ``inc`` units (age part of ``LiftInc``, line 695).

        Pascal::

            realtime:=realtime+inc; t:=trunc(realtime);
            realtime:=realtime-t; age:=age+t;
        """
        self.realtime = add_real(self.realtime, inc)
        t = math.trunc(self.realtime)
        self.realtime = self.realtime - t
        self.age += t

    def snapshot(self) -> dict[str, Any]:
        return {"age": self.age, "realtime": self.realtime}

    @classmethod
    def restore(cls, data: dict[str, Any]) -> "Clock":
        return cls(age=data["age"], realtime=data["realtime"])
