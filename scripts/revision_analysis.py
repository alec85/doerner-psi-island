"""Post-hoc analyses for the revision of both papers (Issue #45, reviews in PR #44).

Everything here is computed from runs that already exist; nothing is part of the
confirmatory study of ``docs/analyseplan-workspace.md``. Output:
``analysis/revision/paper1.json``, ``analysis/revision/paper2.json`` and a
readable summary ``analysis/revision/README.md`` (German, written by hand from
these files).

Inputs (all archived in the repository, none from ``reference/``; review round 2):

* run traces ``runs/baseline/seed*/*.jsonl.gz`` and ``runs/variant-all/seed*/*.jsonl.gz``
  (extract ``traces/port-runs/2026-11-11-baseline/runs-{referenzmodus,moderner-modus}-1001-1100.tar.gz``
  into ``runs/``),
* workspace logs ``runs/ws-*/seed*/raw/Workspace(1).jsonl`` (``scripts/sync_workspace_runs.py restore``),
* ``analysis/workspace/bestaetigung/kennzahlen.csv``,
* ``analysis/revision/eingangsdaten/`` (actions, motive reports, stalls, guard interventions,
  parameter snapshot; derived once by ``scripts/extract_revision_inputs.py``).

A missing input stops the run with its path. ``scripts/reproduce_revision.sh`` runs the whole
chain in a fresh copy and compares the results.

Usage:
    python scripts/revision_analysis.py [--runs runs] [--out analysis/revision] [--only paper1|paper2]
                                        [--parts late_seeds,signed_rank,...]
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median, stdev

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from psi_gw.analysis.metrics import NUCLEOTIDES_AT_START, PRIMARY, describe, holm, paired_comparison, primary_metrics  # noqa: E402
from psi_gw.analysis.workspace_metrics import read_log, spells  # noqa: E402
from psi_gw.tracing.runfile import read_run  # noqa: E402

SEEDS = range(1001, 1101)
INPUTS = ROOT / "analysis" / "revision" / "eingangsdaten"
PARTS2 = ("late_seeds", "signed_rank", "plans_actions", "windows", "a_compare", "kinds")


def need(path: Path, hint: str = "") -> Path:
    if not path.exists():
        raise SystemExit(f"missing input: {path}" + (f" ({hint})" if hint else ""))
    return path


def read_csv(path: Path) -> list[dict]:
    with need(path, "archived in analysis/revision/eingangsdaten").open() as f:
        return list(csv.DictReader(f))
HYP = [("H1", "W2b_lead_goal_switches_per_100", "E", "B"), ("H2", "W3_plans_aborted_per_100", "E", "B"),
       ("H3", "W5_arousal_dwell_spearman", "D", "B"), ("H4", "W1_dwell_nonmotive", "C", "B"),
       ("H5", "W4_opportunistic_per_100", "E", "B"), ("H6", "W6_share_history_dependent", "E", "B")]


def nan_to_none(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, dict):
        return {k: nan_to_none(v) for k, v in x.items()}
    if isinstance(x, list):
        return [nan_to_none(v) for v in x]
    return x


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sd(xs):
    return stdev(xs) if len(xs) > 1 else math.nan


def summary(xs):
    xs = [x for x in xs if x is not None and not (isinstance(x, float) and math.isnan(x))]
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "mean": mean(xs), "sd": sd(xs), "median": median(xs), "min": min(xs), "max": max(xs)}


def wilcoxon_perm(diffs: list[float], n_perm: int = 10_000, seed: int = 0) -> float:
    """Two-sided signed-rank test by sign-flip permutation of the ranks (robust sensitivity)."""
    d = [x for x in diffs if x != 0 and not math.isnan(x)]
    if not d:
        return 1.0
    order = sorted(range(len(d)), key=lambda i: abs(d[i]))
    ranks = [0.0] * len(d)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and abs(d[order[j + 1]]) == abs(d[order[i]]):
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    w = sum(r for r, x in zip(ranks, d) if x > 0) - sum(r for r, x in zip(ranks, d) if x < 0)
    rng = random.Random(seed)
    count = sum(1 for _ in range(n_perm) if abs(sum(r * rng.choice((1, -1)) for r in ranks)) >= abs(w) - 1e-9)
    return (count + 1) / (n_perm + 1)


# --- paper 1 ----------------------------------------------------------------------------------------


def life_of(run_dir: Path, seed: int, info: dict) -> dict:
    """One life from its archived trace and the extracted counts (``leben-paper1.csv``)."""
    sdir = run_dir / f"seed{seed}"
    trace = next(sdir.glob("*.jsonl.gz"), None)
    if trace is None:
        raise SystemExit(f"missing input: {sdir}/*.jsonl.gz (extract the baseline archives into runs/)")
    if sha256(trace) != info["sha256_trace"]:
        raise SystemExit(f"trace {trace} does not match the hash in leben-paper1.csv")
    run = read_run(trace)
    metrics = {**primary_metrics(run), "cycles": int(info["cycles"]), "age": int(info["age"]),
               "crash": info["crash"]}
    return {"seed": seed, "metrics": metrics, "run": run, "trace_sha256": info["sha256_trace"],
            "variant": info["variant"], "guarded": int(info["guarded"]), "n_actions": int(info["n_actions"]),
            "motive_entries": int(info["motive_entries"]), "nukleo_entries": int(info["nukleo_entries"]),
            "motive_switches": int(info["motive_switches"])}


def window_metrics(run, n: int) -> dict[str, float]:
    """P1, P2 and P6 over the first ``n`` cycles (common observation window of a pair)."""
    cyc = run.cycles[:n]
    last = cyc[-1].counters
    return {"P1_exitus_per_1000_cycles": 1000 * last["exitus"] / n,
            "P2_nucleotides_per_100_cycles": 100 * (last["nucleotides_collected"] - NUCLEOTIDES_AT_START) / n,
            "P6_mean_damage_pct": mean(c.need_pct["damage"] for c in cyc)}


def age_weighted_damage(run) -> float:
    """Mean damage need weighted with the age increment of each cycle (model time instead of cycles)."""
    total = weight = 0.0
    prev = 0.0
    for c in run.cycles:
        dt = c.age - prev
        prev = c.age
        total += c.need_pct["damage"] * dt
        weight += dt
    return total / weight if weight else math.nan


def paper1(runs: Path) -> dict:
    ref_dir, mod_dir = runs / "baseline", runs / "variant-all"
    infos = {(r["mode"], int(r["seed"])): r for r in read_csv(INPUTS / "leben-paper1.csv")}
    manifest, ref, mod = [], {}, {}
    for s in SEEDS:
        for name, d, store in (("reference", ref_dir, ref), ("modern", mod_dir, mod)):
            life = life_of(d, s, infos[(name, s)])
            store[s] = life
            m = life["metrics"]
            manifest.append({"mode": name, "seed": s, "variant": life["variant"],
                             "crash": m.get("crash") or "", "guarded": life["guarded"], "cycles": m["cycles"],
                             "age": m["age"], "trace_sha256": life["trace_sha256"]})
    complete = [s for s in SEEDS if not ref[s]["metrics"].get("crash") and not mod[s]["metrics"].get("crash")]

    def per(store, key):
        return [store[s]["metrics"][key] for s in complete]

    exposure = {}
    for name, store in (("reference", ref), ("modern", mod)):
        lives = [store[s] for s in complete]
        exitus = [life["run"].cycles[-1].counters["exitus"] for life in lives]
        exposure[name] = {
            "cycles": summary([life["metrics"]["cycles"] for life in lives]),
            "exitus_per_life": summary(exitus),
            "age_at_end": summary([life["metrics"]["age"] for life in lives]),
            "age_per_cycle": summary([life["metrics"]["age"] / life["metrics"]["cycles"] for life in lives]),
            "actions_per_life": summary([life["n_actions"] for life in lives]),
            "exitus_per_1000_actions": summary([1000 * e / life["n_actions"] for e, life in zip(exitus, lives)
                                                if life["n_actions"]]),
            "exitus_per_million_age": summary([1e6 * e / life["metrics"]["age"] for e, life in zip(exitus, lives)]),
            "damage_age_weighted": summary([age_weighted_damage(life["run"]) for life in lives]),
        }
    # paired sensitivities on complete pairs
    sens = {}
    for key in ("exitus_per_1000_actions", "exitus_per_million_age", "damage_age_weighted"):
        def val(life, key=key):
            e = life["run"].cycles[-1].counters["exitus"]
            if key == "exitus_per_1000_actions":
                return 1000 * e / life["n_actions"]
            if key == "exitus_per_million_age":
                return 1e6 * e / life["metrics"]["age"]
            return age_weighted_damage(life["run"])
        sens[key] = paired_comparison({s: val(ref[s]) for s in complete}, {s: val(mod[s]) for s in complete})
    window = {k: {} for k in ("P1_exitus_per_1000_cycles", "P2_nucleotides_per_100_cycles", "P6_mean_damage_pct")}
    wref, wmod = {}, {}
    for s in complete:
        n = min(len(ref[s]["run"].cycles), len(mod[s]["run"].cycles))
        wref[s], wmod[s] = window_metrics(ref[s]["run"], n), window_metrics(mod[s]["run"], n)
    for k in window:
        window[k] = paired_comparison({s: wref[s][k] for s in complete}, {s: wmod[s][k] for s in complete})
    arms = {k: {"reference": describe(per(ref, k)), "modern": describe(per(mod, k))} for k in PRIMARY}
    arms["cycles"] = {"reference": describe(per(ref, "cycles")), "modern": describe(per(mod, "cycles"))}
    dominance = {}
    for name, store in (("reference", ref), ("modern", mod)):
        done = [s for s in SEEDS if not store[s]["metrics"].get("crash")]
        shares = [store[s]["nukleo_entries"] / store[s]["motive_entries"] for s in done]
        dominance[name] = {"lives": len(shares), "share_per_life": summary(shares),
                           "pooled_share": sum(store[s]["nukleo_entries"] for s in done)
                           / sum(store[s]["motive_entries"] for s in done),
                           "motive_entries": sum(store[s]["motive_entries"] for s in done),
                           "lives_without_switch": sum(1 for s in done if store[s]["motive_switches"] == 0)}
    params = json.loads(need(INPUTS / "parameter-inseliii.json").read_text())
    flow = {
        "reference": {"seeds": 100, "complete": sum(1 for s in SEEDS if not ref[s]["metrics"].get("crash")),
                      "stalled": {s: ref[s]["metrics"]["crash"] for s in SEEDS if ref[s]["metrics"].get("crash")}},
        "modern": {"seeds": 100, "complete": sum(1 for s in SEEDS if not mod[s]["metrics"].get("crash")),
                   "guard_interventions": {s: mod[s]["guarded"] for s in SEEDS if mod[s]["guarded"]},
                   "variant_lists": dict(Counter(row["variant"] for row in manifest if row["mode"] == "modern"))},
        "complete_pairs": len(complete),
    }
    return {"manifest": manifest, "flow": flow, "arms": arms, "exposure": exposure,
            "exposure_sensitivity_modern_minus_reference": sens,
            "common_window_modern_minus_reference": window, "motive_dominance": dominance,
            "params": params}


# --- paper 2 ----------------------------------------------------------------------------------------


def load_kennzahlen() -> dict[str, dict[int, dict[str, float]]]:
    data: dict[str, dict[int, dict[str, float]]] = {}
    with (ROOT / "analysis/workspace/bestaetigung/kennzahlen.csv").open() as f:
        for row in csv.DictReader(f):
            data.setdefault(row["condition"], {})[int(row["seed"])] = {
                k: (float(v) if v not in ("", "nan") else math.nan) for k, v in row.items()
                if k not in ("condition", "seed")}
    return data


def col(data, cond, key, seeds):
    return {s: data[cond][s][key] for s in seeds if s in data[cond]}


def ws_log(runs: Path, cond: str, seed: int):
    path = runs / f"ws-{cond}" / f"seed{seed}" / "raw" / "Workspace(1).jsonl"
    return read_log(need(path, "scripts/sync_workspace_runs.py restore"))


def spearman(x, y):
    import numpy as np
    if len(x) < 3:
        return math.nan
    def rank(v):
        a = np.asarray(v, float)
        order = a.argsort(kind="mergesort")
        r = np.empty(len(a))
        r[order] = np.arange(len(a), dtype=float)
        for val in np.unique(a):
            idx = np.where(a == val)[0]
            if len(idx) > 1:
                r[idx] = r[idx].mean()
        return r
    rx, ry = rank(x), rank(y)
    if rx.std() == 0 or ry.std() == 0:
        return math.nan
    return float(np.corrcoef(rx, ry)[0, 1])


def spells_with_entry(records):
    """Spells with entry cycle index and a flag for spells still running at the end (right-censored)."""
    out, running = [], {}
    for i, r in enumerate(records):
        present = {c["name"]: c["kind"] for c in r.get("contents", [])}
        for name in list(running):
            if name not in present:
                out.append({**running.pop(name), "censored": False})
        for name, kind in present.items():
            if name in running:
                running[name]["length"] += 1
            else:
                running[name] = {"kind": kind, "name": name, "length": 1, "arousal": r["arousal"], "entry": i}
    out.extend({**v, "censored": True} for v in running.values())
    return out


def paper2(runs: Path, parts=PARTS2) -> dict:
    """Parts can be run separately; each needs only its own inputs."""
    data = load_kennzahlen()
    out: dict = {}
    logs_cache: dict = {}

    def logs_of(c):
        if c not in logs_cache:
            logs_cache[c] = {s: ws_log(runs, c, s) for s in SEEDS}
        return logs_cache[c]

    if "late_seeds" in parts:
        out.update(_late_seeds(data))
    if "signed_rank" in parts:
        out.update(_signed_rank(data))
    if "plans_actions" in parts:
        out.update(_plans_actions(runs, logs_of))
    if "windows" in parts:
        out.update(_windows(logs_of))
    if "a_compare" in parts:
        out.update(_a_compare(runs, data))
    if "kinds" in parts:
        out.update(_kinds(logs_of))
    return out


def _late_seeds(data) -> dict:
    out = {}
    late = list(range(1021, 1101))
    res = {}
    for h, key, base, other in HYP:
        res[h] = paired_comparison(col(data, base, key, late), col(data, other, key, late))
    for h, p in holm({h: r["p"] for h, r in res.items()}).items():
        res[h]["p_holm"] = p
    out["seeds_1021_1100"] = res
    return out


def _signed_rank(data) -> dict:
    """Sensitivity to the weighting of large differences (ranks instead of raw differences).
    Like the sign-flip test it assumes exchangeable signs under the null hypothesis."""
    out = {}
    robust = {}
    for h, key, base, other in HYP:
        b, o = col(data, base, key, SEEDS), col(data, other, key, SEEDS)
        diffs = [o[s] - b[s] for s in sorted(set(b) & set(o)) if not (math.isnan(o[s]) or math.isnan(b[s]))]
        robust[h] = {"n": len(diffs), "median_diff": median(diffs), "p_signed_rank": wilcoxon_perm(diffs)}
    for h, p in holm({h: r["p_signed_rank"] for h, r in robust.items()}).items():
        robust[h]["p_holm"] = p
    out["signed_rank_all_seeds"] = robust
    return out


def _plans_actions(runs, logs_of) -> dict:
    """Failed plans per executed plan; opportunistic satisfactions per 1,000 actions (action
    counts from ``handlungen-paper2.csv``, checked against the hash of the workspace log)."""
    out = {}
    acts = {(r["condition"], int(r["seed"])): r for r in read_csv(INPUTS / "handlungen-paper2.csv")}
    per_plan, per_action = {}, {}
    for cond in "BCDE":
        pp, pa = {}, {}
        for s in SEEDS:
            records, final = logs_of(cond)[s]
            ev = final["events"]
            pp[s] = ev["plans_aborted"] / ev["plans_carried_out"] if ev["plans_carried_out"] else math.nan
            log_path = runs / f"ws-{cond}" / f"seed{s}" / "raw" / "Workspace(1).jsonl"
            if sha256(log_path) != acts[(cond, s)]["sha256_workspace_log"]:
                raise SystemExit(f"{log_path} does not match the hash in handlungen-paper2.csv")
            n_act = int(acts[(cond, s)]["n_actions"])
            pa[s] = 1000 * ev["opportunistic"] / n_act if n_act else math.nan
        per_plan[cond], per_action[cond] = pp, pa
    out["plans_failed_per_executed_plan"] = {c: summary(list(v.values())) for c, v in per_plan.items()}
    out["plans_failed_per_executed_plan_B_minus_E"] = paired_comparison(per_plan["E"], per_plan["B"])
    out["opportunistic_per_1000_actions"] = {c: summary(list(v.values())) for c, v in per_action.items()}
    out["opportunistic_per_1000_actions_B_minus_E"] = paired_comparison(per_action["E"], per_action["B"])
    out["plans_executed_per_100_cycles"] = {
        c: summary([100 * logs_of(c)[s][1]["events"]["plans_carried_out"] / logs_of(c)[s][1]["cycles"]
                    for s in SEEDS]) for c in "BCDE"}
    return out


def _windows(logs_of) -> dict:
    out = {}
    cens, window_w1, window_w5, realized = {}, {c: {} for c in "BCDE"}, {c: {} for c in "BCDE"}, {}
    logs = {c: {s: logs_of(c)[s][0] for s in SEEDS} for c in "BCDE"}
    common = {s: min(len(logs[c][s]) for c in "BCDE") for s in SEEDS}
    cap = 200
    for c in "BCDE":
        all_sp = [sp for s in SEEDS for sp in spells_with_entry(logs[c][s]) if sp["kind"] != "motive"]
        cens[c] = {"spells": len(all_sp), "censored": sum(sp["censored"] for sp in all_sp),
                   "share_censored": sum(sp["censored"] for sp in all_sp) / len(all_sp),
                   "share_of_spell_cycles_censored": sum(sp["length"] for sp in all_sp if sp["censored"])
                   / sum(sp["length"] for sp in all_sp)}
        for s in SEEDS:
            recs = logs[c][s][:common[s]]
            sp = [x for x in spells_with_entry(recs) if x["kind"] != "motive"]
            window_w1[c][s] = mean(x["length"] for x in sp) if sp else math.nan
            # W5 with a fixed observation window per spell: entries at least `cap` cycles before the
            # end, lengths capped at `cap`, so every spell has the same chance to reach the cap
            n = len(logs[c][s])
            sp_full = [x for x in spells_with_entry(logs[c][s]) if x["kind"] != "motive" and x["entry"] <= n - cap]
            window_w5[c][s] = spearman([x["arousal"] for x in sp_full], [min(x["length"], cap) for x in sp_full])
        thr = [r["threshold"] for s in SEEDS for r in logs[c][s]]
        ks = [r["k"] for s in SEEDS for r in logs[c][s] if "k" in r]
        entry_arousal = [x["arousal"] for s in SEEDS for x in spells_with_entry(logs[c][s]) if x["kind"] != "motive"]
        realized[c] = {"threshold_per_cycle": summary(thr), "k_distribution": dict(sorted(Counter(ks).items())),
                       "k": summary(ks), "arousal_at_entry_nonmotive": summary(entry_arousal)}
    out["censoring_nonmotive"] = cens
    out["common_window_cycles"] = summary(list(common.values()))
    out["common_window_W1_nonmotive"] = {
        "means": {c: summary(list(v.values())) for c, v in window_w1.items()},
        "B_minus_C": paired_comparison(window_w1["C"], window_w1["B"]),
        "B_minus_E": paired_comparison(window_w1["E"], window_w1["B"])}
    out["fixed_window_W5"] = {"cap_cycles": cap, "means": {c: summary(list(v.values())) for c, v in window_w5.items()},
                              "B_minus_D": paired_comparison(window_w5["D"], window_w5["B"])}
    out["realized"] = realized
    return out


def _a_compare(runs, data) -> dict:
    out = {}
    first = list(range(1001, 1021))
    a = {}
    for s in first:
        records, final = read_log(need(runs / "ws-A" / f"seed{s}" / "raw" / "Workspace(1).jsonl",
                                       "scripts/sync_workspace_runs.py restore"))
        lead = [r.get("lead_goal") for r in records]
        n = sum(1 for x, y in zip(lead, lead[1:]) if x is not None and y is not None and x != y)
        a[s] = 100 * n / final["cycles"]
    out["W2b_seeds_1001_1020"] = {
        "A": summary(list(a.values())),
        "B": summary([data["B"][s]["W2b_lead_goal_switches_per_100"] for s in first]),
        "E": summary([data["E"][s]["W2b_lead_goal_switches_per_100"] for s in first]),
        "B_minus_A": paired_comparison(a, col(data, "B", "W2b_lead_goal_switches_per_100", first)),
        "E_minus_A": paired_comparison(a, col(data, "E", "W2b_lead_goal_switches_per_100", first))}
    return out


def _kinds(logs_of) -> dict:
    out = {}
    logs = {c: {s: logs_of(c)[s][0] for s in SEEDS} for c in "BCDE"}
    changes, per_kind = {}, {}
    for c in "BCDE":
        n_change = n_spells = 0
        kinds = Counter()
        lives_with = Counter()
        for s in SEEDS:
            seen = set()
            running = {}
            for r in logs[c][s]:
                present = {x["name"]: x["kind"] for x in r.get("contents", [])}
                for name, kind in present.items():
                    if name in running and running[name] != kind:
                        n_change += 1
                    running[name] = kind
                for name in list(running):
                    if name not in present:
                        del running[name]
            for sp in spells(logs[c][s]):
                kinds[sp["kind"]] += 1
                seen.add(sp["kind"])
                n_spells += 1
            lives_with.update(seen)
        changes[c] = {"kind_changes_within_spells": n_change, "spells": n_spells}
        per_kind[c] = {"spells": dict(kinds), "lives_with_kind": dict(lives_with)}
    out["kind_changes"] = changes
    out["spells_per_kind"] = per_kind
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=ROOT / "runs")
    ap.add_argument("--out", type=Path, default=ROOT / "analysis" / "revision")
    ap.add_argument("--only", choices=("paper1", "paper2"))
    ap.add_argument("--parts", default=",".join(PARTS2), help="paper 2 parts: " + ",".join(PARTS2))
    args = ap.parse_args()
    parts = tuple(p for p in args.parts.split(",") if p)
    unknown = set(parts) - set(PARTS2)
    if unknown:
        raise SystemExit(f"unknown parts: {sorted(unknown)}")
    args.out.mkdir(parents=True, exist_ok=True)
    if args.only in (None, "paper1"):
        p1 = paper1(args.runs)
        with (args.out / "laufmanifest-paper1.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(p1["manifest"][0]))
            w.writeheader()
            w.writerows(p1["manifest"])
        p1.pop("manifest")
        (args.out / "paper1.json").write_text(json.dumps(nan_to_none(p1), indent=1, ensure_ascii=False) + "\n")
        print("paper1 done")
    if args.only in (None, "paper2"):
        p2 = paper2(args.runs, parts)
        (args.out / "paper2.json").write_text(json.dumps(nan_to_none(p2), indent=1, ensure_ascii=False) + "\n")
        print("paper2 done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
