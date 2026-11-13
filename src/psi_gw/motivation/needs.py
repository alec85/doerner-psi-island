"""Terms of Psi's motivation: needs, modulators, action tendencies (ADR 0010).

Enumerations follow the types of ``UStrukturen.Pas`` in the original order, so
``int(member)`` is the Pascal ordinal.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Motive(IntEnum):
    """Needs and the motives they give rise to (``TMotiv``)."""

    NIL = 0
    """„NilMotiv“: no motive selected."""
    HUNGER = 1
    """„Hunger“: energy."""
    DURST = 2
    """„Durst“: water."""
    NUKLEO = 3
    """„Nukleo“: nucleotides, collected in the island world."""
    SCHADEN = 4
    """„Schaden“: damage, need for physical integrity."""
    BESTIMMTHEIT = 5
    """„Bestimmtheit“: certainty, need for predictability."""
    KOMPETENZ = 6
    """„Kompetenz“: competence, need for efficacy."""
    AFFILI = 7
    """„Affili“: affiliation, need for social contact."""


NEEDS = tuple(m for m in Motive if m is not Motive.NIL)
"""The seven real needs, ``hunger..affili``, in the original's loop order."""


class Modulator(IntEnum):
    """Emotional modulators („Modulatoren“, ``TModulat``)."""

    AROUSAL = 0
    """„Arousal“: activation („Aktiviertheit“)."""
    RESOLUTION_LEVEL = 1
    """„ResolutionLevel“: resolution level („Auflösungsgrad“)."""
    SELECT_THRESHOLD = 2
    """„SelectThreshold“: selection threshold („Selektionsschwelle“)."""


class Tendency(IntEnum):
    """Action tendencies („Handlungstendenzen“, ``TTendenz``)."""

    SAFEGUARD = 0
    """„Safeguard“: securing („Sicherung“)."""
    AGGRESSION = 1
    """„Aggression“."""
    FLIGHT = 2
    """„Flight“: flight („Flucht“)."""
    SPEC_EXPLO = 3
    """„SpecExplo“: specific exploration."""
    DIV_EXPLO = 4
    """„DivExplo“: diversive exploration."""


@dataclass(frozen=True, slots=True)
class NeedParams:
    """Parameters of one need (one line of the second block of ``Param.Dat``).

    Attributes:
        weight: „Motivgewicht“, weight of the need in motive strength.
        increment: „Inkrement“, factor for consumption (need rises).
        decrement: „Dekrement“, factor for satisfaction (need falls).
    """

    weight: float
    increment: float
    decrement: float


@dataclass(frozen=True, slots=True)
class ModulatorParams:
    """Parameters of one modulator (third block of ``Param.Dat``).

    Attributes:
        gain: „modulatG“, weight of the modulator.
        minimum: „modulatMin“, lower bound.
        maximum: „modulatMax“, upper bound.
    """

    gain: float
    minimum: float
    maximum: float
