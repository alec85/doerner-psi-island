"""Deterministic kinematic PiCrawler testbed implementing the draft Body API.

Locomotion is prescribed; stance feet stay fixed in world coordinates while a
four-beat crawl lifts one foot at a time. Forces, stability, slip and servo
dynamics are deliberately outside this model. See docs/picrawler/ADR-prototype.md.
"""

from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from typing import Any

from psi_gw.body import Action, Observation
from psi_gw.random_source import NumpySource, RandomSource, restore_source

from .energy import (EnergyConfig, EnergyEnvironment, EnergyState, advance_energy,
                     energy_readings, initial_energy, need_signals)
from .kinematics import Geometry, LEG_ORDER, body_to_leg, inverse_leg, leg_points, leg_to_body
from .sensors import CameraConfig, RangeConfig, render_camera, sample_range
from .peripherals import PeripheralConfig, PeripheralSim
from .world import World, finite

_SNAPSHOT_TYPE = "psi_gw.picrawler.kinematic"
_PHASE_OFFSETS = (0.0, 0.5, 0.25, 0.75)
_DUTY_FACTOR = 0.75


@dataclass(frozen=True, slots=True)
class SimConfig:
    dt_s: float = 0.05
    gait_period_s: float = 0.8
    foot_lift_m: float = 0.016
    collision_radius_m: float = 0.18
    maximum_speed_mps: float = 0.03
    maximum_yaw_rps: float = 0.30
    initial_x_m: float = -0.60
    initial_y_m: float = 0.0
    initial_yaw_rad: float = 0.0
    camera_enabled: bool = True
    geometry: Geometry = field(default_factory=Geometry)
    range_sensor: RangeConfig = field(default_factory=RangeConfig)
    camera: CameraConfig = field(default_factory=CameraConfig)
    energy: EnergyConfig = field(default_factory=EnergyConfig)
    peripherals_enabled: bool = False
    peripherals: PeripheralConfig = field(default_factory=PeripheralConfig)

    def __post_init__(self) -> None:
        for name in ("dt_s", "gait_period_s", "foot_lift_m", "collision_radius_m",
                     "maximum_speed_mps", "maximum_yaw_rps", "initial_x_m",
                     "initial_y_m", "initial_yaw_rad"):
            finite(getattr(self, name), name)
        if not 0 < self.dt_s <= 0.1 or self.gait_period_s < 0.4:
            raise ValueError("dt must be in (0, 0.1], gait period at least 0.4 seconds")
        if self.foot_lift_m < 0 or self.foot_lift_m >= self.geometry.nominal_height_m:
            raise ValueError("foot lift must remain below nominal body height")
        if min(self.collision_radius_m, self.maximum_speed_mps, self.maximum_yaw_rps) <= 0:
            raise ValueError("radius and speed limits must be positive")
        if type(self.peripherals_enabled) is not bool:
            raise ValueError("peripherals_enabled must be boolean")
        if self.peripherals_enabled and self.peripherals.dt_s != self.dt_s:
            raise ValueError("peripherals and body must share one tick duration")
        if type(self.camera_enabled) is not bool:
            raise ValueError("camera_enabled must be boolean")
        if max(self.range_sensor.offset_forward_m, self.camera.offset_forward_m) >= self.collision_radius_m:
            raise ValueError("sensors must fit inside the collision envelope")

    @classmethod
    def restore(cls, data: dict[str, Any]) -> SimConfig:
        values = copy.deepcopy(data)
        values["geometry"] = Geometry(**values["geometry"])
        values["range_sensor"] = RangeConfig(**values["range_sensor"])
        values["camera"] = CameraConfig(**values["camera"])
        values["energy"] = EnergyConfig(**values.get("energy", {"enabled": False}))
        values["peripherals"] = PeripheralConfig(**values.get("peripherals", {}))
        values.setdefault("peripherals_enabled", False)
        return cls(**values)


