"""Files from ``reference/`` that the reconstruction needs, one SHA-256 per file (paper 1).

``reference/`` is never published (Alec, 2026-11-12). The manifest lets a reader who has an
own copy of the original distribution check that it is the same material:

    sha256sum -c analysis/revision/eingaben.sha256      # run in the repository root

The hashes are ordinary SHA-256 sums of the file bytes. Writes ``eingaben.csv`` (category,
purpose, path, bytes, sha256; paths shown as Windows-1252) and ``eingaben.sha256``
(``sha256sum`` format with the exact bytes of the file names). A missing file
or directory, or an empty directory, stops the script with an error.

Usage: python scripts/input_manifest.py [--out analysis/revision]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "reference"
# category, purpose, path below reference/ (file or directory)
CATEGORIES = [
    ("parameters", "needed by every Python run: parameters of needs, modulators and memory",
     "delphi-original/PsiCode/PsiDaten/InselIII/Param.Dat"),
    ("world", "needed by every Python run: situations, objects, actions and manipulations of the island",
     "delphi-original/PsiCode/Reality/InselIII"),
    ("bitmaps", "needed by every Python run: object bitmaps read by perception",
     "delphi-runtime/PsiCode/Bitmaps"),
    ("executable", "only for runs of the original under Wine and tests that read the binary",
     "delphi-runtime/PsiCode/Psi.exe"),
]


def files_of(rel: str) -> list[Path]:
    path = REF / rel
    if not path.exists():
        raise SystemExit(f"missing required input: {path}")
    if path.is_file():
        return [path]
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        raise SystemExit(f"required input directory is empty: {path}")
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "analysis" / "revision")
    args = ap.parse_args()
    rows = []
    for category, purpose, rel in CATEGORIES:
        for f in files_of(rel):
            data = f.read_bytes()
            raw = os.fsencode(f.relative_to(ROOT))  # file names of the original are Windows-1252
            rows.append({"category": category, "purpose": purpose, "path": raw.decode("cp1252"),
                         "path_bytes": raw, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / "eingaben.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["category", "purpose", "path", "bytes", "sha256"], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    # sha256sum format with the exact bytes of the file names, so that `sha256sum -c` finds them
    (args.out / "eingaben.sha256").write_bytes(b"".join(r["sha256"].encode() + b"  " + r["path_bytes"] + b"\n"
                                                        for r in rows))
    counts = {c: sum(1 for r in rows if r["category"] == c) for c, _, _ in CATEGORIES}
    print(f"{len(rows)} files: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
