"""Evaluate the workspace experiments (``docs/analyseplan-workspace.md``).

Reads ``<runs>/ws-<A..E>/seed<seed>/metrics.json`` and writes to ``<out>``:

* ``kennzahlen.csv``: one row per condition and seed, all P and W measures,
* ``beschreibung.json``: description of every measure per condition,
* ``tests.json`` / ``tests.md``: H1 to H6, paired over seeds, Holm over all six,
* ``leistung.json`` / ``leistung.md``: P1 to P6 for B to E against A, Holm per condition,
* ``README.md``: seeds, broken off lives, commit.

With ``--stage vorauswahl`` the tests are labelled as screening (not confirmatory).

Usage:
    python scripts/workspace_analysis.py --seeds 1001-1020 --stage vorauswahl --out analysis/workspace/vorauswahl
    python scripts/workspace_analysis.py --seeds 1001-1100 --stage bestaetigung --out analysis/workspace/bestaetigung
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from baseline import parse_seeds  # noqa: E402

from psi_gw.analysis.metrics import PRIMARY, describe, holm, paired_comparison  # noqa: E402
from psi_gw.analysis.workspace_metrics import WORKSPACE  # noqa: E402

CONDITIONS = ("A", "B", "C", "D", "E")

# (name, measure, condition x, condition y, predicted sign of mean(y - x))
HYPOTHESES = [
    ("H1", "W2b_lead_goal_switches_per_100", "E", "B", -1),
    ("H2", "W3_plans_aborted_per_100", "E", "B", -1),
    ("H3", "W5_arousal_dwell_spearman", "D", "B", +1),
    ("H4", "W1_dwell_nonmotive", "C", "B", +1),
    ("H5", "W4_opportunistic_per_100", "E", "B", -1),
    ("H6", "W6_share_history_dependent", "E", "B", +1),
]
DESCRIPTIVE_ONLY = [("H1 (Fassung 1)", "W2_motive_switches_per_100", "E", "B", -1)]
ALPHA = 0.05


def _baseline_csv() -> dict[int, dict]:
    path = ROOT / "analysis" / "grundlinie-modern" / "kennzahlen.csv"
    if not path.exists():
        return {}
    with path.open() as f:
        return {int(r["seed"]): {k: float(v) for k, v in r.items() if k != "seed"} for r in csv.DictReader(f)}


BASELINE_CSV = _baseline_csv()


def load(runs: Path, seeds: list[int]) -> tuple[dict[str, dict[int, dict]], dict[str, dict[int, str]]]:
    data: dict[str, dict[int, dict]] = {c: {} for c in CONDITIONS}
    broken: dict[str, dict[int, str]] = {c: {} for c in CONDITIONS}
    for c in CONDITIONS:
        for s in seeds:
            p = runs / f"ws-{c}" / f"seed{s}" / "metrics.json"
            if not p.exists() and c == "A":
                # A is the modern-mode baseline; ws-A (with workspace log) equals it seed by
                # seed on 1001-1020 (HANDOFF, step 5a), so the baseline runs stand in for the rest.
                p = runs / "variant-all" / f"seed{s}" / "metrics.json"
            if not p.exists() and c == "A" and s in BASELINE_CSV:
                # without runs/ (public repository): the archived table of the same baseline
                data[c][s] = BASELINE_CSV[s]
                continue
            if not p.exists():
                continue
            m = json.loads(p.read_text())
            if m.get("crash"):
                broken[c][s] = m["crash"]
            else:
                data[c][s] = m
    return data, broken


def column(data: dict[int, dict], name: str) -> dict[int, float]:
    out = {}
    for s, m in data.items():
        v = m.get(name)
        out[s] = math.nan if v is None else float(v)
    return out


def verdict(res: dict, sign: int, confirmatory: bool) -> str:
    if res.get("n", 0) == 0 or math.isnan(res.get("mean_diff", math.nan)):
        return "nicht auswertbar"
    p = res.get("p_holm", res["p"])
    if p >= ALPHA:
        return "nicht signifikant"
    direction = "vorhergesagte Richtung" if res["mean_diff"] * sign > 0 else "gegen die Vorhersage"
    return f"signifikant, {direction}" + ("" if confirmatory else " (Vorauswahl)")


def fmt(x: float, nd: int = 4) -> str:
    return "" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{nd}f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--runs", type=Path, default=ROOT / "runs")
    ap.add_argument("--stage", choices=("vorauswahl", "bestaetigung"), required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    seeds = parse_seeds(args.seeds)
    data, broken = load(args.runs, seeds)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    confirmatory = args.stage == "bestaetigung"
    measures = ["cycles", *PRIMARY, *WORKSPACE]

    with (out / "kennzahlen.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "seed", *measures])
        for c in CONDITIONS:
            for s in sorted(data[c]):
                w.writerow([c, s, *[data[c][s].get(m, "") for m in measures]])

    desc = {c: {m: describe([v for v in column(data[c], m).values()]) for m in measures} for c in CONDITIONS
            if data[c]}
    (out / "beschreibung.json").write_text(json.dumps(desc, indent=1))

    tests: dict[str, dict] = {}
    for name, measure, x, y, sign in HYPOTHESES + DESCRIPTIVE_ONLY:
        res = paired_comparison(column(data[x], measure), column(data[y], measure))
        tests[name] = {"measure": measure, "base": x, "other": y, "predicted_sign": sign, **res}
    adj = holm({n: tests[n]["p"] for n, *_ in HYPOTHESES if tests[n].get("n", 0) > 0})
    for n, p in adj.items():
        tests[n]["p_holm"] = p
    for name, *_rest in HYPOTHESES + DESCRIPTIVE_ONLY:
        sign = tests[name]["predicted_sign"]
        tests[name]["verdict"] = (verdict(tests[name], sign, confirmatory) if name in adj
                                  else "nur beschreibend")
    core = all(tests[h].get("verdict", "").startswith("signifikant, vorhergesagte") for h in ("H1", "H3", "H4"))
    summary = {"stage": args.stage, "seeds": [seeds[0], seeds[-1]],
               "n_per_condition": {c: len(data[c]) for c in CONDITIONS},
               "core_claim_supported": core if confirmatory else None, "tests": tests}
    (out / "tests.json").write_text(json.dumps(summary, indent=1))

    perf: dict[str, dict] = {}
    for c in "BCDE":
        if not data[c] or not data["A"]:
            continue
        res = {m: paired_comparison(column(data["A"], m), column(data[c], m)) for m in PRIMARY}
        for m, p in holm({m: r["p"] for m, r in res.items() if r.get("n", 0) > 0}).items():
            res[m]["p_holm"] = p
        perf[c] = res
    (out / "leistung.json").write_text(json.dumps(perf, indent=1))

    label = "Bestätigung" if confirmatory else "Vorauswahl (nicht bestätigend)"
    lines = [f"# Workspace-Experimente: {label}", "",
             f"Seeds {seeds[0]} bis {seeds[-1]}; Leben je Bedingung: "
             + ", ".join(f"{c} {len(data[c])}" for c in CONDITIONS), "",
             "| Test | Kennzahl | Vergleich | n | Differenz | 95-%-KI | p | p (Holm) | Urteil |",
             "|---|---|---|---:|---:|---|---:|---:|---|"]
    for name, *_rest in HYPOTHESES + DESCRIPTIVE_ONLY:
        t = tests[name]
        lines.append(f"| {name} | {t['measure']} | {t['other']} − {t['base']} | {t.get('n', 0)} | "
                     f"{fmt(t.get('mean_diff'))} | [{fmt(t.get('ci95_low'))}, {fmt(t.get('ci95_high'))}] | "
                     f"{fmt(t.get('p'))} | {fmt(t.get('p_holm'))} | {t['verdict']} |")
    if confirmatory:
        lines += ["", "Kernaussage (H1, H3 und H4 signifikant in vorhergesagter Richtung): "
                  + ("gestützt" if core else "nicht gestützt")]
    lines += ["", "## P1 bis P6 gegen A (beschreibend, Holm je Bedingung)", "",
              "| Bedingung | Kennzahl | n | Differenz | 95-%-KI | p (Holm) |", "|---|---|---:|---:|---|---:|"]
    for c, res in perf.items():
        for m, r in res.items():
            lines.append(f"| {c} | {m} | {r.get('n', 0)} | {fmt(r.get('mean_diff'))} | "
                         f"[{fmt(r.get('ci95_low'))}, {fmt(r.get('ci95_high'))}] | {fmt(r.get('p_holm'))} |")
    lines += ["", "## Mittelwerte je Bedingung", "",
              "| Kennzahl | " + " | ".join(c for c in CONDITIONS if c in desc) + " |",
              "|---|" + "---:|" * len(desc)]
    for m in measures:
        lines.append(f"| {m} | " + " | ".join(fmt(desc[c][m].get("mean"), 3) for c in CONDITIONS if c in desc)
                     + " |")
    if any(broken.values()):
        lines += ["", "## Abgebrochene Leben", ""]
        for c in CONDITIONS:
            for s, why in sorted(broken[c].items()):
                lines.append(f"- {c}, Seed {s}: {why}")
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    lines += ["", f"Erzeugt mit `scripts/workspace_analysis.py` auf Commit {commit}."]
    (out / "tests.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
