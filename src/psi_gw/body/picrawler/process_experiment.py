"""Execute direct/process equivalence and real child kill/restart experiments."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from psi_gw.body import Action

from .controller_process import ProcessController
from .robot_benchmark import BenchmarkCase, Episode, run_episode, run_process_episode
from .validation_io import canonical, digest, source_info, write_json


def run_process_experiment(output: str | Path) -> dict[str, Any]:
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("process experiment output must be new or empty")
    comparisons, restarts = [], []
    for policy in ("reactive", "memory"):
        for sensors in ("nominal", "noisy", "delayed"):
            case = BenchmarkCase(0, "open", policy, sensors, "progress", max_ticks=80)
            direct = run_episode(case)
            separate = run_process_episode(case)
            record = {"case": case.__dict__, "identical": direct == separate,
                "direct_sha256": digest(direct), "process_sha256": digest(separate), "ticks": direct["ticks"]}
            comparisons.append(record)
            write_json(output / "equivalence" / (case.id + ".json"), record)
        with ProcessController(policy, 20_000) as controller:
            episode = Episode(BenchmarkCase(0, "open", policy, "nominal", "progress", max_ticks=50), controller=controller)
            for _ in range(12):
                episode.step()
            before_pose = episode.body.frame(include_camera=False)["pose"]
            old_session, old_pid = controller.session, controller.process.pid
            controller.process.kill()
            controller.process.wait(timeout=2)
            episode.step()
            after_pose = episode.body.frame(include_camera=False)["pose"]
            stopped = controller.failed and episode.previous_action == Action("stop") and before_pose == after_pose
            latched = controller.choose(episode.body.observe()) == Action("stop")
            failure = controller.failure_reason
            restarted = controller.restart()
            new_session = controller.session
            episode.done = False  # Explicit host-authorized new controller session, not auto-recovery.
            for _ in range(10):
                episode.step()
            record = {"policy": policy, "stopped_on_child_exit": stopped, "fenced_until_restart": latched,
                "failure": failure, "restarted": restarted, "new_session": old_session != new_session,
                "new_process": controller.process.pid != old_pid, "post_restart_ticks": 10,
                "limits": "Restart starts a fresh policy; no unobserved command history or odometry is reconstructed."}
            restarts.append(record)
            write_json(output / (policy + "-kill-restart.json"), record)
    passed = all(r["identical"] for r in comparisons) and all(
        r["stopped_on_child_exit"] and r["fenced_until_restart"] and r["restarted"] and r["new_session"] and r["new_process"] for r in restarts)
    summary = {"type": "psi_gw.picrawler.process_experiment", "version": 1, "runtime": source_info(),
        "passed": passed, "comparisons": comparisons, "kill_restart": restarts,
        "limits": "Local pipes and host-side simulation stop; no network service or independent hardware motor watchdog."}
    write_json(output / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run_process_experiment(args.output)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(canonical({"passed": result["passed"], "equivalence_cases": len(result["comparisons"]), "kill_restarts": len(result["kill_restart"])}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
