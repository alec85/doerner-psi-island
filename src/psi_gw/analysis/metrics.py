"""Primary metrics P1 to P6 of the analysis plan (``docs/analyseplan-referenzlaeufe.md``).

All metrics are computed from a run file (ADR 0006), so runs of the original
and of the port are evaluated by the same code. Counters in the per-cycle
records are cumulative; the values of the last cycle are the values at the end
of life.
"""

from __future__ import annotations

import math
import random
from statistics import mean, median, stdev

from psi_gw.tracing.runfile import Run

NUCLEOTIDES_AT_START = 5
"""``Leistung[NNukleotide]`` after ``InitPsi``."""

PRIMARY = ("P1_exitus_per_1000_cycles", "P2_nucleotides_per_100_cycles", "P3_locations_discovered",
           "P4_manipulation_success_rate", "P5_share_cycles_trial_and_error", "P6_mean_damage_pct")


def primary_metrics(run: Run) -> dict[str, float]:
    """P1 to P6 for one run (one life)."""
    cycles = run.cycles
    n = len(cycles)
    if n == 0:
        raise ValueError("run without cycles")
    last = cycles[-1].counters
    succ, fail = last["successful_manipulations"], last["unsuccessful_manipulations"]
    with_stage = [c for c in cycles if c.stage_times is not None]
    return {
        "P1_exitus_per_1000_cycles": 1000 * last["exitus"] / n,
        "P2_nucleotides_per_100_cycles": 100 * (last["nucleotides_collected"] - NUCLEOTIDES_AT_START) / n,
        "P3_locations_discovered": float(last["locations_discovered"]),
        "P4_manipulation_success_rate": succ / (succ + fail) if succ + fail else math.nan,
        "P5_share_cycles_trial_and_error": (sum(1 for c in with_stage if c.stage_times["what_could_be_done"] > 0)
                                            / len(with_stage)) if with_stage else math.nan,
        "P6_mean_damage_pct": mean(c.need_pct["damage"] for c in cycles),
    }


def describe(values: list[float], n_boot: int = 10_000, seed: int = 0) -> dict[str, float]:
    """Mean, standard deviation, median, interquartile range and a 95 % bootstrap interval of the mean.

    The bootstrap resamples over seeds (percentile method) with a fixed seed,
    so the report is reproducible.
    """
    xs = sorted(v for v in values if not math.isnan(v))
    k = len(xs)
    if k == 0:
        return {"n": 0}

    def quantile(q: float) -> float:
        pos = (k - 1) * q
        lo, hi = math.floor(pos), math.ceil(pos)
        return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)

    rng = random.Random(seed)
    boot = sorted(mean(rng.choices(xs, k=k)) for _ in range(n_boot)) if k > 1 else [xs[0]]
    return {
        "n": k,
        "mean": mean(xs),
        "sd": stdev(xs) if k > 1 else math.nan,
        "median": median(xs),
        "iqr": quantile(0.75) - quantile(0.25),
        "ci95_low": boot[int(0.025 * (len(boot) - 1))],
        "ci95_high": boot[int(0.975 * (len(boot) - 1))],
    }


def paired_comparison(base: dict[int, float], other: dict[int, float], n_perm: int = 10_000,
                      n_boot: int = 10_000, seed: int = 0) -> dict[str, float]:
    """Paired comparison over seeds: mean difference ``other - base``.

    Returns the mean difference, its 95 % bootstrap interval (percentile) and the
    two-sided p-value of a sign-flip permutation test (exact for up to 16 pairs,
    else Monte Carlo with a fixed seed). Pairs with a missing value are dropped.
    """
    diffs = [other[s] - base[s] for s in sorted(set(base) & set(other))
             if not (math.isnan(base[s]) or math.isnan(other[s]))]
    k = len(diffs)
    if k == 0:
        return {"n": 0}
    observed = abs(mean(diffs))
    rng = random.Random(seed)
    if k <= 16:
        import itertools
        stats = [abs(mean(d * s for d, s in zip(diffs, signs)))
                 for signs in itertools.product((1, -1), repeat=k)]
        p = sum(1 for t in stats if t >= observed - 1e-12) / len(stats)
    else:
        stats = [abs(mean(d * rng.choice((1, -1)) for d in diffs)) for _ in range(n_perm)]
        # Monte Carlo p-value with the observed statistic counted (never exactly 0)
        p = (sum(1 for t in stats if t >= observed - 1e-12) + 1) / (n_perm + 1)
    boot = sorted(mean(rng.choices(diffs, k=k)) for _ in range(n_boot))
    return {"n": k, "mean_diff": mean(diffs), "ci95_low": boot[int(0.025 * (n_boot - 1))],
            "ci95_high": boot[int(0.975 * (n_boot - 1))], "p": p}


def holm(pvalues: dict[str, float]) -> dict[str, float]:
    """Holm-adjusted p-values."""
    items = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(items)
    adjusted: dict[str, float] = {}
    running = 0.0
    for i, (name, p) in enumerate(items):
        running = max(running, min(1.0, (m - i) * p))
        adjusted[name] = running
    return adjusted


def first_divergent_cycle(a: Run, b: Run) -> int | None:
    """Index of the first cycle whose counters, needs or age differ; None if the shorter run is a prefix."""
    for ca, cb in zip(a.cycles, b.cycles):
        if (ca.counters, ca.need_pct, ca.age) != (cb.counters, cb.need_pct, cb.age):
            return ca.cycle
    return None if len(a.cycles) == len(b.cycles) else min(len(a.cycles), len(b.cycles))