@dataclass(frozen=True, slots=True)
class FootState:
    position: tuple[float, float, float]
    swing_start: tuple[float, float, float] | None = None
    swing_target: tuple[float, float, float] | None = None

    @classmethod
    def restore(cls, data: dict[str, Any]) -> FootState:
        values: dict[str, Any] = {}
        for name in ("position", "swing_start", "swing_target"):
            point = data[name]
            if point is None:
                if name == "position":
                    raise ValueError("foot position is required")
                values[name] = None
            else:
                if len(point) != 3:
                    raise ValueError("foot points must have three coordinates")
                values[name] = tuple(finite(v, "foot coordinate") for v in point)
        if (values["swing_start"] is None) != (values["swing_target"] is None):
            raise ValueError("incomplete swing state")
        return cls(**values)


def _advance_pose(pose: tuple[float, float, float], command: dict[str, float], dt: float) -> tuple[float, float, float]:
    """Exact planar integration of a constant body-frame twist."""
    x, y, yaw = pose
    vx, vy, omega = command["forward_mps"], command["lateral_mps"], command["yaw_rps"]
    theta = omega * dt
    if abs(theta) < 1e-10:
        # Stable series near zero, including the lateral component.
        sinc = 1 - theta * theta / 6
        cosc = theta / 2 - theta ** 3 / 24
        bx, by = dt * (vx * sinc - vy * cosc), dt * (vx * cosc + vy * sinc)
    else:
        bx = (vx * math.sin(theta) - vy * (1 - math.cos(theta))) / omega
        by = (vx * (1 - math.cos(theta)) + vy * math.sin(theta)) / omega
    co, si = math.cos(yaw), math.sin(yaw)
    return x + co * bx - si * by, y + si * bx + co * by, math.remainder(yaw + theta, 2 * math.pi)


