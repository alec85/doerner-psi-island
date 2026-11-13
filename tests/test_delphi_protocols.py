"""Converters for the original's protocols, tested against the real files in reference/."""

from collections import Counter
from pathlib import Path

import pytest

from psi_gw.tracing import read_run, write_run
from psi_gw.tracing.delphi_protocols import (
    convert_run,
    parse_ach,
    parse_event_protocol,
    parse_start_time,
)
from psi_gw.tracing.vocabulary import STATUS_BEGIN, STATUS_END

ROOT = Path(__file__).resolve().parents[1] / "reference" / "delphi-original" / "PsiCode" / "Protokoll"
TEST = ROOT / "Test"
ACH_2014 = TEST / "ach16(1).Prt"
EVENTS_2014 = TEST / "Protokoll(1).Dat"


def test_start_time_formats():
    assert parse_start_time("26.05.2003 12:07:01") == "2003-05-26T12:07:01"
    assert parse_start_time("Sun 09.03.2014 19:42:08") == "2014-03-09T19:42:08"
    assert parse_start_time("3/9/2014 7:42:08 PM") == "2014-03-09T19:42:08"
    assert parse_start_time("1/2/2003 12:05:00 AM") == "2003-01-02T00:05:00"
    assert parse_start_time("no date") is None


def test_ach_2014():
    ach = parse_ach(ACH_2014)
    assert ach.seed == 16
    assert ach.started_at == "2014-03-09T19:42:08"
    assert len(ach.cycles) == 46
    assert ach.skipped_lines == []

    start = ach.cycles[0]
    assert start.age == 0
    assert start.counters["nucleotides_collected"] == 5  # initial value set in UStrukturen
    assert start.counters["locations_discovered"] == 1   # the start location

    assert ach.cycles[1].age == 2108
    assert ach.cycles[2].counters["unsuccessful_manipulations"] == 2


def test_ach_variants():
    assert len(parse_ach(TEST / "ach1.Prt").cycles) == 335
    empty = parse_ach(TEST / "ach30.Prt")
    assert empty.seed == 30 and empty.cycles == []


def test_event_protocol_2014():
    ev = parse_event_protocol(EVENTS_2014)
    assert ev.program_version == "Psi 4.9.1.200"
    assert ev.started_at == "2014-03-09T19:42:08"
    assert len(ev.events) == 419
    assert Counter(e.action for e in ev.events) == {
        "Start": 1, "Aggression": 70, "Manipuliere": 164, "Motivation": 65,
        "Regression": 34, "Locomotion": 84, "Stop": 1,
    }

    begin, end = ev.events[1], ev.events[2]
    assert (begin.action, begin.status, begin.params) == ("Aggression", STATUS_BEGIN, ["129", "133"])
    assert (end.status, end.object, end.position) == (STATUS_END, "Hasel", (130, 129))
    assert end.needs["hunger"] == pytest.approx(0.0239499478078753, rel=1e-15)
    assert set(end.modulators) == {"arousal", "resolution_level", "selection_threshold"}
    assert all(not e.extra for e in ev.events)


def test_event_protocol_without_nr_column():
    ev = parse_event_protocol(ROOT / "depress" / "Protokoll(1).Dat")
    assert ev.program_version == "Psi 4.9.0.100"
    assert "Nr" not in ev.columns
    assert len(ev.events) == 26
    assert all(e.seq is None for e in ev.events)


def test_ach_counters_match_event_protocol():
    """Two independent protocols of the same run must agree.

    Cycle record k holds the counters after behaviour cycle k (Takt k), so it
    equals the number of completed actions in events with cycle <= k.
    """
    ach = parse_ach(ACH_2014)
    events = parse_event_protocol(EVENTS_2014).events
    for k, cycle in enumerate(ach.cycles):
        done = Counter(e.action for e in events if e.status == STATUS_END and e.cycle <= k)
        c = cycle.counters
        assert done["Locomotion"] == c["successful_locomotions"] + c["unsuccessful_locomotions"], k
        assert done["Manipuliere"] == c["successful_manipulations"] + c["unsuccessful_manipulations"], k
        assert done["Aggression"] == c["aggressions"], k


def test_convert_and_round_trip(tmp_path):
    run = convert_run(ACH_2014, EVENTS_2014, world="InselIII", psi_data="InselIII")
    assert run.header.source == "delphi"
    assert run.header.seed == 16
    assert run.header.program_version == "Psi 4.9.1.200"
    assert run.summary.cycles == 46 and run.summary.events == 419
    assert run.summary.counters["successful_locomotions"] == 17

    path = tmp_path / "insel__seed-16__1.jsonl.gz"
    write_run(path, run)
    assert read_run(path) == run


def test_files_of_different_runs_are_rejected():
    with pytest.raises(ValueError, match="same run"):
        convert_run(TEST / "ach16.Prt", EVENTS_2014)  # 2003 vs 2014


WINE_RAW = (Path(__file__).resolve().parents[1] / "traces" / "original-runs"
            / "2026-11-09-determinismus" / "r1" / "raw" / "seed16")


def test_summary_protocols_of_wine_run():
    from psi_gw.tracing.delphi_protocols import parse_consum, parse_each, parse_inpro

    each = parse_each(WINE_RAW / "eAch(1).Prt")[16]
    assert each["counters"]["aggressions"] == 59
    assert each["need_pct_mean"] == {"hunger": 1, "thirst": 1, "damage": 49, "affiliation": 0}

    consum = parse_consum(WINE_RAW / "Consum(1).Prt")[16]
    assert consum["consumption"]["damage"] == pytest.approx(2.29)
    assert consum["intake"]["nucleotides"] == pytest.approx(30.0)

    inpro = parse_inpro(WINE_RAW / "Inpro(1).Prt")[16]
    assert len(inpro["int_proc"]) == 43                       # all members of TIntProc
    assert list(inpro["int_proc"])[:3] == ["SgOp", "SsOp", "SaOp"]
    assert inpro["int_proc"]["SgOp"] == 53
    assert len(inpro["check_freq"]) == 10


def test_stage_times_and_activities_of_wine_run():
    from psi_gw.tracing.delphi_protocols import convert_run_dir

    run = convert_run_dir(WINE_RAW, "seed16.Prt")
    assert run.cycles[4].stage_times == {"look_around": 0, "automatism": 185, "plan": 6,
                                         "what_could_be_done": 124}
    acts = [a for c in run.cycles for a in c.extra.get("activities", [])]
    acts += run.summary.extra["trailing_cycles"]["72"]["activities"]
    assert len(acts) == 298
    assert Counter(a["act"] for a in acts) == {"Mani": 117, "Loco": 64, "Aggr": 59, "Regr": 58}
    # every motor act except regressions has a begin event in the event protocol
    begins = Counter(e.action for e in run.events if e.status == STATUS_BEGIN)
    assert begins == {"Manipuliere": 117, "Locomotion": 64, "Aggression": 59}
    assert set(run.summary.extra) == {"each", "consum", "inpro", "trailing_cycles"}
