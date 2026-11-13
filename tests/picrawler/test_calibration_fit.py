"""Known forward fixtures, held-out prediction and malformed measurement rejection."""

import copy
import csv
import json
import math
import subprocess
import sys

import pytest

from psi_gw.body.picrawler.calibration import default_profile, validate_profile
from psi_gw.body.picrawler.calibration_experiment import TRUTH, run_experiment, synthetic_datasets
from psi_gw.body.picrawler.calibration_fit import (
    fit_measurements, fitted_profile, import_csv, validate_measurements,
)
from psi_gw.body.picrawler.validation_io import read_json, write_json


@pytest.mark.parametrize("seed", [0, 1, 42])
@pytest.mark.parametrize("kind", ["battery_load", "thermal", "range"])
def test_recovers_exact_independent_forward_parameters(seed, kind):
    data = next(d for d in synthetic_datasets(seed, noisy=False) if d["kind"] == kind)
    report = fit_measurements(data)
    for key, expected in TRUTH.items():
        if key in report["parameters"]:
            assert report["parameters"][key] == pytest.approx(expected, rel=1e-6, abs=1e-9)
    validation = report["scores"]["validation"]
    metric = validation["rollout_degC"] if kind == "thermal" else (
        validation["corrected_distance_m"] if kind == "range" else validation)
    assert metric["rmse"] < 1e-6


@pytest.mark.parametrize("kind", ["battery_load", "thermal", "range"])
def test_held_out_observations_cannot_change_fitted_parameters(kind):
    data = next(d for d in synthetic_datasets() if d["kind"] == kind)
    baseline = fit_measurements(data)
    altered = copy.deepcopy(data)
    field = {"battery_load": "battery_voltage_v", "thermal": "cpu_temperature_c", "range": "distance_m"}[kind]
    for row in altered["samples"]:
        if row["partition"] == "validation" and row[field] is not None:
            row[field] += 1
    changed = fit_measurements(altered)
    assert changed["parameters"] == baseline["parameters"]
    assert changed["scores"]["validation"] != baseline["scores"]["validation"]
    assert changed["scores"]["train"] == baseline["scores"]["train"]


@pytest.mark.parametrize("kind", ["battery_load", "thermal", "range"])
@pytest.mark.parametrize("origin", ["synthetic", "measured"])
def test_export_keeps_provenance_and_unrelated_values(kind, origin):
    data = next(d for d in synthetic_datasets() if d["kind"] == kind)
    data["origin"] = origin
    base = default_profile()
    original = copy.deepcopy(base)
    report = fit_measurements(data)
    profile = fitted_profile(data, report, base)
    validate_profile(profile)
    assert base == original
    assert profile["servos"] == base["servos"]
    assert profile["geometry"] == base["geometry"]
    section = {"battery_load": "electrical", "thermal": "thermal", "range": "range_sensor"}[kind]
    for key in report["parameters"]:
        if key in profile[section]:
            record = profile[section][key]
            assert record["provenance"]["kind"] == ("assumed" if origin == "synthetic" else "measured")
            assert record["provenance"]["measured_at"] == (None if origin == "synthetic" else data["recorded_at"])
    if kind == "range":
        assert profile["range_sensor"]["noise_half_width_m"] == base["range_sensor"]["noise_half_width_m"]
        assert "range_offset_m" not in profile["range_sensor"]


@pytest.mark.parametrize("change", [
    lambda d: d.update(version=True), lambda d: d.update(origin="assumed"),
    lambda d: d.update(recorded_at="2026-11-11T00:00:00"),
    lambda d: d["units"].update(current_a="mA"),
    lambda d: d["samples"][0].update(current_a=True),
    lambda d: d["samples"][0].update(current_a=-1),
    lambda d: d["samples"][0].update(current_a=math.nan),
    lambda d: d["samples"][0].update(extra=1),
    lambda d: d.update(source=""), lambda d: d.update(samples=[]),
])
def test_rejects_ambiguous_or_invalid_measurement_data(change):
    data = synthetic_datasets()[0]
    change(data)
    with pytest.raises(ValueError):
        fit_measurements(data)


@pytest.mark.parametrize("kind", ["battery_load", "thermal", "range"])
def test_no_train_validation_split_is_rejected(kind):
    data = next(d for d in synthetic_datasets() if d["kind"] == kind)
    for row in data["samples"]:
        row["partition"] = "train"
    with pytest.raises(ValueError, match="held-out"):
        validate_measurements(data)


