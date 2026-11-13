"""Tables and figures for both papers (``paper/*/register.md``, ADR 0017).

Reads analysis results and workspace logs, writes ``paper/<n-name>/tabellen/<id>.md|.tex``
and ``paper/<n-name>/abbildungen/<id>.pdf|.png`` (paper 1 ``1-portierung``: T2, T3;
paper 2 ``2-hysterese``: T1, T2, A2 to A5). Missing inputs are reported and skipped.
Output carries no timestamps, so a rerun on the same data gives the same files.

Usage:
    python scripts/paper_artifacts.py [--runs runs] [--stage bestaetigung]
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from psi_gw.analysis.workspace_metrics import KINDS, read_log, spells  # noqa: E402

PORT = ROOT / "paper" / "1-portierung"      # paper 1: the port
HYST = ROOT / "paper" / "2-hysterese"       # paper 2: workspace hysteresis
P_LABELS = {
    "P1_exitus_per_1000_cycles": "P1 Exitus per 1,000 cycles",
    "P2_nucleotides_per_100_cycles": "P2 Nucleotides per 100 cycles",
    "P3_locations_discovered": "P3 Locations discovered",
    "P4_manipulation_success_rate": "P4 Manipulation success rate",
    "P5_share_cycles_trial_and_error": "P5 Share of cycles with trial and error",
    "P6_mean_damage_pct": "P6 Mean damage (%)",
}
VERDICT_EN = {
    "signifikant, vorhergesagte Richtung": "supported",
    "signifikant, gegen die Vorhersage": "opposite direction",
    "nicht signifikant": "not significant",
    "nur beschreibend": "descriptive only",
    "nicht auswertbar": "not evaluable",
}
P_SHORT = {
    "P1_exitus_per_1000_cycles": "P1 Exitus/1,000 cycles",
    "P2_nucleotides_per_100_cycles": "P2 Nucleotides/100 cycles",
    "P3_locations_discovered": "P3 Locations",
    "P4_manipulation_success_rate": "P4 Manipulation success",
    "P5_share_cycles_trial_and_error": "P5 Trial and error",
    "P6_mean_damage_pct": "P6 Damage need (%)",
}
COND_COLORS = {"A": "#7f7f7f", "B": "#1f77b4", "C": "#2ca02c", "D": "#ff7f0e", "E": "#d62728"}


def fmt(x, nd: int = 3) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:.{nd}f}"


def pfmt(p) -> str:
    if p is None:
        return ""
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def write_table(paper: Path, tid: str, caption: str, header: list[str], rows: list[list[str]],
                align: str) -> None:
    TAB = paper / "tabellen"
    TAB.mkdir(parents=True, exist_ok=True)
    md = [f"**{tid}.** {caption}", "", "| " + " | ".join(header) + " |",
          "|" + "|".join("---:" if a == "r" else "---" for a in align) + "|"]
    md += ["| " + " | ".join(r) + " |" for r in rows]
    (TAB / f"{tid}.md").write_text("\n".join(md) + "\n")

    def tex(s: str) -> str:
        return (s.replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("%", "\\%")
                .replace("&", "\\&").replace("<", "$<$").replace("−", "$-$").replace("`", ""))
    lines = ["\\begin{table}[t]", "\\centering", f"\\caption{{{tex(caption)}}}", f"\\label{{tab:{tid}}}",
             f"\\begin{{tabular}}{{{align}}}", "\\toprule", " & ".join(tex(h) for h in header) + " \\\\",
             "\\midrule"]
    lines += [" & ".join(tex(c) for c in r) + " \\\\" for r in rows]
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table}"]
    (TAB / f"{tid}.tex").write_text("\n".join(lines) + "\n")
    print(f"{tid}: {(TAB / tid).relative_to(ROOT)}.md/.tex")


# --- tables ---------------------------------------------------------------------------------------


def table_switches() -> None:
    """Paper 1, T2: the artefact switches with the first sentence of their docstring."""
    tree = ast.parse((ROOT / "src" / "psi_gw" / "variant.py").read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Variant")
    rows, last = [], None
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            ann = ast.unparse(node.annotation)
            last = node.target.id if ann == "bool" else None
        elif last and isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            doc = " ".join(node.value.value.split()).replace("``", "`")
            first = re.split(r"(?<!e\.g)\.\s", doc, maxsplit=1)[0].rstrip(".")
            rows.append([last, first + "."])
            last = None
    write_table(PORT, "T2", "Implementation artefacts of the original and the switches that turn them off "
                "(ADR 0015). The modern mode switches all of them off.", ["Switch", "Artefact"], rows, "ll")


def table_modern_vs_reference() -> None:
    """Paper 1, T3: modern against reference mode, paired over seeds, with the means of both modes."""
    src = ROOT / "analysis" / "varianten" / "all-100" / "vergleich.json"
    arms_src = ROOT / "analysis" / "revision" / "paper1.json"
    if not src.exists():
        print(f"T3: {src} missing, skipped")
        return
    d = json.loads(src.read_text())
    arms = json.loads(arms_src.read_text())["arms"] if arms_src.exists() else {}
    units = {
        "P1_exitus_per_1000_cycles": "P1 Deaths per 1,000 cycles",
        "P2_nucleotides_per_100_cycles": "P2 Nucleotides per 100 cycles",
        "P3_locations_discovered": "P3 Locations discovered",
        "P4_manipulation_success_rate": "P4 Manipulation success (share)",
        "P5_share_cycles_trial_and_error": "P5 Trial-and-error cycles (share)",
        "P6_mean_damage_pct": "P6 Damage need (%)",
    }
    rows = []
    for key, label in units.items():
        r = d["metrics"][key]
        a = arms.get(key, {})
        ref = fmt(a["reference"]["mean"]) if a else ""
        mod = fmt(a["modern"]["mean"]) if a else ""
        rows.append([label, ref, mod, fmt(r["mean_diff"]), f"[{fmt(r['ci95_low'])}, {fmt(r['ci95_high'])}]",
                     pfmt(r.get("p_holm"))])
    n = d["metrics"]["P1_exitus_per_1000_cycles"]["n"]
    write_table(PORT, "T3", f"Modern against reference mode over the {n} seeds of 1001 to 1100 in which the "
                "reference life completed. Means per mode; difference modern minus reference, paired by seed, "
                "with pointwise 95% bootstrap interval; p from a sign-flip permutation test, Holm-adjusted "
                "across the six measures.",
                ["Measure", "Reference", "Modern", "Difference", "95% CI", "p (Holm)"], rows, "lrrrlr")


def _tests(stage: str) -> dict | None:
    src = ROOT / "analysis" / "workspace" / stage / "tests.json"
    if not src.exists():
        print(f"tables of paper 2: {src} missing, skipped")
        return None
    return json.loads(src.read_text())


def table_hypotheses(stage: str) -> None:
    """Paper 2, T1: H1 to H6."""
    d = _tests(stage)
    if d is None:
        return
    rows = []
    for name, t in d["tests"].items():
        rows.append([name, t["measure"], f"{t['other']} − {t['base']}", str(t.get("n", 0)),
                     fmt(t.get("mean_diff")), f"[{fmt(t.get('ci95_low'))}, {fmt(t.get('ci95_high'))}]",
                     pfmt(t.get("p_holm")), VERDICT_EN.get(t["verdict"].replace(" (Vorauswahl)", ""), t["verdict"])])
    label = "confirmatory" if stage == "bestaetigung" else "screening, not confirmatory"
    write_table(HYST, "T1", f"Tests of the hysteresis hypothesis ({label}), seeds {d['seeds'][0]} to {d['seeds'][1]}.",
                ["Test", "Measure", "Contrast", "n", "Difference", "95% CI", "p (Holm)", "Verdict"], rows,
                "lllrrlrl")


def table_performance(stage: str) -> None:
    """Paper 2, T2: P1 to P6 for B to E against A."""
    src = ROOT / "analysis" / "workspace" / stage / "leistung.json"
    if not src.exists():
        print(f"T2 (paper 2): {src} missing, skipped")
        return
    d = json.loads(src.read_text())
    rows = []
    for key, label in P_SHORT.items():
        row = [label]
        for c in "BCDE":
            r = d.get(c, {}).get(key)
            row.append("" if r is None else f"{fmt(r['mean_diff'])} ({pfmt(r.get('p_holm'))})")
        rows.append(row)
    write_table(HYST, "T2", "Survival and performance: each workspace condition minus condition A, paired over "
                "seeds; difference (Holm-adjusted p within condition).", ["Measure", "B", "C", "D", "E"],
                rows, "lllll")


# --- figures --------------------------------------------------------------------------------------


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False,
                         "pdf.fonttype": 42, "svg.hashsalt": "psi-gw"})
    return plt


def _save(fig, fid: str, paper: Path = HYST) -> None:
    FIG = paper / "abbildungen"
    FIG.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG / f"{fid}.pdf", metadata={"CreationDate": None, "ModDate": None, "Producer": None,
                                              "Creator": None})
    fig.savefig(FIG / f"{fid}.png", dpi=200, metadata={"Software": None})
    print(f"{fid}: {(FIG / fid).relative_to(ROOT)}.pdf/.png")


def _logs(runs: Path, cond: str, seeds: list[int] | None = None) -> dict[int, tuple[list, dict]]:
    out = {}
    for p in sorted((runs / f"ws-{cond}").glob("seed*/raw/Workspace(1).jsonl")):
        seed = int(p.parent.parent.name[4:])
        if seeds is None or seed in seeds:
            out[seed] = read_log(p)
    return out


def figure_dwell(runs: Path, seeds: list[int]) -> None:
    """A2: dwell time per kind of content and condition (mean per life, distribution over lives)."""
    data = {c: _logs(runs, c, seeds) for c in "BCDE"}
    if not any(data.values()):
        print("A2: no workspace logs, skipped")
        return
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6.5, 2.8))
    width = 0.2
    for j, c in enumerate("BCDE"):
        for i, kind in enumerate(KINDS):
            vals = []
            for records, _ in data[c].values():
                sp = [s["length"] for s in spells(records) if s["kind"] == kind]
                if sp:
                    vals.append(sum(sp) / len(sp))
            if vals:
                bp = ax.boxplot(vals, positions=[i + (j - 1.5) * width], widths=width * 0.8,
                                patch_artist=True, showfliers=False,
                                medianprops={"color": "black", "lw": 1})
                for patch in bp["boxes"]:
                    patch.set_facecolor(COND_COLORS[c])
                    patch.set_alpha(0.7)
    ax.set_xticks(range(len(KINDS)), KINDS)
    ax.set_yscale("log")
    ax.set_ylabel("Mean dwell time per life (cycles)")
    for c in "BCDE":
        ax.plot([], [], color=COND_COLORS[c], lw=6, alpha=0.7, label=c)
    ax.legend(frameon=False, ncol=4, loc="upper right")
    fig.tight_layout()
    _save(fig, "A2")
    plt.close(fig)


def figure_arousal_dwell(runs: Path, seeds: list[int]) -> None:
    """A3: arousal at entry against dwell time, non-motive contents, conditions B and D."""
    plt = _plt()
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.6), sharey=True)
    any_data = False
    for ax, c in zip(axes, "BD"):
        xs, ys = [], []
        for records, _ in _logs(runs, c, seeds).values():
            for s in spells(records):
                if s["kind"] != "motive":
                    xs.append(s["arousal"])
                    ys.append(s["length"])
        if xs:
            any_data = True
            ax.scatter(xs, ys, s=3, alpha=0.25, color=COND_COLORS[c], linewidths=0)
            ax.set_yscale("log")
        ax.set_title(f"Condition {c}")
        ax.set_xlabel("Arousal at entry")
    axes[0].set_ylabel("Dwell time (cycles)")
    if any_data:
        fig.tight_layout()
        _save(fig, "A3")
    else:
        print("A3: no workspace logs, skipped")
    plt.close(fig)


def figure_timeline(runs: Path, seed: int = 1001) -> None:
    """A4: which contents are in the workspace, cycle by cycle, conditions B and E."""
    logs = {c: _logs(runs, c, [seed]).get(seed) for c in "BE"}
    if not all(logs.values()):
        print(f"A4: logs of seed {seed} in B and E missing, skipped")
        return
    plt = _plt()
    fig, axes = plt.subplots(2, 1, figsize=(6.5, 4.2), sharex=True)
    kind_color = {"motive": "#444444", "goal": "#1f77b4", "object": "#ff7f0e", "memory": "#2ca02c",
                  "plan": "#9467bd"}
    for ax, c in zip(axes, "BE"):
        records, _ = logs[c]
        order: dict[str, int] = {}
        for r in records:
            for x in r.get("contents", []):
                order.setdefault(x["name"], len(order))
        for r in records:
            for x in r.get("contents", []):
                ax.plot([r["cycle"] - 0.5, r["cycle"] + 0.5], [order[x["name"]]] * 2,
                        color=kind_color[x["kind"]], lw=1.5, solid_capstyle="butt")
        ax.set_ylabel(f"{c}: content")
        ax.set_yticks([])
    axes[-1].set_xlabel("Cycle")
    for k, col in kind_color.items():
        axes[0].plot([], [], color=col, lw=3, label=k)
    axes[0].legend(frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, 1.25))
    fig.tight_layout()
    _save(fig, "A4")
    plt.close(fig)


def figure_capacity(runs: Path, seed: int = 1001) -> None:
    """A5: capacity K and arousal over one life (condition B)."""
    log = _logs(runs, "B", [seed]).get(seed)
    if not log:
        print(f"A5: log of seed {seed} in B missing, skipped")
        return
    records, _ = log
    plt = _plt()
    fig, ax = plt.subplots(figsize=(6.5, 2.4))
    cyc = [r["cycle"] for r in records if "k" in r]
    ax.step(cyc, [r["k"] for r in records if "k" in r], where="mid", color="#1f77b4", lw=1, label="K")
    ax.set_ylabel("Capacity K")
    ax.set_xlabel("Cycle")
    ax2 = ax.twinx()
    ax2.plot(cyc, [r["arousal"] for r in records if "k" in r], color="#d62728", lw=0.6, alpha=0.7)
    ax2.set_ylabel("Arousal", color="#d62728")
    fig.tight_layout()
    _save(fig, "A5")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=Path, default=ROOT / "runs")
    ap.add_argument("--stage", choices=("vorauswahl", "bestaetigung"), default="bestaetigung")
    args = ap.parse_args()
    seeds = list(range(1001, 1021)) if args.stage == "vorauswahl" else list(range(1001, 1101))
    table_switches()
    table_modern_vs_reference()
    table_hypotheses(args.stage)
    table_performance(args.stage)
    figure_dwell(args.runs, seeds)
    figure_arousal_dwell(args.runs, seeds)
    figure_timeline(args.runs)
    figure_capacity(args.runs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
