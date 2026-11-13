"""Reproducible cross-product experiments against the existing Body/Mock-Bridge."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import itertools
import json
import math
from pathlib import Path
from typing import Any

from psi_gw.body import Action

from .body import PiCrawlerSimBody, SimConfig
from .bridge import BridgeEndpoint, InMemoryTransport, Reply, Request, StaleObservation
from .energy import EnergyConfig
from .sensors import CameraConfig, RangeConfig
from .validation_io import canonical, digest, read_json, source_info, write_json
from .world import demo_world

ENERGY = ("normal", "hot", "low", "empty", "power_limit", "tiny_capacity")
SENSORS = ("ideal", "noisy", "blackout")
LINKS = ("normal", "lossy", "delayed", "reconnect")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _diagnostic(value: Any) -> Any:
    """Keep corrupt/nonfinite state printable in a failure artifact."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"invalid_number": repr(value)}
    if isinstance(value, dict):
        return {key: _diagnostic(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_diagnostic(item) for item in value]
    return value


@dataclass(frozen=True)
class Case:
    seed: int
    energy: str
    sensors: str
    link: str
    ticks: int = 80

    def __post_init__(self) -> None:
        if type(self.seed) is not int or self.seed < 0 or type(self.ticks) is not int or self.ticks < 24:
            raise ValueError("nonnegative integer seed and at least 24 ticks are required")
        if self.energy not in ENERGY or self.sensors not in SENSORS or self.link not in LINKS:
            raise ValueError("unknown stress profile")

    @property
    def id(self) -> str:
        return f"s{self.seed}-{self.energy}-{self.sensors}-{self.link}-t{self.ticks}"

    def config(self) -> SimConfig:
        energy = EnergyConfig()
        if self.energy == "hot":
            energy = replace(energy, battery_initial_soc=.15, initial_cpu_temperature_c=84, cpu_load=1)
        elif self.energy == "low":
            energy = replace(energy, battery_initial_soc=.02)
        elif self.energy == "empty":
            energy = replace(energy, battery_initial_soc=0)
        elif self.energy == "power_limit":
            energy = replace(energy, battery_internal_resistance_ohm=3)
        elif self.energy == "tiny_capacity":
            energy = replace(energy, battery_capacity_ah=.00005)
        sensor = RangeConfig(noise_half_width_m=.005 if self.sensors == "noisy" else 0,
            dropout_probability={"ideal": 0, "noisy": .15, "blackout": 1}[self.sensors])
        return SimConfig(initial_x_m=.085, peripherals_enabled=True, energy=energy,
            range_sensor=sensor, camera_enabled=self.sensors != "blackout", camera=CameraConfig(width=12, height=8))


class _CheckedBody:
    def __init__(self, case: Case) -> None:
        self.case = case
        self.body = PiCrawlerSimBody(demo_world(), case.config(), seed=case.seed)
        self.initial = self.body.snapshot()
        self.oracle: PiCrawlerSimBody | None = None
        self.trace: list[dict[str, Any]] = []
        self.continuation_ticks = 0
        self.metrics = {k: 0 for k in ("collision_ticks", "workspace_limited_ticks", "unpowered_ticks",
            "dropout_ticks", "throttled_ticks", "undervoltage_ticks", "nonstop_actions", "readonly_checks")}

    @property
    def tick(self) -> int:
        return self.body.tick

    def observe(self):
        return self.body.observe()

    def button(self, button: str, down: bool) -> None:
        self.trace.append({"kind": "button", "tick": self.tick, "button": button, "down": down})
        self.body.inject_button(button, down)
        if self.oracle:
            self.oracle.inject_button(button, down)

    def environment(self, load: float, ambient: float) -> None:
        self.trace.append({"kind": "environment", "tick": self.tick, "cpu_load": load, "ambient_temperature_c": ambient})
        self.body.set_environment(cpu_load=load, ambient_temperature_c=ambient)
        if self.oracle:
            self.oracle.set_environment(cpu_load=load, ambient_temperature_c=ambient)

    def act(self, action: Action) -> None:
        previous = self.body.frame(include_camera=False)
        self.trace.append({"kind": "action", "tick": self.tick, "name": action.name, "params": action.params.copy()})
        self.body.act(action)
        require(self.tick == previous["tick"] + 1, "one tick per action")
        frame, observation = self.body.frame(include_camera=False), self.body.observe()
        telemetry, old = frame["telemetry"], previous["telemetry"]
        peripheral = observation.sensors["peripherals"]
        require(observation.tick == peripheral["tick"] == self.tick, "synchronized clocks")
        require(0 <= telemetry["state_of_charge"] <= 1, "bounded charge")
        config = self.body.config.energy
        charge_balance = config.battery_initial_soc - telemetry["charge_used_ah"] / config.battery_capacity_ah
        require(abs(telemetry["state_of_charge"] - charge_balance) < 1e-10, "charge conservation")
        for key in ("energy_consumed_j", "charge_used_ah", "battery_loss_j"):
            require(telemetry[key] >= old[key], "nondecreasing " + key)
        energy_increment = telemetry["energy_consumed_j"] - old["energy_consumed_j"]
        require(math.isclose(energy_increment, telemetry["power_w"] * self.body.config.dt_s, abs_tol=1e-10), "energy conservation")
        if action.name == "stop" or not telemetry["powered"]:
            require(frame["pose"] == previous["pose"], "no motion on stop or cutoff")
        if not telemetry["powered"]:
            require(not peripheral["speaker"]["playing"] and not peripheral["user_led"], "peripherals dark on cutoff")
        require(all(value is None or 0 <= value <= 1 for value in frame["needs"].values()), "bounded need inputs")
        require(self.body.world.is_free(frame["pose"]["x_m"], frame["pose"]["y_m"], self.body.config.collision_radius_m), "collision-free body position")
        for name, condition in (("collision_ticks", frame["collision"]), ("workspace_limited_ticks", frame["workspace_limited"]),
            ("unpowered_ticks", not telemetry["powered"]), ("throttled_ticks", telemetry["thermal_throttled"]),
            ("undervoltage_ticks", telemetry["undervoltage"]), ("dropout_ticks", observation.sensors["ultrasonic"]["status"] == "dropout"),
            ("nonstop_actions", action.name != "stop")):
            self.metrics[name] += int(condition)
        if self.case.sensors == "blackout":
            require("camera" not in observation.sensors and observation.sensors["ultrasonic"]["distance_m"] is None, "sensor blackout")
        if self.oracle:
            self.oracle.act(action)
            require(self.oracle.snapshot() == self.body.snapshot(), "checkpoint continuation differs")
            self.continuation_ticks += 1
        elif self.tick >= self.case.ticks // 2:
            # Exercise checkpoint while an external button event is still pending.
            self.button("reset", True)
            self.oracle = PiCrawlerSimBody.restore(json.loads(canonical(self.body.snapshot())))
            require(self.oracle.snapshot() == self.body.snapshot(), "checkpoint round trip differs")
        snapshot = self.body.snapshot()
        state_hash = digest(snapshot)  # Fails for nonfinite/unserializable state.
        self.trace[-1]["state_sha256"] = state_hash
        if self.tick % 5 == 0:
            self.body.observe()
            self.body.frame()
            require(self.body.snapshot() == snapshot, "observation mutates state or RNG")
            self.metrics["readonly_checks"] += 1


def run_case(case: Case) -> dict[str, Any]:
    checked = _CheckedBody(case)
    result: dict[str, Any] = {"type": "psi_gw.picrawler.stress_case", "version": 1,
                             "case": asdict(case), "config": asdict(case.config())}
    endpoint = BridgeEndpoint(checked, watchdog_ticks=3)
    link = InMemoryTransport(endpoint)
    completed: dict[tuple[str, int], str] = {}
    stale, expired = 0, 0

    def collect() -> None:
        nonlocal stale, expired
        for wire in link.receive():
            reply = Reply.from_json(wire)
            if reply.status == "completed":
                # Session generation is included because reconnect restarts sequences.
                key = (reply.session, reply.sequence)
                require(key not in completed or completed[key] == wire, "retry ACK changed")
                completed[key] = wire
            expired += int(reply.status == "expired")
            if reply.observation.tick < link.tick:
                try:
                    reply.fresh_observation(now_tick=link.tick, max_age_ticks=0)
                except StaleObservation:
                    stale += 1
                else:
                    raise AssertionError("stale observation accepted")

    try:
        checked.act(Action("led", {"on": True}))
        checked.act(Action("speak", {"text": "Stress scenario", "duration_s": .5}))
        for _ in range(12):
            checked.act(Action("drive", {"forward_mps": .03}))
        checked.button("user", True)
        checked.environment(1, 35)
        session = link.connect("stress")
        nonstop_before = checked.metrics["nonstop_actions"]
        sequence, wire = 0, None
        scripted = (Action("drive", {"forward_mps": .02}), Action("led", {"on": False}),
                    Action("tone", {"hz": 440, "duration_s": .15}),
                    Action("sound", {"id": "warning", "duration_s": .2}))
        for number in range(case.ticks):
            if case.link == "reconnect" and number == case.ticks // 2:
                old_wire = wire
                link.disconnect()
                session = link.connect("stress")
                sequence, wire = 0, None
                if old_wire:
                    require(Reply.from_json(endpoint.receive(old_wire)).reason == "wrong_session", "old session was not fenced")
            if number % 8 == 0:
                sequence += 1
                wire = Request(session, f"command-{sequence}", sequence, link.tick, link.tick + 6,
                               scripted[(sequence - 1) % len(scripted)]).to_json()
                link.send(wire, request_delay_ticks=8 if case.link == "delayed" else 0,
                    reply_delay_ticks=2 if case.link == "delayed" else 0,
                    drop_request=case.link == "lossy" and sequence % 2 == 0,
                    drop_reply=case.link == "lossy" and sequence % 2 == 1)
            if number % 8 == 2 and wire and case.link == "lossy":
                link.send(wire)  # Exactly the same wire/sequence, not a new command.
            link.step()
            collect()
        for _ in range(12):
            link.step()
            collect()
        # All scripted requests are non-stop actions, all successful ACKs recovered.
        require(checked.metrics["nonstop_actions"] - nonstop_before == len(completed), "commands executed more than once or ACK missing")
        require(endpoint.watchdog_tripped and endpoint.pending_count == 0 and link.queued_counts == (0, 0), "link did not drain and stop")
        require(checked.continuation_ticks > 0, "checkpoint was not exercised")
        if case.link == "lossy":
            require(link.request_drops > 0 and link.reply_drops > 0, "loss injection not exercised")
        if case.link == "delayed":
            require(expired > 0 and stale > 0, "late requests/stale replies not exercised")
        require(checked.metrics["workspace_limited_ticks"] == 0, "unexpected workspace limit")
        result["status"] = "passed"
    except Exception as error:
        result.update(status="failed", error={"type": type(error).__name__, "message": str(error)},
                      initial_snapshot=checked.initial, last_snapshot=_diagnostic(checked.body.snapshot()), trace=checked.trace)
    result.update(body_ticks=checked.tick, continuation_ticks=checked.continuation_ticks,
                  metrics=checked.metrics, trace_sha256=digest(checked.trace),
                  request_drops=link.request_drops, reply_drops=link.reply_drops,
                  completed_commands=len(completed), expired_replies=expired, stale_replies_rejected=stale,
                  final_state_sha256=digest(_diagnostic(checked.body.snapshot())))
    result["result_sha256"] = digest(result)
    return result


def run_matrix(output: str | Path, cases: list[Case], *, resume: bool = False) -> dict[str, Any]:
    if not cases or len({case.id for case in cases}) != len(cases):
        raise ValueError("matrix needs distinct cases")
    output = Path(output)
    manifest = {"type": "psi_gw.picrawler.stress_matrix", "version": 1,
                "runtime": source_info(), "cases": [asdict(case) for case in cases]}
    manifest_path = output / "manifest.json"
    if output.exists() and any(output.iterdir()):
        if not resume or not manifest_path.exists() or read_json(manifest_path) != manifest:
            raise ValueError("nonempty output requires --resume and an identical manifest/runtime")
    else:
        write_json(manifest_path, manifest)
    results = []
    for case in cases:
        path = output / "cases" / (case.id + ".json")
        cached = read_json(path) if path.exists() else None
        if cached is not None:
            checksum = cached.pop("result_sha256", None)
            if checksum != digest(cached) or cached.get("case") != asdict(case):
                raise ValueError("corrupt or mismatched case report: " + case.id)
            cached["result_sha256"] = checksum
        if cached is not None and cached.get("status") == "passed":
            result = cached
        else:
            result = run_case(case)
            write_json(path, result, replace=cached is not None)
        results.append(result)
    summary = {"type": "psi_gw.picrawler.stress_summary", "version": 1,
        "manifest_sha256": digest(manifest), "cases": len(results),
        "passed": sum(r["status"] == "passed" for r in results),
        "failed": [case.id for case, r in zip(cases, results) if r["status"] != "passed"],
        "body_ticks": sum(r["body_ticks"] for r in results),
        "continuation_ticks": sum(r["continuation_ticks"] for r in results),
        "case_results": {case.id: r["result_sha256"] for case, r in zip(cases, results)}}
    write_json(output / "summary.json", summary, replace=(output / "summary.json").exists())
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 42])
    parser.add_argument("--energy", nargs="+", choices=ENERGY, default=list(ENERGY))
    parser.add_argument("--sensors", nargs="+", choices=SENSORS, default=list(SENSORS))
    parser.add_argument("--links", nargs="+", choices=LINKS, default=list(LINKS))
    parser.add_argument("--ticks", type=int, default=80)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        cases = [Case(seed, energy, sensor, link, args.ticks) for seed, energy, sensor, link in
                 itertools.product(args.seeds, args.energy, args.sensors, args.links)]
        report = run_matrix(args.output, cases, resume=args.resume)
    except (ValueError, OSError, TypeError) as error:
        parser.error(str(error))
    print(canonical({key: value for key, value in report.items() if key != "case_results"}))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
