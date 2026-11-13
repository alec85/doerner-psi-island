"""Reading and writing run files in JSON Lines (ADR 0006).

A run file starts with exactly one ``run`` record, followed by ``cycle`` and
``event`` records in any order, and ends with at most one ``summary`` record.
Files ending in ``.gz`` are gzip-compressed.
"""

from __future__ import annotations

import gzip
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO, Iterator, Union

from psi_gw.tracing.records import CycleRecord, EventRecord, RunHeader, RunSummary
from psi_gw.tracing.vocabulary import STATUS_END

Record = Union[RunHeader, CycleRecord, EventRecord, RunSummary]

_PARSERS = {
    "run": RunHeader.from_dict,
    "cycle": CycleRecord.from_dict,
    "event": EventRecord.from_dict,
    "summary": RunSummary.from_dict,
}


@dataclass
class Run:
    """A complete run held in memory."""

    header: RunHeader
    cycles: list[CycleRecord] = field(default_factory=list)
    events: list[EventRecord] = field(default_factory=list)
    summary: RunSummary | None = None


def compute_summary(run: Run) -> RunSummary:
    """Derive totals from cycles and events.

    Counters are the values of the last cycle. Action counts include begin and
    info events but not end events, so that each action is counted once.
    """
    counters = dict(run.cycles[-1].counters) if run.cycles else {}
    actions = Counter(e.action for e in run.events if e.status != STATUS_END)
    return RunSummary(
        cycles=len(run.cycles),
        events=len(run.events),
        counters=counters,
        action_counts=dict(sorted(actions.items())),
    )


def _open(path: Path, mode: str) -> IO[str]:
    if path.suffix == ".gz":
        return gzip.open(path, mode + "t", encoding="utf-8")
    return open(path, mode, encoding="utf-8")


class RunWriter:
    """Streaming writer that enforces record order."""

    def __init__(self, path: str | Path, header: RunHeader) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = _open(self._path, "w")
        self._closed_by_summary = False
        self._write(header.to_dict())

    def _write(self, data: dict) -> None:
        self._fh.write(json.dumps(data, ensure_ascii=False) + "\n")

    def write(self, record: CycleRecord | EventRecord | RunSummary) -> None:
        if self._closed_by_summary:
            raise ValueError("no records may follow the summary")
        if isinstance(record, RunHeader):
            raise ValueError("the run header is written once by the constructor")
        self._write(record.to_dict())
        if isinstance(record, RunSummary):
            self._closed_by_summary = True

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> RunWriter:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def write_run(path: str | Path, run: Run) -> None:
    """Write a run: header, cycles, events, then the summary if present."""
    with RunWriter(path, run.header) as writer:
        for cycle in run.cycles:
            writer.write(cycle)
        for event in run.events:
            writer.write(event)
        if run.summary is not None:
            writer.write(run.summary)


def iter_records(path: str | Path) -> Iterator[Record]:
    """Yield typed records and check the order rules of the format."""
    path = Path(path)
    seen_header = False
    seen_summary = False
    with _open(path, "r") as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            if seen_summary:
                raise ValueError(f"{path}:{lineno}: record after summary")
            data = json.loads(line)
            kind = data.get("type")
            if kind not in _PARSERS:
                raise ValueError(f"{path}:{lineno}: unknown record type {kind!r}")
            if not seen_header and kind != "run":
                raise ValueError(f"{path}:{lineno}: first record must be 'run'")
            if seen_header and kind == "run":
                raise ValueError(f"{path}:{lineno}: second 'run' record")
            try:
                record = _PARSERS[kind](data)
            except ValueError as exc:
                raise ValueError(f"{path}:{lineno}: {exc}") from exc
            seen_header = True
            seen_summary = kind == "summary"
            yield record
    if not seen_header:
        raise ValueError(f"{path}: empty run file")


def read_run(path: str | Path) -> Run:
    """Read a whole run file into memory."""
    run: Run | None = None
    for record in iter_records(path):
        if isinstance(record, RunHeader):
            run = Run(header=record)
        elif isinstance(record, CycleRecord):
            run.cycles.append(record)  # type: ignore[union-attr]
        elif isinstance(record, EventRecord):
            run.events.append(record)  # type: ignore[union-attr]
        else:
            run.summary = record  # type: ignore[union-attr]
    assert run is not None
    return run
