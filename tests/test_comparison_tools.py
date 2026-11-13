"""CLI regression tests using controlled evidence and a deterministic life double."""
import gzip
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from comparison_report import compare_sequences
import compare_raw
import compare_life


def test_sequence_lengths_and_context():
    for a, b in [(["a"], ["a", "b"]), (["a", "b"], ["a"])]:
        item = compare_sequences(a, b)
        assert item["status"] == "different"
        assert item["first_difference"] == 2
        assert item["context"][-1]["original"] != item["context"][-1]["port"]
        assert compare_sequences(a, b, prefix=True)["status"] == "prefix"
    assert compare_sequences([], ["x"], prefix=True)["status"] == "different"


@pytest.fixture
def raw_dirs(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(); b.mkdir()
    for name in ["actu1(1).Prt", "seed1.Prt", "IntTimes(1).Txt", "Activities(1).Txt",
                 "eAch(1).Prt", "Inpro(1).Prt", "Consum(1).Prt"]:
        for d in (a, b):
            (d / name).write_bytes(b"same\r\n")
    return a, b


@pytest.mark.parametrize("change,code,status", [
    ("none", 0, "identical"), ("value", 1, "different"),
    ("extra", 1, "different"), ("missing", 2, "error"), ("empty", 2, "error")])
def test_raw_cli(raw_dirs, tmp_path, change, code, status):
    a, b = raw_dirs
    target = b / "Consum(1).Prt"
    if change == "value": target.write_bytes(b"different\r\n")
    if change == "extra": target.write_bytes(b"same\r\nextra\r\n")
    if change == "missing": target.unlink()
    if change == "empty": target.write_bytes(b"")
    report = tmp_path / "report.json"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/compare_raw.py"),
        "--seed", "1", "--original", str(a), "--port", str(b), "--json", str(report)],
        capture_output=True, text=True)
    assert result.returncode == code, result.stderr
    data = json.loads(report.read_text())
    assert data["status"] == status
    assert data["exit_code"] == code
    assert "result:" in result.stdout


def test_raw_masks_only_existing_clock_rules(raw_dirs):
    a, b = raw_dirs
    (a / "actu1(1).Prt").write_bytes("Protokoll für A: yesterday\r\nsame\r\n".encode("cp1252"))
    (b / "actu1(1).Prt").write_bytes("Protokoll für A: today\nsame\n".encode("cp1252"))
    assert compare_raw.main(["--seed", "1", "--original", str(a), "--port", str(b)]) == 0


@pytest.fixture
def evidence(tmp_path):
    protocol = tmp_path / "actu1(1).Prt"
    protocol.write_bytes("Protokoll für test\r\nline\r\n".encode("cp1252"))
    (tmp_path / "Activities(1).Txt").write_bytes(b"action\r\n")
    for name in ("eAch", "Inpro", "Consum"):
        (tmp_path / f"{name}(1).Prt").write_bytes(b"summary\r\n")
    draws = tmp_path / "draws.tsv.gz"
    with gzip.open(draws, "wt") as fh:
        fh.write("site\trandseed\nsite\t42\n")
    return SimpleNamespace(seed=1, scope="full", cycles=1, max_life=1,
                           context=2, protocol=protocol, draws=draws)


class FakeLife:
    def __init__(self, *, ended=True, line="line", activity="action", draw=42, crash=False):
        self.ended = False
        self.should_end = ended
        self.line, self.activity, self.draw, self.crash = line, activity, draw, crash
        self.state = SimpleNamespace(prn=SimpleNamespace(lines=[]), activity_log=[])
        self.rng = SimpleNamespace(log=[])
    def check_max_life(self, max_life):
        if self.state.prn.lines and self.should_end:
            self.ended = True
        return self.ended
    def cycle(self):
        if self.crash: raise RuntimeError("cycle failed")
        self.state.prn.lines.append(self.line)
        self.state.activity_log.append(self.activity)
        self.rng.log.append(SimpleNamespace(site="site", state_before=self.draw))
    def summary_files(self, seed):
        return {n: ["summary"] for n in ("eAch", "Inpro", "Consum")}


def run(args, **kwargs):
    life = FakeLife(**kwargs)
    return compare_life.run_comparison(args, factory=lambda seed: (life, life.rng))


def test_complete_life_includes_final_boundary_and_all_summaries(evidence):
    report = run(evidence)
    assert report["exit_code"] == 0
    assert report["life_ended"] is True
    assert set(report["checks"]) == {"protocol", "activities", "draws", "eAch", "Inpro", "Consum"}


@pytest.mark.parametrize("kwargs,check", [({"line": "wrong"}, "protocol"),
    ({"activity": "wrong"}, "activities"), ({"draw": 43}, "draws")])
def test_life_differences_are_failures(evidence, kwargs, check):
    report = run(evidence, **kwargs)
    assert report["exit_code"] == 1
    assert report["checks"][check]["first_difference"] == 1


@pytest.mark.parametrize("name", ["protocol", "activities", "draws", "eAch", "Inpro", "Consum"])
def test_missing_required_evidence(evidence, name):
    path = {"protocol": evidence.protocol, "activities": evidence.protocol.parent / "Activities(1).Txt",
            "draws": evidence.draws}.get(name, evidence.protocol.parent / f"{name}(1).Prt")
    path.unlink()
    report = run(evidence)
    assert report["exit_code"] == 2
    assert report["checks"][name]["status"] == "missing"


