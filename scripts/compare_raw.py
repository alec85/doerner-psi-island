"""Compare the raw protocols of the original and of the port for one seed (ADR 0008, analysis plan amendment 1).

Wall clock times are masked. Reports per file whether it is identical and, if
not, the number of differing lines and the first ones.

Usage: python scripts/compare_raw.py --seed 1001 --original <dir with actu1001(1).Prt> --port <dir>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from comparison_report import compare_sequences, emit, finish, input_error


def lines(path: Path) -> list[str]:
    out = []
    for i, line in enumerate(path.read_bytes().decode("cp1252").replace("\r\n", "\n").replace("\r", "").split("\n")):
        if line.startswith("---------------") and line.endswith("-----"):
            line = "<time rule>"
        elif line.startswith(("Ende der Simulation: ", "Protokoll für ", "PsiAlpha2 Probelauf: ")):
            line = line.split(":")[0] + ": <time>"
        out.append(line)
    while out and out[-1] == "":
        out.pop()
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--original", type=Path, required=True)
    ap.add_argument("--port", type=Path, required=True)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)
    names = [f"actu{args.seed}(1).Prt", f"seed{args.seed}.Prt", "IntTimes(1).Txt", "Activities(1).Txt",
             "eAch(1).Prt", "Inpro(1).Prt", "Consum(1).Prt"]
    report = {"tool": "compare_raw", "seed": args.seed, "scope": "full", "checks": {}}
    for name in names:
        a, b = args.original / name, args.port / name
        try:
            la, lb = lines(a), lines(b)
            if not la or not lb:
                raise ValueError(f"{name}: empty protocol")
            item = compare_sequences(la, lb)
        except (OSError, UnicodeError, ValueError) as exc:
            item = input_error(exc)
        item.update(original_path=str(a), port_path=str(b))
        report["checks"][name] = item
    return emit(finish(report), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
