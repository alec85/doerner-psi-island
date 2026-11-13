"""Run many island lives with the port and evaluate them (analysis plan, Issue #28).

Each seed is one life with MaxLife 5,000,000. Results go to ``<runs>/seed<seed>/``:
raw protocols, the run file and ``metrics.json``. Seeds whose ``metrics.json``
exists are skipped, so an interrupted series is continued by starting the same
command again.

``--report`` writes the per-seed table and the description of each metric
(mean, sd, median, IQR, bootstrap CI) to ``<report>``.

Usage:
    python scripts/baseline.py --seeds 901-905 --runs runs/baseline --jobs 2
    python scripts/baseline.py --seeds 901-905 --runs runs/baseline --report analysis/referenzlaeufe/pilot
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from psi_gw.analysis.metrics import PRIMARY, describe, primary_metrics  # noqa: E402
from psi_gw.analysis.workspace_metrics import WORKSPACE, workspace_metrics  # noqa: E402
from psi_gw.tracing.runfile import read_run  # noqa: E402

MAX_LIFE = 5_000_000


def parse_seeds(text: str) -> list[int]:
    seeds: list[int] = []
    for part in text.split(","):
        a, _, b = part.partition("-")
        seeds += list(range(int(a), int(b or a) + 1))
    return seeds


def one(seed: int, runs: Path, variant: str = "") -> dict:
    from run_port import run_and_write

    from psi_gw.variant import Variant
    out = runs / f"seed{seed}"
    t0 = time.monotonic()
    life, trace, crash = run_and_write(seed, MAX_LIFE, out, Variant.from_names(variant))
    metrics = primary_metrics(read_run(trace))
    ws_log = out / "raw" / "Workspace(1).jsonl"
    if ws_log.exists():
        metrics.update(workspace_metrics(ws_log))
    result = {"seed": seed, "variant": life.state.variant.active(), "crash": crash,
              "guarded": life.state.n_guarded, "cycles": life.state.cycle, "age": life.state.clock.age,
              "seconds": round(time.monotonic() - t0), **metrics}
    (out / "metrics.json").write_text(json.dumps(result, indent=1))
    return result


def report(seeds: list[int], runs: Path, target: Path) -> None:
    rows, crashed = [], []
    for seed in seeds:
        f = runs / f"seed{seed}" / "metrics.json"
        if f.exists():
            r = json.loads(f.read_text())
            (crashed if r.get("crash") else rows).append(r)
    if not rows:
        raise SystemExit("no finished seeds")
    target.mkdir(parents=True, exist_ok=True)
    cols = ["seed", "cycles", "age", *PRIMARY] + [c for c in WORKSPACE if c in rows[0]]
    with (target / "kennzahlen.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in rows:
            w.writerow([r[c] for c in cols])
    desc = {c: describe([float(r[c]) for r in rows]) for c in cols[3:] + ["cycles"]}
    (target / "beschreibung.json").write_text(json.dumps(desc, indent=1))
    (target / "abgebrochen.json").write_text(json.dumps([{"seed": r["seed"], "crash": r["crash"]} for r in crashed],
                                                       indent=1))
    print(f"{len(rows)} of {len(seeds)} seeds, {len(crashed)} broken off (not described)")
    for c, d in desc.items():
        print(f"  {c:34s} mean {d['mean']:10.3f}  sd {d['sd']:9.3f}  median {d['median']:10.3f}  "
              f"CI [{d['ci95_low']:.3f}, {d['ci95_high']:.3f}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True, help="e.g. 901-905 or 1001-1100")
    ap.add_argument("--runs", type=Path, default=ROOT / "runs" / "baseline")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--variant", default="",
                    help="switched off artefacts (psi_gw.variant); use a separate --runs directory per variant")
    args = ap.parse_args()
    seeds = parse_seeds(args.seeds)
    if args.report:
        report(seeds, args.runs, args.report)
        return 0
    todo = [s for s in seeds if not (args.runs / f"seed{s}" / "metrics.json").exists()]
    print(f"{len(seeds) - len(todo)} done, {len(todo)} to run", flush=True)
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {pool.submit(one, s, args.runs, args.variant): s for s in todo}
        for f in as_completed(futures):
            r = f.result()
            print(f"seed {r['seed']}: {r['cycles']} cycles, {r['seconds']} s"
                  + (f", BROKE OFF {r['crash']}" if r.get("crash") else ""), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
