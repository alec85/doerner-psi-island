"""Calibration provenance, versioning and safe read-only CLI behaviour."""

import copy
from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from psi_gw.body.picrawler.calibration import (
    default_profile,
    load_profile,
    main,
    profile_values,
    save_profile,
    validate_profile,
)
from psi_gw.body.picrawler.energy import EnergyConfig
from psi_gw.body.picrawler.kinematics import Geometry, LEG_ORDER


def measured(record, value):
    record["value"] = value
    record["provenance"] = {
        "kind": "measured", "source": "bench-notebook-2026-11-10",
        "method": "Repeated direct bench measurement", "measured_at": "2026-11-10T13:00:00+01:00",
    }


def test_template_is_json_compatible_and_never_claims_measured_defaults():
    profile = default_profile()
    validate_profile(profile)
    assert profile["version"] == 1
    assert json.loads(json.dumps(profile, allow_nan=False)) == profile
    for name in ("electrical", "thermal", "camera", "range_sensor"):
        assert all(record["provenance"]["kind"] == "assumed" for record in profile[name].values())
    assert profile["geometry"]["coxa_m"]["provenance"]["kind"] == "manufacturer"
    assert all(servo["sdk_offset_deg"]["value"] is None for servo in profile["servos"])
    assert all(servo["model_joint"]["provenance"]["kind"] == "unknown" for servo in profile["servos"])
    assert all(servo["model_zero_offset_rad"]["value"] is None for servo in profile["servos"])


def test_default_values_match_geometry_and_energy_config_without_new_defaults():
    profile = default_profile()
    assert Geometry(**profile_values(profile, "geometry")) == Geometry()
    electrical = profile_values(profile, "electrical")
    thermal = profile_values(profile, "thermal")
    expected_keys = set(asdict(EnergyConfig())) - {"enabled"}
    assert set(electrical) | set(thermal) == expected_keys
    assert not set(electrical) & set(thermal)
    assert EnergyConfig(**electrical, **thermal) == EnergyConfig()


def test_sdk_wiring_and_directions_are_explicit_but_not_pwm_transformations():
    servos = default_profile()["servos"]
    assert [servo["leg"] for servo in servos] == [leg for leg in LEG_ORDER for _ in range(3)]
    assert [servo["channel"]["value"] for servo in servos] == [9, 10, 11, 3, 4, 5, 0, 1, 2, 6, 7, 8]
    assert [servo["sdk_direction"]["value"] for servo in servos] == [1, 1, -1, 1, 1, 1, 1, 1, -1, 1, 1, 1]
    assert [servo["sdk_angle_name"] for servo in servos[:3]] == ["beta", "alpha", "gamma"]
    assert all(servo["model_direction"]["value"] is None for servo in servos)


def test_profiles_and_extracted_values_are_not_aliased():
    first, second = default_profile(), default_profile()
    first["geometry"]["upper_m"]["value"] = 0.049
    first["servos"][0]["sdk_offset_deg"]["provenance"]["method"] = "different"
    assert second == default_profile()
    values = profile_values(second, "camera")
    values["position_body_m"][0] = 999
    assert second["camera"]["position_body_m"]["value"][0] == 0.035


def test_measured_values_have_method_source_and_timezone_and_survive_json(tmp_path):
    profile = default_profile("measured-prototype-01")
    measured(profile["electrical"]["battery_voltage_full_v"], 8.32)
    measured(profile["servos"][0]["sdk_offset_deg"], 1.4)
    validate_profile(profile)
    path = tmp_path / "calibration" / "profile.json"
    save_profile(profile, path)
    assert load_profile(path) == profile
    assert profile_values(load_profile(path), "electrical")["battery_voltage_full_v"] == 8.32


