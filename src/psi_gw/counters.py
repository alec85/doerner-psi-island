"""Process and performance counters (``NIntProc``, ``Leistung``; ADR 0010).

The original counts internal processes (``TIntProc``) and performance
(``TLeistung``) in global arrays that many procedures increment. They feed the
protocol files and are part of Psi's state, so they live here, in one object
shared by the modules that count.
"""

from __future__ import annotations

from enum import IntEnum
from typing import Any


class IntProc(IntEnum):
    """Internal processes (``TIntProc``), names as in the original."""

    SgOp = 0; SsOp = 1; SaOp = 2; ScOp = 3     # search for operators: general, specific, aggressive, consumptive  # noqa: E702
    SnOp = 4                                    # search not yet applied
    SfAu = 5; SbAu = 6                          # search forward / backward automatisms  # noqa: E702
    SPla = 7; SCon = 8                          # search plans, confirmations  # noqa: E702
    SGoa = 9                                    # search main or background goal (GoalGen)
    FgOp = 10; FsOp = 11; FaOp = 12; FcOp = 13  # operators found  # noqa: E702
    FnOp = 14                                   # found not yet applied
    FfAu = 15; FbAu = 16                        # found forward / backward automatisms  # noqa: E702
    FmGo = 17; FbGo = 18; FiGo = 19; FaGo = 20  # found main / background goal (LookAround)  # noqa: E702
    FcAs = 21; FcAu = 22                        # contradictory associations / automatisms  # noqa: E702
    FPla = 23                                   # made plan
    MfAs = 24; MfAu = 25; MbAs = 26; MbAu = 27  # automatisms forward, backward, plus, minus  # noqa: E702
    MPls = 28; MPld = 29; MPlu = 30             # plans successful, disappointing, unsuccessful  # noqa: E702
    MAgg = 31; MReg = 32                        # aggression, regression  # noqa: E702
    MaMs = 33; MaMu = 34; MaLs = 35; MaLu = 36  # manipulations, locomotions  # noqa: E702
    MchM = 37                                   # change of motive
    MapG = 38; MavG = 39                        # learned appetitive / aversive goal  # noqa: E702
    MmGo = 40; MbGo = 41; MiGo = 42             # goals stated: main, background, intermediate  # noqa: E702


class Performance(IntEnum):
    """Performance counters („Leistung“, ``TLeistung``)."""

    NSucLoc = 0; NUsuLoc = 1; NLoc = 2; NExit = 3; NAgg = 4; NSucMan = 5; NuSuMan = 6  # noqa: E702
    NNukleotide = 7; Hun = 8; Dur = 9; Scha = 10; Affil = 11; Life = 12; DiffLife = 13  # noqa: E702


class Counters:
    """``NIntProc`` and ``Leistung``; ``InitPsi`` sets all to 0 and ``Leistung[NNukleotide]`` to 5."""

    def __init__(self) -> None:
        self.int_proc = [0] * len(IntProc)
        self.performance = [0] * len(Performance)
        self.performance[Performance.NNukleotide] = 5
        self.proc_times = [0, 0]
        """„ProcTimes“: time spent recollecting (``Association``) and planning (``Planen``)."""
        self.check_freq = [0] * 10
        """„CheckFreq[1..10]“: how often the branches of operator choice in ``WhatCouldBeDone`` ran."""

    def count(self, proc: IntProc, n: int = 1) -> None:
        self.int_proc[proc] += n

    def snapshot(self) -> dict[str, Any]:
        return {"int_proc": list(self.int_proc), "performance": list(self.performance),
                "proc_times": list(self.proc_times), "check_freq": list(self.check_freq)}

    @classmethod
    def restore(cls, data: dict[str, Any]) -> "Counters":
        c = cls()
        c.int_proc = list(data["int_proc"])
        c.performance = list(data["performance"])
        c.proc_times = list(data.get("proc_times", [0, 0]))
        c.check_freq = list(data.get("check_freq", [0] * 10))
        return c
