"""Closed-loop reference-controller benchmark; ground truth stays in evaluation."""

from __future__ import annotations

import argparse
import copy
from dataclasses import asdict, dataclass
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

from psi_gw.body import Action, Observation

from .body import PiCrawlerSimBody, SimConfig
from .energy import EnergyConfig
from .perception import perceive
from .replay import write_replay
from .robot_controllers import POLICIES, ReferenceController, sensor_view
from .robot_courses import (Course, FAMILIES, SENSOR_PROFILES, TASKS, cell_for,
                            generate_course, reachable_cells, shutter_world)
from .sensors import CameraConfig, RangeConfig
from .validation_io import canonical, digest, read_json, source_info, write_json


@dataclass(frozen=True)
class BenchmarkCase:
    seed: int
    family: str
    policy: str
    sensors: str
    task: str
    split: str = "development"
    max_ticks: int = 900

    def __post_init__(self) -> None:
        allowed = range(4) if self.split == "development" else range(1000, 1004)
        if self.split not in ("development", "validation") or type(self.seed) is not int or self.seed not in allowed:
            raise ValueError("seed does not belong to the preregistered split")
        if self.family not in FAMILIES or self.policy not in POLICIES or self.sensors not in SENSOR_PROFILES or self.task not in TASKS:
            raise ValueError("unknown benchmark condition")
        if type(self.max_ticks) is not int or self.max_ticks < 5:
            raise ValueError("max_ticks must be an integer >= 5")

    @property
    def id(self) -> str:
        return f"{self.split}-s{self.seed}-{self.family}-{self.sensors}-{self.task}-{self.policy}-t{self.max_ticks}"

    @property
    def budget(self) -> int:
        return 30 if self.task == "energy_stop" else self.max_ticks


class DeliveryBuffer:
    """Bounded acquisition/delivery history with explicit original timestamps."""

    def __init__(self, profile: str, dt_s: float = .05) -> None:
        if profile not in SENSOR_PROFILES:
            raise ValueError("unknown sensor profile")
        self.profile, self.dt_s = profile, dt_s
        self.history: list[dict[str, Any]] = []

    def deliver(self, observation: Observation) -> Observation:
        current = sensor_view(observation)
        for sample in current.sensors.values():
            sample["captured_at_s"] = observation.tick * self.dt_s
        if observation.tick % 5:
            current.sensors.pop("camera", None)  # Acquire/store images at 4 Hz, not five copies of each image.
        self.history.append(asdict(current))
        self.history = self.history[-16:]
        delivered = {}
        delay = 4 if self.profile == "delayed" else 0
        cutoff = observation.tick - delay
        # Occasional extra delay is a repeated older acquisition, not a fresh sample.
        if self.profile == "delayed" and observation.tick % 17 == 0:
            cutoff -= 3
        for channel in ("ultrasonic", "camera"):
            eligible = [h for h in self.history if h["tick"] <= cutoff and
                (channel != "camera" or h["tick"] % 5 == 0) and channel in h["sensors"]]
            if eligible:
                delivered[channel] = copy.deepcopy(eligible[-1]["sensors"][channel])
        return Observation(observation.tick, delivered, copy.deepcopy(current.internal))

    def snapshot(self) -> dict[str, Any]:
        return {"profile": self.profile, "dt_s": self.dt_s, "history": copy.deepcopy(self.history)}

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> DeliveryBuffer:
        obj = cls(payload["profile"], payload["dt_s"])
        obj.history = copy.deepcopy(payload["history"])
        if len(obj.history) > 16:
            raise ValueError("delivery history exceeds bound")
        return obj


