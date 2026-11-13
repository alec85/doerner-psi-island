"""Shared exact-comparison reports for command-line diagnostics (no simulation code)."""
from __future__ import annotations

import json
from pathlib import Path

EXIT_CODES = {"identical": 0, "different": 1, "error": 2, "partial": 3}


def compare_sequences(original, port, *, prefix=False, context=3):
    """Compare whole sequences; permit a matching common prefix only explicitly."""
    n = min(len(original), len(port))
    differences = [i for i in range(n) if original[i] != port[i]]
    first = differences[0] if differences else (n if len(original) != len(port) else None)
    status = "different" if differences else "identical"
    if not differences and len(original) != len(port):
        status = "prefix" if prefix and n else "different"
    lo = max(0, (first or 0) - context)
    hi = min(max(len(original), len(port)), (first or 0) + context + 1)
    return {
        "status": status,
        "original_count": len(original), "port_count": len(port),
        "compared_count": n, "equal_prefix_count": differences[0] if differences else n,
        "uncompared_original": len(original) - n, "uncompared_port": len(port) - n,
        "differing": len(differences) + (0 if status == "prefix" else abs(len(original) - len(port))),
        "first_difference": first + 1 if first is not None and status == "different" else None,
        "context": [{"index": i + 1,
                     "original": original[i] if i < len(original) else None,
                     "port": port[i] if i < len(port) else None}
                    for i in range(lo, hi)] if first is not None else [],
    }


def finish(report, *, incomplete=False):
    statuses = [item["status"] for item in report["checks"].values()]
    # Errors take precedence; detected differences remain available in every check.
    status = ("error" if any(s in {"missing", "error"} for s in statuses)
              else "different" if "different" in statuses
              else "partial" if incomplete or any(s in {"prefix", "not_requested"} for s in statuses)
              else "identical")
    report.update(format_version=1, status=status, exit_code=EXIT_CODES[status])
    return report


def emit(report, path):
    for name, item in report["checks"].items():
        counts = (f" (original={item['original_count']}, port={item['port_count']}, "
                  f"compared={item['compared_count']})" if "compared_count" in item else "")
        print(f"{name}: {item['status']}{counts}")
        if item.get("first_difference") is not None:
            print(f"  first difference: {item['first_difference']}")
        if "error" in item:
            print(f"  {item['error']}")
        for row in item.get("context", []):
            print(f"  {row['index']}: original={row['original']!r} port={row['port']!r}")
    print(f"result: {report['status']} (exit {report['exit_code']})")
    if path is not None:
        try:
            path = Path(path)
            inputs = {Path(item[key]).resolve() for item in report["checks"].values()
                      for key in ("original_path", "port_path") if key in item}
            if path.resolve() in inputs:
                raise ValueError("JSON output must not overwrite an input protocol")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                            encoding="utf-8")
        except (OSError, ValueError) as exc:
            print(f"report error: {exc}")
            return 2
    return report["exit_code"]


def input_error(exc):
    return {"status": "missing" if isinstance(exc, FileNotFoundError) else "error",
            "error": f"{type(exc).__name__}: {exc}"}
