"""Deterministic battery/CPU model and local Psi need signals.

These parameters are explicit experiment assumptions, not a calibrated PiCrawler
digital twin. Battery charge is integrated from current; CPU heat follows a
single thermal RC. Nothing here reads hardware or changes the motivation core.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .world import finite


@dataclass(frozen=True, slots=True)
class EnergyConfig:
    enabled: bool = True
    battery_capacity_ah: float = 2.0
    battery_voltage_empty_v: float = 6.4
    battery_voltage_full_v: float = 8.4
    battery_internal_resistance_ohm: float = 0.15
    battery_initial_soc: float = 0.8
    battery_cutoff_voltage_v: float = 6.0
    supply_nominal_voltage_v: float = 5.0
    regulator_min_input_v: float = 6.5
    supply_undervoltage_v: float = 4.63
    regulator_efficiency: float = 0.9
    idle_cpu_power_w: float = 2.5
    active_cpu_power_w: float = 3.0
    camera_power_w: float = 0.5
    servo_idle_power_w: float = 0.8
    servo_motion_power_w: float = 8.0
    servo_stall_power_w: float = 12.0
    cpu_load: float = 0.5
    ambient_temperature_c: float = 25.0
    initial_cpu_temperature_c: float = 40.0
    thermal_resistance_c_per_w: float = 15.0
    thermal_capacity_j_per_c: float = 10.0
    temperature_warning_c: float = 65.0
    temperature_critical_c: float = 85.0
    temperature_throttle_c: float = 80.0
    throttled_dynamic_power_factor: float = 0.55
    hunger_soc_warning: float = 0.30
    hunger_soc_critical: float = 0.05

    def __post_init__(self) -> None:
        if type(self.enabled) is not bool:
            raise ValueError("enabled must be boolean")
        for name, value in asdict(self).items():
            if name != "enabled":
                finite(value, name)
        positive = ("battery_capacity_ah", "battery_voltage_empty_v", "battery_voltage_full_v",
                    "battery_cutoff_voltage_v", "supply_nominal_voltage_v", "regulator_min_input_v",
                    "supply_undervoltage_v", "thermal_resistance_c_per_w", "thermal_capacity_j_per_c")
        if any(getattr(self, name) <= 0 for name in positive):
            raise ValueError("capacity, voltages and thermal constants must be positive")
        if self.battery_internal_resistance_ohm < 0 or any(
            value < 0 for name, value in asdict(self).items() if name.endswith("_power_w")
        ):
            raise ValueError("resistance and power must be nonnegative")
        if not (0 < self.regulator_efficiency <= 1 and 0 <= self.battery_initial_soc <= 1
                and 0 <= self.cpu_load <= 1 and 0 <= self.throttled_dynamic_power_factor <= 1):
            raise ValueError("efficiency, charge and load fractions are out of bounds")
        if not (self.battery_cutoff_voltage_v <= self.battery_voltage_empty_v < self.battery_voltage_full_v
                and self.supply_undervoltage_v <= self.supply_nominal_voltage_v
                and self.regulator_min_input_v >= self.supply_nominal_voltage_v):
            raise ValueError("inconsistent voltage thresholds")
        if not (0 <= self.hunger_soc_critical < self.hunger_soc_warning <= 1):
            raise ValueError("hunger charge thresholds must be ordered in [0, 1]")
        if not self.temperature_warning_c < self.temperature_throttle_c <= self.temperature_critical_c:
            raise ValueError("temperature thresholds must be ordered")
        if min(self.ambient_temperature_c, self.initial_cpu_temperature_c) < -273.15:
            raise ValueError("temperature cannot be below absolute zero")


@dataclass(frozen=True, slots=True)
class EnergyEnvironment:
    """Explicit experiment inputs, independent of the robot's action space."""

    cpu_load: float = 0.5
    ambient_temperature_c: float = 25.0

    def __post_init__(self) -> None:
        if not 0 <= finite(self.cpu_load, "cpu_load") <= 1:
            raise ValueError("cpu_load must be in [0, 1]")
        if finite(self.ambient_temperature_c, "ambient_temperature_c") < -273.15:
            raise ValueError("temperature cannot be below absolute zero")


@dataclass(frozen=True, slots=True)
class EnergyState:
    state_of_charge: float
    cpu_temperature_c: float
    charge_used_ah: float = 0.0
    energy_consumed_j: float = 0.0
    battery_loss_j: float = 0.0
    undervoltage_occurred: bool = False
    thermal_throttling_occurred: bool = False
    shutdown_reason: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= finite(self.state_of_charge, "state_of_charge") <= 1:
            raise ValueError("state of charge must be in [0, 1]")
        if finite(self.cpu_temperature_c, "cpu_temperature_c") < -273.15:
            raise ValueError("temperature cannot be below absolute zero")
        for name in ("charge_used_ah", "energy_consumed_j", "battery_loss_j"):
            if finite(getattr(self, name), name) < 0:
                raise ValueError("cumulative consumption must be nonnegative")
        if type(self.undervoltage_occurred) is not bool or type(self.thermal_throttling_occurred) is not bool:
            raise ValueError("history flags must be boolean")
        if self.shutdown_reason not in (None, "battery_empty", "battery_cutoff", "power_limit"):
            raise ValueError("invalid shutdown reason")