class Episode:
    """Evaluator/controller separation, complete logical checkpoint and metrics."""

    def __init__(self, case: BenchmarkCase, *, controller: Any = None) -> None:
        self.case, self.course = case, generate_course(case.seed, case.family)
        config = SimConfig(initial_x_m=self.course.initial_x_m, initial_y_m=self.course.initial_y_m,
            initial_yaw_rad=self.course.initial_yaw_rad, peripherals_enabled=True,
            camera=CameraConfig(width=24, height=16),
            range_sensor=RangeConfig(noise_half_width_m=.003 if case.sensors == "noisy" else 0,
                                    dropout_probability=.08 if case.sensors == "noisy" else 0),
            energy=EnergyConfig(battery_initial_soc=.07 if case.task == "energy_stop" else .8))
        self.body = PiCrawlerSimBody(self.course.world, config, seed=case.seed + 10_000)
        self.controller = controller if controller is not None else ReferenceController(case.policy, case.seed + 20_000)
        self.delivery = DeliveryBuffer(case.sensors)
        self.reachable = reachable_cells(self.course.world, (self.course.initial_x_m, self.course.initial_y_m))
        self.visited = {cell_for(self.course.initial_x_m, self.course.initial_y_m)} & self.reachable
        self.previous_action = Action("stop")
        self.done, self.reached = False, False
        self.metrics = {key: 0 for key in ("collision_ticks", "workspace_limited_ticks", "unknown_range_ticks",
            "held_range_ticks", "posture_resets", "action_changes", "unpowered_ticks", "late_stop_ticks")}
        self.metrics["unseen_body_contact_ticks"] = 0
        self.metrics["maximum_heading_error_rad"] = 0.0
        self.first_hazard_tick: int | None = None
        self.first_stop_tick: int | None = None
        self.stationary_after_hazard = 0
        self.world_event = "pending" if self.course.shutter_tick is not None else "none"
        self.trace_sha256 = "0" * 64
        self.last_row: dict[str, Any] = {}
        self.trace: list[dict[str, Any]] = []
        self.frames: list[dict[str, Any]] = []
        self._record_frame()

    def _record_frame(self) -> None:
        frame = self.body.frame()
        frame["world"] = self.body.world.snapshot()
        frame["controller"] = copy.deepcopy(self.controller.last_decision)
        self.frames.append(frame)

    def step(self) -> None:
        if self.done:
            raise ValueError("episode is already finished")
        now_tick = self.body.tick
        old_pose = self.last_row["pose"] if self.last_row else self.frames[0]["pose"]
        if self.world_event == "pending" and now_tick >= self.course.shutter_tick:
            candidate = shutter_world(self.course)
            pose = old_pose
            if candidate.is_free(pose["x_m"], pose["y_m"], self.body.config.collision_radius_m):
                self.body.world = candidate
                self.world_event = "inserted"
            else:
                self.world_event = "skipped_occupied"
        delivered = self.delivery.deliver(self.body.observe())
        before = digest(asdict(delivered))
        action = self.controller.choose(delivered, self.previous_action)
        if digest(asdict(delivered)) != before:
            raise AssertionError("controller mutated its input")
        if self.first_hazard_tick is None and (delivered.internal["hunger"] >= .85 or delivered.internal["damage"] >= .95):
            self.first_hazard_tick = now_tick
        self.body.act(action)
        frame = self.body.frame(include_camera=False)
        pose, telemetry = frame["pose"], frame["telemetry"]
        if self.body.tick != now_tick + 1 or not self.body.world.is_free(pose["x_m"], pose["y_m"], self.body.config.collision_radius_m):
            raise AssertionError("invalid clock or penetrating body position")
        self.visited |= {cell_for(pose["x_m"], pose["y_m"])} & self.reachable
        features = self.controller.last_decision.get("features", {})
        self.metrics["collision_ticks"] += int(frame["collision"])
        self.metrics["workspace_limited_ticks"] += int(frame["workspace_limited"])
        self.metrics["unknown_range_ticks"] += int(features.get("range_source") == "unknown")
        self.metrics["held_range_ticks"] += int(features.get("range_source") == "held_estimate")
        self.metrics["posture_resets"] += int(action.name == "stand")
        self.metrics["action_changes"] += int(asdict(action) != asdict(self.previous_action))
        self.metrics["unpowered_ticks"] += int(not telemetry["powered"])
        if frame["collision"] and features.get("distance_m") is not None and features["distance_m"] >= self.controller.config.near_m:
            self.metrics["unseen_body_contact_ticks"] += 1
        estimate = self.controller.last_decision.get("heading_estimate_rad", 0.0)
        error = abs(math.remainder(pose["yaw_rad"] - self.course.initial_yaw_rad - estimate, 2 * math.pi))
        self.metrics["maximum_heading_error_rad"] = max(self.metrics["maximum_heading_error_rad"], error)
        if self.first_hazard_tick is not None:
            stationary = action.name == "stop" and pose == old_pose
            if stationary and self.first_stop_tick is None:
                self.first_stop_tick = now_tick
            self.stationary_after_hazard = self.stationary_after_hazard + 1 if stationary else 0
            if now_tick - self.first_hazard_tick >= 2 and not stationary:
                self.metrics["late_stop_ticks"] += 1
        self.reached = (pose["x_m"] >= .35 if self.case.task == "progress" else
            len(self.visited) / len(self.reachable) >= .08 if self.case.task == "explore" else
            self.stationary_after_hazard >= 10)
        self.done = self.reached or self.body.tick >= self.case.budget or bool(getattr(self.controller, "failed", False))
        self.last_row = {"tick": self.body.tick, "input_sha256": before, "action": asdict(action),
            "pose": copy.deepcopy(pose), "energy_consumed_j": telemetry["energy_consumed_j"],
            "decision": copy.deepcopy(self.controller.last_decision), "world_event": self.world_event}
        self.trace_sha256 = hashlib.sha256((self.trace_sha256 + canonical(self.last_row)).encode()).hexdigest()
        self.trace.append(copy.deepcopy(self.last_row))
        self.previous_action = copy.deepcopy(action)
        if self.body.tick % 20 == 0 or self.done:
            self._record_frame()

    def snapshot(self) -> dict[str, Any]:
        return {"type": "psi_gw.picrawler.robot_episode", "version": 1, "case": asdict(self.case),
            "course": self.course.snapshot(), "body": self.body.snapshot(), "controller": self.controller.snapshot(),
            "delivery": self.delivery.snapshot(), "reachable": sorted(self.reachable), "visited": sorted(self.visited),
            "previous_action": asdict(self.previous_action), "done": self.done, "reached": self.reached,
            "metrics": self.metrics.copy(), "first_hazard_tick": self.first_hazard_tick,
            "first_stop_tick": self.first_stop_tick, "stationary_after_hazard": self.stationary_after_hazard,
            "world_event": self.world_event, "trace_sha256": self.trace_sha256, "last_row": copy.deepcopy(self.last_row),
            "controller_health": {"failed": bool(getattr(self.controller, "failed", False)),
                                  "reason": getattr(self.controller, "failure_reason", None)}}

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> Episode:
        if payload.get("type") != "psi_gw.picrawler.robot_episode" or payload.get("version") != 1:
            raise ValueError("unsupported robot episode")
        obj = cls.__new__(cls)
        obj.case = BenchmarkCase(**payload["case"])
        obj.course = Course.restore(payload["course"])
        obj.body = PiCrawlerSimBody.restore(payload["body"])
        obj.controller = ReferenceController.restore(payload["controller"])
        health = payload.get("controller_health", {"failed": False, "reason": None})
        obj.controller.failed, obj.controller.failure_reason = health["failed"], health["reason"]
        obj.delivery = DeliveryBuffer.restore(payload["delivery"])
        for name in ("reachable", "visited"):
            setattr(obj, name, {tuple(cell) for cell in payload[name]})
        obj.previous_action = Action(**payload["previous_action"])
        for name in ("done", "reached", "metrics", "first_hazard_tick", "first_stop_tick", "stationary_after_hazard",
                     "world_event", "trace_sha256", "last_row"):
            setattr(obj, name, copy.deepcopy(payload[name]))
        obj.frames, obj.trace = [], []
        return obj

    def result(self) -> dict[str, Any]:
        frame = self.body.frame(include_camera=False)
        guard = (self.metrics["workspace_limited_ticks"] == 0 and self.metrics["late_stop_ticks"] == 0 and
                 self.metrics["unpowered_ticks"] == 0)
        contact_ok = self.metrics["collision_ticks"] / max(1, self.body.tick) <= .01
        failed_controller = bool(getattr(self.controller, "failed", False))
        success = self.reached and guard and contact_ok and not failed_controller
        reason = ("controller_failure" if failed_controller else "workspace_limit" if self.metrics["workspace_limited_ticks"] else
                  "late_energy_stop" if self.metrics["late_stop_ticks"] else "power_loss" if self.metrics["unpowered_ticks"] else
                  "contact_budget" if not contact_ok else "reached" if self.reached else "time_budget")
        return {"type": "psi_gw.picrawler.robot_result", "version": 1, "case": asdict(self.case),
            "success": success, "reason": reason, "goal_reached": self.reached, "ticks": self.body.tick,
            "coverage_fraction": len(self.visited) / len(self.reachable), "visited_cells": len(self.visited),
            "reachable_cells": len(self.reachable), "distance_m": frame["distance_travelled_m"],
            "energy_j": frame["telemetry"]["energy_consumed_j"], "metrics": self.metrics.copy(),
            "world_event": self.world_event, "trace_sha256": self.trace_sha256,
            "energy_reaction_ticks": None if self.first_stop_tick is None else self.first_stop_tick - self.first_hazard_tick,
            "final_state_sha256": digest(self.snapshot()), "preregistered_budget": self.case.max_ticks == 900}


