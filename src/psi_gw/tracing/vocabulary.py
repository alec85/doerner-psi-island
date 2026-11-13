"""Canonical names used in traces and their Delphi counterparts (ADR 0006).

English identifiers carry the German original term in comments, following the
terminology rule in AGENTS.md.
"""

from __future__ import annotations

FORMAT_VERSION = 1

# Motives (TMotiv in UStrukturen.Pas, without NilMotiv), in Delphi order.
MOTIVES: tuple[str, ...] = (
    "hunger",        # Hunger
    "thirst",        # Durst
    "nucleotides",   # Nukleo (Nukleotide)
    "damage",        # Schaden (Unversehrtheit)
    "certainty",     # Bestimmtheit
    "competence",    # Kompetenz
    "affiliation",   # Affili / Affiliation
)

MOTIVE_FROM_DELPHI: dict[str, str] = {
    "Hunger": "hunger",
    "Durst": "thirst",
    "Nukleo": "nucleotides",
    "Schaden": "damage",
    "Bestimmtheit": "certainty",
    "Kompetenz": "competence",
    "Affili": "affiliation",
    "Affiliation": "affiliation",
}

# Modulators (TModulat), in Delphi order.
MODULATORS: tuple[str, ...] = (
    "arousal",              # Arousal, Aktiviertheit
    "resolution_level",     # ResolutionLevel, Auflösungsgrad
    "selection_threshold",  # SelectThreshold, Selektionsschwelle
)

MODULATOR_FROM_DELPHI: dict[str, str] = {
    "Arousal": "arousal",
    "ResolutionLevel": "resolution_level",
    "ResLevel": "resolution_level",
    "SelectThreshold": "selection_threshold",
    "SelectThresh": "selection_threshold",
}

# Cumulative performance counters (TLeistung, NSucLoc..NNukleotide), in Delphi order.
COUNTERS: tuple[tuple[str, str], ...] = (
    ("successful_locomotions", "NSucLoc"),
    ("unsuccessful_locomotions", "NUsuLoc"),
    ("locations_discovered", "NLoc"),
    ("exitus", "NExit"),
    ("aggressions", "NAgg"),
    ("successful_manipulations", "NSucMan"),
    ("unsuccessful_manipulations", "NuSuMan"),
    ("nucleotides_collected", "NNukleotide"),
)
COUNTER_NAMES: tuple[str, ...] = tuple(name for name, _ in COUNTERS)

# Need strength in percent written to ach*.Prt (TLeistung Hun, Dur, Scha, Affil).
NEED_PCT: tuple[tuple[str, str], ...] = (
    ("hunger", "Hun"),
    ("thirst", "Dur"),
    ("damage", "Scha"),
    ("affiliation", "Affil"),
)
NEED_PCT_NAMES: tuple[str, ...] = tuple(name for name, _ in NEED_PCT)

# Stages of the Rasmussen ladder as timed in IntTimes.txt.
STAGES: tuple[tuple[str, str], ...] = (
    ("look_around", "LookAr"),
    ("automatism", "Auto"),
    ("plan", "Plan"),
    ("what_could_be_done", "WCBD"),
)
STAGE_NAMES: tuple[str, ...] = tuple(name for name, _ in STAGES)

# Event actions, verbatim from USmallProtokoll.WritePrt calls in the original.
ACTIONS: tuple[str, ...] = (
    "Start", "Stop", "Locomotion", "Manipuliere", "Aggression", "Regression",
    "Motivation", "Take", "Give", "Bag", "Open", "Close", "Pause",
)

# Event status codes (second argument of WritePrt).
STATUS_BEGIN = 0
STATUS_END = 1
STATUS_INFO = -1
