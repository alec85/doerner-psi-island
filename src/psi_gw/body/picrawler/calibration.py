"""Versioned, provenance-bearing calibration profiles and read-only collection.

The template separates manufacturer dimensions and SDK wiring from unmeasured
physical parameters. In particular SDK direction/offset fields are not a
conversion from our mathematical joint angles to PWM. No code in this module
imports Robot HAT or emits actuator commands.

Usage:
    python -m psi_gw.body.picrawler.calibration template --output profile.json
    python -m psi_gw.body.picrawler.calibration collect --output telemetry.json

See docs/picrawler/CALIBRATION.md for the measurement procedure and sources.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime
import json
import math
from pathlib import Path
from typing import Any, Callable

from .kinematics import Geometry, LEG_ORDER
from .telemetry import collect_telemetry


PROFILE_TYPE = "psi_gw.picrawler.calibration"
PROFILE_VERSION = 1
_SDK_SOURCE = "https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler/picrawler.py"
_DIM_SOURCE = "https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler-control/references/api.md"
_ASSUMPTION_SOURCE = "psi_gw PiCrawler generic simulation preset; not a hardware measurement"
_UNKNOWN_SOURCE = "not yet measured on the target PiCrawler"
_CONVENTION = "body x forward, y left, z up; local model yaw/hip/knee in radians; not SDK/PWM angles"
_CAMERA_FRAME = "body-aligned camera x forward, y left, z up; image u right=-y, v down=-z"
_PIN_LIST = (9, 10, 11, 3, 4, 5, 0, 1, 2, 6, 7, 8)
_SDK_DIRECTIONS = (1, 1, -1, 1, 1, 1, 1, 1, -1, 1, 1, 1)
_GEOMETRY_UNITS = {name: "m" for name in Geometry.__dataclass_fields__}
_ELECTRICAL_DEFAULTS = {
    "battery_capacity_ah": (2.0, "Ah"),
    "battery_voltage_empty_v": (6.4, "V"),
    "battery_voltage_full_v": (8.4, "V"),
    "battery_internal_resistance_ohm": (0.15, "ohm"),
    "battery_initial_soc": (0.8, "1"),
    "idle_cpu_power_w": (2.5, "W"),
    "active_cpu_power_w": (3.0, "W"),
    "camera_power_w": (0.5, "W"),
    "servo_idle_power_w": (0.8, "W"),
    "servo_motion_power_w": (8.0, "W"),
    "servo_stall_power_w": (12.0, "W"),
    "regulator_efficiency": (0.9, "1"),
    "supply_nominal_voltage_v": (5.0, "V"),
    "battery_cutoff_voltage_v": (6.0, "V"),
    "regulator_min_input_v": (6.5, "V"),
    "supply_undervoltage_v": (4.63, "V"),
    "cpu_load": (0.5, "1"),
    "hunger_soc_warning": (0.30, "1"),
    "hunger_soc_critical": (0.05, "1"),
}
_THERMAL_DEFAULTS = {
    "ambient_temperature_c": (25.0, "degC"),
    "initial_cpu_temperature_c": (40.0, "degC"),
    "thermal_resistance_c_per_w": (15.0, "degC/W"),
    "thermal_capacity_j_per_c": (10.0, "J/degC"),
    "temperature_warning_c": (65.0, "degC"),
    "temperature_throttle_c": (80.0, "degC"),
    "temperature_critical_c": (85.0, "degC"),
    "throttled_dynamic_power_factor": (0.55, "1"),
}
_CAMERA_UNITS = {
    "width_px": "px", "height_px": "px", "fx_px": "px", "fy_px": "px",
    "cx_px": "px", "cy_px": "px", "distortion_k1_k2_p1_p2_k3": "1",
    "position_body_m": "m", "rpy_body_rad": "rad",
}
_RANGE_DEFAULTS = {
    "minimum_m": (0.02, "m"), "maximum_m": (4.0, "m"),
    "noise_half_width_m": (0.0, "m"), "dropout_probability": (0.0, "1"),
    "offset_forward_m": (0.045, "m"), "mount_height_m": (0.03, "m"),
}
_SERVO_UNITS = {
    "channel": "index", "sdk_direction": "1", "sdk_offset_deg": "deg",
    "model_joint": "name", "model_direction": "1", "model_zero_offset_rad": "rad",
    "model_minimum_rad": "rad", "model_maximum_rad": "rad",
}
_PROVENANCE_KEYS = {"kind", "source", "method", "measured_at"}


def _record(value: Any, unit: str, kind: str = "assumed", *, source: str | None = None,
            method: str = "Uncalibrated generic simulation parameter") -> dict[str, Any]:
    return {"value": value, "unit": unit, "provenance": {
        "kind": kind, "source": source or (_UNKNOWN_SOURCE if kind == "unknown" else _ASSUMPTION_SOURCE),
        "method": method, "measured_at": None,
    }}


def default_profile(name: str = "uncalibrated-picrawler") -> dict[str, Any]:
    """Create a fresh JSON-compatible template; no parameter claims measurement."""
    geometry = Geometry()
    geometric = {}
    for field_name in _GEOMETRY_UNITS:
        known = field_name not in {"nominal_height_m", "nominal_reach_m"}
        geometric[field_name] = _record(
            getattr(geometry, field_name), "m", "manufacturer" if known else "assumed",
            source=(_SDK_SOURCE if field_name == "hip_spacing_m" else _DIM_SOURCE) if known else _ASSUMPTION_SOURCE,
            method="Manufacturer SDK dimension, converted mm to m" if known else "Chosen nominal simulated stance",
        )
    servos = []
    for i, channel in enumerate(_PIN_LIST):
        record = {"leg": LEG_ORDER[i // 3], "sdk_slot": i % 3,
                  "sdk_angle_name": ("beta", "alpha", "gamma")[i % 3]}
        record["channel"] = _record(channel, "index", "manufacturer", source=_SDK_SOURCE,
                                     method="SDK PIN_LIST, RF/LF/LR/RR order")
        record["sdk_direction"] = _record(_SDK_DIRECTIONS[i], "1", "manufacturer", source=_SDK_SOURCE,
                                           method="SDK direction array; not a model-joint sign")
        for field_name, unit in _SERVO_UNITS.items():
            if field_name not in record:
                record[field_name] = _record(None, unit, "unknown", method="Requires target-device calibration; never inferred from model angles")
        servos.append(record)
    width, height = 48, 32
    focal = width / (2 * math.tan(math.pi / 6))
    camera_values = {"width_px": width, "height_px": height, "fx_px": focal, "fy_px": focal,
                     "cx_px": width / 2, "cy_px": height / 2,
                     "distortion_k1_k2_p1_p2_k3": [0.0] * 5,
                     "position_body_m": [0.035, 0.0, 0.04], "rpy_body_rad": [0.0, 0.0, 0.0]}
    profile = {
        "type": PROFILE_TYPE, "version": PROFILE_VERSION, "name": name,
        "model_angle_convention": _CONVENTION, "camera_frame_convention": _CAMERA_FRAME,
        "geometry": geometric, "servos": servos,
        "camera": {key: _record(value, _CAMERA_UNITS[key], method="Ideal pinhole renderer, 60-degree horizontal field of view; not camera calibration") for key, value in camera_values.items()},
        "range_sensor": {key: _record(value, unit, method="Ideal beam parameters; 4 m cap chosen from inconsistent manufacturer 4/5 m documentation") for key, (value, unit) in _RANGE_DEFAULTS.items()},
        "electrical": {key: _record(value, unit, method="Assumed generic 2S battery/Pi-like power model; no measured state of charge") for key, (value, unit) in _ELECTRICAL_DEFAULTS.items()},
        "thermal": {key: _record(value, unit, method="Assumed lumped thermal model and experimental thresholds; not a hardware safety limit") for key, (value, unit) in _THERMAL_DEFAULTS.items()},
    }
    validate_profile(profile)
    return profile


def _keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} must contain exactly {sorted(expected)}")


def _number(value: Any, label: str, *, minimum: float | None = None,
            positive: bool = False, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if positive and value <= 0 or minimum is not None and value < minimum or maximum is not None and value > maximum:
        raise ValueError(f"{label} is outside its allowed range")
    return float(value)


def _validate_record(record: Any, unit: str, label: str, *, allow_unknown: bool = False) -> Any:
    _keys(record, {"value", "unit", "provenance"}, label)
    if record["unit"] != unit:
        raise ValueError(f"{label} unit must be {unit!r}")
    provenance = record["provenance"]
    _keys(provenance, _PROVENANCE_KEYS, f"{label}.provenance")
    kind = provenance["kind"]
    if kind not in {"manufacturer", "assumed", "measured", "unknown"}:
        raise ValueError(f"{label} has an invalid provenance kind")
    if any(not isinstance(provenance[key], str) or not provenance[key].strip() for key in ("source", "method")):
        raise ValueError(f"{label} needs a nonempty source and method")
    if kind == "measured":
        try:
            timestamp = datetime.fromisoformat(provenance["measured_at"])
        except (ValueError, TypeError) as error:
            raise ValueError(f"{label} needs an ISO measurement timestamp") from error
        if timestamp.utcoffset() is None:
            raise ValueError(f"{label} measurement timestamp must include timezone")
    elif provenance["measured_at"] is not None:
        raise ValueError(f"{label} cannot have a measurement timestamp without measured provenance")
    value = record["value"]
    if kind == "unknown":
        if not allow_unknown or value is not None:
            raise ValueError(f"{label} unknown provenance requires an allowed null value")
    elif value is None:
        raise ValueError(f"{label} has no value despite known provenance")
    return value


def _section(profile: dict[str, Any], name: str, units: dict[str, str]) -> dict[str, Any]:
    section = profile[name]
    _keys(section, set(units), name)
    return {key: _validate_record(section[key], unit, f"{name}.{key}") for key, unit in units.items()}


def validate_profile(profile: dict[str, Any]) -> None:
    """Reject invalid versions, units, geometry, wiring or missing provenance.

    Validation establishes a well-formed record, not a claim that measurements
    are accurate or that hardware actuation is safe or authorised.
    """
    _keys(profile, {"type", "version", "name", "model_angle_convention", "camera_frame_convention",
                    "geometry", "servos", "camera", "range_sensor", "electrical", "thermal"}, "profile")
    if profile["type"] != PROFILE_TYPE or type(profile["version"]) is not int or profile["version"] != PROFILE_VERSION:
        raise ValueError("unsupported calibration profile type/version")
    if not isinstance(profile["name"], str) or not profile["name"].strip():
        raise ValueError("profile name must be nonempty")
    if profile["model_angle_convention"] != _CONVENTION or profile["camera_frame_convention"] != _CAMERA_FRAME:
        raise ValueError("unsupported coordinate/angle convention")
    geometry = _section(profile, "geometry", _GEOMETRY_UNITS)
    Geometry(**geometry)

    servos = profile["servos"]
    if not isinstance(servos, list) or len(servos) != 12:
        raise ValueError("profile must describe exactly twelve servo slots")
    seen_slots, seen_channels, seen_model_joints = set(), set(), set()
    for servo in servos:
        _keys(servo, {"leg", "sdk_slot", "sdk_angle_name"} | set(_SERVO_UNITS), "servo")
        if servo["leg"] not in LEG_ORDER or type(servo["sdk_slot"]) is not int or servo["sdk_slot"] not in range(3):
            raise ValueError("invalid leg or SDK servo slot")
        slot = (servo["leg"], servo["sdk_slot"])
        if slot in seen_slots:
            raise ValueError("duplicate leg/SDK slot")
        seen_slots.add(slot)
        if servo["sdk_angle_name"] != ("beta", "alpha", "gamma")[servo["sdk_slot"]]:
            raise ValueError("SDK angle label does not match its documented slot")
        values = {key: _validate_record(servo[key], unit, f"servo.{key}", allow_unknown=key not in {"channel", "sdk_direction"}) for key, unit in _SERVO_UNITS.items()}
        channel = values["channel"]
        if type(channel) is not int or channel not in range(12) or channel in seen_channels:
            raise ValueError("servo channels must be unique integers from 0 to 11")
        seen_channels.add(channel)
        for key in ("sdk_direction", "model_direction"):
            if values[key] is not None and (type(values[key]) is not int or values[key] not in (-1, 1)):
                raise ValueError(f"{key} must be +1 or -1")
        if values["sdk_offset_deg"] is not None:
            _number(values["sdk_offset_deg"], "SDK offset", minimum=-20, maximum=20)
        if values["model_joint"] is not None and values["model_joint"] not in {"yaw", "hip", "knee"}:
            raise ValueError("model_joint must be yaw, hip, knee or unknown")
        if values["model_joint"] is not None:
            assignment = (servo["leg"], values["model_joint"])
            if assignment in seen_model_joints:
                raise ValueError("duplicate model joint assignment for a leg")
            seen_model_joints.add(assignment)
        for key in ("model_zero_offset_rad", "model_minimum_rad", "model_maximum_rad"):
            if values[key] is not None:
                _number(values[key], key)
        lo, hi = values["model_minimum_rad"], values["model_maximum_rad"]
        if lo is not None and hi is not None and lo >= hi:
            raise ValueError("joint minimum must be below maximum")

    camera = _section(profile, "camera", _CAMERA_UNITS)
    for key in ("width_px", "height_px"):
        if type(camera[key]) is not int or camera[key] < 1:
            raise ValueError("camera dimensions must be positive integers")
    for key in ("fx_px", "fy_px"):
        _number(camera[key], key, positive=True)
    _number(camera["cx_px"], "cx_px", minimum=0, maximum=camera["width_px"])
    _number(camera["cy_px"], "cy_px", minimum=0, maximum=camera["height_px"])
    for key, length in (("distortion_k1_k2_p1_p2_k3", 5), ("position_body_m", 3), ("rpy_body_rad", 3)):
        if not isinstance(camera[key], list) or len(camera[key]) != length:
            raise ValueError(f"{key} must be a list of length {length}")
        for value in camera[key]:
            _number(value, key)
    if camera["position_body_m"][2] < 0:
        raise ValueError("camera mount height must not be negative")

    ranging = _section(profile, "range_sensor", {key: unit for key, (_, unit) in _RANGE_DEFAULTS.items()})
    for key, value in ranging.items():
        _number(value, key, minimum=0, maximum=1 if key == "dropout_probability" else None)
    if ranging["minimum_m"] >= ranging["maximum_m"]:
        raise ValueError("range interval must be increasing")

    electrical = _section(profile, "electrical", {key: unit for key, (_, unit) in _ELECTRICAL_DEFAULTS.items()})
    for key, value in electrical.items():
        _number(value, key, minimum=0)
    for key in ("battery_capacity_ah", "battery_voltage_empty_v", "battery_voltage_full_v", "battery_cutoff_voltage_v", "supply_nominal_voltage_v", "supply_undervoltage_v", "regulator_min_input_v", "regulator_efficiency"):
        _number(electrical[key], key, positive=True)
    if not 0 <= electrical["battery_initial_soc"] <= 1 or not 0 < electrical["regulator_efficiency"] <= 1:
        raise ValueError("SOC/efficiency must be fractions in their allowed intervals")
    if not 0 <= electrical["cpu_load"] <= 1 or not 0 <= electrical["hunger_soc_critical"] < electrical["hunger_soc_warning"] <= 1:
        raise ValueError("load and need thresholds must be ordered fractions")
    if not electrical["battery_cutoff_voltage_v"] <= electrical["battery_voltage_empty_v"] < electrical["battery_voltage_full_v"]:
        raise ValueError("battery cutoff/empty/full voltages are not ordered")
    if not electrical["supply_undervoltage_v"] <= electrical["supply_nominal_voltage_v"] <= electrical["regulator_min_input_v"]:
        raise ValueError("regulator/supply voltages are not ordered")

    thermal = _section(profile, "thermal", {key: unit for key, (_, unit) in _THERMAL_DEFAULTS.items()})
    for key, value in thermal.items():
        _number(value, key, minimum=-273.15)
    for key in ("thermal_resistance_c_per_w", "thermal_capacity_j_per_c"):
        _number(thermal[key], key, positive=True)
    if not thermal["temperature_warning_c"] < thermal["temperature_throttle_c"] <= thermal["temperature_critical_c"]:
        raise ValueError("thermal thresholds must be increasing")
    _number(thermal["throttled_dynamic_power_factor"], "throttled_dynamic_power_factor", minimum=0, maximum=1)
    # Also catches non-JSON types added inside a free text record accidentally.
    try:
        json.dumps(profile, allow_nan=False)
    except (ValueError, TypeError) as error:
        raise ValueError("profile is not finite JSON data") from error


def profile_values(profile: dict[str, Any], section: str) -> dict[str, Any]:
    """Return a detached value dictionary for a validated parameter section.

    Electrical and thermal keys use the EnergyConfig field names. Geometry keys
    match Geometry. Camera calibration includes intrinsics/pose and is not a
    drop-in CameraConfig: the current renderer remains an ideal pinhole model.
    """
    validate_profile(profile)
    if section not in {"geometry", "camera", "range_sensor", "electrical", "thermal"}:
        raise ValueError("unknown calibration parameter section")
    return {key: copy.deepcopy(record["value"]) for key, record in profile[section].items()}


def _unique_json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r} in calibration profile")
        result[key] = value
    return result


def load_profile(path: str | Path) -> dict[str, Any]:
    """Read a profile without silently overwriting duplicate keys at any depth."""
    with Path(path).open(encoding="utf-8") as stream:
        profile = json.load(stream, object_pairs_hook=_unique_json_object)
    validate_profile(profile)
    return profile


def _save_json(data: dict[str, Any], path: str | Path, *, overwrite: bool) -> None:
    text = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w" if overwrite else "x", encoding="utf-8") as stream:
        stream.write(text)


def save_profile(profile: dict[str, Any], path: str | Path, *, overwrite: bool = False) -> None:
    validate_profile(profile)
    _save_json(profile, path, overwrite=overwrite)


def main(argv: list[str] | None = None, *, collector: Callable[[], dict[str, Any]] = collect_telemetry) -> int:
    parser = argparse.ArgumentParser(description="PiCrawler calibration records; no servo or GPIO outputs")
    commands = parser.add_subparsers(dest="command", required=True)
    template = commands.add_parser("template", help="write an explicitly uncalibrated profile")
    template.add_argument("--name", default="uncalibrated-picrawler")
    collect = commands.add_parser("collect", help="read available Raspberry Pi telemetry into separate JSON")
    for command in (template, collect):
        command.add_argument("--output", required=True, type=Path)
        command.add_argument("--overwrite", action="store_true", help="replace an existing output file")
    args = parser.parse_args(argv)
    if args.command == "template":
        save_profile(default_profile(args.name), args.output, overwrite=args.overwrite)
    else:
        _save_json(collector(), args.output, overwrite=args.overwrite)
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
