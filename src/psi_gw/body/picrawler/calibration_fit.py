"""Import SI measurements, fit limited models and evaluate held-out samples.

No hardware access, automatic control or new dependency. Synthetic fits remain
assumptions in the existing calibration profile. See MEASUREMENT-FIT.md.
"""

from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime
import math
from pathlib import Path
from typing import Any

import numpy as np

from .calibration import default_profile, load_profile, validate_profile
from .validation_io import digest, read_json, source_info, write_json

UNITS = {
    "battery_load": {"open_circuit_voltage_v": "V", "current_a": "A", "battery_voltage_v": "V"},
    "thermal": {"time_s": "s", "cpu_temperature_c": "degC", "ambient_temperature_c": "degC", "cpu_power_w": "W"},
    "range": {"reference_m": "m", "distance_m": "m"},
}
DATA_TYPE = "psi_gw.picrawler.measurements"


def _keys(value: Any, names: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != names:
        raise ValueError(f"{label} requires exactly {sorted(names)}")


def _number(value: Any, label: str, minimum: float = 0.0) -> float:
    if type(value) not in (int, float) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"invalid {label}")
    return float(value)


def validate_measurements(data: dict[str, Any]) -> None:
    _keys(data, {"type", "version", "kind", "origin", "source", "method", "device", "recorded_at", "units", "samples"}, "dataset")
    if data["type"] != DATA_TYPE or type(data["version"]) is not int or data["version"] != 1:
        raise ValueError("unsupported measurement type/version")
    if not isinstance(data["kind"], str) or data["kind"] not in UNITS:
        raise ValueError("unsupported measurement kind")
    if data["origin"] not in ("synthetic", "measured"):
        raise ValueError("origin must be synthetic or measured")
    for key in ("source", "method", "device", "recorded_at"):
        if not isinstance(data[key], str) or not data[key].strip():
            raise ValueError(f"{key} must be nonempty")
    try:
        if datetime.fromisoformat(data["recorded_at"]).utcoffset() is None:
            raise ValueError("missing timezone")
    except (ValueError, TypeError) as error:
        raise ValueError("recorded_at needs an ISO timestamp with timezone") from error
    units = UNITS[data["kind"]]
    if data["units"] != units:
        raise ValueError("units must match the documented SI schema")
    samples = data["samples"]
    if not isinstance(samples, list) or len(samples) < 4:
        raise ValueError("at least four samples are required")
    for row in samples:
        _keys(row, {"partition"} | set(units), "sample")
        if row["partition"] not in ("train", "validation"):
            raise ValueError("each sample needs a train/validation partition")
        for name in units:
            value = row[name]
            if name == "distance_m" and value is None:
                continue
            _number(value, name, -273.15 if name.endswith("temperature_c") else 0.0)
        if data["kind"] == "battery_load" and row["open_circuit_voltage_v"] <= 0:
            raise ValueError("open-circuit voltage must be positive")
        if data["kind"] == "range" and row["reference_m"] <= 0:
            raise ValueError("reference distance must be positive")
    if {r["partition"] for r in samples} != {"train", "validation"}:
        raise ValueError("both train and held-out validation samples are required")
    if data["kind"] == "thermal" and any(b["time_s"] <= a["time_s"] for a, b in zip(samples, samples[1:])):
        raise ValueError("thermal times must be strictly increasing")


def import_csv(path: str | Path, *, kind: str, origin: str, source: str, method: str,
               device: str, recorded_at: str) -> dict[str, Any]:
    if kind not in UNITS:
        raise ValueError("unsupported measurement kind")
    with Path(path).open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        expected = {"partition"} | set(UNITS[kind])
        if reader.fieldnames is None or len(reader.fieldnames) != len(expected) or set(reader.fieldnames) != expected:
            raise ValueError(f"CSV columns must be exactly {sorted(expected)}")
        rows = []
        for row in reader:
            if set(row) != expected or any(v is None for v in row.values()):
                raise ValueError("malformed CSV row")
            rows.append({key: value.strip() if key == "partition" else
                         None if key == "distance_m" and not value.strip() else float(value)
                         for key, value in row.items()})
    data = {"type": DATA_TYPE, "version": 1, "kind": kind, "origin": origin,
            "source": source, "method": method, "device": device, "recorded_at": recorded_at,
            "units": UNITS[kind].copy(), "samples": rows}
    validate_measurements(data)
    return data