@pytest.mark.parametrize("name", ["protocol", "activities", "draws", "Consum"])
def test_full_life_rejects_length_only_difference(evidence, name):
    if name == "draws":
        with gzip.open(evidence.draws, "at") as fh: fh.write("site\t99\n")
    else:
        path = {"protocol": evidence.protocol, "activities": evidence.protocol.parent / "Activities(1).Txt"}.get(
            name, evidence.protocol.parent / f"{name}(1).Prt")
        with path.open("ab") as fh: fh.write(b"extra\r\n")
    assert run(evidence)["exit_code"] == 1


def test_prefix_and_no_selected_draws_never_claim_complete_equality(evidence):
    evidence.scope = "prefix"
    with evidence.protocol.open("ab") as fh: fh.write(b"later\r\n")
    report = run(evidence, ended=False)
    assert report["exit_code"] == 3
    assert report["checks"]["protocol"]["uncompared_original"] == 1
    assert report["checks"]["summaries"]["status"] == "not_applicable"
    evidence.draws = None
    assert run(evidence, ended=False)["checks"]["draws"]["status"] == "not_requested"


def test_equal_lengths_do_not_prove_life_ended(evidence):
    assert run(evidence, ended=False)["exit_code"] == 3


def test_execution_failure(evidence):
    report = run(evidence, crash=True)
    assert report["exit_code"] == 2
    assert "cycle failed" in report["checks"]["execution"]["error"]


@pytest.mark.parametrize("contents", ["", "bad\theader\n", "site\trandseed\nsite\tbad\n",
    "site\trandseed\nsite\t42\nsite\tinvalid\n"])
def test_invalid_or_empty_trace_is_input_error(evidence, contents):
    with gzip.open(evidence.draws, "wt") as fh: fh.write(contents)
    assert run(evidence)["exit_code"] == 2


def test_corrupt_gzip_is_input_error(evidence):
    evidence.draws.write_bytes(b"not gzip")
    assert run(evidence)["exit_code"] == 2


def test_report_write_failure(raw_dirs):
    a, b = raw_dirs
    assert compare_raw.main(["--seed", "1", "--original", str(a), "--port", str(b),
                             "--json", str(a)]) == 2


def test_life_cli_writes_json_on_missing_input(tmp_path):
    report = tmp_path / "result.json"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/compare_life.py"), "--seed", "1",
        "--protocol", str(tmp_path / "missing"), "--json", str(report)], capture_output=True, text=True)
    assert result.returncode == 2
    assert json.loads(report.read_text())["status"] == "error"


@pytest.mark.parametrize("option,value", [("--cycles", "0"), ("--cycles", "-1"),
                                          ("--context", "-1"), ("--max-life", "-1")])
def test_invalid_cli_limits(option, value):
    with pytest.raises(SystemExit) as exc:
        compare_life.main([option, value])
    assert exc.value.code == 2


def test_report_cannot_overwrite_input(raw_dirs):
    a, b = raw_dirs
    path = a / "Consum(1).Prt"
    original = path.read_bytes()
    assert compare_raw.main(["--seed", "1", "--original", str(a), "--port", str(b),
                             "--json", str(path)]) == 2
    assert path.read_bytes() == original


def test_life_initialization_error_is_reported(evidence):
    def fail(seed):
        raise RuntimeError("initialization failed")
    report = compare_life.run_comparison(evidence, factory=fail)
    assert report["exit_code"] == 2
    assert "initialization failed" in report["checks"]["execution"]["error"]


def test_summary_value_difference(evidence):
    (evidence.protocol.parent / "Inpro(1).Prt").write_bytes(b"wrong\r\n")
    report = run(evidence)
    assert report["exit_code"] == 1
    assert report["checks"]["Inpro"]["status"] == "different"


def test_short_random_archive_does_not_claim_full_coverage(evidence):
    evidence.scope = "prefix"
    evidence.cycles = 2
    report = run(evidence, ended=False)
    assert report["exit_code"] == 3
    assert report["checks"]["draws"]["uncompared_port"] == 1
    assert report["checks"]["draws"]["equal_prefix_count"] == 1


def test_unselected_random_trace_is_reported_for_finished_life(evidence):
    evidence.draws = None
    report = run(evidence)
    assert report["exit_code"] == 3
    assert report["checks"]["draws"]["status"] == "not_requested"


def test_empty_activity_protocol(evidence):
    evidence.protocol.write_bytes(b"")
    assert run(evidence)["exit_code"] == 2


def test_malformed_random_row_with_extra_fields(evidence):
    with gzip.open(evidence.draws, "wt") as fh:
        fh.write("site\trandseed\nsite\t42\textra\n")
    assert run(evidence)["exit_code"] == 2


def test_missing_and_difference_both_remain_in_report(raw_dirs, tmp_path):
    a, b = raw_dirs
    (b / "Consum(1).Prt").write_bytes(b"different\n")
    (a / "eAch(1).Prt").unlink()
    path = tmp_path / "report.json"
    assert compare_raw.main(["--seed", "1", "--original", str(a), "--port", str(b),
                             "--json", str(path)]) == 2
    checks = json.loads(path.read_text())["checks"]
    assert checks["Consum(1).Prt"]["status"] == "different"
    assert checks["eAch(1).Prt"]["status"] == "missing"
