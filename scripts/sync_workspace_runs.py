"""Keep the results of the workspace runs in the repository, so another session can go on.

``runs/`` is not in the repository. This script copies, for every finished life,
``metrics.json`` and the gzipped workspace log to
``traces/port-runs/2026-11-11-workspace/ws-<cond>/seed<seed>/`` (each file is
written once and never changed afterwards), and restores them into ``runs/``.
After a restore ``scripts/workspace_runs.sh`` skips the restored seeds, and the
analysis and the paper figures work as on the original machine.

Usage:
    python scripts/sync_workspace_runs.py save
    python scripts/sync_workspace_runs.py restore
"""

from __future__ import annotations

import gzip
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "traces" / "port-runs" / "2026-11-11-workspace"
RUNS = ROOT / "runs"
LOG = "Workspace(1).jsonl"


def save() -> int:
    n = 0
    for metrics in sorted([*RUNS.glob("ws-*/seed*/metrics.json"), *RUNS.glob("sens-*/seed*/metrics.json")]):
        seed_dir = metrics.parent
        dest = STORE / seed_dir.parent.name / seed_dir.name
        if (dest / "metrics.json").exists():
            continue
        dest.mkdir(parents=True, exist_ok=True)
        log = seed_dir / "raw" / LOG
        if log.exists():
            with log.open("rb") as src, gzip.GzipFile(dest / (LOG + ".gz"), "wb", mtime=0) as gz:
                shutil.copyfileobj(src, gz)
        shutil.copy(metrics, dest / "metrics.json")  # last: marks the seed as complete
        n += 1
    print(f"saved {n} new lives to {STORE.relative_to(ROOT)}")
    return 0


def restore() -> int:
    n = 0
    for metrics in sorted([*STORE.glob("ws-*/seed*/metrics.json"), *STORE.glob("sens-*/seed*/metrics.json")]):
        src = metrics.parent
        dest = RUNS / src.parent.name / src.name
        if (dest / "metrics.json").exists():
            continue
        (dest / "raw").mkdir(parents=True, exist_ok=True)
        gz = src / (LOG + ".gz")
        if gz.exists():
            with gzip.open(gz, "rb") as f, (dest / "raw" / LOG).open("wb") as out:
                shutil.copyfileobj(f, out)
        shutil.copy(metrics, dest / "metrics.json")
        n += 1
    print(f"restored {n} lives into {RUNS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("save", "restore"):
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(save() if sys.argv[1] == "save" else restore())