def _metrics(residuals: list[float] | np.ndarray) -> dict[str, Any]:
    a = np.asarray(residuals, dtype=float)
    if not a.size:
        return {"count": 0, "bias": None, "mae": None, "rmse": None, "maximum_absolute_error": None}
    return {"count": int(a.size), "bias": float(a.mean()), "mae": float(np.abs(a).mean()),
            "rmse": float(np.sqrt(np.mean(a * a))), "maximum_absolute_error": float(np.abs(a).max())}


def _intervals(rows: list[dict[str, Any]], partition: str) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(a, b) for a, b in zip(rows, rows[1:]) if a["partition"] == b["partition"] == partition]


def _thermal_prediction(a: dict[str, Any], dt: float, resistance: float, tau: float,
                        temperature: float | None = None) -> float:
    equilibrium = a["ambient_temperature_c"] + resistance * a["cpu_power_w"]
    start = a["cpu_temperature_c"] if temperature is None else temperature
    return equilibrium + (start - equilibrium) * math.exp(-dt / tau)


def _fit_thermal(rows: list[dict[str, Any]]) -> tuple[dict[str, float], dict[str, Any]]:
    pairs = _intervals(rows, "train")
    if len(pairs) < 4 or not _intervals(rows, "validation"):
        raise ValueError("thermal fitting needs four training intervals and a held-out interval")
    dt = np.array([b["time_s"] - a["time_s"] for a, b in pairs])
    temp = np.array([a["cpu_temperature_c"] for a, _ in pairs])
    ambient = np.array([a["ambient_temperature_c"] for a, _ in pairs])
    power = np.array([a["cpu_power_w"] for a, _ in pairs])
    end = np.array([b["cpu_temperature_c"] for _, b in pairs])
    if max(np.ptp(temp), np.ptp(end)) < .5 or not np.any(power > 0):
        raise ValueError("thermal experiment lacks a useful powered transient")

    def solve(log_tau: float) -> tuple[float, float]:
        tau = math.exp(log_tau)
        alpha = np.exp(-dt / tau)
        x = power * (-np.expm1(-dt / tau))
        z = end - ambient - (temp - ambient) * alpha
        denominator = float(x @ x)
        if denominator <= 1e-20:
            return math.inf, 0.0
        resistance = float(x @ z / denominator)
        if resistance <= 0:
            return math.inf, resistance
        error = z - x * resistance
        return float(error @ error), resistance

    # Profile out R analytically; deterministic bounded search of log(tau).
    grid = np.linspace(math.log(.1), math.log(100_000), 161)
    best = min(range(len(grid)), key=lambda i: solve(float(grid[i]))[0])
    if best in (0, len(grid) - 1) or not math.isfinite(solve(float(grid[best]))[0]):
        raise ValueError("thermal time constant is not identifiable inside 0.1..100000 s")
    lo, hi = float(grid[best - 1]), float(grid[best + 1])
    ratio = (math.sqrt(5) - 1) / 2
    for _ in range(80):
        left, right = hi - ratio * (hi - lo), lo + ratio * (hi - lo)
        if solve(left)[0] < solve(right)[0]:
            hi = right
        else:
            lo = left
    tau = math.exp((lo + hi) / 2)
    _, resistance = solve(math.log(tau))
    # Reject nearly collinear local sensitivities in log(R), log(tau).
    alpha = np.exp(-dt / tau)
    jacobian = np.column_stack((resistance * power * (1 - alpha),
        (temp - ambient - resistance * power) * alpha * dt / tau))
    norms = np.linalg.norm(jacobian, axis=0)
    if min(norms) <= 1e-10:
        raise ValueError("thermal parameters are not independently identifiable")
    singular = np.linalg.svd(jacobian / norms, compute_uv=False)
    condition = float(singular[-1] / singular[0])
    if condition < 1e-4:
        raise ValueError("thermal parameter sensitivities are nearly collinear")
    parameters = {"thermal_resistance_c_per_w": resistance, "thermal_capacity_j_per_c": tau / resistance}
    scores = {}
    for partition in ("train", "validation"):
        intervals = _intervals(rows, partition)
        residuals, rollout = [], []
        previous_end = None
        predicted = None
        for a, b in intervals:
            duration = b["time_s"] - a["time_s"]
            residuals.append(_thermal_prediction(a, duration, resistance, tau) - b["cpu_temperature_c"])
            if previous_end != a["time_s"]:
                predicted = a["cpu_temperature_c"]
            predicted = _thermal_prediction(a, duration, resistance, tau, predicted)
            rollout.append(predicted - b["cpu_temperature_c"])
            previous_end = b["time_s"]
        scores[partition] = {"one_step_degC": _metrics(residuals), "rollout_degC": _metrics(rollout)}
    scores["identifiability_singular_ratio"] = condition
    scores["time_constant_s"] = tau
    return parameters, scores