def run_episode(case: BenchmarkCase, output: Path | None = None, *, checkpoint: bool = True,
                controller: Any = None) -> dict[str, Any]:
    if output is not None:
        output = Path(output)
        if output.exists() and any(output.iterdir()):
            raise ValueError("episode output must be new or empty")
    episode = Episode(case, controller=controller)
    continued, resumed = 0, None
    checkpoint_payload = None
    while not episode.done:
        episode.step()
        if resumed is not None:
            resumed.step()
            if digest(resumed.snapshot()) != digest(episode.snapshot()):
                raise AssertionError(f"episode checkpoint differs at tick {episode.body.tick}")
            continued += 1
        checkpoint_tick = 5 if case.task == "energy_stop" else min(episode.case.budget // 2, 80)
        if checkpoint and resumed is None and episode.body.tick >= checkpoint_tick and not episode.done:
            checkpoint_payload = json.loads(canonical(episode.snapshot()))
            resumed = Episode.restore(checkpoint_payload)
    report = episode.result()
    report["verified_continuation_ticks"] = continued
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".episode-", dir=output.parent) as temporary:
            target = Path(temporary)
            write_json(target / "result.json", report)
            write_json(target / "course.json", episode.course.snapshot())
            write_json(target / "trace.json", episode.trace)
            if checkpoint_payload:
                write_json(target / "checkpoint.json", checkpoint_payload)
            write_replay(target / "replay.html", episode.frames, {"title": f"PiCrawler · {case.policy} · {case.family}",
                "world": episode.course.world.snapshot(), "seed": case.seed, "dt_s": episode.body.config.dt_s,
                "collision_radius_m": .18, "source_commit": source_info()["revision"],
                "assumptions": "Technischer Referenzcontroller, keine PSI-Kognition. Kinematik und angenommene Energieparameter.",
                "initial_conditions": "3D/Kamera zeigen gespeicherte Körperdaten. Verzögerte Controller-Eingänge sind im Trace über Hash/Features dokumentiert."})
            os.rename(target, output)  # Publish all artifacts together, never a partial example.
    return report


