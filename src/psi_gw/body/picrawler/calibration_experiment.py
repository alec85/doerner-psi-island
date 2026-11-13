"""Executable synthetic recovery experiment, never a hardware calibration."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Any

from psi_gw.random_source import NumpySource

from .calibration import default_profile
from .calibration_fit import DATA_TYPE, UNITS, fit_measurements, fitted_profile, import_csv
from .validation_io import canonical, source_info, write_json

TRUTH = {"battery_internal_resistance_ohm": .23,
         "thermal_resistance_c_per_w": 12.0, "thermal_capacity_j_per_c": 18.0,
         "range_offset_m": .012}


def synthetic_datasets(seed: int = 42, *, noisy: bool = True) -> list[dict[str, Any]]:
    rng = NumpySource(seed)
    if type(noisy) is not bool:
        raise ValueError("noisy must be boolean")

    def noise(width: float) -> float:
        return (2 * rng.random(site="picrawler.calibration.synthetic") - 1) * width if noisy else 0.0

    data = []
    for kind in UNITS:
        rows = []
        if kind == "battery_load":
            for i in range(40):
                current, voc = .2 + (i % 10) * .25, 8.1 - (i // 10) * .02
                rows.append({"partition": "train" if i < 25 else "validation",
                    "open_circuit_voltage_v": voc, "current_a": current,
                    "battery_voltage_v": voc - current * TRUTH["battery_internal_resistance_ohm"] + noise(.002)})
        elif kind == "thermal":
            temperature, time_s = 35.0, 0.0
            for i in range(161):
                ambient, power = (25.0 if i < 100 else 28.0), (2.0, 5.0, 0.0, 3.0)[(i // 15) % 4]
                rows.append({"partition": "train" if i < 101 else "validation", "time_s": time_s,
                    "cpu_temperature_c": temperature + noise(.015),
                    "ambient_temperature_c": ambient, "cpu_power_w": power})
                dt = 3.0 + i % 3
                # Independent scalar forward fixture, not advance_energy() or the fitter.
                equilibrium = ambient + power * TRUTH["thermal_resistance_c_per_w"]
                tau = TRUTH["thermal_resistance_c_per_w"] * TRUTH["thermal_capacity_j_per_c"]
                temperature = equilibrium + (temperature - equilibrium) * math.exp(-dt / tau)
                time_s += dt
        else:
            for i in range(80):
                reference = .1 + .2 * (i % 6)
                missing = i % 9 == 0
                rows.append({"partition": "train" if i < 50 else "validation", "reference_m": reference,
                    "distance_m": None if missing else reference + TRUTH["range_offset_m"] + noise(.004)})
        data.append({"type": DATA_TYPE, "version": 1, "kind": kind, "origin": "synthetic",
            "source": f"Independent analytic fixture; seed {seed}",
            "method": "Known forward parameters; bounded uniform observation noise; not device measurements",
            "device": "synthetic-fixture", "recorded_at": "2026-11-11T00:00:00+00:00",
            "units": UNITS[kind].copy(), "samples": rows})
    return data


def run_experiment(output: str | Path, seed: int = 42) -> dict[str, Any]:
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("experiment output must be new or empty")
    output.mkdir(parents=True, exist_ok=True)
    profile, results = default_profile("synthetic-fit-not-hardware"), []
    for data in synthetic_datasets(seed):
        kind = data["kind"]
        csv_path = output / (kind + ".csv")
        with csv_path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=["partition", *UNITS[kind]])
            writer.writeheader()
            writer.writerows(data["samples"])
        imported = import_csv(csv_path, kind=kind, **{k: data[k] for k in
            ("origin", "source", "method", "device", "recorded_at")})
        if imported != data:
            raise AssertionError("CSV round trip differs")
        write_json(output / (kind + ".json"), imported)
        fit = fit_measurements(imported)
        profile = fitted_profile(imported, fit, profile)
        recovered = {key: {"expected": truth, "fitted": fit["parameters"][key],
            "absolute_error": abs(fit["parameters"][key] - truth)} for key, truth in TRUTH.items() if key in fit["parameters"]}
        checks = [abs(v["fitted"] - v["expected"]) <= (.002 if key == "range_offset_m" else .08 * v["expected"])
                  for key, v in recovered.items()]
        validation = fit["scores"]["validation"]
        rmse = validation["rollout_degC"]["rmse"] if kind == "thermal" else (
            validation["corrected_distance_m"]["rmse"] if kind == "range" else validation["rmse"])
        threshold = {"thermal": .15, "range": .006, "battery_load": .005}[kind]
        checks.append(rmse is not None and rmse <= threshold)
        results.append({"kind": kind, "recovery": recovered, "validation_rmse": rmse,
            "validation_rmse_limit": threshold, "passed": all(checks), "scores": fit["scores"]})
        write_json(output / (kind + "-fit.json"), {**fit, "runtime": source_info()})
    write_json(output / "synthetic-profile.json", profile)
    summary = {"type": "psi_gw.picrawler.synthetic_recovery", "version": 1, "seed": seed,
        "origin": "synthetic", "runtime": source_info(), "results": results,
        "passed": all(r["passed"] for r in results),
        "limits": "Predefined engineering checks for synthetic fixtures; no hardware validity or statistical confidence claim."}
    write_json(output / "summary.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--seed", default=42, type=int)
    args = parser.parse_args(argv)
    try:
        report = run_experiment(args.output, args.seed)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(canonical({"passed": report["passed"], "origin": "synthetic", "results": report["results"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
