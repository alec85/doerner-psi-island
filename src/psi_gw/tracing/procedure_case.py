"""Procedure test cases for exact comparison with the original (ADR 0005, level 1).

A case records which random numbers a procedure drew, the relevant state
before the call, and the expected result and state afterwards.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from psi_gw.tracing.vocabulary import FORMAT_VERSION

INT_RULE = "floor(value*n)"
DEFAULT_REL_TOL = 1e-9


def resolve_path(obj: Any, path: str) -> Any:
    """Resolve a dotted path like ``state.goal_list`` or ``state.needs.hunger.store``."""
    current = obj
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise KeyError(f"path {path!r} not found at {part!r}")
    return current


@dataclass
class ProcedureCase:
    procedure: str
    unit: str
    case_id: str
    random_stream: list[float]
    random_consumed: int
    inputs: dict[str, Any]
    expected: dict[str, Any]
    compare_exact: list[str] = field(default_factory=list)
    compare_approx: list[str] = field(default_factory=list)
    rel_tol: float = DEFAULT_REL_TOL
    harness: dict[str, Any] = field(default_factory=dict)
    format_version: int = FORMAT_VERSION

    def __post_init__(self) -> None:
        if self.format_version != FORMAT_VERSION:
            raise ValueError(f"{self.case_id}: unsupported format_version {self.format_version}")
        if any(not (0.0 <= v < 1.0) for v in self.random_stream):
            raise ValueError(f"{self.case_id}: random values must lie in [0, 1)")
        if not 0 <= self.random_consumed <= len(self.random_stream):
            raise ValueError(f"{self.case_id}: consumed must be between 0 and the stream length")
        for path in self.compare_exact + self.compare_approx:
            resolve_path(self.expected, path)  # raises KeyError if the path is wrong

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": self.format_version,
            "procedure": self.procedure,
            "unit": self.unit,
            "case_id": self.case_id,
            "harness": self.harness,
            "random": {
                "stream": self.random_stream,
                "int_rule": INT_RULE,
                "consumed": self.random_consumed,
            },
            "inputs": self.inputs,
            "expected": self.expected,
            "compare": {
                "exact": self.compare_exact,
                "approx": self.compare_approx,
                "rel_tol": self.rel_tol,
            },
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ProcedureCase:
        required = {"format_version", "procedure", "unit", "case_id", "random",
                    "inputs", "expected", "compare"}
        missing = required - set(data)
        unknown = set(data) - required - {"harness"}
        if missing or unknown:
            raise ValueError(f"procedure case: missing {sorted(missing)}, unknown {sorted(unknown)}")
        random = data["random"]
        if random.get("int_rule") != INT_RULE:
            raise ValueError(f"procedure case: int_rule must be {INT_RULE!r}")
        compare = data["compare"]
        return cls(
            procedure=data["procedure"],
            unit=data["unit"],
            case_id=data["case_id"],
            random_stream=[float(v) for v in random["stream"]],
            random_consumed=int(random["consumed"]),
            inputs=dict(data["inputs"]),
            expected=dict(data["expected"]),
            compare_exact=list(compare.get("exact", [])),
            compare_approx=list(compare.get("approx", [])),
            rel_tol=float(compare.get("rel_tol", DEFAULT_REL_TOL)),
            harness=dict(data.get("harness") or {}),
            format_version=data["format_version"],
        )

    def check(self, actual: Mapping[str, Any], consumed: int) -> list[str]:
        """Compare an actual outcome with the expectation; return a list of mismatches.

        ``actual`` has the same shape as ``expected`` (keys ``result`` and ``state``).
        """
        problems: list[str] = []
        if consumed != self.random_consumed:
            problems.append(f"random draws: expected {self.random_consumed}, got {consumed}")
        for path in self.compare_exact:
            want = resolve_path(self.expected, path)
            try:
                got = resolve_path(actual, path)
            except KeyError:
                problems.append(f"{path}: missing in actual")
                continue
            if got != want:
                problems.append(f"{path}: expected {want!r}, got {got!r}")
        for path in self.compare_approx:
            want = resolve_path(self.expected, path)
            try:
                got = resolve_path(actual, path)
            except KeyError:
                problems.append(f"{path}: missing in actual")
                continue
            if not _close(want, got, self.rel_tol):
                problems.append(f"{path}: expected {want!r}, got {got!r} (rel_tol {self.rel_tol})")
        return problems


def _close(want: Any, got: Any, rel_tol: float) -> bool:
    if isinstance(want, Mapping) and isinstance(got, Mapping):
        return want.keys() == got.keys() and all(_close(want[k], got[k], rel_tol) for k in want)
    if isinstance(want, list) and isinstance(got, list):
        return len(want) == len(got) and all(_close(a, b, rel_tol) for a, b in zip(want, got))
    if isinstance(want, (int, float)) and isinstance(got, (int, float)):
        return math.isclose(want, got, rel_tol=rel_tol, abs_tol=0.0) or want == got
    return want == got


def load_case(path: str | Path) -> ProcedureCase:
    return ProcedureCase.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def save_case(path: str | Path, case: ProcedureCase) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(case.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
