"""Converters from the Delphi original's protocol files to run files (ADR 0006).

Supported so far:

* ``ach*.Prt``: one line per behaviour cycle with life percentage and the 14
  performance counters (written in ``UFPsi.pas``).
* ``Protokoll*.Dat``: the event protocol written by ``USmallProtokoll.WritePrt``.
  Columns are read from the header line, because older versions of the original
  (e.g. 4.9.0.100) omit the ``Nr`` column.

All files are Windows-1252 encoded with CRLF line endings.

Command line::

    python -m psi_gw.tracing.delphi_protocols --ach ach16.Prt --events Protokoll.Dat \\
        --world InselIII --out traces/original-runs/test/insel__seed-16__1.jsonl
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from psi_gw.tracing.records import CycleRecord, EventRecord, RunHeader
from psi_gw.tracing.runfile import Run, compute_summary, write_run
from psi_gw.tracing.vocabulary import (
    COUNTER_NAMES,
    MODULATOR_FROM_DELPHI,
    MOTIVE_FROM_DELPHI,
    MOTIVES,
    NEED_PCT_NAMES,
    STAGE_NAMES,
)

ENCODING = "cp1252"

_ACH_HEADER = re.compile(r"Probelauf:\s*(\d+)\s+(.*\S)\s*$")
_VERSION = re.compile(r"Psi\s+(\d+(?:\.\d+)+)")
_DATE_DE = re.compile(r"(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})")
_DATE_US = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})\s*([AP]M)", re.I)

# Maximum difference between the start times of an ach file and an event file
# that are claimed to belong to the same run.
MAX_START_SKEW_SECONDS = 120


def _read_lines(path: Path) -> list[str]:
    return path.read_bytes().decode(ENCODING).replace("\r\n", "\n").replace("\r", "\n").split("\n")


def parse_start_time(text: str) -> str | None:
    """Parse the date formats found in the original's protocols into ISO 8601.

    Handles ``26.05.2003 12:07:01``, ``Sun 09.03.2014 19:42:08`` and the US
    format ``3/9/2014 7:42:08 PM`` that appears in files written on an
    English-language Windows.
    """
    m = _DATE_DE.search(text)
    if m:
        d, mo, y, h, mi, s = (int(x) for x in m.groups())
        return datetime(y, mo, d, h, mi, s).isoformat()
    m = _DATE_US.search(text)
    if m:
        mo, d, y, h, mi, s = (int(x) for x in m.groups()[:6])
        ampm = m.group(7).upper()
        if ampm == "PM" and h != 12:
            h += 12
        if ampm == "AM" and h == 12:
            h = 0
        return datetime(y, mo, d, h, mi, s).isoformat()
    return None


@dataclass
class AchProtocol:
    seed: int | None
    started_at: str | None
    cycles: list[CycleRecord]
    header_raw: str = ""
    skipped_lines: list[str] = field(default_factory=list)


def parse_ach(path: str | Path) -> AchProtocol:
    """Parse an ``ach*.Prt`` file.

    Each data row holds 15 integers: life percentage, the eight cumulative
    counters, four need strengths in percent, age and age difference.
    """
    path = Path(path)
    seed = started_at = None
    header_raw = ""
    cycles: list[CycleRecord] = []
    skipped: list[str] = []
    for line in _read_lines(path):
        stripped = line.strip()
        if not stripped:
            continue
        header = _ACH_HEADER.search(stripped)
        if header:
            if cycles:
                raise ValueError(f"{path}: second run header after data rows")
            seed = int(header.group(1))
            started_at = parse_start_time(header.group(2))
            header_raw = stripped
            continue
        parts = stripped.split()
        if len(parts) == 15 and all(p.lstrip("-").isdigit() for p in parts):
            v = [int(p) for p in parts]
            cycles.append(CycleRecord(
                cycle=len(cycles),
                life_pct=v[0],
                counters=dict(zip(COUNTER_NAMES, v[1:9])),
                need_pct=dict(zip(NEED_PCT_NAMES, v[9:13])),
                age=v[13],
                age_diff=v[14],
            ))
        elif parts[0] != "NsL":  # the column header line is expected, anything else is reported
            skipped.append(stripped)
    return AchProtocol(seed=seed, started_at=started_at, cycles=cycles,
                       header_raw=header_raw, skipped_lines=skipped)


@dataclass
class EventProtocol:
    meta: dict[str, str]
    columns: list[str]
    events: list[EventRecord]

    @property
    def program_version(self) -> str | None:
        m = _VERSION.search(self.meta.get("Version", ""))
        return f"Psi {m.group(1)}" if m else None

    @property
    def started_at(self) -> str | None:
        return parse_start_time(self.meta.get("Datum", ""))


def _int(value: str) -> int | None:
    value = value.strip()
    return int(value) if value else None


def _float(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def _str(value: str) -> str | None:
    value = value.strip()
    return value or None


_SIMPLE = {
    "Nr": ("seq", _int),
    "Zeit": ("wall_time", _str),
    "msec": ("wall_ms", _int),
    "Age": ("age", _int),
    "Takt": ("cycle", _int),
    "Aktion": ("action", _str),
    "Status": ("status", _int),
    "Situation": ("situation", _str),
    "Objekt": ("object", _str),
    "Nuk/100": ("nucleotides_scaled", _float),
}
_HANDLED = set(_SIMPLE) | {"Para1", "Para2", "Para3", "PosX", "PosY", "Bag", "Open",
                           "Bag1", "Bag2", "Bag3"} | set(MOTIVE_FROM_DELPHI) | set(MODULATOR_FROM_DELPHI)


def _event_from_row(row: dict[str, str]) -> EventRecord:
    fields: dict = {}
    for column, (name, convert) in _SIMPLE.items():
        if column in row:
            fields[name] = convert(row[column])

    params = [row.get(f"Para{i}", "").strip() for i in (1, 2, 3)]
    while params and not params[-1]:
        params.pop()
    fields["params"] = params

    x, y = _int(row.get("PosX", "")), _int(row.get("PosY", ""))
    fields["position"] = (x, y) if x is not None and y is not None else None

    bag: dict = {}
    if "Bag" in row:
        bag["count"] = _int(row["Bag"])
    if "Open" in row:
        bag["open"] = _int(row["Open"])
    bag["items"] = [item for item in (row.get(f"Bag{i}", "").strip() for i in (1, 2, 3)) if item]
    fields["bag"] = bag

    fields["needs"] = {MOTIVE_FROM_DELPHI[c]: _float(v) for c, v in row.items() if c in MOTIVE_FROM_DELPHI}
    fields["modulators"] = {MODULATOR_FROM_DELPHI[c]: _float(v) for c, v in row.items()
                            if c in MODULATOR_FROM_DELPHI}
    fields["extra"] = {c: v for c, v in row.items() if c not in _HANDLED and v.strip()}

    if not fields.get("action"):
        raise ValueError(f"event row without action: {row}")
    return EventRecord(**fields)


def parse_event_protocol(path: str | Path) -> EventProtocol:
    """Parse a ``Protokoll*.Dat`` event protocol."""
    path = Path(path)
    meta: dict[str, str] = {}
    columns: list[str] | None = None
    events: list[EventRecord] = []
    for lineno, line in enumerate(_read_lines(path), 1):
        if not line.strip():
            continue
        if columns is None:
            if ";Aktion;" in line:
                columns = [c.strip() for c in line.split(";")]
            elif ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
            continue
        values = line.split(";")
        if len(values) < len(columns):
            values += [""] * (len(columns) - len(values))
        row = {c: v for c, v in zip(columns, values) if c}
        try:
            events.append(_event_from_row(row))
        except ValueError as exc:
            raise ValueError(f"{path}:{lineno}: {exc}") from exc
    if columns is None:
        raise ValueError(f"{path}: no column header found")
    return EventProtocol(meta=meta, columns=[c for c in columns if c], events=events)


def _data_lines(path: Path) -> list[str]:
    return [line for line in _read_lines(path) if line.strip()]


def parse_each(path: str | Path) -> dict[int, dict]:
    """Parse ``eAch*.Prt``: end-of-life counters and mean need strengths per seed.

    Each row: seed, the eight counters, then the four need strengths in percent
    averaged over all cycles (``round(sumLeist/cnr)`` in ``UParam.CheckMaxLife``).
    """
    result: dict[int, dict] = {}
    for line in _data_lines(Path(path)):
        parts = line.split()
        if parts[0] == "NsL" or not all(p.lstrip("-").isdigit() for p in parts):
            continue
        values = [int(p) for p in parts]
        if len(values) != 13:
            raise ValueError(f"{path}: expected 13 values, got {len(values)}: {line!r}")
        result[values[0]] = {
            "counters": dict(zip(COUNTER_NAMES, values[1:9])),
            "need_pct_mean": dict(zip(NEED_PCT_NAMES, values[9:13])),
        }
    return result


def parse_consum(path: str | Path) -> dict[int, dict]:
    """Parse ``Consum*.Prt``: total consumption and intake per motive and seed."""
    result: dict[int, dict] = {}
    for line in _data_lines(Path(path)):
        parts = line.split()
        if parts[0] == "Hung":
            continue
        if len(parts) != 1 + 2 * len(MOTIVES):
            raise ValueError(f"{path}: unexpected row {line!r}")
        values = [float(p) for p in parts[1:]]
        result[int(parts[0])] = {
            "consumption": dict(zip(MOTIVES, values[: len(MOTIVES)])),
            "intake": dict(zip(MOTIVES, values[len(MOTIVES):])),
        }
    return result


def parse_inpro(path: str | Path) -> dict[int, dict]:
    """Parse ``Inpro*.Prt``: counts of internal processes (``TIntProc``) per seed.

    After the header with the abbreviations follow three lines per run: seed and
    counts, process times (``TProcTimes``), and ten check frequencies.
    """
    lines = _data_lines(Path(path))
    names = [n.strip() for n in lines[0].split(";") if n.strip()]
    result: dict[int, dict] = {}
    rows = [[v.strip() for v in line.split(";") if v.strip()] for line in lines[1:]]
    if len(rows) % 3:
        raise ValueError(f"{path}: expected groups of three lines after the header")
    for counts, times, freqs in zip(rows[0::3], rows[1::3], rows[2::3]):
        if len(counts) != len(names) + 1:
            raise ValueError(f"{path}: {len(counts) - 1} counts for {len(names)} names")
        result[int(counts[0])] = {
            "int_proc": dict(zip(names, (int(v) for v in counts[1:]))),
            "proc_times": [int(v) for v in times],
            "check_freq": [int(v) for v in freqs],
        }
    return result


def parse_inttimes(path: str | Path) -> dict[int, dict]:
    """Parse ``IntTimes*.Txt``: time per Rasmussen stage, summed per cycle.

    Times are in age units. A cycle can have several rows (passes); they are
    summed, and the number of passes is reported.
    """
    result: dict[int, dict] = {}
    for line in _data_lines(Path(path)):
        if ":" not in line:
            continue
        cycle_str, _, rest = line.partition(":")
        values = rest.split()
        stage = dict(zip(STAGE_NAMES, (int(v) for v in values[:4])))
        entry = result.setdefault(int(cycle_str), {"stage_times": dict.fromkeys(STAGE_NAMES, 0), "passes": 0})
        for name, value in stage.items():
            entry["stage_times"][name] += value
        entry["passes"] += 1
    return result


def parse_activities(path: str | Path) -> dict[int, list[dict]]:
    """Parse ``Activities*.Txt``: one line per motor act with the internal procedures before it.

    Columns: cycle, running number, act (``Aggr``, ``Mani``, ``Loco``, ``Regr``),
    age at completion, then pairs of procedure label and duration in age units.
    """
    result: dict[int, list[dict]] = {}
    for line in _data_lines(Path(path)):
        parts = [p.strip() for p in line.split(";")]
        while parts and not parts[-1]:
            parts.pop()
        cycle, nr, act, age = int(parts[0]), int(parts[1]), parts[2], int(parts[3])
        steps = [[parts[i], int(parts[i + 1])] for i in range(4, len(parts) - 1, 2)]
        result.setdefault(cycle, []).append({"nr": nr, "act": act, "age": age, "steps": steps})
    return result


def _find(directory: Path, pattern: str) -> Path | None:
    matches = sorted(directory.glob(pattern))
    if len(matches) > 1:
        raise ValueError(f"{directory}: several files match {pattern}: {[m.name for m in matches]}")
    return matches[0] if matches else None


def convert_run_dir(
    directory: str | Path,
    ach_name: str,
    *,
    world: str | None = None,
    psi_data: str | None = None,
    params: dict | None = None,
) -> Run:
    """Convert all protocols of one run in ``directory``.

    ``ach_name`` is the per-cycle protocol, ``<Param>.Prt`` for runs with a
    parameter file. The other files are found by their names; summaries that
    collect several runs (eAch, Consum, Inpro) are filtered by the run's seed.
    """
    directory = Path(directory)
    run = convert_run(directory / ach_name, _find(directory, "Protokoll*.Dat"),
                      world=world, psi_data=psi_data, params=params)
    seed = run.header.seed
    files = {"each": _find(directory, "eAch*.Prt"), "consum": _find(directory, "Consum*.Prt"),
             "inpro": _find(directory, "Inpro*.Prt"), "inttimes": _find(directory, "IntTimes*.Txt"),
             "activities": _find(directory, "Activities*.Txt")}
    parsers = {"each": parse_each, "consum": parse_consum, "inpro": parse_inpro}
    for key, parser in parsers.items():
        if files[key] is not None:
            per_seed = parser(files[key])
            if seed in per_seed:
                run.summary.extra[key] = per_seed[seed]
    trailing: dict[str, dict] = {}
    if files["inttimes"] is not None:
        for cycle_nr, entry in parse_inttimes(files["inttimes"]).items():
            if cycle_nr < len(run.cycles):
                run.cycles[cycle_nr].stage_times = entry["stage_times"]
                run.cycles[cycle_nr].extra["stage_passes"] = entry["passes"]
            else:
                trailing.setdefault(str(cycle_nr), {}).update(entry)
    if files["activities"] is not None:
        for cycle_nr, acts in parse_activities(files["activities"]).items():
            if cycle_nr < len(run.cycles):
                run.cycles[cycle_nr].extra["activities"] = acts
            else:
                trailing.setdefault(str(cycle_nr), {})["activities"] = acts
    if trailing:
        # the ach protocol ends before the last cycle; keep its data instead of dropping it
        run.summary.extra["trailing_cycles"] = trailing
    run.header.source_files += [str(p) for p in files.values() if p is not None]
    return run


def convert_run(
    ach_path: str | Path | None = None,
    event_path: str | Path | None = None,
    *,
    world: str | None = None,
    psi_data: str | None = None,
    params: dict | None = None,
) -> Run:
    """Combine an ach file and an event protocol of the same run into a ``Run``.

    Raises ``ValueError`` if both files are given and their start times differ
    by more than ``MAX_START_SKEW_SECONDS``.
    """
    if ach_path is None and event_path is None:
        raise ValueError("at least one of ach_path and event_path is required")
    ach = parse_ach(ach_path) if ach_path is not None else None
    ev = parse_event_protocol(event_path) if event_path is not None else None

    if ach and ev and ach.started_at and ev.started_at:
        skew = abs((datetime.fromisoformat(ach.started_at)
                    - datetime.fromisoformat(ev.started_at)).total_seconds())
        if skew > MAX_START_SKEW_SECONDS:
            raise ValueError(
                f"files do not belong to the same run: started {ach.started_at} vs {ev.started_at}"
            )

    extra: dict = {}
    if ach:
        extra["ach_header"] = ach.header_raw
        if ach.skipped_lines:
            extra["ach_skipped_lines"] = ach.skipped_lines
    if ev:
        extra["event_protocol_meta"] = ev.meta

    header = RunHeader(
        source="delphi",
        program_version=ev.program_version if ev else None,
        world=world,
        psi_data=psi_data,
        seed=ach.seed if ach else None,
        started_at=(ev.started_at if ev and ev.started_at else (ach.started_at if ach else None)),
        params=dict(params or {}),
        source_files=[str(p) for p in (ach_path, event_path) if p is not None],
        extra=extra,
    )
    run = Run(header=header, cycles=ach.cycles if ach else [], events=ev.events if ev else [])
    run.summary = compute_summary(run)
    return run


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Convert protocols of the Delphi original to a run file.")
    parser.add_argument("--ach", help="ach*.Prt file")
    parser.add_argument("--events", help="Protokoll*.Dat file")
    parser.add_argument("--world")
    parser.add_argument("--psi-data")
    parser.add_argument("--out", required=True, help="output .jsonl or .jsonl.gz")
    args = parser.parse_args(argv)
    run = convert_run(args.ach, args.events, world=args.world, psi_data=args.psi_data)
    write_run(args.out, run)
    s = run.summary
    print(f"{args.out}: {s.cycles} cycles, {s.events} events")


if __name__ == "__main__":
    main()
