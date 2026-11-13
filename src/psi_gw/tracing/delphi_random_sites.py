"""Call sites of Delphi's random routines in Psi.exe 4.9.1.200 (Issue #14, ADR 0009).

Each key is the return address of a ``call`` to ``System.Random`` (0x402BA0,
kind ``R``) or ``System.Random(n)`` (0x402B88, kind ``I``), i.e. the value of
``ret0`` in a random trace. The mapping was derived by enumerating all 44 static
calls in the machine code and aligning them with the ``Random`` calls in the
source in source order (Delphi lays out code per unit in source order). Two
``Random`` calls of the source (in ``LUnion`` and ``LDifferenz``) do not exist
in the program, because both functions are never called by built code and were
removed by the linker. Details: docs/zufallsmitschnitt.md.

Source lines refer to reference/delphi-original/PsiCode and give the routine
header; ``nth`` counts the Random calls within the routine in source order.
"""

from __future__ import annotations

from typing import NamedTuple


class RandomSite(NamedTuple):
    unit: str
    routine: str
    line: int
    nth: int
    kind: str
    role: str  # "cognition", "world" or "interface"


def _eeg(i: int) -> RandomSite:
    return RandomSite("UFEEG.pas", "TFEEG.PBEEGPaint", 77, i, "I", "interface")


_EEG_ADDRESSES = (
    0x47673F, 0x4767C3, 0x476831, 0x476859, 0x4768B9, 0x4768EA, 0x4769C1, 0x4769EF,
    0x476A78, 0x476ACE, 0x476B24, 0x476B56, 0x476B95, 0x476BB5, 0x476BF2, 0x476C1B,
)

SITES: dict[int, RandomSite] = {
    **{addr: _eeg(i) for i, addr in enumerate(_EEG_ADDRESSES, 1)},
    0x477E93: RandomSite("UStrukturen.Pas", "RandomChoice", 670, 1, "I", "cognition"),
    0x478086: RandomSite("UStrukturen.Pas", "LiftInc", 695, 1, "I", "cognition"),
    0x47836C: RandomSite("UStrukturen.Pas", "LiftInc", 695, 2, "I", "cognition"),
    0x4790C0: RandomSite("UStrukturen.Pas", "Decay", 1030, 1, "R", "cognition"),
    0x47916F: RandomSite("UStrukturen.Pas", "Junction", 1049, 1, "R", "cognition"),
    0x4797D6: RandomSite("UStrukturen.Pas", "LSection", 1312, 1, "R", "cognition"),
    0x47B49E: RandomSite("UStrukturen.Pas", "AddToFan", 2237, 1, "R", "cognition"),
    0x47B4D2: RandomSite("UStrukturen.Pas", "RememberDir", 2244, 1, "I", "cognition"),
    0x47D165: RandomSite("USound.Pas", "SpeakRandom", 97, 1, "R", "interface"),
    0x47D1B3: RandomSite("USound.Pas", "Utter", 104, 1, "R", "interface"),
    0x47D1DE: RandomSite("USound.Pas", "Utter", 104, 2, "I", "interface"),
    0x485DF2: RandomSite("UPSIMain.Pas", "Confirmation", 155, 1, "R", "cognition"),
    0x486015: RandomSite("UPSIMain.Pas", "Confirmation", 155, 2, "R", "cognition"),
    0x486046: RandomSite("UPSIMain.Pas", "Confirmation", 155, 3, "R", "cognition"),
    0x48664B: RandomSite("UPSIMain.Pas", "Association", 345, 1, "R", "cognition"),
    0x486801: RandomSite("UPSIMain.Pas", "Association", 345, 2, "R", "cognition"),
    0x489523: RandomSite("UPSIMain.Pas", "GoalGen", 1500, 1, "R", "cognition"),
    0x48ABCA: RandomSite("UPSIMain.Pas", "WhatCouldBeDone", 1892, 1, "R", "cognition"),
    0x48B5A8: RandomSite("UPSIMain.Pas", "WhatCouldBeDone", 1892, 2, "R", "cognition"),
    0x48B5EC: RandomSite("UPSIMain.Pas", "WhatCouldBeDone", 1892, 3, "R", "cognition"),
    0x48B65B: RandomSite("UPSIMain.Pas", "WhatCouldBeDone", 1892, 4, "R", "cognition"),
    0x48B796: RandomSite("UPSIMain.Pas", "WhatCouldBeDone", 1892, 5, "R", "cognition"),
    0x48B989: RandomSite("UPSIMain.Pas", "WhatCouldBeDone", 1892, 6, "R", "cognition"),
    0x48C55B: RandomSite("UPSIMain.Pas", "LookAround", 2436, 1, "R", "cognition"),
    0x48C785: RandomSite("UPSIMain.Pas", "LookAround", 2436, 2, "R", "cognition"),
    0x49F59F: RandomSite("UFPsi.pas", "TFPsi.Simulation", 232, 1, "R", "cognition"),
    0x49F5AF: RandomSite("UFPsi.pas", "TFPsi.Simulation", 232, 2, "R", "cognition"),
    0x4A2E12: RandomSite("UPsiServer.pas", "SetMotivation", 461, 1, "R", "world"),
}


def site_name(ret0: int) -> str:
    """Readable label such as ``UStrukturen.Junction#1``, or the hex address if unknown."""
    site = SITES.get(ret0)
    if site is None:
        return f"{ret0:08X}"
    return f"{site.unit.split('.')[0]}.{site.routine}#{site.nth}"
