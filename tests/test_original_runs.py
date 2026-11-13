"""Checks on reference runs of the original produced under Wine (docs/delphi-build.md)."""

from collections import Counter
from pathlib import Path

from psi_gw.tracing import read_run
from psi_gw.tracing.vocabulary import STATUS_END

DET = Path(__file__).resolve().parents[1] / "traces" / "original-runs" / "2026-11-09-determinismus"


def _load(name: str):
    return read_run(DET / name / "inseliii__seed-16.jsonl.gz")


def test_same_seed_runs_are_identical():
    a, b = _load("r1"), _load("r2")
    assert a.header.seed == b.header.seed == 16
    assert a.summary.cycles == 72 and a.summary.events == 647
    assert [c.to_dict() for c in a.cycles] == [c.to_dict() for c in b.cycles]

    def behaviour(e):
        d = e.to_dict()
        for wall_clock_field in ("wall_time", "wall_ms"):
            d.pop(wall_clock_field)
        return d

    assert [behaviour(e) for e in a.events] == [behaviour(e) for e in b.events]


def test_counters_match_events_in_wine_run():
    run = _load("r1")
    for k, cycle in enumerate(run.cycles):
        done = Counter(e.action for e in run.events if e.status == STATUS_END and e.cycle <= k)
        c = cycle.counters
        assert done["Locomotion"] == c["successful_locomotions"] + c["unsuccessful_locomotions"], k
        assert done["Manipuliere"] == c["successful_manipulations"] + c["unsuccessful_manipulations"], k
        assert done["Aggression"] == c["aggressions"], k


MEASURE = DET.parent / "2026-11-10-messlauf"


def test_longer_run_starts_exactly_like_shorter_run():
    """MaxLife only truncates a run: cycles 1 to 71 match the 100000-unit runs."""
    long_run = read_run(MEASURE / "inseliii__seed-16.jsonl.gz")
    short_run = _load("r1")
    assert long_run.summary.cycles == 316

    def behaviour(run):
        out = []
        for e in run.events:
            if e.cycle is not None and e.cycle <= 71:
                d = e.to_dict()
                d.pop("wall_time")
                d.pop("wall_ms")
                out.append(d)
        return out

    assert behaviour(long_run) == behaviour(short_run)

    def cycle_data(run):
        out = []
        for c in run.cycles[:72]:
            d = c.to_dict()
            d.pop("life_pct")  # age in percent of MaxLife, differs by definition
            out.append(d)
        return out

    assert cycle_data(long_run) == cycle_data(short_run)


FULL = DET.parent / "2026-11-10-volles-leben"


def test_full_life_starts_exactly_like_measurement_run():
    full = read_run(FULL / "inseliii__seed-16.jsonl.gz")
    measure = read_run(MEASURE / "inseliii__seed-16.jsonl.gz")
    assert full.summary.cycles == 739
    assert full.summary.counters["exitus"] == 8
    assert [d["cycle"] for d in full.header.extra["dialogs_dismissed"]] == [571]

    def behaviour(run, max_cycle):
        out = []
        for e in run.events:
            if e.cycle is not None and e.cycle <= max_cycle:
                d = e.to_dict()
                d.pop("wall_time")
                d.pop("wall_ms")
                out.append(d)
        return out

    assert behaviour(full, 315) == behaviour(measure, 315)


def test_full_life_is_identical_on_repetition_including_dialog():
    """The GravityList dialog appears at the same cycle and does not change the run,
    although it waited 5.5 minutes in the first run and a few seconds in the second."""
    first = read_run(FULL / "inseliii__seed-16.jsonl.gz")
    second = read_run(FULL / "wiederholung" / "inseliii__seed-16.jsonl.gz")
    assert [d["cycle"] for d in second.header.extra["dialogs_dismissed"]] == [571]

    def behaviour(run):
        out = []
        for e in run.events:
            d = e.to_dict()
            d.pop("wall_time")
            d.pop("wall_ms")
            out.append(d)
        return out

    assert behaviour(first) == behaviour(second)
    assert [c.to_dict() for c in first.cycles] == [c.to_dict() for c in second.cycles]
    assert first.summary.to_dict() == second.summary.to_dict()
