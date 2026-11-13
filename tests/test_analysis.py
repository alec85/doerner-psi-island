"""Run files of the port and metrics of the analysis plan."""

import math
from pathlib import Path

from psi_gw.analysis.metrics import PRIMARY, describe, primary_metrics
from psi_gw.life import IslandLife
from psi_gw.tracing.delphi_protocols import convert_run_dir

ROOT = Path(__file__).resolve().parents[1]
FULL_LIFE = ROOT / "traces" / "original-runs" / "2026-11-10-volles-leben" / "raw" / "seed16"


def test_port_run_file_matches_the_original_per_cycle(tmp_path):
    """Short life (MaxLife 30,000): the per-cycle records equal those of the original's full life.

    MaxLife only cuts the life short (analysis plan, known fact 2); the life
    percentage differs and is left out.
    """
    life = IslandLife(seed=16, max_life=30_000)
    life.run_life(30_000)
    assert life.ended
    life.write_protocols(tmp_path, 16)
    port = convert_run_dir(tmp_path, "seed16.Prt")
    orig = convert_run_dir(FULL_LIFE, "seed16.Prt")
    assert len(port.cycles) == life.state.cycle
    for p, o in zip(port.cycles, orig.cycles):
        assert (p.counters, p.need_pct, p.age, p.age_diff) == (o.counters, o.need_pct, o.age, o.age_diff)
        if p.cycle + 1 < len(port.cycles):  # the last cycle has the extra IntTimes line after CheckMaxLife
            assert p.stage_times == o.stage_times
    m = primary_metrics(port)
    assert set(m) == set(PRIMARY)
    assert all(not math.isnan(v) for v in m.values())


def test_primary_metrics_of_the_original_full_life():
    m = primary_metrics(convert_run_dir(FULL_LIFE, "seed16.Prt"))
    # 8 deaths in 739 cycles of the ach file (the ach file has one line per cycle)
    assert m["P1_exitus_per_1000_cycles"] == 1000 * 8 / 739
    assert m["P3_locations_discovered"] == 88


def test_describe():
    d = describe([1.0, 2.0, 3.0, 4.0], n_boot=2000)
    assert d["n"] == 4 and d["mean"] == 2.5 and d["median"] == 2.5 and d["iqr"] == 1.5
    assert 1.0 <= d["ci95_low"] < 2.5 < d["ci95_high"] <= 4.0


def test_paired_comparison_and_holm():
    from psi_gw.analysis.metrics import holm, paired_comparison
    base = {s: float(s) for s in range(10)}
    same = paired_comparison(base, dict(base))
    assert same["mean_diff"] == 0 and same["p"] == 1.0
    shifted = paired_comparison(base, {s: v + 1 + 0.1 * (s % 3) for s, v in base.items()})
    assert shifted["p"] == 2 / 2 ** 10 and shifted["ci95_low"] > 0.9
    assert holm({"a": 0.01, "b": 0.04, "c": 0.03}) == {"a": 0.03, "c": 0.06, "b": 0.06}
