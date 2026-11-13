"""Compare two JSON result files numerically (reproduction check).

Prints every leaf that differs by more than ``--tol`` or exists in only one file and exits
with status 1 if there is any; keys listed with ``--ignore`` (dotted prefixes) are skipped.

Usage: python scripts/compare_json.py expected.json actual.json [--tol 1e-12] [--ignore a.b,c]
"""

from __future__ import annotations

import argparse
import json
import math
import sys


def leaves(x, prefix=""):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from leaves(v, f"{prefix}.{k}" if prefix else str(k))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, x


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("expected")
    ap.add_argument("actual")
    ap.add_argument("--tol", type=float, default=1e-12)
    ap.add_argument("--ignore", default="")
    args = ap.parse_args()
    ignore = [p for p in args.ignore.split(",") if p]
    a = dict(leaves(json.load(open(args.expected))))
    b = dict(leaves(json.load(open(args.actual))))
    bad = []
    for key in sorted(set(a) | set(b)):
        if any(key == p or key.startswith(p + ".") or key.startswith(p + "[") for p in ignore):
            continue
        if key not in a or key not in b:
            bad.append(f"only in {'actual' if key in b else 'expected'}: {key}")
            continue
        x, y = a[key], b[key]
        if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
            if not (x == y or (math.isnan(x) and math.isnan(y)) or abs(x - y) <= args.tol * max(1, abs(x))):
                bad.append(f"{key}: {x} != {y}")
        elif x != y:
            bad.append(f"{key}: {x!r} != {y!r}")
    for line in bad[:50]:
        print(line)
    print(f"{args.actual}: {len(a)} values compared, {len(bad)} differences")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
