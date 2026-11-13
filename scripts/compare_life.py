"""Run PSI against recorded protocols; report exact coverage and failures.

Exit 0: complete equality; 1: difference; 2: input/execution/report error;
3: matching partial comparison. See docs/comparison-tools.md.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import sys
from pathlib import Path

from comparison_report import compare_sequences, emit, finish, input_error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
TRACE_DIR = ROOT / "traces" / "original-runs" / "2026-11-10-zufallsmitschnitt"


def original_draws(path):
    """Read and validate the fields actually compared, including every row."""
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        if not {"site", "randseed"}.issubset(reader.fieldnames or []):
            raise ValueError("random trace requires site and randseed columns")
        rows = []
        for lineno, row in enumerate(reader, 2):
            if not row.get("site") or row.get("randseed") is None or None in row:
                raise ValueError(f"invalid random trace row {lineno}")
            rows.append([row["site"], int(row["randseed"])])
    if not rows:
        raise ValueError("empty random trace")
    return rows


def original_protocol(path):
    from psi_gw.agent import CYCLE_RULE
    raw = path.read_bytes().decode("cp1252")
    lines = raw.replace("\r\n", "\n").replace("\r", "").split("\n")
    if not lines[0].startswith("Protokoll für "):
        raise ValueError(f"{path}: missing activity protocol header")
    out = []
    for line in lines[1:]:
        if line.startswith("---------------") and line.endswith("-----"):
            line = CYCLE_RULE
        elif line.startswith("Ende der Simulation: "):
            line = "Ende der Simulation: <time>"
        out.append(line)
    while out and out[-1] == "":
        out.pop()
    if not out:
        raise ValueError(f"{path}: empty activity protocol")
    return out


def text_lines(path):
    """Normalize CRLF and a terminal newline, preserving interior blank lines."""
    rows = path.read_bytes().decode("cp1252").splitlines()
    if not rows:
        raise ValueError(f"{path}: empty protocol")
    return rows


def make_life(seed):
    from psi_gw.life import IslandLife
    from psi_gw.random_source import DelphiRandom, RecordingSource
    rng = RecordingSource(DelphiRandom(seed))
    return IslandLife(seed=seed, rng=rng), rng


def run_comparison(args, factory=make_life):
    report = {"tool": "compare_life", "seed": args.seed, "scope": args.scope,
              "cycles_requested": args.cycles, "cycles_run": 0, "life_ended": False,
              "checks": {}}
    checks = report["checks"]
    # Read required inputs before running the simulation. A named missing trace is never skipped.
    paths = {"protocol": args.protocol, "activities": args.protocol.parent / "Activities(1).Txt"}
    originals = {}
    for name, path in paths.items():
        try:
            originals[name] = original_protocol(path) if name == "protocol" else text_lines(path)
        except (OSError, UnicodeError, ValueError) as exc:
            checks[name] = dict(input_error(exc), original_path=str(path))
    if args.draws is None:
        checks["draws"] = {"status": "not_requested", "reason": "no random trace selected"}
    else:
        try:
            originals["draws"] = original_draws(args.draws)
        except (OSError, UnicodeError, ValueError, EOFError) as exc:
            checks["draws"] = dict(input_error(exc), original_path=str(args.draws))
    if any(item["status"] in {"missing", "error"} for item in checks.values()):
        return finish(report, incomplete=True)
    try:
        life, rng = factory(args.seed)
        checked_lines = checked_draws = 0
        for c in range(args.cycles):
            if life.check_max_life(args.max_life):
                break
            life.cycle()
            report["cycles_run"] = c + 1
            # Compare only newly available evidence for early divergence. Lengths are
            # classified below: archived random traces may end inside a cycle.
            port = life.state.prn.lines
            n = min(len(port), len(originals["protocol"]))
            if port[checked_lines:n] != originals["protocol"][checked_lines:n]:
                break
            checked_lines = n
            if "draws" in originals:
                n = min(len(rng.log), len(originals["draws"]))
                draws = [[d.site, d.state_before] for d in rng.log[checked_draws:n]]
                if draws != originals["draws"][checked_draws:n]:
                    break
                checked_draws = n
        else:
            # Check the boundary after the last requested cycle too.
            life.check_max_life(args.max_life)
        report["life_ended"] = life.ended
        prefix = args.scope == "prefix" and not life.ended
        for name, port in (("protocol", life.state.prn.lines),
                           ("activities", life.state.activity_log)):
            # A shortened original may also be an explicitly requested prefix.
            checks[name] = compare_sequences(originals[name], port, prefix=prefix, context=args.context)
            checks[name]["original_path"] = str(paths[name])
        if "draws" in originals:
            checks["draws"] = compare_sequences(
                originals["draws"], [[d.site, d.state_before] for d in rng.log],
                prefix=args.scope == "prefix", context=args.context)
            checks["draws"]["original_path"] = str(args.draws)
        if life.ended:
            for name, port in life.summary_files(args.seed).items():
                path = args.protocol.parent / f"{name}(1).Prt"
                try:
                    checks[name] = compare_sequences(text_lines(path), port, context=args.context)
                except (OSError, UnicodeError, ValueError) as exc:
                    checks[name] = input_error(exc)
                checks[name]["original_path"] = str(path)
        else:
            checks["summaries"] = {"status": "not_applicable", "reason": "life has not ended"}
    except Exception as exc:
        # A failed cycle or initialization is an execution failure, not equality.
        checks["execution"] = input_error(exc)
    return finish(report, incomplete=not report["life_ended"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=16)
    ap.add_argument("--cycles", type=int, default=29)
    ap.add_argument("--context", type=int, default=6)
    ap.add_argument("--draws", type=Path, help="random trace (seed 16 defaults to the archived trace)")
    ap.add_argument("--max-life", type=int, default=0)
    ap.add_argument("--protocol", type=Path)
    ap.add_argument("--scope", choices=("full", "prefix"), default="prefix",
                    help="full rejects unequal lengths; prefix reports partial coverage with exit 3")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    if args.cycles <= 0 or args.context < 0 or args.max_life < 0:
        ap.error("cycles must be positive; context and max-life must be nonnegative")
    if args.protocol is None:
        args.protocol = TRACE_DIR / "raw" / f"seed{args.seed}" / f"actu{args.seed}(1).Prt"
    if args.draws is None and args.seed == 16:
        args.draws = TRACE_DIR / "random_draws.tsv.gz"
    return emit(run_comparison(args), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
