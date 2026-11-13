"""Record every random draw of the Delphi original under Wine (Issue #14, ADR 0009).

Starts Psi.exe under ``winedbg --gdb``, attaches gdb with
scripts/gdb_random_trace.py (breakpoints on Delphi's two random routines),
starts the simulation via the menu and stops after a given number of draws.
The debugger slows Psi down roughly fivefold; it does not change its behaviour
(checked against reference runs, docs/zufallsmitschnitt.md).

Output in ``--out``:
    random_draws.tsv.gz   one line per draw, with cycle and call site added
    raw/                  protocols written by Psi up to the stop

Usage:
    python scripts/trace_random.py --seed 16 --max-draws 20000 --out traces/...
"""

from __future__ import annotations

import argparse
import csv
import gzip
import os
import shutil
import subprocess
import sys
import tempfile
import time
from bisect import bisect_right
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from psi_gw.random_source import DelphiRandom  # noqa: E402
from psi_gw.tracing.delphi_random_sites import SITES, site_name  # noqa: E402

START_MENU_XY = (58, 40)


def _xdotool(env: dict, *args: str) -> str:
    return subprocess.run(["xdotool", *args], env=env, capture_output=True, text=True).stdout


def _event_offsets(events: Path) -> tuple[list[int], list[int | None]]:
    """Byte offset after each line of the event protocol and the cycle of that line."""
    ends, cycles = [], []
    pos = 0
    header_done = False
    for raw in events.read_bytes().split(b"\n"):
        pos += len(raw) + 1
        line = raw.decode("cp1252").strip()
        if not header_done:
            header_done = ";Aktion;" in line
            ends.append(pos)
            cycles.append(None)
            continue
        parts = line.split(";")
        cycle = int(parts[4]) if len(parts) > 4 and parts[4].strip().isdigit() else None
        ends.append(pos)
        cycles.append(cycle)
    return ends, cycles


def write_draws(tsv: Path, events: Path, seed: int, target: Path) -> dict:
    """Check a raw gdb trace for completeness and write the annotated draw file.

    Columns: nr, kind, n, randseed, site, events_before (event lines written
    before the draw, exact because the original closes the protocol after each
    event), prev_event_cycle and next_event_cycle (Takt of the surrounding
    events; the draw belongs to a cycle in this range, see
    docs/zufallsmitschnitt.md), ret0..ret2.
    """
    rows = list(csv.DictReader(tsv.open(), delimiter="\t"))
    rng = DelphiRandom(seed)
    for r in rows:
        if int(r["randseed"]) != rng._state:
            raise RuntimeError(f"draw {r['nr']}: RandSeed does not follow DelphiRandom({seed})")
        rng.randint(int(r["n"])) if r["kind"] == "I" else rng.random()

    ends, cycles = _event_offsets(events)
    first_event = next(i for i, c in enumerate(cycles) if c is not None)
    unknown = 0
    with gzip.open(target, "wt", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["nr", "kind", "n", "randseed", "site", "events_before",
                    "prev_event_cycle", "next_event_cycle", "ret0", "ret1", "ret2"]
                   + (["names"] if rows and "names" in rows[0] else []))
        for r in rows:
            idx = bisect_right(ends, int(r["events_bytes"])) - 1
            before = max(0, idx - first_event + 1)
            prev = next((c for c in reversed(cycles[: idx + 1]) if c is not None), "")
            nxt = next((c for c in cycles[idx + 1:] if c is not None), "")
            ret0 = int(r["ret0"], 16)
            unknown += ret0 not in SITES
            w.writerow([r["nr"], r["kind"], r["n"], r["randseed"], site_name(ret0), before,
                        prev, nxt, r["ret0"], r["ret1"], r["ret2"]]
                       + ([r["names"]] if "names" in r else []))
    return {"draws": len(rows), "unknown_sites": unknown}


