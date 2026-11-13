"""Extract the inputs of the revision analyses that the run archives do not contain.

The archives in ``traces/port-runs/`` hold the run traces (``*.jsonl.gz``) of the baseline
lives and ``metrics.json`` plus the workspace log of the workspace lives. The revision
analyses (``scripts/revision_analysis.py``) also count actions (``Activities(1).Txt``),
motive reports (``AktMot:`` in ``actu*.Prt``) and guard interventions, and read the
parameter file of the original. This script derives these quantities once from the full
local runs and writes them, with SHA-256 hashes of every source file, to
``analysis/revision/eingangsdaten/``:

* ``leben-paper1.csv``: reference and modern mode, seeds 1001 to 1100,
* ``handlungen-paper2.csv``: workspace conditions B to E, seeds 1001 to 1100,
* ``parameter-inseliii.json``: the parameters read from ``Param.Dat``, with its hash.

Counting rules: actions = non-empty lines of ``Activities(1).Txt``; motive entries = lines of
``actu*.Prt`` that start with ``AktMot:`` (second token is the motive); guard interventions =
occurrences of ``nil abgefangen`` in ``actu*.Prt``.

Needs ``runs/`` with raw files and ``reference/``. Existing files are overwritten only with
``--force``.

Usage: python scripts/extract_revision_inputs.py [--runs runs] [--force]
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "analysis" / "revision" / "eingangsdaten"
SEEDS = range(1001, 1101)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def need(path: Path) -> Path:
    if not path.exists():
        raise SystemExit(f"missing input: {path} (this step needs the full local runs)")
    return path


def actions(raw: Path) -> tuple[int, str]:
    act = need(raw / "Activities(1).Txt")
    return sum(1 for line in act.read_bytes().splitlines() if line.strip()), sha(act)


def life_row(mode: str, run_dir: Path, seed: int) -> dict:
    sdir = run_dir / f"seed{seed}"
    metrics = json.loads(need(sdir / "metrics.json").read_text())
    raw = sdir / "raw"
    actu = need(next(raw.glob("actu*.Prt"), raw / "actu-missing.Prt"))
    text = actu.read_bytes()
    motives = [line.split()[1].decode("cp1252") for line in text.splitlines()
               if line.strip().startswith(b"AktMot:")]
    n_actions, act_sha = actions(raw)
    trace = next(sdir.glob("*.jsonl.gz"))
    return {"mode": mode, "seed": seed, "crash": metrics.get("crash") or "", "guarded": text.count(b"nil abgefangen"),
            "cycles": metrics["cycles"], "age": metrics["age"],
            "variant": "+".join(metrics.get("variant") or []) or "reference",
            "n_actions": n_actions, "motive_entries": len(motives),
            "nukleo_entries": sum(m == "Nukleo" for m in motives),
            "motive_switches": sum(1 for a, b in zip(motives, motives[1:]) if a != b),
            "other_motives": ";".join(sorted({m for m in motives if m != "Nukleo"})),
            "sha256_actu": sha(actu), "sha256_activities": act_sha, "sha256_trace": sha(trace)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=ROOT / "runs")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    targets = [OUT / "leben-paper1.csv", OUT / "handlungen-paper2.csv", OUT / "parameter-inseliii.json"]
    if any(t.exists() for t in targets) and not args.force:
        raise SystemExit(f"{OUT} already holds extracted inputs; use --force to overwrite")
    rows = [life_row(mode, args.runs / d, s) for s in SEEDS
            for mode, d in (("reference", "baseline"), ("modern", "variant-all"))]
    with targets[0].open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    rows2 = []
    for cond in "BCDE":
        for s in SEEDS:
            raw = args.runs / f"ws-{cond}" / f"seed{s}" / "raw"
            n, act_sha = actions(raw)
            rows2.append({"condition": cond, "seed": s, "n_actions": n, "sha256_activities": act_sha,
                          "sha256_workspace_log": sha(need(raw / "Workspace(1).jsonl"))})
    with targets[1].open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows2[0]))
        w.writeheader()
        w.writerows(rows2)
    from psi_gw.params import ISLAND_PARAM_DAT, read_param_dat
    params = read_param_dat()
    snap = {"source": "reference/delphi-original/PsiCode/PsiDaten/InselIII/Param.Dat",
            "sha256": sha(need(Path(ISLAND_PARAM_DAT))),
            "params": dataclasses.asdict(params) if dataclasses.is_dataclass(params) else repr(params),
            "need_names": {str(int(k)): getattr(k, "name", str(k)) for k in params.needs}}
    targets[2].write_text(json.dumps(snap, indent=1, default=str) + "\n")
    print(f"wrote {len(rows)} + {len(rows2)} rows and the parameter snapshot to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
