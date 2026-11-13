"""Structural inventory of the Delphi original under reference/delphi-original.

Extracts per unit: line count, uses clauses, declared types, routines,
calls to random sources and unit-level (global) variables. The parser is a
heuristic line/token scanner, good enough for an inventory, not a compiler.

Usage:
    python scripts/delphi_inventory.py [--json out.json] [--root reference/delphi-original]
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

COMMENT_RE = re.compile(r"\{[^}]*\}|\(\*.*?\*\)|//[^\n]*", re.S)
STRING_RE = re.compile(r"'(?:[^']|'')*'")
HEADER_RE = re.compile(r"^\s*(unit|program|library)\s+(\w+)", re.I | re.M)
ROUTINE_RE = re.compile(
    r"^\s*(?:class\s+)?(procedure|function|constructor|destructor)\s+([\w.]+)",
    re.I,
)
TYPE_RE = re.compile(
    r"^\s*(\w+)\s*=\s*(?:packed\s+)?(class|record|object|interface|set\s+of|array|\(|\^|procedure|function|\w+)",
    re.I,
)
RANDOM_RE = re.compile(r"\b(Randomize|RandSeed|RandG|RandomRange|Random)\b", re.I)
OPEN_RE = re.compile(r"\b(begin|case|try|asm|record|object)\b", re.I)
CLASS_OPEN_RE = re.compile(r"=\s*(?:packed\s+)?class\b(?!\s+of\b)(?!\s*;)(?!\s*\([\w\s,]*\)\s*;)", re.I)
END_RE = re.compile(r"\bend\b", re.I)


@dataclass
class Unit:
    path: str
    name: str
    kind: str
    lines: int
    uses_interface: list[str] = field(default_factory=list)
    uses_implementation: list[str] = field(default_factory=list)
    types: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    routines_interface: list[str] = field(default_factory=list)
    routines_implementation: int = 0
    globals_interface: list[str] = field(default_factory=list)
    globals_implementation: list[str] = field(default_factory=list)
    random_calls: list[str] = field(default_factory=list)
    leading_comment: str = ""


def strip(text: str) -> str:
    """Remove comments and string literals, keeping line structure."""
    def blank(m: re.Match) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    text = STRING_RE.sub(blank, text)
    return COMMENT_RE.sub(blank, text)


def parse_uses(clause: str) -> list[str]:
    names = []
    for part in clause.split(","):
        part = part.strip()
        if not part:
            continue
        names.append(re.split(r"\s+in\s+", part, flags=re.I)[0].strip())
    return names


def var_names(line: str) -> list[str]:
    if ":" not in line:
        return []
    left = line.split(":", 1)[0]
    left = re.sub(r"^\s*(var|threadvar)\b", "", left, flags=re.I)
    return [n.strip() for n in left.split(",") if re.fullmatch(r"\s*\w+\s*", n)]


def leading_comment(raw: str) -> str:
    m = re.match(r"\s*(\{.*?\}|\(\*.*?\*\)|(?://[^\n]*\n\s*)+)", raw, re.S)
    if not m:
        return ""
    text = re.sub(r"[{}()*/]", " ", m.group(1))
    return " ".join(text.split())[:300]


def analyse(path: Path, root: Path) -> Unit | None:
    raw = path.read_bytes().decode("cp1252", errors="replace")
    code = strip(raw)
    header = HEADER_RE.search(code)
    if not header:
        return None
    unit = Unit(
        path=str(path.relative_to(root)),
        name=header.group(2),
        kind=header.group(1).lower(),
        lines=raw.count("\n") + 1,
        leading_comment=leading_comment(raw),
    )

    for lineno, line in enumerate(raw.splitlines(), 1):
        if RANDOM_RE.search(strip(line)):
            unit.random_calls.append(f"{lineno}: {line.strip()[:120]}")

    section = "interface" if unit.kind == "unit" else "implementation"
    block = None          # current declaration block: uses/type/var/const
    uses_buf = ""
    depth = 0             # begin/end nesting inside routines and records
    in_routine = False

    for line in code.splitlines():
        low = line.strip().lower()
        if not low:
            continue
        if re.match(r"^implementation\b", low):
            section, block = "implementation", None
            continue
        if re.match(r"^(initialization|finalization)\b", low):
            block = None
            in_routine = True  # treat like a routine body
            continue

        if block == "uses":
            uses_buf += " " + line
            if ";" in line:
                target = unit.uses_interface if section == "interface" else unit.uses_implementation
                target.extend(parse_uses(uses_buf.split(";")[0]))
                block = None
            continue
        if re.match(r"^uses\b", low) and depth == 0:
            uses_buf = re.sub(r"^\s*uses\b", "", line, flags=re.I)
            block = "uses"
            if ";" in line:
                target = unit.uses_interface if section == "interface" else unit.uses_implementation
                target.extend(parse_uses(uses_buf.split(";")[0]))
                block = None
            continue

        routine = ROUTINE_RE.match(line)
        if routine and depth == 0:
            name = routine.group(2)
            if section == "interface" and block != "type":
                unit.routines_interface.append(name)
            elif section == "implementation" and not re.search(r"\bforward\s*;", low):
                unit.routines_implementation += 1
                in_routine = True
            block = None
            continue

        if depth == 0 and re.match(r"^(type|var|threadvar|const|resourcestring)\b", low):
            block = low.split()[0]
            if block == "threadvar":
                block = "var"
            line = re.sub(r"^\s*\w+", "", line)
            low = line.strip().lower()

        opens = len(OPEN_RE.findall(line)) + len(CLASS_OPEN_RE.findall(line))
        closes = len(END_RE.findall(line))

        if depth == 0 and block == "type" and not in_routine:
            t = TYPE_RE.match(line)
            if t:
                unit.types.append(t.group(1))
                if t.group(2).lower() == "class" and CLASS_OPEN_RE.search(line):
                    unit.classes.append(t.group(1))
        if depth == 0 and block == "var" and not in_routine:
            names = var_names(line)
            (unit.globals_interface if section == "interface" else unit.globals_implementation).extend(names)

        depth += opens - closes
        if depth < 0:
            depth = 0
        if depth == 0 and closes and in_routine and re.search(r"\bend\s*;", low):
            in_routine = False
            block = None

    return unit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default="reference/delphi-original")
    parser.add_argument("--json", help="write full inventory as JSON")
    args = parser.parse_args()

    root = Path(args.root)
    units = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() in {".pas", ".dpr"} and path.is_file():
            unit = analyse(path, root)
            if unit:
                units.append(unit)

    if args.json:
        Path(args.json).write_text(json.dumps([asdict(u) for u in units], indent=2, ensure_ascii=False))

    for u in units:
        print(f"{u.path}  [{u.kind} {u.name}, {u.lines} Zeilen, "
              f"{len(u.routines_interface)}+{u.routines_implementation} Routinen, "
              f"{len(u.globals_interface)}+{len(u.globals_implementation)} Globale, "
              f"{len(u.random_calls)} Zufall]")


if __name__ == "__main__":
    main()