@pytest.mark.parametrize("original,ambiguous", [
    ('"version": 1', '"version": 999, "version": 1'),
    ('"value": 0.033', '"value": -1, "value": 0.033'),
    ('"kind": "manufacturer"', '"kind": "measured", "kind": "manufacturer"'),
])
def test_duplicate_json_keys_cannot_hide_invalid_version_value_or_provenance(tmp_path, original, ambiguous):
    profile = default_profile()
    text = json.dumps(profile)
    assert original in text
    text = text.replace(original, ambiguous, 1)
    # A last-key-wins loader would silently turn each conflicting file into a valid profile.
    assert json.loads(text) == profile
    path = tmp_path / "ambiguous-profile.json"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_profile(path)


@pytest.mark.parametrize("timestamp", [None, "2026-11-10", "2026-11-10T12:00:00", "not a date", 0])
def test_measured_provenance_requires_an_explicit_time_with_timezone(timestamp):
    profile = default_profile()
    record = profile["geometry"]["upper_m"]
    measured(record, 0.0482)
    record["provenance"]["measured_at"] = timestamp
    with pytest.raises(ValueError, match="timestamp"):
        validate_profile(profile)


@pytest.mark.parametrize("change", [
    "version", "bool_version", "missing_section", "extra_section", "missing_provenance",
    "unknown_source", "empty_method", "wrong_unit", "negative_geometry", "nan_geometry",
    "null_known", "unmeasured_timestamp", "unknown_with_value", "frame_convention",
])
def test_schema_and_provenance_errors_are_rejected(change):
    profile = default_profile()
    record = profile["geometry"]["upper_m"]
    if change == "version":
        profile["version"] = 2
    elif change == "bool_version":
        profile["version"] = True
    elif change == "missing_section":
        profile.pop("camera")
    elif change == "extra_section":
        profile["secret_extra"] = {}
    elif change == "missing_provenance":
        record.pop("provenance")
    elif change == "unknown_source":
        record["provenance"]["source"] = ""
    elif change == "empty_method":
        record["provenance"]["method"] = ""
    elif change == "wrong_unit":
        record["unit"] = "mm"
    elif change == "negative_geometry":
        record["value"] = -0.048
    elif change == "nan_geometry":
        record["value"] = float("nan")
    elif change == "null_known":
        record["value"] = None
    elif change == "unmeasured_timestamp":
        record["provenance"]["measured_at"] = "2026-11-10T12:00:00Z"
    elif change == "unknown_with_value":
        profile["servos"][0]["sdk_offset_deg"]["value"] = 0
    elif change == "frame_convention":
        profile["model_angle_convention"] = "SDK PWM degrees"
    with pytest.raises(ValueError):
        validate_profile(profile)


@pytest.mark.parametrize("change", ["count", "channel_duplicate", "channel_out_of_range", "slot_duplicate", "direction", "sdk_label", "unknown_joint", "model_joint_duplicate", "offset", "limits"])
def test_invalid_servo_maps_cannot_be_loaded(change):
    profile = default_profile()
    servos = profile["servos"]
    if change == "count":
        servos.pop()
    elif change == "channel_duplicate":
        servos[1]["channel"]["value"] = servos[0]["channel"]["value"]
    elif change == "channel_out_of_range":
        servos[0]["channel"]["value"] = 12
    elif change == "slot_duplicate":
        servos[1]["sdk_slot"] = 0
    elif change == "direction":
        servos[0]["sdk_direction"]["value"] = 0
    elif change == "sdk_label":
        servos[0]["sdk_angle_name"] = "alpha"
    elif change == "unknown_joint":
        measured(servos[0]["model_joint"], "shoulder")
    elif change == "model_joint_duplicate":
        measured(servos[0]["model_joint"], "hip")
        measured(servos[1]["model_joint"], "hip")
    elif change == "offset":
        measured(servos[0]["sdk_offset_deg"], 21)
    elif change == "limits":
        measured(servos[0]["model_minimum_rad"], 0.5)
        measured(servos[0]["model_maximum_rad"], -0.5)
    with pytest.raises(ValueError):
        validate_profile(profile)