def initial_energy(config: EnergyConfig) -> EnergyState:
    return EnergyState(config.battery_initial_soc, config.initial_cpu_temperature_c)


def open_circuit_voltage(state_of_charge: float, config: EnergyConfig) -> float:
    """Assumed piecewise 2S discharge curve; not a voltage-to-SOC estimator."""
    soc = finite(state_of_charge, "state_of_charge")
    if not 0 <= soc <= 1:
        raise ValueError("state of charge must be in [0, 1]")
    knots = ((0.0, 0.0), (0.1, 0.25), (0.5, 0.55), (0.9, 0.85), (1.0, 1.0))
    for (a, va), (b, vb) in zip(knots, knots[1:]):
        if soc <= b:
            fraction = va + (soc - a) / (b - a) * (vb - va)
            return config.battery_voltage_empty_v + fraction * (
                config.battery_voltage_full_v - config.battery_voltage_empty_v)
    raise AssertionError("unreachable charge interval")


def _load(state: EnergyState, config: EnergyConfig, environment: EnergyEnvironment,
          motion_fraction: float, stalled: bool, camera_enabled: bool, accessory_power_w: float = 0.0) -> dict[str, Any]:
    """Operating point at the start of a fixed integration interval."""
    motion = finite(motion_fraction, "motion_fraction")
    if not 0 <= motion <= 1 or type(stalled) is not bool or type(camera_enabled) is not bool:
        raise ValueError("invalid motion/load inputs")
    accessory = finite(accessory_power_w, "accessory_power_w")
    if accessory < 0:
        raise ValueError("accessory power must be nonnegative")
    thermal = state.cpu_temperature_c >= config.temperature_throttle_c
    cpu = config.idle_cpu_power_w + config.active_cpu_power_w * environment.cpu_load * (
        config.throttled_dynamic_power_factor if thermal else 1.0)
    servo = config.servo_idle_power_w + motion * (
        config.servo_stall_power_w if stalled else config.servo_motion_power_w)
    requested = (cpu + (config.camera_power_w if camera_enabled else 0.0) + servo + accessory) / config.regulator_efficiency
    voc = open_circuit_voltage(state.state_of_charge, config)
    resistance = config.battery_internal_resistance_ohm
    limit = math.inf if resistance == 0 else voc * voc / (4 * resistance)
    limited = requested > limit
    supplied = min(requested, limit)
    current = supplied / voc if resistance == 0 else 2 * supplied / (
        voc + math.sqrt(max(0.0, voc * voc - 4 * resistance * supplied)))
    terminal = voc - current * resistance
    shutdown = state.shutdown_reason
    if state.state_of_charge <= 0:
        shutdown = "battery_empty"
    elif shutdown is None and limited:
        shutdown = "power_limit"
    elif shutdown is None and terminal < config.battery_cutoff_voltage_v:
        shutdown = "battery_cutoff"
    if shutdown is not None:
        current, supplied, cpu, servo, terminal = 0.0, 0.0, 0.0, 0.0, voc
    supply = 0.0 if shutdown else config.supply_nominal_voltage_v * min(1.0, terminal / config.regulator_min_input_v)
    return {"open_circuit_voltage_v": voc, "battery_voltage_v": terminal,
            "supply_voltage_v": supply, "core_voltage_v": None,
            "current_a": current, "power_w": supplied, "requested_power_w": requested,
            "cpu_power_w": cpu, "servo_power_w": servo,
            "undervoltage": supply < config.supply_undervoltage_v,
            "thermal_throttled": thermal and shutdown is None, "power_limited": limited,
            "powered": shutdown is None, "shutdown_reason": shutdown}


def _telemetry(state: EnergyState, point: dict[str, Any], config: EnergyConfig,
               environment: EnergyEnvironment) -> dict[str, Any]:
    return {**point, "source": "simulated", "state_of_charge": state.state_of_charge,
            "cpu_temperature_c": state.cpu_temperature_c,
            "battery_depleted": state.state_of_charge <= 0,
            "charge_used_ah": state.charge_used_ah,
            "energy_consumed_j": state.energy_consumed_j,
            "battery_loss_j": state.battery_loss_j,
            "ambient_temperature_c": environment.ambient_temperature_c,
            "cpu_load": environment.cpu_load,
            "thermal_throttled": state.cpu_temperature_c >= config.temperature_throttle_c and point["powered"],
            "history": {"undervoltage": state.undervoltage_occurred,
                        "thermal_throttled": state.thermal_throttling_occurred}}