def record(seed: int, max_draws: int, out: Path, world: str, psi_data: str,
           display: int, port: int, wineprefix: Path, timeout: float) -> dict:
    run_id = f"seed{seed}"
    workdir = Path(tempfile.mkdtemp(prefix="psi-trace-"))
    psi_dir = workdir / "psi"
    subprocess.run([str(ROOT / "scripts" / "assemble_original.sh"), str(psi_dir)], check=True, capture_output=True)
    (psi_dir / "Execute" / f"{run_id}.Dat").write_bytes(f"5000000 {seed}\r\n".encode())
    (psi_dir / "Protokoll" / run_id).mkdir(parents=True, exist_ok=True)
    events = psi_dir / "Protokoll" / run_id / run_id / "Protokoll(1).Dat"
    tsv = workdir / "draws.tsv"

    env = dict(os.environ, DISPLAY=f":{display}", WINEPREFIX=str(wineprefix), WINEDEBUG="-all",
               PSI_TRACE_OUT=str(tsv), PSI_TRACE_EVENTS=str(events), PSI_TRACE_LIMIT=str(max_draws),
               PSI_TRACE_DUMP=os.environ.get("PSI_TRACE_DUMP", ""),
               PSI_TRACE_WATCH=os.environ.get("PSI_TRACE_WATCH", ""),
               PSI_TRACE_NAMES=os.environ.get("PSI_TRACE_NAMES", ""))
    procs = []
    try:
        procs.append(subprocess.Popen(["Xvfb", f":{display}", "-screen", "0", "1280x1024x24"],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(1.5)
        procs.append(subprocess.Popen(
            ["winedbg", "--gdb", "--port", str(port), "--no-start", "./Psi.exe", f"Daten={world}",
             f"PsiDaten={psi_data}", f"Protokoll={run_id}", "Geschwindigkeit=0.0", f"Param={run_id}", "Stop"],
            cwd=psi_dir, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        time.sleep(6)
        gdb = subprocess.Popen(
            ["gdb", "-q", "-batch", "-ex", "set architecture i386", "-ex", "set pagination off",
             "-ex", f"target remote localhost:{port}", "-x", str(ROOT / "scripts" / "gdb_random_trace.py"),
             "-ex", "continue", "-ex", "kill"],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        procs.append(gdb)
        deadline = time.monotonic() + 120
        while not _xdotool(env, "search", "--name", "Psi 4.9.1.200").strip():
            if time.monotonic() > deadline:
                raise RuntimeError("Psi main window did not appear under the debugger")
            time.sleep(1)
        time.sleep(5)
        _xdotool(env, "mousemove", str(START_MENU_XY[0]), str(START_MENU_XY[1]), "click", "1")
        try:
            gdb.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"draw limit not reached within {timeout} s")
    finally:
        for p in reversed(procs):
            if p.poll() is None:
                p.kill()
        subprocess.run(["wineserver", "-k"], env=env, capture_output=True)

    out.mkdir(parents=True, exist_ok=True)
    stats = write_draws(tsv, events, seed, out / "random_draws.tsv.gz")
    raw = out / "raw"
    if raw.exists():
        shutil.rmtree(raw)
    shutil.copytree(psi_dir / "Protokoll" / run_id, raw)
    if os.environ.get("PSI_TRACE_KEEP_TSV"):
        shutil.copy(tsv, os.environ["PSI_TRACE_KEEP_TSV"])
    shutil.rmtree(workdir, ignore_errors=True)
    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-draws", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--world", default="InselIII")
    parser.add_argument("--psi-data", default="InselIII")
    parser.add_argument("--display", type=int, default=96)
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--wineprefix", type=Path, default=Path.home() / ".wine-psi")
    parser.add_argument("--timeout", type=float, default=3600)
    args = parser.parse_args()
    started = time.monotonic()
    result = record(args.seed, args.max_draws, args.out, args.world, args.psi_data,
                    args.display, args.port, args.wineprefix, args.timeout)
    print(f"{args.out}: {result['draws']} draws, {result['unknown_sites']} at unknown sites "
          f"({time.monotonic() - started:.0f} s)")


if __name__ == "__main__":
    main()
