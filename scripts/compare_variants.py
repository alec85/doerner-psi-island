"""Compare runs of a variant with the baseline, paired by seed (ADR 0015, Issue #29).

Reads ``metrics.json`` and the run files written by ``scripts/baseline.py`` in
two run directories and reports per primary metric the mean difference
(variant minus baseline) with a 95 % bootstrap interval and a sign-flip
permutation test, Holm-adjusted over the six metrics. Also reports per seed the
first cycle in which the variant's life departs from the baseline's.

Usage:
    python scripts/compare_variants.py --base runs/baseline --variant runs/variant-all \\
        --seeds 1001-1020 --out analysis/varianten/all
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from baseline import parse_seeds  # noqa: E402
from psi_gw.analysis.metrics import PRIMARY, first_divergent_cycle, holm, paired_comparison  # noqa: E402
from psi_gw.tracing.runfile import read_run  # noqa: E402


def load(runs: Path, seeds: list[int]) -> dict[int, dict]:
    out = {}
    for s in seeds:
        f = runs / f"seed{s}" / "metrics.json"
        if f.exists():
            out[s] = json.loads(f.read_text())
    return out


def broken(runs: dict[int, dict]) -> dict[int, str]:
    return {s: r["crash"] for s, r in runs.items() if r.get("crash")}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=Path, required=True)
    ap.add_argument("--variant", type=Path, required=True)
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    seeds = parse_seeds(args.seeds)
    base, var = load(args.base, seeds), load(args.variant, seeds)
    crashes = {"base": broken(base), "variant": broken(var)}
    common = sorted((set(base) - set(crashes["base"])) & (set(var) - set(crashes["variant"])))
    results = {}
    for m in ["cycles", *PRIMARY]:
        results[m] = paired_comparison({s: float(base[s][m]) for s in common},
                                       {s: float(var[s][m]) for s in common})
    adjusted = holm({m: results[m]["p"] for m in PRIMARY})
    for m in PRIMARY:
        results[m]["p_holm"] = adjusted[m]
    divergence = {}
    for s in common:
        a = read_run(args.base / f"seed{s}" / f"inseliii__seed-{s}.jsonl.gz")
        b = read_run(args.variant / f"seed{s}" / f"inseliii__seed-{s}.jsonl.gz")
        divergence[s] = first_divergent_cycle(a, b)
    args.out.mkdir(parents=True, exist_ok=True)
    variant_names = var[common[0]].get("variant", []) if common else []
    report = {"variant": variant_names, "seeds": common, "broken_off": crashes, "metrics": results,
              "first_divergent_cycle": divergence}
    (args.out / "vergleich.json").write_text(json.dumps(report, indent=1))
    lines = [f"Variante: {', '.join(variant_names) or 'Referenz'}; {len(common)} Seeds, gepaart",
             "",
             "| Kennzahl | Differenz (Variante − Basis) | 95-%-KI | p | p (Holm) |",
             "|---|---:|---|---:|---:|"]
    for m in ["cycles", *PRIMARY]:
        r = results[m]
        ph = f"{r['p_holm']:.4f}" if "p_holm" in r else ""
        lines.append(f"| {m} | {r['mean_diff']:.4f} | [{r['ci95_low']:.4f}, {r['ci95_high']:.4f}] | {r['p']:.4f} | {ph} |")
    for side, label in (("base", "Basis"), ("variant", "Variante")):
        for s, msg in crashes[side].items():
            lines.append(f"\nAbgebrochen ({label}, Seed {s}, aus dem Vergleich genommen): {msg}")
    lines += ["", "Erster abweichender Zyklus je Seed: "
              + ", ".join(f"{s}: {c}" for s, c in divergence.items())]
    (args.out / "vergleich.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