def energy_readings(state: EnergyState, config: EnergyConfig,
                    environment: EnergyEnvironment, *, motion_fraction: float = 0.0,
                    stalled: bool = False, camera_enabled: bool = True,
                    accessory_power_w: float = 0.0) -> dict[str, Any]:
    """Read the instantaneous assumed operating point without consuming energy."""
    return _telemetry(state, _load(state, config, environment, motion_fraction, stalled, camera_enabled, accessory_power_w),
                      config, environment)


def advance_energy(state: EnergyState, config: EnergyConfig, environment: EnergyEnvironment,
                   *, dt_s: float, motion_fraction: float, stalled: bool = False,
                   camera_enabled: bool = True, accessory_power_w: float = 0.0) -> tuple[EnergyState, dict[str, Any]]:
    """Integrate charge and CPU heat for a fixed tick; no RNG or wall clock.

    Current and power in the returned cache are interval averages. Battery
    voltages describe the interval's initial loaded operating point; supply
    voltage and powered flags describe the end status. A final
    partial interval is bounded by remaining charge, so consumption cannot
    exceed capacity. On cutoff the power stage latches off until reset. The
    external simulator continues observing the cooling, unpowered body.
    """
    dt = finite(dt_s, "dt_s")
    if dt <= 0:
        raise ValueError("dt_s must be positive")
    point = _load(state, config, environment, motion_fraction, stalled, camera_enabled, accessory_power_w)
    active_dt = dt
    current = point["current_a"]
    if current > 0:
        active_dt = min(dt, state.state_of_charge * config.battery_capacity_ah * 3600 / current)
    charge = current * active_dt / 3600
    remaining = max(0.0, state.state_of_charge - charge / config.battery_capacity_ah)
    if active_dt < dt or (remaining <= 1e-15 and current > 0):
        remaining = 0.0
    # Exact RC solution for constant dissipation, then passive cooling if empty.
    rth, cth = config.thermal_resistance_c_per_w, config.thermal_capacity_j_per_c
    ambient = environment.ambient_temperature_c
    equilibrium = ambient + point["cpu_power_w"] * rth
    temperature = equilibrium + (state.cpu_temperature_c - equilibrium) * math.exp(-active_dt / (rth * cth))
    if active_dt < dt:
        temperature = ambient + (temperature - ambient) * math.exp(-(dt - active_dt) / (rth * cth))
    shutdown = "battery_empty" if remaining == 0 else point["shutdown_reason"]
    end_thermal = temperature >= config.temperature_throttle_c and shutdown is None
    result = EnergyState(
        remaining, temperature, state.charge_used_ah + charge,
        state.energy_consumed_j + point["power_w"] * active_dt,
        state.battery_loss_j + current * current * config.battery_internal_resistance_ohm * active_dt,
        state.undervoltage_occurred or point["undervoltage"] or shutdown is not None,
        state.thermal_throttling_occurred or point["thermal_throttled"] or end_thermal, shutdown)
    for key in ("current_a", "power_w", "cpu_power_w", "servo_power_w"):
        point[key] *= active_dt / dt
    if shutdown:
        point.update(powered=False, shutdown_reason=shutdown, supply_voltage_v=0.0, undervoltage=True,
                     thermal_throttled=False)
    return result, _telemetry(result, point, config, environment)


def need_signals(telemetry: Mapping[str, Any], config: EnergyConfig) -> dict[str, float | None]:
    """Map energy to „Hunger“ and thermal/electrical risk to „Schaden“.

    These are proposed normalized inputs, not the core's motivational state.
    Missing charge/temperature/voltage information remains unknown. In
    particular, a battery voltage alone is never turned into a fake SOC.
    """
    soc = telemetry.get("state_of_charge")
    temperature = telemetry.get("cpu_temperature_c")
    hunger = None
    if soc is not None:
        soc = finite(soc, "state_of_charge")
        if not 0 <= soc <= 1:
            raise ValueError("state of charge must be in [0, 1]")
        hunger = max(0.0, min(1.0, (config.hunger_soc_warning - soc) /
                                  (config.hunger_soc_warning - config.hunger_soc_critical)))
    risks = []
    if temperature is not None:
        risks.append(max(0.0, min(1.0, (finite(temperature, "cpu_temperature_c") - config.temperature_warning_c) /
                                        (config.temperature_critical_c - config.temperature_warning_c))))
    undervoltage = telemetry.get("undervoltage")
    if undervoltage is not None:
        if type(undervoltage) is not bool:
            raise ValueError("undervoltage must be boolean or None")
        risks.append(float(undervoltage))
    return {"hunger": hunger, "damage": max(risks) if risks else None}