def run_process_episode(case: BenchmarkCase, output: Path | None = None, *, checkpoint: bool = True) -> dict[str, Any]:
    from .controller_process import ProcessController

    with ProcessController(case.policy, case.seed + 20_000) as controller:
        return run_episode(case, output, checkpoint=checkpoint, controller=controller)


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    paired: dict[str, dict[str, dict[str, Any]]] = {}
    for result in results:
        c = result["case"]
        group = "/".join(c[k] for k in ("split", "task", "sensors", "policy"))
        grouped.setdefault(group, []).append(result)
        pair = "/".join(str(c[k]) for k in ("split", "seed", "family", "sensors", "task"))
        paired.setdefault(pair, {})[c["policy"]] = result
    comparison = []
    for pair, policies in sorted(paired.items()):
        if set(policies) == set(POLICIES):
            a, b = policies["reactive"], policies["memory"]
            comparison.append({"pair": pair, "success_difference_memory_minus_reactive": int(b["success"]) - int(a["success"]),
                "both_successful": a["success"] and b["success"],
                "energy_difference_j": b["energy_j"] - a["energy_j"] if a["success"] and b["success"] else None})
    return {"episodes": len(results), "successful": sum(r["success"] for r in results),
        "body_ticks": sum(r["ticks"] for r in results),
        "verified_continuation_ticks": sum(r["verified_continuation_ticks"] for r in results),
        "groups": {k: {"episodes": len(v), "successes": sum(r["success"] for r in v),
            "mean_coverage": sum(r["coverage_fraction"] for r in v) / len(v),
            "mean_energy_j": sum(r["energy_j"] for r in v) / len(v)} for k, v in sorted(grouped.items())},
        "paired_descriptive": comparison, "limits": "Descriptive paired comparison; no superiority or PSI claim."}


