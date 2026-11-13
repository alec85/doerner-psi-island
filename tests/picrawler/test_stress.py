"""Cross-component invariants, reproducibility, failures and resumable matrices."""

import itertools
import json
import subprocess
import sys

import pytest

from psi_gw.body.picrawler import stress
from psi_gw.body.picrawler.stress import Case, run_case, run_matrix
from psi_gw.body.picrawler.validation_io import read_json, write_json


@pytest.mark.parametrize("energy,sensors,link", list(itertools.product(stress.ENERGY, stress.SENSORS, stress.LINKS)))
def test_combined_energy_sensor_transport_invariants(energy, sensors, link):
    result = run_case(Case(42, energy, sensors, link, 32))
    assert result["status"] == "passed", result.get("error")
    assert result["continuation_ticks"] > 0
    assert result["metrics"]["workspace_limited_ticks"] == 0
    if energy in ("empty", "power_limit", "tiny_capacity"):
        assert result["metrics"]["unpowered_ticks"] > 0
    if sensors == "blackout":
        assert result["metrics"]["dropout_ticks"] == result["body_ticks"]
    if energy == "normal":
        assert result["metrics"]["collision_ticks"] > 0


def test_same_seed_case_is_byte_reproducible():
    case = Case(7, "hot", "noisy", "lossy", 40)
    assert run_case(case) == run_case(case)


def test_failure_artifact_preserves_case_actions_and_corrupt_state(monkeypatch):
    original = stress.PiCrawlerSimBody.act

    def corrupt(body, action):
        original(body, action)
        body._readings["telemetry"]["energy_consumed_j"] = float("nan")
    monkeypatch.setattr(stress.PiCrawlerSimBody, "act", corrupt)
    report = run_case(Case(42, "normal", "ideal", "normal", 24))
    assert report["status"] == "failed"
    assert report["trace"][0]["name"] == "led"
    assert "nondecreasing" in report["error"]["message"]
    assert report["last_snapshot"]["readings"]["telemetry"]["energy_consumed_j"] == {"invalid_number": "nan"}
    json.dumps(report, allow_nan=False)


def test_resume_skips_only_valid_successes_and_rejects_changed_plan_or_corruption(tmp_path, monkeypatch):
    cases = [Case(1, "normal", "ideal", "normal", 24)]
    first = run_matrix(tmp_path, cases)
    monkeypatch.setattr(stress, "run_case", lambda case: pytest.fail("successful case was rerun"))
    assert run_matrix(tmp_path, cases, resume=True) == first
    with pytest.raises(ValueError, match="identical"):
        run_matrix(tmp_path, [Case(2, "normal", "ideal", "normal", 24)], resume=True)
    path = tmp_path / "cases" / (cases[0].id + ".json")
    data = read_json(path)
    data["body_ticks"] += 1
    write_json(path, data, replace=True)
    with pytest.raises(ValueError, match="corrupt"):
        run_matrix(tmp_path, cases, resume=True)


def test_resume_rejects_changed_runtime_fingerprint(tmp_path, monkeypatch):
    cases = [Case(0, "empty", "blackout", "normal", 24)]
    run_matrix(tmp_path, cases)
    original = stress.source_info()
    monkeypatch.setattr(stress, "source_info", lambda: {**original, "code_sha256": "changed"})
    with pytest.raises(ValueError, match="identical"):
        run_matrix(tmp_path, cases, resume=True)


def test_failed_cases_are_reexecuted_on_resume(tmp_path, monkeypatch):
    case = Case(0, "normal", "ideal", "normal", 24)
    original = stress.run_case
    original_require = stress.require
    monkeypatch.setattr(stress, "require", lambda c, m: original_require(False, "injected failure"))
    assert run_matrix(tmp_path, [case])["failed"] == [case.id]
    monkeypatch.setattr(stress, "require", original_require)
    assert run_matrix(tmp_path, [case], resume=True)["failed"] == []


def test_cli_runs_from_another_directory_and_refuses_nonempty_output(tmp_path):
    command = [sys.executable, "-m", "psi_gw.body.picrawler.stress", "--output", str(tmp_path / "matrix"),
               "--seeds", "42", "--energy", "normal", "--sensors", "ideal", "--links", "lossy", "--ticks", "24"]
    run = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["passed"] == 1
    rerun = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert rerun.returncode != 0
    resumed = subprocess.run([*command, "--resume"], cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert resumed.returncode == 0, resumed.stderr


@pytest.mark.parametrize("changes", [{"seed": -1}, {"ticks": 2}, {"seed": True}, {"energy": "unknown"}])
def test_invalid_case_configuration_is_rejected(changes):
    with pytest.raises(ValueError):
        Case(**({"seed": 0, "energy": "normal", "sensors": "ideal", "link": "normal"} | changes))
