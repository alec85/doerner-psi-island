"""How often the current motive changes in a life (paper 1, section on the original's behaviour).

Reads the ``AktMot:`` lines of ``actu*.Prt`` (one per motive report in the protocol) for every
life of a run directory that did not break off, and writes a JSON summary.

Usage:
    python scripts/motive_dominance.py runs/baseline runs/variant-all --seeds 1001-1100 --out analysis/referenzlaeufe/motivdominanz.json
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path


def summarize(run_dir: Path, first: int, last: int) -> dict:
    lives = never = entries = nukleo = 0
    switches: list[int] = []
    others: collections.Counter[str] = collections.Counter()
    for seed_dir in sorted(run_dir.glob("seed*")):
        if not first <= int(seed_dir.name[4:]) <= last:
            continue
        metrics = json.loads((seed_dir / "metrics.json").read_text())
        if metrics.get("crash"):
            continue
        protocol = next((seed_dir / "raw").glob("actu*.Prt"))
        motives = [line.split()[1].decode("cp1252") for line in protocol.open("rb")
                   if line.strip().startswith(b"AktMot:")]
        lives += 1
        n = sum(1 for a, b in zip(motives, motives[1:]) if a != b)
        switches.append(n)
        never += n == 0
        entries += len(motives)
        nukleo += sum(m == "Nukleo" for m in motives)
        others.update(m for m in motives if m != "Nukleo")
    return {"lives": lives, "lives_without_switch": never, "motive_entries": entries,
            "share_nukleo": nukleo / entries if entries else None, "max_switches": max(switches, default=0),
            "switch_histogram": dict(sorted(collections.Counter(switches).items())), "other_motives": dict(others)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seeds", default="1001-1100", help="first-last")
    args = ap.parse_args()
    first, last = map(int, args.seeds.split("-"))
    result = {"seeds": args.seeds, **{str(r): summarize(r, first, last) for r in args.runs}}
    args.out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(result, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
