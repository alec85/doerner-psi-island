"""Finite JSON, atomic reports and source fingerprints for local experiments."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import tempfile
from typing import Any

import numpy as np


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: str | Path) -> Any:
    def invalid(token: str) -> None:
        raise ValueError(f"nonfinite JSON number: {token}")
    data = json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique,
                      parse_constant=invalid)
    canonical(data)  # Also catches an overflowing exponent such as 1e999.
    return data


def write_json(path: str | Path, value: Any, *, replace: bool = False) -> None:
    """Publish a complete file atomically; existing output is protected by default."""
    text = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".report-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, path)
        else:
            os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def source_info() -> dict[str, Any]:
    package = Path(__file__).resolve().parent
    files = {"picrawler/" + path.name: hashlib.sha256(path.read_bytes()).hexdigest()
             for path in sorted(package.glob("*.py"))}
    for name, path in (("body/base.py", package.parent / "base.py"),
                       ("random_source.py", package.parent.parent / "random_source.py")):
        files[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=package,
                                  capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = "unavailable"
    return {"revision": revision, "files_sha256": files, "code_sha256": digest(files),
            "python": platform.python_version(), "numpy": np.__version__}
