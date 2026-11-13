"""Reproducible obstacle-course demo and offline recording utilities."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterator

from psi_gw.body import Action

from .body import PiCrawlerSimBody, SimConfig
from .energy import EnergyConfig
from .perception import perceive
from .replay import write_replay
from .sensors import RangeConfig
from .world import demo_world


def demo_actions(dt_s: float = 0.05) -> Iterator[tuple[str, Action]]:
    """A script deliberately reaches the block, then walks around its left side.

    This is a test controller, not PSI cognition or a learned obstacle policy.
    Posture resets between segments are explicit kinematic operations.
    """
    if not math.isfinite(dt_s) or dt_s <= 0:
        raise ValueError("dt_s must be finite and positive")
    turns = math.ceil((math.pi / 2 / 0.30) / dt_s)
    turn_rate = (math.pi / 2) / (turns * dt_s)
    segments = (
        ("approach_block", round(25.0 / dt_s), {"forward_mps": 0.03}),
        ("turn_left", turns, {"yaw_rps": turn_rate}),
        ("pass_left", round(15.0 / dt_s), {"forward_mps": 0.03}),
        ("turn_forward", turns, {"yaw_rps": -turn_rate}),
        ("pass_block", round(20.0 / dt_s), {"forward_mps": 0.03}),
    )
    for label, count, params in segments:
        yield "stand", Action("stand")
        for _ in range(count):
            yield label, Action("drive", params)
    for _ in range(round(2.0 / dt_s)):
        yield "stop", Action("stop")


def run_demo(output: Path, *, seed: int = 42, camera: bool = True,
             noise_m: float = 0.0, dropout: float = 0.0, sample_every: int = 5,
             source_commit: str = "working tree", scenario: str = "obstacles") -> dict[str, Any]:
    """Write a replay, trace, midpoint checkpoint and measured run summary.

    The output directory must be empty to avoid destroying earlier results.
    Every tick is in trace.jsonl; the HTML samples recorded ticks for size.
    """
    if type(sample_every) is not int or sample_every < 1:
        raise ValueError("sample_every must be a positive integer")
    if scenario not in ("obstacles", "resources", "peripherals"):
        raise ValueError("scenario must be obstacles, resources or peripherals")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"output directory must be empty: {output}")
    config = SimConfig(camera_enabled=camera, peripherals_enabled=scenario == "peripherals",
                       range_sensor=RangeConfig(noise_half_width_m=noise_m,
                                                dropout_probability=dropout),
                       energy=EnergyConfig(battery_initial_soc=0.15, initial_cpu_temperature_c=78.0,
                                           cpu_load=1.0) if scenario in ("resources", "peripherals") else EnergyConfig())
    sim = PiCrawlerSimBody(demo_world(), config, seed=seed)
    output.mkdir(parents=True, exist_ok=True)
    actions = list(demo_actions(config.dt_s))
    if scenario == "peripherals":
        # Add commands *between* motion ticks so a beep or spoken warning has
        # real model duration and does not silently replace a walking command.
        events = {
            4: [("led_on", Action("led", {"on": True}))],
            150: [("hello", Action("speak", {"text": "Ich erkunde die Umgebung.", "duration_s": 2.8}))],
            460: [("obstacle_warning", Action("sound", {"id": "obstacle_warning", "duration_s": 1.0}))],
            670: [("tone", Action("tone", {"hz": 440.0, "duration_s": 1.4}))],
            910: [("energy_warning", Action("speak", {"text": "Meine Energiereserve ist niedrig.", "duration_s": 3.0}))],
            1210: [("led_off", Action("led", {"on": False}))],
        }
        scripted = []
        for n, step in enumerate(actions):
            scripted.extend(events.get(n, []))
            scripted.append(step)
        actions = scripted
    midpoint = len(actions) // 2
    resumed: PiCrawlerSimBody | None = None
    def recorded_frame(*, include_camera: bool = True) -> dict[str, Any]:
        frame = sim.frame(include_camera=include_camera)
        frame["perception"] = perceive(sim.observe().sensors, now_s=sim.time_s,
                                      sample_time_s=sim.time_s).to_dict()
        return frame

    replay = [recorded_frame()]
    initial_telemetry = replay[0]["telemetry"].copy()
    maximum_temperature = initial_telemetry["cpu_temperature_c"]
    minimum_voltage = initial_telemetry["battery_voltage_v"]
    throttled_ticks, undervoltage_ticks = 0, 0
    collision_ticks, limited_ticks, verified_ticks = 0, 0, 0
    with (output / "trace.jsonl").open("w", encoding="utf-8") as trace:
        initial = recorded_frame(include_camera=False)
        initial["scenario_segment"] = "initial"
        trace.write(json.dumps(initial, allow_nan=False, separators=(",", ":")) + "\n")
        for number, (label, action) in enumerate(actions, start=1):
            sim.act(action)
            if resumed is not None:
                resumed.act(action)
                if sim.snapshot() != resumed.snapshot():
                    raise AssertionError(f"checkpoint continuation differs at tick {sim.tick}")
                verified_ticks += 1
            if number == midpoint:
                checkpoint = json.dumps(sim.snapshot(), allow_nan=False, indent=2)
                (output / "checkpoint.json").write_text(checkpoint + "\n", encoding="utf-8")
                resumed = PiCrawlerSimBody.restore(json.loads(checkpoint))
            frame = recorded_frame(include_camera=False)
            frame["scenario_segment"] = label
            collision_ticks += int(frame["collision"])
            limited_ticks += int(frame["workspace_limited"])
            maximum_temperature = max(maximum_temperature, frame["telemetry"]["cpu_temperature_c"])
            minimum_voltage = min(minimum_voltage, frame["telemetry"]["battery_voltage_v"])
            throttled_ticks += int(frame["telemetry"]["thermal_throttled"])
            undervoltage_ticks += int(frame["telemetry"]["undervoltage"])
            trace.write(json.dumps(frame, allow_nan=False, separators=(",", ":")) + "\n")
            if number % sample_every == 0 or number == len(actions):
                sampled = sim.frame()
                sampled["perception"] = frame["perception"]
                sampled["scenario_segment"] = label
                replay.append(sampled)
    summary = {
        "model": "kinematic locomotion with assumed electrical/thermal dynamics",
        "scenario": scenario,
        "seed": seed, "source_commit": source_commit, "ticks": sim.tick, "simulation_time_s": sim.time_s,
        "distance_travelled_m": sim.frame()["distance_travelled_m"],
        "final_pose": sim.frame()["pose"], "collision_ticks": collision_ticks,
        "workspace_limited_ticks": limited_ticks, "checkpoint_tick": midpoint,
        "verified_continuation_ticks": verified_ticks, "replay_frames": len(replay),
        "range_noise_half_width_m": noise_m, "range_dropout_probability": dropout,
        "initial_telemetry": initial_telemetry, "final_telemetry": sim.frame()["telemetry"],
        "final_needs": sim.observe().internal,
        "maximum_cpu_temperature_c": maximum_temperature, "minimum_battery_voltage_v": minimum_voltage,
        "thermal_throttled_ticks": throttled_ticks, "undervoltage_ticks": undervoltage_ticks,
        "config": asdict(config),
        "peripheral_events": sim.peripherals.events if sim.peripherals is not None else [],
    }
    (output / "summary.json").write_text(json.dumps(summary, allow_nan=False, indent=2) + "\n", encoding="utf-8")
    write_replay(output / "replay.html", replay, {
        "title": "PiCrawler · " + ("Sprechen, Licht und Energie" if scenario == "peripherals" else
                                 "Wärme und Energie" if scenario == "resources" else "Hindernisparcours"),
        "scenario": scenario, "seed": seed, "dt_s": config.dt_s,
        "world": sim.world.snapshot(), "model_kind": "kinematic",
        "collision_radius_m": config.collision_radius_m,
        "source_commit": source_commit,
        "energy_config": asdict(config.energy),
        "assumptions": "Modellannahmen: 2S-Akku, Ladungsbilanz, Innenwiderstand, CPU-RC-Modell; keine Hardwaremessung.",
        "initial_conditions": ("Start: 15 % Akku, 78 °C CPU, 100 % CPU-Last. Zeit entspricht Simulationssekunden."
                               if scenario in ("resources", "peripherals") else "Start: 80 % Akku, 40 °C CPU, 50 % CPU-Last."),
    })
    if limited_ticks:
        raise AssertionError(f"demo hit a kinematic workspace limit on {limited_ticks} ticks")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the isolated PiCrawler kinematics/sensor demo.")
    parser.add_argument("--output", type=Path, default=Path("picrawler-run"), help="New or empty output directory")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-camera", action="store_true", help="Omit synthetic RGB images")
    parser.add_argument("--noise-m", type=float, default=0.0, help="Uniform range-noise half-width in metres")
    parser.add_argument("--dropout", type=float, default=0.0, help="Range-reading dropout probability")
    parser.add_argument("--sample-every", type=int, default=5, help="Recorded ticks per HTML frame")
    parser.add_argument("--source-commit", default="working tree", help="Revision label for the recording")
    parser.add_argument("--scenario", choices=("obstacles", "resources", "peripherals"), default="obstacles")
    args = parser.parse_args()
    try:
        result = run_demo(args.output, seed=args.seed, camera=not args.no_camera,
                          noise_m=args.noise_m, dropout=args.dropout, sample_every=args.sample_every,
                          source_commit=args.source_commit, scenario=args.scenario)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps({key: value for key, value in result.items() if key != "config"}, indent=2))
    print(f"Replay: {args.output / 'replay.html'}")


if __name__ == "__main__":
    main()
