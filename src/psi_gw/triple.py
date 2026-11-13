"""Three-valued result of regulation procedures (``Triple`` in UStrukturen.Pas)."""

from __future__ import annotations

from enum import IntEnum


class Triple(IntEnum):
    """``Triple = (tfalse, ttrue, tpartial)``: failed, succeeded, partly succeeded."""

    FALSE = 0
    TRUE = 1
    PARTIAL = 2
