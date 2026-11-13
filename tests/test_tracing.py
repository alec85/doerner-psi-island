"""Tests for run files and procedure test cases (ADR 0006)."""

import gzip
import json

import pytest

from psi_gw.tracing import (
    CycleRecord,
    EventRecord,
    ProcedureCase,
    Run,
    RunHeader,
    RunWriter,
    compute_summary,
    load_case,
    read_run,
    save_case,
    write_run,
)
from psi_gw.tracing.vocabulary import COUNTER_NAMES, STATUS_BEGIN, STATUS_END, STATUS_INFO


def _counters(**overrides):
    values = {name: 0 for name in COUNTER_NAMES}
    values.update(overrides)
    return values


def _sample_run() -> Run:
    header = RunHeader(source="python", program_version="0.0.1", world="InselIII", seed=42)
    cycles = [
        CycleRecord(cycle=0, age=0, counters=_counters(nucleotides_collected=5), life_pct=0),
        CycleRecord(cycle=1, age=1585, age_diff=1585,
                    counters=_counters(aggressions=1, nucleotides_collected=5),
                    need_pct={"hunger": 2, "thirst": 3, "damage": 0, "affiliation": 1}),
    ]
    events = [
        EventRecord(action="Aggression", seq=1, cycle=1, age=1585, status=STATUS_BEGIN,
                    params=["129", "133"], situation="Haselwald",
                    needs={"hunger": 0.0239, "thirst": 0.0257},
                    modulators={"arousal": 0.344, "resolution_level": 0.759,
                                "selection_threshold": 0.0344}),
        EventRecord(action="Aggression", seq=1, cycle=1, age=1585, status=STATUS_END,
                    situation="Haselwald", object="Hasel", position=(130, 129)),
        EventRecord(action="Motivation", seq=3, cycle=1, status=STATUS_INFO,
                    params=["Hunger", "-0.3"]),
    ]
    run = Run(header=header, cycles=cycles, events=events)
    run.summary = compute_summary(run)
    return run


@pytest.mark.parametrize("name", ["run.jsonl", "run.jsonl.gz"])
def test_round_trip(tmp_path, name):
    run = _sample_run()
    path = tmp_path / name
    write_run(path, run)
    loaded = read_run(path)
    assert loaded == run
    if name.endswith(".gz"):
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            assert json.loads(fh.readline())["type"] == "run"


def test_summary_counts_each_action_once():
    summary = compute_summary(_sample_run())
    assert summary.cycles == 2
    assert summary.events == 3
    assert summary.action_counts == {"Aggression": 1, "Motivation": 1}
    assert summary.counters["aggressions"] == 1


def test_header_must_come_first(tmp_path):
    path = tmp_path / "bad.jsonl"
    cycle = CycleRecord(cycle=0, age=0, counters=_counters()).to_dict()
    path.write_text(json.dumps(cycle) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="first record must be 'run'"):
        read_run(path)


def test_nothing_after_summary(tmp_path):
    run = _sample_run()
    path = tmp_path / "run.jsonl"
    with RunWriter(path, run.header) as writer:
        writer.write(run.summary)
        with pytest.raises(ValueError, match="follow the summary"):
            writer.write(run.cycles[0])


def test_unknown_format_version_is_rejected(tmp_path):
    path = tmp_path / "future.jsonl"
    header = RunHeader(source="delphi").to_dict()
    header["format_version"] = 99
    path.write_text(json.dumps(header) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported format_version"):
        read_run(path)


def test_unknown_keys_and_names_are_rejected():
    data = EventRecord(action="Start").to_dict()
    data["mood"] = "fine"
    with pytest.raises(ValueError, match="unknown keys"):
        EventRecord.from_dict(data)
    with pytest.raises(ValueError, match="unknown names"):
        EventRecord(action="Start", needs={"boredom": 0.5})
    with pytest.raises(ValueError, match="missing counters"):
        CycleRecord(cycle=0, age=0, counters={"exitus": 0})


def _case(**overrides) -> ProcedureCase:
    values = dict(
        procedure="GoalGen",
        unit="UPSIMain.Pas",
        case_id="goalgen-001",
        random_stream=[0.31, 0.77, 0.05],
        random_consumed=2,
        inputs={"args": {"motive": "hunger"}, "state": {"needs": {"hunger": {"activity": 0.8}}}},
        expected={"result": None, "state": {"goal_list": ["Sdab", "Sdgb"],
                                            "needs": {"hunger": {"activity": 0.75}}}},
        compare_exact=["state.goal_list"],
        compare_approx=["state.needs.hunger.activity"],
    )
    values.update(overrides)
    return ProcedureCase(**values)


def test_case_round_trip(tmp_path):
    case = _case()
    path = tmp_path / "procedures" / "GoalGen" / "goalgen-001.json"
    save_case(path, case)
    assert load_case(path) == case


def test_case_check_reports_mismatches():
    case = _case()
    good = {"result": None, "state": {"goal_list": ["Sdab", "Sdgb"],
                                      "needs": {"hunger": {"activity": 0.75 * (1 + 1e-12)}}}}
    assert case.check(good, consumed=2) == []

    bad = {"result": None, "state": {"goal_list": ["Sdgb", "Sdab"],
                                     "needs": {"hunger": {"activity": 0.76}}}}
    problems = case.check(bad, consumed=3)
    assert len(problems) == 3
    assert any("random draws" in p for p in problems)


def test_case_validation():
    with pytest.raises(ValueError, match=r"\[0, 1\)"):
        _case(random_stream=[1.0])
    with pytest.raises(ValueError, match="consumed"):
        _case(random_consumed=5)
    with pytest.raises(KeyError):
        _case(compare_exact=["state.no_such_field"])