def run_suite(output: Path, cases: list[BenchmarkCase], *, resume: bool = False,
              record_examples: bool = False, verify_checkpoints: bool = False,
              execution: str = "direct", progress: Callable[[str, dict[str, Any]], None] | None = None) -> dict[str, Any]:
    if not cases or len({c.id for c in cases}) != len(cases):
        raise ValueError("suite needs distinct cases")
    if execution not in ("direct", "process"):
        raise ValueError("unknown execution mode")
    output = Path(output)
    manifest = {"type": "psi_gw.picrawler.robot_suite", "version": 1, "runtime": source_info(),
                "cases": [asdict(c) for c in cases], "record_examples": record_examples,
                "verify_checkpoints": verify_checkpoints, "execution": execution}
    if output.exists() and any(output.iterdir()):
        if not resume or read_json(output / "manifest.json") != manifest:
            raise ValueError("resume requires an identical manifest/runtime")
    else:
        write_json(output / "manifest.json", manifest)
    results = []
    for case in cases:
        path = output / "cases" / (case.id + ".json")
        if path.exists():
            cached = read_json(path)
            checksum = cached.pop("result_sha256", None)
            if cached.get("case") != asdict(case) or digest(cached) != checksum:
                raise ValueError("corrupt benchmark report")
            results.append(cached)
            if progress is not None:
                progress(case.id, cached)
            continue
        example = output / "examples" / case.id if record_examples and case.seed == min(c.seed for c in cases) and case.sensors == "nominal" and case.task == "progress" else None
        # Always cover both policies, all sensor/task profiles and the dynamic event
        # on the first seed; optionally verify every episode's continuation.
        verify = verify_checkpoints or (case.seed == min(c.seed for c in cases) and case.family == "gate")
        runner = run_episode if execution == "direct" else run_process_episode
        report = runner(case, example, checkpoint=verify)
        write_json(path, {**report, "result_sha256": digest(report)})
        results.append(report)
        if progress is not None:
            progress(case.id, report)
    summary = {"type": "psi_gw.picrawler.robot_summary", "version": 1,
               "manifest_sha256": digest(manifest), **summarize(results)}
    write_json(output / "summary.json", summary, replace=(output / "summary.json").exists())
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--split", choices=("development", "validation"), default="development")
    parser.add_argument("--seeds", nargs="+", type=int)
    parser.add_argument("--families", nargs="+", choices=FAMILIES, default=list(FAMILIES))
    parser.add_argument("--policies", nargs="+", choices=POLICIES, default=list(POLICIES))
    parser.add_argument("--sensors", nargs="+", choices=SENSOR_PROFILES, default=list(SENSOR_PROFILES))
    parser.add_argument("--tasks", nargs="+", choices=TASKS, default=list(TASKS))
    parser.add_argument("--max-ticks", type=int, default=900)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--record-examples", action="store_true")
    parser.add_argument("--verify-checkpoints", action="store_true")
    parser.add_argument("--execution", choices=("direct", "process"), default="direct")
    parser.add_argument("--progress", action="store_true")
    args = parser.parse_args(argv)
    seeds = args.seeds if args.seeds is not None else ([0, 1] if args.split == "development" else [1000, 1001, 1002, 1003])
    def progress(case_id: str, result: dict[str, Any]) -> None:
        import sys
        print(f"{case_id}: {result['reason']} ({result['ticks']} ticks)", file=sys.stderr, flush=True)
    try:
        cases = [BenchmarkCase(seed, family, policy, sensors, task, args.split, args.max_ticks) for
                 seed, family, policy, sensors, task in itertools.product(seeds, args.families, args.policies, args.sensors, args.tasks)]
        summary = run_suite(args.output, cases, resume=args.resume, record_examples=args.record_examples,
                            verify_checkpoints=args.verify_checkpoints, execution=args.execution,
                            progress=progress if args.progress else None)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(canonical({k: v for k, v in summary.items() if k not in ("groups", "paired_descriptive")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
