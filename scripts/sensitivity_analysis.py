"""Evaluation of the post-hoc sensitivity runs (docs/analyseplan-sensitivitaet.md).

Writes ``analysis/revision/sensitivitaet/ergebnis.json``. Parts whose runs are missing are skipped.

Usage: python scripts/sensitivity_analysis.py [--runs runs]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from statistics import mean, median

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from psi_gw.analysis.metrics import PRIMARY, paired_comparison  # noqa: E402
from psi_gw.analysis.workspace_metrics import read_log, workspace_metrics  # noqa: E402

SEEDS = list(range(1001, 1021))
OUT = ROOT / "analysis" / "revision" / "sensitivitaet"


def logs(runs: Path, name: str) -> dict[int, list[dict]]:
    out = {}
    for s in SEEDS:
        p = runs / name / f"seed{s}" / "raw" / "Workspace(1).jsonl"
        if p.exists() and (runs / name / f"seed{s}" / "metrics.json").exists():
            out[s] = read_log(p)[0]
    return out


def metrics(runs: Path, name: str) -> dict[int, dict]:
    out = {}
    for s in SEEDS:
        p = runs / name / f"seed{s}" / "metrics.json"
        if p.exists():
            m = json.loads(p.read_text())
            m.update(workspace_metrics(runs / name / f"seed{s}" / "raw" / "Workspace(1).jsonl"))
            out[s] = m
    return out


def any_memoryless_share(recs: list[dict]) -> float:
    rs = [r for r in recs if "differs_from_any_memoryless" in r]
    return mean(bool(r["differs_from_any_memoryless"]) for r in rs) if rs else math.nan


def diagnostics(recs: list[dict], bonus_of) -> dict:
    rs = [r for r in recs if "tie_at_boundary" in r]
    margins = [r["margin"] for r in rs if r.get("margin") is not None]
    rel = [r["margin"] / bonus_of(r) for r in rs if r.get("margin") is not None and bonus_of(r) > 0]
    return {"cycles": len(rs), "share_tie_at_boundary": mean(bool(r["tie_at_boundary"]) for r in rs),
            "share_without_loser": mean(r.get("margin") is None for r in rs),
            "margin_median": median(margins) if margins else None,
            "share_margin_below_bonus": mean(m < 1 for m in rel) if rel else None,
            "share_differs_from_any_memoryless": any_memoryless_share(recs),
            "share_differs_from_memoryless_by_name": mean(bool(r.get("differs_from_memoryless")) for r in rs)}


def col(ms, key):
    return {s: m[key] for s, m in ms.items() if key in m and not (isinstance(m[key], float) and math.isnan(m[key]))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=ROOT / "runs")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    runs = args.runs
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict = {"seeds": [SEEDS[0], SEEDS[-1]]}
    # S1: identity with the confirmatory logs, ties and margins in B
    s1 = logs(runs, "sens-S1-B")
    if s1:
        ref = logs(runs, "ws-B")
        identical = [s for s in s1 if len(s1[s]) == len(ref[s]) and all(
            [(c["kind"], c["name"]) for c in a.get("contents", [])] == [(c["kind"], c["name"]) for c in b.get("contents", [])]
            for a, b in zip(s1[s], ref[s]))]
        pooled = [r for s in s1 for r in s1[s]]
        result["S1_B"] = {"lives": len(s1), "identical_to_confirmatory": len(identical),
                          **diagnostics(pooled, lambda r: r["threshold"])}
    # S2: random ties, B against E, and the same seeds under the name rule
    s2b, s2e = metrics(runs, "sens-S2-B"), metrics(runs, "sens-S2-E")
    if s2b and s2e:
        nb, ne = metrics(runs, "ws-B"), metrics(runs, "ws-E")
        keys = ["W2b_lead_goal_switches_per_100", "W1_dwell_nonmotive", "W6_share_history_dependent",
                "W5_arousal_dwell_spearman", "W3_plans_aborted_per_100", "W4_opportunistic_per_100"]
        common = sorted(set(s2b) & set(s2e))
        rand = {k: paired_comparison({s: s2e[s][k] for s in common}, {s: s2b[s][k] for s in common}) for k in keys}
        name = {k: paired_comparison({s: ne[s][k] for s in common}, {s: nb[s][k] for s in common}) for k in keys}
        means = {k: {"B_random": mean(s2b[s][k] for s in common), "E_random": mean(s2e[s][k] for s in common),
                     "B_name": mean(nb[s][k] for s in common), "E_name": mean(ne[s][k] for s in common)}
                 for k in keys}
        lb, le = logs(runs, "sens-S2-B"), logs(runs, "sens-S2-E")
        result["S2"] = {
            "lives": len(common), "B_minus_E_random_ties": rand, "B_minus_E_name_rule_same_seeds": name,
            # exploratory (review round 2): effect of the tie rule within a condition
            "B_random_minus_B_name": {k: paired_comparison({s: nb[s][k] for s in common},
                                                           {s: s2b[s][k] for s in common}) for k in keys},
            "E_random_minus_E_name": {k: paired_comparison({s: ne[s][k] for s in common},
                                                           {s: s2e[s][k] for s in common}) for k in keys},
            "means": means,
            "diagnostics_B_random": diagnostics([r for s in lb for r in lb[s]], lambda r: r["threshold"]),
            "diagnostics_E_random": diagnostics([r for s in le for r in le[s]], lambda r: 0.0)}
    # S3: bonus series 0 (E), 0.02, 0.0646 (D), 0.2
    lo, hi = metrics(runs, "sens-S3-lo"), metrics(runs, "sens-S3-hi")
    if lo and hi:
        series = {"0": metrics(runs, "ws-E"), "0.02": lo, "0.064642": metrics(runs, "ws-D"), "0.2": hi}
        keys = ["W2b_lead_goal_switches_per_100", "W1_dwell_nonmotive", "W6_share_history_dependent",
                *PRIMARY, "cycles"]
        common = sorted(set.intersection(*(set(v) for v in series.values())))
        result["S3"] = {"lives": len(common), "means": {
            b: {k: mean(ms[s][k] for s in common if not (isinstance(ms[s][k], float) and math.isnan(ms[s][k])))
                for k in keys} for b, ms in series.items()},
            "hi_minus_E": {k: paired_comparison({s: series["0"][s][k] for s in common},
                                                {s: hi[s][k] for s in common}) for k in PRIMARY}}
        dl = {b: logs(runs, n) for b, n in (("0.02", "sens-S3-lo"), ("0.2", "sens-S3-hi"))}
        result["S3"]["diagnostics"] = {b: diagnostics([r for s in v for r in v[s]], lambda r, b=b: float(b))
                                       for b, v in dl.items()}
    (out_dir / "ergebnis.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps(result, indent=1)[:6000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