def fit_measurements(data: dict[str, Any]) -> dict[str, Any]:
    validate_measurements(data)
    rows, kind = data["samples"], data["kind"]
    training = [r for r in rows if r["partition"] == "train"]
    if len(training) < 3:
        raise ValueError("at least three training samples are required")
    if kind == "thermal":
        parameters, scores = _fit_thermal(rows)
    elif kind == "battery_load":
        current = np.array([r["current_a"] for r in training])
        drop = np.array([r["open_circuit_voltage_v"] - r["battery_voltage_v"] for r in training])
        if np.count_nonzero(current > 0) < 2 or np.ptp(current) < .1:
            raise ValueError("battery experiment needs multiple distinct loads")
        resistance = float(current @ drop / (current @ current))
        if resistance < 0:
            raise ValueError("negative fitted battery resistance")
        parameters = {"battery_internal_resistance_ohm": resistance}
        scores = {part: _metrics([r["open_circuit_voltage_v"] - resistance * r["current_a"] - r["battery_voltage_v"]
                                  for r in rows if r["partition"] == part]) for part in ("train", "validation")}
    else:
        valid = [r for r in training if r["distance_m"] is not None]
        if len(valid) < 3 or len({r["reference_m"] for r in valid}) < 2:
            raise ValueError("range fitting needs valid echoes at distinct reference distances")
        errors = np.array([r["distance_m"] - r["reference_m"] for r in valid])
        offset = float(errors.mean())
        parameters = {"range_offset_m": offset, "range_noise_standard_deviation_m": float(errors.std(ddof=1)),
                      "dropout_probability": 1 - len(valid) / len(training)}
        scores = {}
        for part in ("train", "validation"):
            subset = [r for r in rows if r["partition"] == part]
            residuals = [r["distance_m"] - offset - r["reference_m"] for r in subset if r["distance_m"] is not None]
            scores[part] = {"corrected_distance_m": _metrics(residuals), "samples": len(subset),
                            "missing_echoes": len(subset) - len(residuals),
                            "dropout_fraction": 1 - len(residuals) / len(subset)}
        if scores["validation"]["corrected_distance_m"]["count"] == 0:
            raise ValueError("range validation needs at least one valid echo")
    report = {"type": "psi_gw.picrawler.fit", "version": 1, "kind": kind, "origin": data["origin"],
              "dataset_sha256": digest(data), "dataset_metadata": {k: copy.deepcopy(v) for k, v in data.items() if k != "samples"},
              "sample_counts": {part: sum(r["partition"] == part for r in rows) for part in ("train", "validation")},
              "parameters": parameters, "scores": scores,
              "limitations": ["Equal-weight descriptive fit; no confidence intervals or hardware certification.",
                              "Thermal power/ambient inputs are held constant over each interval.",
                              "Synthetic results are assumptions, never hardware measurements."]}
    units = {"battery_internal_resistance_ohm": "ohm", "thermal_resistance_c_per_w": "degC/W",
             "thermal_capacity_j_per_c": "J/degC", "range_offset_m": "m",
             "range_noise_standard_deviation_m": "m", "dropout_probability": "1"}
    report["parameter_units"] = {key: units[key] for key in parameters}
    report["comparison"] = model_comparison(data, parameters)
    # Reject numerical overflow instead of producing an invalid report/profile.
    digest(report)
    return report


