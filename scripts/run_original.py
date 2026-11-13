"""Run the Delphi original headless under Wine and convert its protocols.

One call runs one life of Psi with a given seed and maximum life (MaxLife),
waits until the program terminates itself, copies all protocol files to the
output directory and writes a run file in the trace format (ADR 0006).

The simulation is started through the menu instead of the ``Start`` command
line switch, because ``Start`` triggers a bug in the original (see
docs/delphi-build.md): ``SimulRun`` is set before the 500 ms thread timer is
created, so the thread never exists, the time series stay empty and the end of
life ends in an access violation instead of a clean shutdown.

Modal error dialogs of the original (title "Fehler") are confirmed with OK, as an
operator would do under Windows; each one is recorded in the run header under
``extra.dialogs_dismissed`` with cycle, time and a screenshot in ``raw/dialogs``.

Requirements: scripts/setup_wine.sh has been run. Runs must be sequential,
because the original's world server always listens on TCP port 2000.

Usage:
    python scripts/run_original.py --seed 16 --max-life 20000 --out runs/seed16
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from psi_gw.tracing.delphi_protocols import convert_run_dir  # noqa: E402
from psi_gw.tracing.runfile import write_run  # noqa: E402

START_MENU_XY = (58, 40)  # position of the "Start" menu item with the default window layout


def _wait_for(predicate, timeout: float, interval: float = 0.5) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def _xdotool(env: dict, *args: str) -> str:
    return subprocess.run(["xdotool", *args], env=env, capture_output=True, text=True).stdout


def _last_cycle(events: Path) -> int | None:
    """Cycle (Takt) of the last line of the event protocol, or None."""
    try:
        with open(events, "rb") as fh:
            fh.seek(max(0, events.stat().st_size - 2000))
            last = fh.read().decode("cp1252", "replace").strip().splitlines()[-1]
        return int(last.split(";")[4])
    except (OSError, IndexError, ValueError):
        return None


def run_once(seed: int, max_life: int, out: Path, world: str, psi_data: str,
             timeout: float, display: int, wineprefix: Path, keep_workdir: bool) -> Path:
    run_id = f"seed{seed}"
    workdir = Path(tempfile.mkdtemp(prefix="psi-run-"))
    subprocess.run([str(ROOT / "scripts" / "assemble_original.sh"), str(workdir / "psi")],
                   check=True, capture_output=True)
    psi_dir = workdir / "psi"
    (psi_dir / "Execute" / f"{run_id}.Dat").write_bytes(f"{max_life} {seed}\r\n".encode())
    (psi_dir / "Protokoll" / run_id).mkdir(parents=True, exist_ok=True)

    env = dict(os.environ, DISPLAY=f":{display}", WINEPREFIX=str(wineprefix), WINEDEBUG="-all")
    xvfb = subprocess.Popen(["Xvfb", f":{display}", "-screen", "0", "1280x1024x24"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    psi = None
    dialogs: list[dict] = []
    timed_out = False
    try:
        time.sleep(1.5)
        if not wineprefix.exists():
            subprocess.run(["wineboot", "-i"], env=env, check=True, capture_output=True)
        args = ["wine", "Psi.exe", f"Daten={world}", f"PsiDaten={psi_data}",
                f"Protokoll={run_id}", "Geschwindigkeit=0.0", f"Param={run_id}", "Stop"]
        psi = subprocess.Popen(args, cwd=psi_dir, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        title = "Psi 4.9.1.200"
        if not _wait_for(lambda: _xdotool(env, "search", "--name", title).strip(), 60):
            raise RuntimeError("Psi main window did not appear")
        time.sleep(3)  # let all windows finish their layout

        events = psi_dir / "Protokoll" / run_id / run_id / "Protokoll(1).Dat"

        def started() -> bool:
            return events.exists() and events.stat().st_size > 2000

        for _ in range(3):
            _xdotool(env, "mousemove", str(START_MENU_XY[0]), str(START_MENU_XY[1]), "click", "1")
            if _wait_for(started, 15):
                break
        else:
            raise RuntimeError("simulation did not start after clicking the Start menu")

        # The original shows modal error dialogs (MessageDlg, window title "Fehler"),
        # e.g. the GravityList race in UPsiServer.pas, and waits for OK. A human
        # operator under Windows would click OK; we do the same and record it.
        deadline = time.monotonic() + timeout
        dialog_dir = workdir / "dialogs"
        while psi.poll() is None:
            if time.monotonic() > deadline:
                # e.g. after an access violation the cycle never starts again (StartSimul stays
                # false); keep the protocols written so far and mark the run
                timed_out = True
                print(f"warning: Psi did not terminate within {timeout} s; protocols kept", flush=True)
                break
            for window in _xdotool(env, "search", "--name", "^Fehler$").split():
                cycle = _last_cycle(events)
                dialog_dir.mkdir(exist_ok=True)
                shot = dialog_dir / f"cycle-{cycle}-{len(dialogs) + 1}.png"
                subprocess.run(["import", "-window", "root", str(shot)], env=env, capture_output=True)
                _xdotool(env, "key", "--window", window, "Return")
                dialogs.append({"cycle": cycle, "wall_clock": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "screenshot": f"raw/dialogs/{shot.name}"})
            time.sleep(2)
    finally:
        if psi and psi.poll() is None:
            psi.kill()
        subprocess.run(["wineserver", "-k"], env=env, capture_output=True)
        xvfb.terminate()

    out.mkdir(parents=True, exist_ok=True)
    raw = out / "raw"
    if raw.exists():
        shutil.rmtree(raw)
    shutil.copytree(psi_dir / "Protokoll" / run_id, raw)
    if (workdir / "dialogs").exists():
        shutil.copytree(workdir / "dialogs", raw / "dialogs")

    run = convert_run_dir(raw / run_id, f"{run_id}.Prt", world=world, psi_data=psi_data,
                          params={"max_life": max_life, "start": "menu", "runner": "wine"})
    run.header.source_files = [str(Path(p).relative_to(out)) for p in run.header.source_files]
    run.header.extra["dialogs_dismissed"] = dialogs
    run.header.extra["timed_out"] = timed_out
    target = out / f"{world.lower()}__seed-{seed}.jsonl.gz"
    write_run(target, run)
    if not keep_workdir:
        shutil.rmtree(workdir, ignore_errors=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-life", type=int, required=True, help="MaxLife in age units")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--world", default="InselIII")
    parser.add_argument("--psi-data", default="InselIII")
    parser.add_argument("--timeout", type=float, default=1800)
    parser.add_argument("--display", type=int, default=98)
    parser.add_argument("--wineprefix", type=Path, default=Path.home() / ".wine-psi")
    parser.add_argument("--keep-workdir", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    target = run_once(args.seed, args.max_life, args.out, args.world, args.psi_data,
                      args.timeout, args.display, args.wineprefix, args.keep_workdir)
    print(f"{target} ({time.monotonic() - started:.0f} s)")


if __name__ == "__main__":
    main()