@pytest.mark.parametrize(("section", "field", "value"), [
    ("camera", "fx_px", 0), ("camera", "width_px", 48.5),
    ("camera", "cx_px", 100), ("camera", "distortion_k1_k2_p1_p2_k3", [0] * 4),
    ("camera", "position_body_m", [0.035, 0, -0.1]),
    ("camera", "rpy_body_rad", [0, float("inf"), 0]),
    ("range_sensor", "dropout_probability", 1.1), ("range_sensor", "maximum_m", 0.01),
    ("electrical", "battery_capacity_ah", 0), ("electrical", "regulator_efficiency", 1.1),
    ("electrical", "battery_initial_soc", -0.1), ("electrical", "battery_voltage_full_v", 5),
    ("electrical", "battery_internal_resistance_ohm", -0.1),
    ("electrical", "supply_undervoltage_v", 6), ("electrical", "cpu_load", 2),
    ("electrical", "hunger_soc_critical", 0.5),
    ("thermal", "thermal_capacity_j_per_c", 0), ("thermal", "ambient_temperature_c", -274),
    ("thermal", "temperature_throttle_c", 90), ("thermal", "throttled_dynamic_power_factor", 2),
])
def test_numeric_camera_electrical_and_thermal_constraints(section, field, value):
    profile = default_profile()
    profile[section][field]["value"] = value
    with pytest.raises(ValueError):
        validate_profile(profile)


def test_existing_file_is_not_overwritten_without_explicit_option(tmp_path):
    path = tmp_path / "profile.json"
    first = default_profile("first")
    save_profile(first, path)
    with pytest.raises(FileExistsError):
        save_profile(default_profile("second"), path)
    assert load_profile(path) == first
    save_profile(default_profile("second"), path, overwrite=True)
    assert load_profile(path)["name"] == "second"


def test_invalid_profile_is_rejected_before_creating_an_output(tmp_path):
    path = tmp_path / "profile.json"
    profile = default_profile()
    profile["version"] = 100
    with pytest.raises(ValueError):
        save_profile(profile, path)
    assert not path.exists()


def test_template_cli_does_not_call_hardware_collector(tmp_path, capsys):
    def forbidden():
        raise AssertionError("template must not collect telemetry")

    path = tmp_path / "template.json"
    assert main(["template", "--name", "bench", "--output", str(path)], collector=forbidden) == 0
    assert load_profile(path)["name"] == "bench"
    assert str(path) in capsys.readouterr().out


def test_collect_cli_writes_the_actual_collection_without_profile_assumptions(tmp_path):
    from psi_gw.body.picrawler.telemetry import collect_telemetry

    def absent_file(path):
        raise FileNotFoundError(path)

    def forbidden_command(command):
        raise AssertionError("non-Pi collection must not issue commands")

    result = collect_telemetry(read_text=absent_file, run_command=forbidden_command,
                               observed_at="2026-11-10T12:00:00Z")
    calls = []

    def collector():
        calls.append(1)
        return copy.deepcopy(result)

    path = tmp_path / "telemetry.json"
    main(["collect", "--output", str(path)], collector=collector)
    data = json.loads(path.read_text())
    assert data == result
    assert calls == [1]
    assert data["measurements"]["battery_voltage_v"]["value"] is None
    assert data["measurements"]["cpu_temperature_c"]["value"] is None
    assert data["measurements"]["battery_state_of_charge"]["value"] is None
    assert "electrical" not in data


def test_module_cli_can_create_a_profile_in_a_fresh_process(tmp_path):
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(str(Path(path).resolve()) for path in sys.path if path)
    path = tmp_path / "fresh-profile.json"
    subprocess.run([sys.executable, "-m", "psi_gw.body.picrawler.calibration", "template",
                    "--output", str(path)], cwd=tmp_path, env=env, capture_output=True,
                   text=True, check=True, timeout=30)
    assert load_profile(path) == default_profile()