def model_comparison(data: dict[str, Any], parameters: dict[str, float]) -> list[dict[str, Any]]:
    """Return measured/predicted pairs; no parameters are fitted here."""
    validate_measurements(data)
    rows, kind = data["samples"], data["kind"]
    comparison = []
    for index, row in enumerate(rows):
        if kind == "thermal":
            if index == 0 or rows[index - 1]["partition"] != row["partition"]:
                continue
            previous = rows[index - 1]
            r = parameters["thermal_resistance_c_per_w"]
            tau = r * parameters["thermal_capacity_j_per_c"]
            predicted = _thermal_prediction(previous, row["time_s"] - previous["time_s"], r, tau)
            observed, unit = row["cpu_temperature_c"], "degC"
        elif kind == "battery_load":
            predicted = row["open_circuit_voltage_v"] - row["current_a"] * parameters["battery_internal_resistance_ohm"]
            observed, unit = row["battery_voltage_v"], "V"
        else:
            predicted = row["reference_m"] + parameters["range_offset_m"]
            observed, unit = row["distance_m"], "m"
        comparison.append({"sample": index, "partition": row["partition"], "unit": unit,
            "observed": observed, "predicted": predicted,
            "residual": predicted - observed if observed is not None else None})
    return comparison


def fitted_profile(data: dict[str, Any], report: dict[str, Any], base: dict[str, Any] | None = None) -> dict[str, Any]:
    """Apply only representable parameters, preserving all unrelated provenance."""
    if {key: value for key, value in report.items() if key != "runtime"} != fit_measurements(data):
        raise ValueError("fit report does not match the supplied dataset")
    profile = copy.deepcopy(base if base is not None else default_profile())
    validate_profile(profile)
    section = {"battery_load": "electrical", "thermal": "thermal", "range": "range_sensor"}[data["kind"]]
    for key, value in report["parameters"].items():
        if key not in profile[section]:
            continue
        record = profile[section][key]
        record["value"] = value
        record["provenance"] = {
            "kind": "assumed" if data["origin"] == "synthetic" else "measured",
            "source": data["source"] + "; dataset SHA256 " + report["dataset_sha256"],
            "method": "Estimated from training samples only: " + data["method"],
            "measured_at": data["recorded_at"] if data["origin"] == "measured" else None,
        }
    validate_profile(profile)
    return profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    imp = commands.add_parser("import-csv")
    imp.add_argument("--input", type=Path, required=True)
    imp.add_argument("--output", type=Path, required=True)
    imp.add_argument("--kind", choices=UNITS, required=True)
    imp.add_argument("--origin", choices=("synthetic", "measured"), required=True)
    for name in ("source", "method", "device", "recorded-at"):
        imp.add_argument("--" + name, required=True)
    fit = commands.add_parser("fit")
    fit.add_argument("--input", type=Path, required=True)
    fit.add_argument("--output", type=Path, required=True)
    fit.add_argument("--base-profile", type=Path)
    fit.add_argument("--profile-output", type=Path)
    args = parser.parse_args(argv)
    try:
        destinations = [args.output]
        if args.command == "fit" and args.profile_output is not None:
            destinations.append(args.profile_output)
        if len({p.resolve() for p in destinations}) != len(destinations) or any(p.exists() for p in destinations):
            raise ValueError("outputs must be distinct new files")
        if args.command == "import-csv":
            data = import_csv(args.input, kind=args.kind, origin=args.origin, source=args.source,
                method=args.method, device=args.device, recorded_at=args.recorded_at)
            write_json(args.output, data)
        else:
            if args.base_profile is not None and args.profile_output is None:
                raise ValueError("--base-profile requires --profile-output")
            data = read_json(args.input)
            report = fit_measurements(data)
            profile = fitted_profile(data, report, load_profile(args.base_profile) if args.base_profile else None) if args.profile_output else None
            report["runtime"] = source_info()
            write_json(args.output, report)
            if profile is not None:
                write_json(args.profile_output, profile)
    except (ValueError, TypeError, OSError, OverflowError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