def test_thermal_boundary_interval_is_not_used_or_reported():
    data = synthetic_datasets()[1]
    report = fit_measurements(data)
    assert report["scores"]["train"]["one_step_degC"]["count"] == 100
    assert report["scores"]["validation"]["one_step_degC"]["count"] == 59
    assert 101 not in {r["sample"] for r in report["comparison"]}


@pytest.mark.parametrize("failure", ["equilibrium", "unpowered", "reversed_time", "constant_current", "no_echo", "one_distance"])
def test_uninformative_or_invalid_experiments_are_rejected(failure):
    battery, thermal, ranging = synthetic_datasets()
    if failure in ("equilibrium", "unpowered", "reversed_time"):
        data = thermal
        if failure == "reversed_time":
            data["samples"][4]["time_s"] = 0
        else:
            for row in data["samples"]:
                if failure == "equilibrium":
                    row["cpu_temperature_c"] = 40
                else:
                    row["cpu_power_w"] = 0
    elif failure == "constant_current":
        data = battery
        for row in data["samples"]:
            row["current_a"] = 1
    else:
        data = ranging
        for row in data["samples"]:
            row["distance_m" if failure == "no_echo" else "reference_m"] = None if failure == "no_echo" else .4
    with pytest.raises(ValueError):
        fit_measurements(data)


@pytest.mark.parametrize("text", ['{"x":1,"x":2}', '{"x":NaN}', '{"x":1e999}'])
def test_json_reader_rejects_duplicates_and_nonfinite_numbers(tmp_path, text):
    path = tmp_path / "input.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        read_json(path)


@pytest.mark.parametrize("header,row", [
    ("partition,current_a,current_a,battery_voltage_v", "train,1,2,7"),
    ("partition,current_a,open_circuit_voltage_v,battery_voltage_v", "train,1,8,7,extra"),
    ("partition,current_a,open_circuit_voltage_v,battery_voltage_v", "train,,8,7"),
])
def test_malformed_csv_is_rejected(tmp_path, header, row):
    path = tmp_path / "input.csv"
    path.write_text(header + "\n" + row + "\n")
    with pytest.raises(ValueError):
        import_csv(path, kind="battery_load", origin="measured", source="test", method="test",
                   device="fixture", recorded_at="2026-11-11T00:00:00+00:00")


def test_atomic_json_write_preserves_existing_output_and_cleans_temporary_file(tmp_path):
    path = tmp_path / "report.json"
    write_json(path, {"old": 1})
    with pytest.raises(FileExistsError):
        write_json(path, {"new": 2})
    assert read_json(path) == {"old": 1}
    assert list(tmp_path.iterdir()) == [path]


def test_cli_import_fit_profile_and_output_collision(tmp_path):
    run_experiment(tmp_path / "fixtures")
    dataset, fit, profile = (tmp_path / name for name in ("import.json", "fit.json", "profile.json"))
    command = [sys.executable, "-m", "psi_gw.body.picrawler.calibration_fit"]
    run = subprocess.run([*command, "import-csv", "--input", str(tmp_path / "fixtures/battery_load.csv"),
        "--output", str(dataset), "--kind", "battery_load", "--origin", "synthetic", "--source", "test fixture",
        "--method", "analytic", "--device", "synthetic", "--recorded-at", "2026-11-11T00:00:00+00:00"],
        cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    args = [*command, "fit", "--input", str(dataset), "--output", str(fit), "--profile-output", str(profile)]
    run = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    assert read_json(fit)["scores"]["validation"]["rmse"] < .005
    validate_profile(read_json(profile))
    # The saved fit report can also be validated and applied through the public API.
    fitted_profile(read_json(dataset), read_json(fit))
    fit.unlink()
    before = profile.read_bytes()
    run = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert run.returncode != 0
    assert not fit.exists() and profile.read_bytes() == before


@pytest.mark.parametrize("seed", [0, 1, 42])
def test_noisy_synthetic_experiment_passes_predefined_recovery_and_heldout_checks(tmp_path, seed):
    summary = run_experiment(tmp_path / str(seed), seed)
    assert summary["passed"]
    assert all(result["passed"] for result in summary["results"])
    profile = read_json(tmp_path / str(seed) / "synthetic-profile.json")
    assert profile["thermal"]["thermal_resistance_c_per_w"]["provenance"]["kind"] == "assumed"
