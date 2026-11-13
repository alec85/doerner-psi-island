"""Workspace measures W1 to W6 (``docs/analyseplan-workspace.md``).

Computed from the per-cycle log ``Workspace(1).jsonl`` that ``IslandLife``
writes (one record per cycle, a final record with the event counters).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

KINDS = ("motive", "goal", "object", "memory", "plan")
WORKSPACE = ("W1_dwell_all", "W1_dwell_nonmotive", *(f"W1_dwell_{k}" for k in KINDS),
             "W2_motive_switches_per_100", "W2b_lead_goal_switches_per_100", "W3_plans_aborted_per_100", "W4_opportunistic_per_100",
             "W5_arousal_dwell_spearman", "W6_share_history_dependent")


def read_log(path: Path) -> tuple[list[dict], dict]:
    records, final = [], {}
    for line in path.read_bytes().decode("cp1252").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("final"):
            final = r
        else:
            records.append(r)
    return records, final


def spells(records: list[dict]) -> list[dict]:
    """Uninterrupted stays of a content (neuron) in the workspace: kind at entry, name,
    length, arousal at entry. A content may change its kind during a stay (a goal
    becomes the goal of a plan); the stay goes on.

    A stay still running at the end of life counts with its length so far.
    """
    out: list[dict] = []
    running: dict[str, dict] = {}
    for r in records:
        present = {c["name"]: c["kind"] for c in r.get("contents", [])}
        for name in list(running):
            if name not in present:
                out.append(running.pop(name))
        for name, kind in present.items():
            if name in running:
                running[name]["length"] += 1
            else:
                running[name] = {"kind": kind, "name": name, "length": 1, "arousal": r["arousal"]}
    out.extend(running.values())
    return out


def lead_goal_switches(records: list[dict]) -> int:
    """Changes of the leading goal (first entry of the goal list after the broadcast)
    between two consecutive cycles, both with a goal (Nachtrag 1 of the analysis plan)."""
    n = 0
    for prev, cur in zip(records, records[1:]):
        a, b = prev.get("lead_goal"), cur.get("lead_goal")
        if a is not None and b is not None and a != b:
            n += 1
    return n


def _spearman(x: list[float], y: list[float]) -> float:
    if len(x) < 3:
        return math.nan
    def ranks(v):
        a = np.asarray(v, dtype=float)
        order = a.argsort(kind="mergesort")
        rk = np.empty(len(a))
        rk[order] = np.arange(len(a), dtype=float)
        # average ranks for ties
        for val in np.unique(a):
            idx = np.where(a == val)[0]
            if len(idx) > 1:
                rk[idx] = rk[idx].mean()
        return rk
    rx, ry = ranks(x), ranks(y)
    if rx.std() == 0 or ry.std() == 0:
        return math.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def workspace_metrics(path: Path) -> dict[str, float]:
    records, final = read_log(path)
    cycles = final.get("cycles", len(records)) or len(records)
    events = final.get("events") or (records[-1].get("events", {}) if records else {})
    sp = spells(records)
    nonmotive = [s for s in sp if s["kind"] != "motive"]

    def mean_len(items):
        return float(np.mean([s["length"] for s in items])) if items else math.nan

    out = {
        "W1_dwell_all": mean_len(sp),
        "W1_dwell_nonmotive": mean_len(nonmotive),
        **{f"W1_dwell_{k}": mean_len([s for s in sp if s["kind"] == k]) for k in KINDS},
        "W2_motive_switches_per_100": 100 * events.get("motive_switches", 0) / cycles,
        "W2b_lead_goal_switches_per_100": 100 * lead_goal_switches(records) / cycles,
        "W3_plans_aborted_per_100": 100 * events.get("plans_aborted", 0) / cycles,
        "W4_opportunistic_per_100": 100 * events.get("opportunistic", 0) / cycles,
        "W5_arousal_dwell_spearman": _spearman([s["arousal"] for s in nonmotive], [s["length"] for s in nonmotive]),
        "W6_share_history_dependent": (float(np.mean([bool(r.get("differs_from_memoryless")) for r in records
                                                      if "contents" in r]))
                                       if any("contents" in r for r in records) else math.nan),
    }
    return out
