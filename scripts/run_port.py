"""Run one island life with the Python port and write its protocols and trace file.

Writes, like the original into its protocol folder (``IslandLife.protocol_files``):

    actu<seed>(1).Prt    activity protocol (wall clock times as <time>)
    seed<seed>.Prt       ach file: performance counters per cycle
    IntTimes(1).Txt      time of the regulation steps per cycle
    Activities(1).Txt    one line per action
    eAch(1).Prt, Inpro(1).Prt, Consum(1).Prt   end of life summaries

and converts them into a run file ``<out>/inseliii__seed-<seed>.jsonl.gz``
(ADR 0006) with the same converter as the original's runs.

Usage: python scripts/run_port.py --seed 901 --max-life 5000000 --out runs/port901
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from psi_gw.life import IslandLife  # noqa: E402
from psi_gw.memory.lists import NilDereference  # noqa: E402
from psi_gw.tracing.delphi_protocols import convert_run_dir  # noqa: E402
from psi_gw.tracing.runfile import write_run  # noqa: E402
from psi_gw.variant import Variant  # noqa: E402


def run_and_write(seed: int, max_life: int, out: Path, variant: Variant | None = None
                  ) -> tuple[IslandLife, Path, str | None]:
    """One life; raw protocols to ``out/raw``, run file to ``out``.

    If the life breaks off where the original would crash (``NilDereference``),
    the protocols up to that point are written and the error is returned.
    """
    life = IslandLife(seed=seed, max_life=max_life, variant=variant)
    crash = None
    try:
        life.run_life(max_life)
    except NilDereference as exc:
        crash = f"cycle {life.state.cycle}: {exc}"
    raw = out / "raw"
    life.write_protocols(raw, seed)
    run = convert_run_dir(raw, f"seed{seed}.Prt", world="InselIII", psi_data="InselIII",
                          params={"max_life": max_life, "runner": "python",
                                  "variant": life.state.variant.active()})
    run.header.source = "python"
    run.header.program_version = "psi_gw reference mode"
    trace = out / f"inseliii__seed-{seed}.jsonl.gz"
    write_run(trace, run)
    return life, trace, crash


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--max-life", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--variant", default="", help="switched off artefacts (psi_gw.variant), comma-separated or 'all'")
    args = ap.parse_args()
    t0 = time.monotonic()
    life, trace, crash = run_and_write(args.seed, args.max_life, args.out, Variant.from_names(args.variant))
    st = life.state
    print(f"{trace}: {st.cycle} cycles, age {st.clock.age}, {time.monotonic() - t0:.0f} s"
          + (f", BROKE OFF {crash}" if crash else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
