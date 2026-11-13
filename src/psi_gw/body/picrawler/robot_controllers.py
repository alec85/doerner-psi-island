"""Two non-PSI reference policies; only detached observations and commands enter."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import math
from typing import Any

from psi_gw.body import Action, Observation
from psi_gw.random_source import NumpySource

from .perception import range_features
from .temporal import SensorMemory
from .validation_io import digest

POLICIES = ("reactive", "memory")


@dataclass(frozen=True)
class ControllerConfig:
    dt_s: float = .05
    speed_mps: float = .025
    turn_rps: float = .22
    near_m: float = .27
    clear_m: float = .34
    hunger_stop: float = .85
    damage_stop: float = .95
    bypass_ticks: int = 120

    def __post_init__(self) -> None:
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0 for v in asdict(self).values()):
            raise ValueError("invalid controller parameter")
        if not (self.dt_s <= .1 and self.speed_mps <= .03 and self.turn_rps <= .3 and
                self.near_m < self.clear_m and self.hunger_stop <= 1 and self.damage_stop <= 1 and
                type(self.bypass_ticks) is int):
            raise ValueError("controller parameters exceed their envelope")


def sensor_view(observation: Observation) -> Observation:
    """Explicit allowlist: discard debug geometry and arbitrary extra fields."""
    sensors = {}
    for channel, fields in (("ultrasonic", ("distance_m", "status", "captured_at_s")),
                            ("camera", ("rgb", "encoding", "width", "height", "captured_at_s"))):
        value = observation.sensors.get(channel)
        if isinstance(value, dict):
            sensors[channel] = {key: copy.deepcopy(value[key]) for key in fields if key in value}
    return Observation(observation.tick, sensors,
        {key: copy.deepcopy(observation.internal.get(key)) for key in ("hunger", "damage")})


class ReferenceController:
    def __init__(self, policy: str, seed: int = 0, config: ControllerConfig = ControllerConfig()) -> None:
        if policy not in POLICIES or type(seed) is not int or seed < 0:
            raise ValueError("invalid policy or seed")
        self.policy, self.seed, self.config = policy, seed, config
        self.turn_sign = 1 if NumpySource(seed).randint(2, site="picrawler.controller.turn") else -1
        self.memory = SensorMemory()
        self.heading_estimate = 0.0
        self.phase, self.mode = "cruise", "initial"
        self.turn_started = 0.0
        self.bypass_remaining = 0
        self.energy_latched = False
        self.last_tick = -1
        self.last_action = Action("stop")
        self.last_input_hash = None
        self.last_decision: dict[str, Any] = {}

    def choose(self, observation: Observation, previous_action: Action = Action("stop")) -> Action:
        observation = sensor_view(observation)
        if type(observation.tick) is not int or observation.tick < 0:
            raise ValueError("invalid decision tick")
        fingerprint = digest({"observation": asdict(observation), "previous_action": asdict(previous_action)})
        if observation.tick == self.last_tick:
            if fingerprint != self.last_input_hash:
                raise ValueError("conflicting inputs for the same decision tick")
            return copy.deepcopy(self.last_action)
        if observation.tick < self.last_tick:
            raise ValueError("decision time moved backwards")
        dt = self.config.dt_s * (observation.tick - self.last_tick if self.last_tick >= 0 else 0)
        yaw = previous_action.params.get("yaw_rps", 0.0) if previous_action.name == "drive" else 0.0
        self.heading_estimate = math.remainder(self.heading_estimate + yaw * dt, 2 * math.pi)
        now = observation.tick * self.config.dt_s
        if self.policy == "memory":
            features = self.memory.update(observation.sensors, now_s=now, rotated=bool(yaw))
            distance = features["distance_m"]
        else:
            feature = range_features(observation.sensors.get("ultrasonic"), now_s=now)
            distance = feature.distance_m if feature.usable else None
            features = {"distance_m": distance, "range_source": "measured" if distance is not None else "unknown",
                        "range_age_s": feature.age_s, "tracks": []}
        needs = [observation.internal.get(key) for key in ("hunger", "damage")]
        known_needs = all(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= 1 for v in needs)
        if known_needs and (needs[0] >= self.config.hunger_stop or needs[1] >= self.config.damage_stop):
            self.energy_latched = True
        if self.energy_latched:
            action, mode = Action("stop"), "energy_stop"
        elif not known_needs:
            action, mode = Action("stop"), "unknown_needs"
        elif distance is None:
            action, mode = Action("stop"), "unknown_range"
        elif self.policy == "reactive":
            mode = "turn" if distance < self.config.near_m else "drive"
            action = Action("drive", {"yaw_rps": self.config.turn_rps * self.turn_sign} if mode == "turn"
                            else {"forward_mps": self.config.speed_mps})
        else:
            action, mode = self._stateful(distance)
        if mode != self.mode and mode in ("drive", "turn", "bypass", "recover") and self.mode in ("drive", "turn", "bypass", "recover"):
            action = Action("stand")  # Explicit, counted kinematic posture reset.
        self.mode = mode
        self.last_tick, self.last_input_hash = observation.tick, fingerprint
        self.last_action = copy.deepcopy(action)
        self.last_decision = {"mode": mode, "phase": self.phase, "features": features,
            "heading_estimate_rad": self.heading_estimate, "heading_source": "command_integral_not_odometry"}
        return action

    def _stateful(self, distance: float) -> tuple[Action, str]:
        c = self.config
        if distance < c.near_m and self.phase != "avoid":
            self.phase = "avoid"
            self.turn_started = self.heading_estimate
        if self.phase == "avoid":
            angle = abs(math.remainder(self.heading_estimate - self.turn_started, 2 * math.pi))
            if distance >= c.clear_m and angle >= .4:
                self.phase, self.bypass_remaining = "bypass", c.bypass_ticks
            else:
                return Action("drive", {"yaw_rps": c.turn_rps * self.turn_sign}), "turn"
        if self.phase == "bypass":
            if self.bypass_remaining > 0:
                self.bypass_remaining -= 1
                return Action("drive", {"forward_mps": c.speed_mps}), "bypass"
            self.phase = "recover"
        if self.phase == "recover":
            if abs(self.heading_estimate) > .03:
                return Action("drive", {"yaw_rps": -math.copysign(c.turn_rps, self.heading_estimate)}), "recover"
            self.phase = "cruise"
        return Action("drive", {"forward_mps": c.speed_mps}), "drive"

    def snapshot(self) -> dict[str, Any]:
        return {"type": "psi_gw.picrawler.reference_controller", "version": 1,
            "policy": self.policy, "seed": self.seed, "config": asdict(self.config), "turn_sign": self.turn_sign,
            "memory": self.memory.snapshot(), "heading_estimate": self.heading_estimate,
            "phase": self.phase, "mode": self.mode, "turn_started": self.turn_started,
            "bypass_remaining": self.bypass_remaining, "energy_latched": self.energy_latched,
            "last_tick": self.last_tick, "last_action": asdict(self.last_action),
            "last_input_hash": self.last_input_hash, "last_decision": copy.deepcopy(self.last_decision)}

    @classmethod
    def restore(cls, payload: dict[str, Any]) -> ReferenceController:
        if payload.get("type") != "psi_gw.picrawler.reference_controller" or payload.get("version") != 1:
            raise ValueError("unsupported controller snapshot")
        obj = cls(payload["policy"], payload["seed"], ControllerConfig(**payload["config"]))
        for key in ("turn_sign", "heading_estimate", "phase", "mode", "turn_started", "bypass_remaining",
                    "energy_latched", "last_tick", "last_input_hash", "last_decision"):
            setattr(obj, key, copy.deepcopy(payload[key]))
        obj.memory = SensorMemory.restore(payload["memory"])
        obj.last_action = Action(**payload["last_action"])
        return obj