class PiCrawlerSimBody:
    """Small deterministic body backend; construction never touches hardware.

    `drive` accepts forward_mps, lateral_mps and yaw_rps for one tick only.
    `stop` holds the current feet and pose; `stand` resets the nominal posture.
    State/debug reads never draw randomness or advance a simulation tick.
    """

    def __init__(self, world: World | None = None, config: SimConfig | None = None,
                 *, seed: int = 0) -> None:
        self.world = world if world is not None else World()
        self.config = config if config is not None else SimConfig()
        self.reset(seed)

    @property
    def tick(self) -> int:
        return self._tick

    @property
    def time_s(self) -> float:
        return self._tick * self.config.dt_s

    def _sensor_pose(self, pose: tuple[float, float, float]) -> tuple[float, float, float, float]:
        return (*pose, self.config.geometry.nominal_height_m)

    def _body_to_world(self, point: tuple[float, float, float], pose: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, yaw = pose
        co, si = math.cos(yaw), math.sin(yaw)
        return (x + co * point[0] - si * point[1],
                y + si * point[0] + co * point[1],
                self.config.geometry.nominal_height_m + point[2])

    def _world_to_body(self, point: tuple[float, float, float], pose: tuple[float, float, float]) -> tuple[float, float, float]:
        x, y, yaw = pose
        co, si = math.cos(yaw), math.sin(yaw)
        dx, dy = point[0] - x, point[1] - y
        return (co * dx + si * dy, -si * dx + co * dy,
                point[2] - self.config.geometry.nominal_height_m)

    def _nominal_foot(self, name: str, pose: tuple[float, float, float]) -> tuple[float, float, float]:
        geometry = self.config.geometry
        local = (geometry.nominal_reach_m, 0.0, -geometry.nominal_height_m)
        return self._body_to_world(leg_to_body(name, local, geometry), pose)

    def _validate_feet(self, feet: tuple[FootState, ...], pose: tuple[float, float, float]) -> None:
        for name, foot in zip(LEG_ORDER, feet, strict=True):
            point = self._world_to_body(foot.position, pose)
            joints = inverse_leg(body_to_leg(name, point, self.config.geometry), self.config.geometry)
            for local in leg_points(joints, self.config.geometry):
                p = leg_to_body(name, local, self.config.geometry)
                if math.hypot(p[0], p[1]) > self.config.collision_radius_m + 1e-12:
                    raise ValueError("leg extends beyond the collision envelope")

    def _sense(self, pose: tuple[float, float, float], *,
               rng: RandomSource | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
        sensor_pose = self._sensor_pose(pose)
        source = self._rng if rng is None else rng
        ultrasonic, debug = sample_range(self.world, sensor_pose, source, self.config.range_sensor)
        readings: dict[str, Any] = {"ultrasonic": ultrasonic}
        if self.config.camera_enabled:
            rgb = render_camera(self.world, sensor_pose, self.config.camera)
            readings["camera"] = {"encoding": "rgb8", "width": self.config.camera.width,
                                  "height": self.config.camera.height, "rgb": rgb.tolist()}
        return readings, debug

    def reset(self, seed: int, *, random_source: RandomSource | None = None) -> Observation:
        """Reset to the configured start. An optional source supports test replay.

        The supplied source must support snapshot()/restore_source(), as do the
        repository's NumpySource, DelphiRandom and ReplaySource implementations.
        """
        if type(seed) is not int or seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        pose = (self.config.initial_x_m, self.config.initial_y_m,
                math.remainder(self.config.initial_yaw_rad, 2 * math.pi))
        if not self.world.is_free(pose[0], pose[1], self.config.collision_radius_m):
            raise ValueError("initial pose is in collision")
        feet = tuple(FootState(self._nominal_foot(name, pose)) for name in LEG_ORDER)
        self._validate_feet(feet, pose)
        rng = random_source if random_source is not None else NumpySource(seed)
        restore_source(rng.snapshot())  # Validate resumability up front.
        environment = EnergyEnvironment(self.config.energy.cpu_load, self.config.energy.ambient_temperature_c)
        energy = initial_energy(self.config.energy)
        readings, debug = self._sense(pose, rng=rng)
        peripherals = PeripheralSim(self.config.peripherals) if self.config.peripherals_enabled else None
        if peripherals is not None:
            readings["peripherals"] = peripherals.observe()
        if self.config.energy.enabled:
            readings["telemetry"] = energy_readings(energy, self.config.energy, environment,
                                                    camera_enabled=self.config.camera_enabled)
        if peripherals is not None and self.config.energy.enabled:
            telemetry = readings["telemetry"]
            readings["peripherals"] = peripherals.observe(telemetry["battery_voltage_v"],
                                                         powered=telemetry["powered"])
        self._seed, self._rng = seed, rng
        self._pose, self._feet = pose, feet
        self._tick, self._phase = 0, 0.0
        self._readings, self._sensor_debug = readings, debug
        self._command = {"forward_mps": 0.0, "lateral_mps": 0.0, "yaw_rps": 0.0}
        self._collision, self._workspace_limited = False, False
        self._distance_m = 0.0
        self._energy_state, self._environment = energy, environment
        self.peripherals = peripherals
        self._pending_buttons: list[tuple[str, bool]] = []
        return self.observe()

    def available_actions(self) -> list[str]:
        base = ["drive", "stop", "stand"]
        return base + (["tone", "sound", "speak", "stop_audio", "led"] if self.config.peripherals_enabled else [])

    def observe(self) -> Observation:
        internal = need_signals(self._readings["telemetry"], self.config.energy) if self.config.energy.enabled else {}
        return Observation(tick=self._tick, sensors=copy.deepcopy(self._readings), internal=internal)

    def set_environment(self, *, cpu_load: float | None = None,
                        ambient_temperature_c: float | None = None) -> None:
        """Set experiment conditions for the next tick without advancing time.

        This is an external experiment control, not an available robot action.
        Existing observations retain their acquisition-time values until act().
        """
        environment = self._environment
        self._environment = EnergyEnvironment(
            environment.cpu_load if cpu_load is None else cpu_load,
            environment.ambient_temperature_c if ambient_temperature_c is None else ambient_temperature_c)

    def inject_button(self, button: str, down: bool) -> None:
        """Experiment input; applied on the next simulation tick, not a motor action."""
        if self.peripherals is None:
            raise ValueError("peripherals disabled")
        if button not in {"user", "reset"} or type(down) is not bool:
            raise ValueError("invalid button")
        self._pending_buttons.append((button, down))

    def _parse_action(self, action: Action) -> dict[str, float]:
        if not isinstance(action, Action) or action.name not in self.available_actions():
            raise ValueError("unknown PiCrawler action")
        if not isinstance(action.params, dict):
            raise ValueError("action params must be a dictionary")
        command = {"forward_mps": 0.0, "lateral_mps": 0.0, "yaw_rps": 0.0}
        if action.name not in ("drive", "stop", "stand"):
            # Validate on a detached copy before moving, consuming energy or advancing RNG.
            preview = PeripheralSim.restore(self.peripherals.snapshot())
            preview.command(action.name, **action.params)
            return command
        if action.name != "drive":
            if action.params:
                raise ValueError("stop and stand do not take parameters")
            return command
        if set(action.params) - set(command):
            raise ValueError("unknown drive parameter")
        for name, value in action.params.items():
            command[name] = finite(value, name)
        if math.hypot(command["forward_mps"], command["lateral_mps"]) > self.config.maximum_speed_mps + 1e-12:
            raise ValueError("translation exceeds the configured speed limit")
        if abs(command["yaw_rps"]) > self.config.maximum_yaw_rps + 1e-12:
            raise ValueError("rotation exceeds the configured speed limit")
        return command

    def _step_feet(self, feet: tuple[FootState, ...], phase: float,
                   pose: tuple[float, float, float], command: dict[str, float]) -> tuple[FootState, ...]:
        result: list[FootState] = []
        period = self.config.gait_period_s
        for name, old, offset in zip(LEG_ORDER, feet, _PHASE_OFFSETS, strict=True):
            local_phase = (phase + offset) % 1.0
            if local_phase < _DUTY_FACTOR:
                point = old.swing_target if old.swing_target is not None else old.position
                result.append(FootState(point))
                continue
            start, target = old.swing_start, old.swing_target
            if start is None:
                start = old.position
                remaining = (1 - local_phase) * period
                # Put the foot ahead of its nominal position for the stance.
                landing_pose = _advance_pose(pose, command, remaining + 0.5 * _DUTY_FACTOR * period)
                target = self._nominal_foot(name, landing_pose)
            assert target is not None
            progress = (local_phase - _DUTY_FACTOR) / (1 - _DUTY_FACTOR)
            smooth = progress * progress * (3 - 2 * progress)
            point = (start[0] + smooth * (target[0] - start[0]),
                     start[1] + smooth * (target[1] - start[1]),
                     self.config.foot_lift_m * math.sin(math.pi * progress) ** 2)
            result.append(FootState(point, start, target))
        return tuple(result)

    def act(self, action: Action) -> None:
        command = self._parse_action(action)
        pending_peripherals = (PeripheralSim.restore(self.peripherals.snapshot())
                               if self.peripherals is not None else None)
        if pending_peripherals is not None:
            for button, down in self._pending_buttons:
                pending_peripherals.inject_button(button, down)
        if pending_peripherals is not None and action.name not in ("drive", "stop", "stand"):
            pending_peripherals.command(action.name, **action.params)
        accessory_power = pending_peripherals.additional_power_w() if pending_peripherals else 0.0
        motion = min(1.0, max(math.hypot(command["forward_mps"], command["lateral_mps"]) /
                              self.config.maximum_speed_mps, abs(command["yaw_rps"]) / self.config.maximum_yaw_rps))
        allowed = True
        if self.config.energy.enabled:
            allowed = energy_readings(self._energy_state, self.config.energy, self._environment,
                                      motion_fraction=motion, camera_enabled=self.config.camera_enabled,
                                      accessory_power_w=accessory_power)["powered"]
        motor_command = command if allowed else {key: 0.0 for key in command}
        pose, feet, phase = self._pose, self._feet, self._phase
        collision, limited, distance = False, False, self._distance_m
        if action.name == "stand" and allowed:
            feet = tuple(FootState(self._nominal_foot(name, pose)) for name in LEG_ORDER)
            phase = 0.0
        elif any(motor_command.values()):
            count = math.ceil(self.config.dt_s / 0.01)
            h = self.config.dt_s / count
            for _ in range(count):
                trial = _advance_pose(pose, motor_command, h)
                fraction = self.world.sweep(pose[0], pose[1], trial[0] - pose[0], trial[1] - pose[1],
                                            self.config.collision_radius_m)
                if fraction < 1:
                    # Use the checked chord exactly; at this small fixed step
                    # the trajectory model is piecewise chordal, not a force model.
                    trial = (pose[0] + fraction * (trial[0] - pose[0]),
                             pose[1] + fraction * (trial[1] - pose[1]),
                             math.remainder(pose[2] + motor_command["yaw_rps"] * h * fraction, 2 * math.pi))
                    collision = True
                next_phase = (phase + h * fraction / self.config.gait_period_s) % 1.0
                next_feet = self._step_feet(feet, next_phase, trial, motor_command)
                try:
                    self._validate_feet(next_feet, trial)
                except ValueError:
                    limited = True
                    break
                distance += math.hypot(trial[0] - pose[0], trial[1] - pose[1])
                pose, feet, phase = trial, next_feet, next_phase
                if collision:
                    break
        energy = self._energy_state
        telemetry = None
        if self.config.energy.enabled:
            energy, telemetry = advance_energy(energy, self.config.energy, self._environment,
                                               dt_s=self.config.dt_s, motion_fraction=motion,
                                               stalled=collision or limited,
                                               camera_enabled=self.config.camera_enabled,
                                               accessory_power_w=accessory_power)
            if not telemetry["powered"]:
                # Conservative whole-tick stop on a model cutoff; no fictional
                # motor motion after the supply has latched off.
                pose, feet, phase, distance = self._pose, self._feet, self._phase, self._distance_m
        random_before = self._rng.snapshot()
        try:
            readings, debug = self._sense(pose)
            if telemetry is not None:
                readings["telemetry"] = telemetry
            if pending_peripherals is not None:
                pending_peripherals.advance(powered=allowed and (telemetry is None or telemetry["powered"]))
                voltage = telemetry["battery_voltage_v"] if telemetry is not None else None
                readings["peripherals"] = pending_peripherals.observe(voltage,
                    powered=allowed and (telemetry is None or telemetry["powered"]))
        except Exception:
            self._rng = restore_source(random_before)
            raise
        self._pose, self._feet, self._phase = pose, feet, phase
        self._collision, self._workspace_limited = collision, limited
        self._distance_m, self._command = distance, command
        self._readings, self._sensor_debug = readings, debug
        self._energy_state = energy
        self.peripherals = pending_peripherals
        self._pending_buttons = []
        self._tick += 1

    def frame(self, *, include_camera: bool = True) -> dict[str, Any]:
        """Observer-only geometry/ground truth for offline replay and debugging."""
        legs = []
        for name, foot in zip(LEG_ORDER, self._feet, strict=True):
            point = self._world_to_body(foot.position, self._pose)
            joints = inverse_leg(body_to_leg(name, point, self.config.geometry), self.config.geometry)
            points = [list(self._body_to_world(leg_to_body(name, p, self.config.geometry), self._pose))
                      for p in leg_points(joints, self.config.geometry)]
            legs.append({"name": name, "points": points, "joints_rad": asdict(joints),
                         "stance": foot.swing_start is None})
        result = {"tick": self._tick, "time_s": self.time_s,
                  "pose": {"x_m": self._pose[0], "y_m": self._pose[1], "yaw_rad": self._pose[2],
                           "height_m": self.config.geometry.nominal_height_m},
                  "legs": legs, "sensor": copy.deepcopy(self._sensor_debug),
                  "collision": self._collision, "workspace_limited": self._workspace_limited,
                  "distance_travelled_m": self._distance_m, "command": self._command.copy()}
        if self.config.energy.enabled:
            result["telemetry"] = copy.deepcopy(self._readings["telemetry"])
            result["needs"] = need_signals(self._readings["telemetry"], self.config.energy)
        if self.peripherals is not None:
            result["peripherals"] = copy.deepcopy(self._readings["peripherals"])
            result["peripheral_events"] = copy.deepcopy(self.peripherals.events)
        if include_camera and "camera" in self._readings:
            result["camera_rgb"] = copy.deepcopy(self._readings["camera"]["rgb"])
        return result

    def snapshot(self) -> dict[str, Any]:
        return {"type": _SNAPSHOT_TYPE, "version": 3 if self.peripherals is not None else 2, "seed": self._seed,
                "config": asdict(self.config), "world": self.world.snapshot(),
                "tick": self._tick, "pose": list(self._pose), "phase": self._phase,
                "feet": [asdict(f) for f in self._feet], "rng": copy.deepcopy(self._rng.snapshot()),
                "readings": copy.deepcopy(self._readings), "sensor_debug": copy.deepcopy(self._sensor_debug),
                "command": self._command.copy(), "collision": self._collision,
                "workspace_limited": self._workspace_limited, "distance_m": self._distance_m,
                "energy": asdict(self._energy_state), "environment": asdict(self._environment),
                **({"peripherals_state": self.peripherals.snapshot(),
                    "pending_buttons": [list(event) for event in self._pending_buttons]}
                   if self.peripherals else {})}

    @classmethod
    def restore(cls, data: dict[str, Any]) -> PiCrawlerSimBody:
        """Restore a trusted, versioned JSON snapshot without executing code."""
        if data.get("type") != _SNAPSHOT_TYPE or data.get("version") not in (1, 2, 3):
            raise ValueError("unsupported PiCrawler snapshot")
        config_data = copy.deepcopy(data["config"])
        if data["version"] == 1:
            config_data["energy"] = {"enabled": False}
        obj = cls(World.restore(data["world"]), SimConfig.restore(config_data), seed=data["seed"])
        if type(data["tick"]) is not int or data["tick"] < 0:
            raise ValueError("invalid snapshot tick")
        if len(data["pose"]) != 3:
            raise ValueError("invalid snapshot pose")
        pose = tuple(finite(v, "pose coordinate") for v in data["pose"])
        phase = finite(data["phase"], "gait phase")
        distance = finite(data["distance_m"], "travel distance")
        if not 0 <= phase < 1 or distance < 0:
            raise ValueError("invalid snapshot phase/distance")
        if not obj.world.is_free(pose[0], pose[1], obj.config.collision_radius_m):
            raise ValueError("snapshot pose is in collision")
        feet = tuple(FootState.restore(f) for f in data["feet"])
        if len(feet) != 4:
            raise ValueError("snapshot must contain four feet")
        obj._validate_feet(feet, pose)
        command = obj._parse_action(Action("drive", data["command"]))
        for key in ("collision", "workspace_limited"):
            if type(data[key]) is not bool:
                raise ValueError("snapshot flags must be boolean")
        obj._tick, obj._pose, obj._phase, obj._feet = data["tick"], pose, phase, feet
        obj._distance_m, obj._command = distance, command
        obj._collision, obj._workspace_limited = data["collision"], data["workspace_limited"]
        obj._rng = restore_source(copy.deepcopy(data["rng"]))
        obj._readings = copy.deepcopy(data["readings"])
        obj._sensor_debug = copy.deepcopy(data["sensor_debug"])
        if data["version"] in (2, 3):
            obj._energy_state = EnergyState(**data["energy"])
            obj._environment = EnergyEnvironment(**data["environment"])
            if obj.config.energy.enabled:
                need_signals(obj._readings["telemetry"], obj.config.energy)
        if data["version"] == 3:
            if obj.peripherals is None:
                raise ValueError("v3 snapshot requires peripherals")
            obj.peripherals = PeripheralSim.restore(data["peripherals_state"])
            if obj.peripherals.tick != obj.tick:
                raise ValueError("body/peripheral clocks disagree")
            observed = obj.peripherals.observe(
                obj._readings.get("telemetry", {}).get("battery_voltage_v"),
                powered=obj._readings.get("telemetry", {}).get("powered", True))
            if obj._readings.get("peripherals") != observed:
                raise ValueError("inconsistent peripheral sensor cache")
            pending = data.get("pending_buttons", [])
            if not isinstance(pending, list):
                raise ValueError("invalid pending buttons")
            for event in pending:
                if not isinstance(event, (list, tuple)) or len(event) != 2:
                    raise ValueError("invalid pending button")
                obj.inject_button(*event)
        return obj
