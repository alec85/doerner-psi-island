"""A whole island life against the recorded run of the original (golden master, ADR 0010).

Seed 16, Haselwald: the random trace of the original covers the first 20,000
draws (cycles 1 to 29). The port must draw the same numbers at the same call
sites and write the same activity protocol, line by line.
"""

import csv
import gzip
import os
from pathlib import Path

import pytest

from psi_gw.agent import CYCLE_RULE
from psi_gw.life import IslandLife
from psi_gw.random_source import DelphiRandom, RecordingSource

ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt"


def _protocol() -> list[str]:
    raw = (TRACE_DIR / "raw" / "seed16" / "actu16(1).Prt").read_bytes().decode("cp1252")
    lines = raw.replace("\r\n", "\n").replace("\r", "").split("\n")[1:]
    return [CYCLE_RULE if line.startswith("---------------") else line for line in lines]


def _activities() -> list[str]:
    raw = (TRACE_DIR / "raw" / "seed16" / "Activities(1).Txt").read_bytes().decode("cp1252")
    return [line for line in raw.replace("\r\n", "\n").split("\n") if line]


def test_first_29_cycles_identical_to_the_original():
    rng = RecordingSource(DelphiRandom(16))
    life = IslandLife(seed=16, rng=rng)
    life.run(29)
    with gzip.open(TRACE_DIR / "random_draws.tsv.gz", "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert len(rng.log) > len(rows) == 20000
    for row, draw in zip(rows, rng.log):
        assert (row["site"], int(row["randseed"])) == (draw.site, draw.state_before), row["nr"]

    # The original was stopped in the middle of cycle 29; its last line is cut off.
    original = _protocol()
    port = life.state.prn.lines
    assert port[:len(original) - 1] == original[:-1]
    assert port[len(original) - 1].startswith(original[-1])

    # Activities.Txt: age and duration of every step before each action
    acts = _activities()
    assert life.state.activity_log[:len(acts) - 1] == acts[:-1]
    assert life.state.activity_log[len(acts) - 1].startswith(acts[-1])


FULL_LIFE = ROOT / "traces" / "original-runs" / "2026-11-10-volles-leben" / "raw" / "seed16"


def _full_protocol() -> list[str]:
    raw = (FULL_LIFE / "actu16(1).Prt").read_bytes().decode("cp1252")
    lines = raw.replace("\r\n", "\n").replace("\r", "").split("\n")[1:]
    out = []
    for line in lines:
        if line.startswith("---------------"):
            line = CYCLE_RULE
        elif line.startswith("Ende der Simulation: "):
            line = "Ende der Simulation: <time>"
        out.append(line)
    while out and out[-1] == "":
        out.pop()
    return out


def test_first_70_cycles_of_the_full_life():
    """Covers cycle 65, where PlanenUndTun looks for goals in its parameter ``situation``
    (which shadows the global ``Situation``) and so in the situation before the locomotion.
    All 75,000 draws of the longer random trace are compared draw by draw."""
    rng = RecordingSource(DelphiRandom(16))
    life = IslandLife(seed=16, rng=rng)
    life.run(70)
    trace = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt-75k" / "random_draws.tsv.gz"
    with gzip.open(trace, "rt", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    assert len(rng.log) > len(rows) == 75000
    for row, draw in zip(rows, rng.log):
        assert (row["site"], int(row["randseed"])) == (draw.site, draw.state_before), row["nr"]
    original = _full_protocol()
    port = life.state.prn.lines
    assert port == original[:len(port)]
    acts = [x for x in (FULL_LIFE / "Activities(1).Txt").read_bytes().decode("cp1252").split("\r\n") if x]
    assert life.state.activity_log == acts[:len(life.state.activity_log)]


@pytest.mark.skipif(not os.environ.get("PSI_GW_FULL_LIFE"), reason="about 4 minutes; set PSI_GW_FULL_LIFE=1")
def test_full_life_identical_to_the_original():
    """All 739 cycles of the life with seed 16 and MaxLife 5,000,000: protocol, activities, summaries."""
    life = IslandLife(seed=16)
    life.run_life(5_000_000)
    assert life.ended and life.state.cycle == 739
    assert life.state.prn.lines == _full_protocol()
    acts = [x for x in (FULL_LIFE / "Activities(1).Txt").read_bytes().decode("cp1252").split("\r\n") if x]
    assert life.state.activity_log == acts
    for name, lines in life.summary_files(16).items():
        orig = [x for x in (FULL_LIFE / f"{name}(1).Prt").read_bytes().decode("cp1252").split("\r\n") if x]
        assert lines == orig, name


SEED901 = ROOT / "traces" / "original-runs" / "2026-11-10-seed901" / "raw" / "seed901"


@pytest.mark.skipif(not os.environ.get("PSI_GW_FULL_LIFE"), reason="about 4 minutes; set PSI_GW_FULL_LIFE=1")
def test_full_life_seed_901():
    """Second seed: actions, ages and summaries identical; protocol lines differ only where
    RememberDir reads a heap address byte (ADR 0014)."""
    life = IslandLife(seed=901)
    life.run_life(5_000_000)
    assert life.ended and life.state.cycle == 912
    raw = (SEED901 / "actu901(1).Prt").read_bytes().decode("cp1252")
    original = []
    for line in raw.replace("\r\n", "\n").replace("\r", "").split("\n")[1:]:
        if line.startswith("---------------"):
            line = CYCLE_RULE
        elif line.startswith("Ende der Simulation: "):
            line = "Ende der Simulation: <time>"
        original.append(line)
    while original and original[-1] == "":
        original.pop()
    port = life.state.prn.lines
    assert len(port) == len(original)
    differing = [(a, b) for a, b in zip(original, port) if a != b]
    assert len(differing) == 1 and all(" OD:" in a and " OD:" in b for a, b in differing)
    acts = [x for x in (SEED901 / "Activities(1).Txt").read_bytes().decode("cp1252").split("\r\n") if x]
    assert life.state.activity_log == acts
    for name, lines in life.summary_files(901).items():
        orig = [x for x in (SEED901 / f"{name}(1).Prt").read_bytes().decode("cp1252").split("\r\n") if x]
        assert lines == orig, name


def test_life_resumed_from_a_snapshot_equals_an_uninterrupted_life():
    """Acceptance test for persistence at the level of a whole life (Psi and island):
    snapshot after 30 cycles, JSON round trip, continue 15 cycles; the draws, the protocol
    and the actions equal those of an uninterrupted run."""
    import json

    whole = IslandLife(seed=16, rng=RecordingSource(DelphiRandom(16)), max_life=5_000_000)
    whole.run(45)

    first = IslandLife(seed=16, max_life=5_000_000)
    first.run(30)
    data = json.loads(json.dumps(first.snapshot()))
    lines_before = len(first.state.prn.lines)
    acts_before = len(first.state.activity_log)
    draws_before = first.state.rng.draws

    resumed = IslandLife.restore(data, rng_wrap=RecordingSource)
    resumed.run(15)
    assert resumed.state.prn.lines == whole.state.prn.lines[lines_before:]
    assert resumed.state.activity_log == whole.state.activity_log[acts_before:]
    tail = whole.state.rng.log[draws_before:]
    assert [(d.site, d.state_before) for d in resumed.state.rng.log] == [(d.site, d.state_before) for d in tail]
    assert json.dumps(resumed.snapshot()["state"], sort_keys=True) == json.dumps(whole.snapshot()["state"], sort_keys=True)
