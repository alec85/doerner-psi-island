"""Record types of run files (ADR 0006, traces/README.md).

Every record converts to and from a plain dict. ``from_dict`` is strict: unknown
or missing keys raise ``ValueError`` so that format drift is noticed early.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from psi_gw.tracing.vocabulary import (
    COUNTER_NAMES,
    FORMAT_VERSION,
    MODULATORS,
    MOTIVES,
    NEED_PCT_NAMES,
    STAGE_NAMES,
)

SOURCES = ("delphi", "python")


def _check_keys(data: Mapping[str, Any], required: set[str], optional: set[str], where: str) -> None:
    keys = set(data)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise ValueError(f"{where}: missing keys {sorted(missing)}")
    if unknown:
        raise ValueError(f"{where}: unknown keys {sorted(unknown)}")


def _check_subset(mapping: Mapping[str, Any] | None, allowed: tuple[str, ...], where: str) -> None:
    if mapping is None:
        return
    unknown = set(mapping) - set(allowed)
    if unknown:
        raise ValueError(f"{where}: unknown names {sorted(unknown)}")


def _check_type(data: Mapping[str, Any], expected: str) -> None:
    if data.get("type") != expected:
        raise ValueError(f"expected record type {expected!r}, got {data.get('type')!r}")


@dataclass
class RunHeader:
    """First record of a run file."""

    source: str
    format_version: int = FORMAT_VERSION
    program_version: str | None = None
    world: str | None = None
    psi_data: str | None = None
    seed: int | None = None
    started_at: str | None = None
    params: dict[str, Any] = field(default_factory=dict)
    source_files: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.source not in SOURCES:
            raise ValueError(f"run: source must be one of {SOURCES}, got {self.source!r}")
        if self.format_version != FORMAT_VERSION:
            raise ValueError(
                f"run: unsupported format_version {self.format_version}, expected {FORMAT_VERSION}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "run",
            "format_version": self.format_version,
            "source": self.source,
            "program_version": self.program_version,
            "world": self.world,
            "psi_data": self.psi_data,
            "seed": self.seed,
            "started_at": self.started_at,
            "params": self.params,
            "source_files": self.source_files,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RunHeader:
        _check_type(data, "run")
        _check_keys(
            data,
            {"type", "format_version", "source"},
            {"program_version", "world", "psi_data", "seed", "started_at",
             "params", "source_files", "extra"},
            "run",
        )
        return cls(
            source=data["source"],
            format_version=data["format_version"],
            program_version=data.get("program_version"),
            world=data.get("world"),
            psi_data=data.get("psi_data"),
            seed=data.get("seed"),
            started_at=data.get("started_at"),
            params=dict(data.get("params") or {}),
            source_files=list(data.get("source_files") or []),
            extra=dict(data.get("extra") or {}),
        )


@dataclass
class CycleRecord:
    """One behaviour cycle (Verhaltenszyklus) with cumulative performance counters."""

    cycle: int
    age: int
    counters: dict[str, int]
    life_pct: int | None = None
    age_diff: int | None = None
    need_pct: dict[str, int] | None = None
    stage_times: dict[str, float] | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        missing = set(COUNTER_NAMES) - set(self.counters)
        if missing:
            raise ValueError(f"cycle {self.cycle}: missing counters {sorted(missing)}")
        _check_subset(self.counters, COUNTER_NAMES, f"cycle {self.cycle} counters")
        _check_subset(self.need_pct, NEED_PCT_NAMES, f"cycle {self.cycle} need_pct")
        _check_subset(self.stage_times, STAGE_NAMES, f"cycle {self.cycle} stage_times")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "cycle",
            "cycle": self.cycle,
            "life_pct": self.life_pct,
            "age": self.age,
            "age_diff": self.age_diff,
            "counters": self.counters,
            "need_pct": self.need_pct,
            "stage_times": self.stage_times,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CycleRecord:
        _check_type(data, "cycle")
        _check_keys(
            data,
            {"type", "cycle", "age", "counters"},
            {"life_pct", "age_diff", "need_pct", "stage_times", "extra"},
            "cycle",
        )
        return cls(
            cycle=data["cycle"],
            age=data["age"],
            counters=dict(data["counters"]),
            life_pct=data.get("life_pct"),
            age_diff=data.get("age_diff"),
            need_pct=None if data.get("need_pct") is None else dict(data["need_pct"]),
            stage_times=None if data.get("stage_times") is None else dict(data["stage_times"]),
            extra=dict(data.get("extra") or {}),
        )


@dataclass
class EventRecord:
    """One entry of the event protocol (USmallProtokoll.WritePrt in the original)."""

    action: str
    seq: int | None = None
    wall_time: str | None = None
    wall_ms: int | None = None
    age: int | None = None
    cycle: int | None = None
    status: int | None = None
    params: list[str] = field(default_factory=list)
    situation: str | None = None
    object: str | None = None
    position: tuple[int, int] | None = None
    bag: dict[str, Any] = field(default_factory=dict)
    needs: dict[str, float | None] = field(default_factory=dict)
    nucleotides_scaled: float | None = None
    modulators: dict[str, float | None] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.action:
            raise ValueError("event: action must not be empty")
        if self.position is not None:
            self.position = (int(self.position[0]), int(self.position[1]))
        _check_subset(self.needs, MOTIVES, "event needs")
        _check_subset(self.modulators, MODULATORS, "event modulators")
        _check_subset(self.bag, ("count", "open", "items"), "event bag")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "event",
            "seq": self.seq,
            "wall_time": self.wall_time,
            "wall_ms": self.wall_ms,
            "age": self.age,
            "cycle": self.cycle,
            "action": self.action,
            "status": self.status,
            "params": self.params,
            "situation": self.situation,
            "object": self.object,
            "position": None if self.position is None else list(self.position),
            "bag": self.bag,
            "needs": self.needs,
            "nucleotides_scaled": self.nucleotides_scaled,
            "modulators": self.modulators,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EventRecord:
        _check_type(data, "event")
        _check_keys(
            data,
            {"type", "action"},
            {"seq", "wall_time", "wall_ms", "age", "cycle", "status", "params",
             "situation", "object", "position", "bag", "needs",
             "nucleotides_scaled", "modulators", "extra"},
            "event",
        )
        position = data.get("position")
        return cls(
            action=data["action"],
            seq=data.get("seq"),
            wall_time=data.get("wall_time"),
            wall_ms=data.get("wall_ms"),
            age=data.get("age"),
            cycle=data.get("cycle"),
            status=data.get("status"),
            params=list(data.get("params") or []),
            situation=data.get("situation"),
            object=data.get("object"),
            position=None if position is None else (position[0], position[1]),
            bag=dict(data.get("bag") or {}),
            needs=dict(data.get("needs") or {}),
            nucleotides_scaled=data.get("nucleotides_scaled"),
            modulators=dict(data.get("modulators") or {}),
            extra=dict(data.get("extra") or {}),
        )


@dataclass
class RunSummary:
    """Optional last record with totals over the run."""

    cycles: int
    events: int
    counters: dict[str, int] = field(default_factory=dict)
    action_counts: dict[str, int] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _check_subset(self.counters, COUNTER_NAMES, "summary counters")

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "summary",
            "cycles": self.cycles,
            "events": self.events,
            "counters": self.counters,
            "action_counts": self.action_counts,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> RunSummary:
        _check_type(data, "summary")
        _check_keys(
            data,
            {"type", "cycles", "events"},
            {"counters", "action_counts", "extra"},
            "summary",
        )
        return cls(
            cycles=data["cycles"],
            events=data["events"],
            counters=dict(data.get("counters") or {}),
            action_counts=dict(data.get("action_counts") or {}),
            extra=dict(data.get("extra") or {}),
        )
