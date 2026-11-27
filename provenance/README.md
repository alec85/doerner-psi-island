# Provenance of the commit identifiers cited in the papers

The papers cite short commit identifiers (for example `68bd418` or `c0194b6`). These commits belong to the private development repository from which this public repository was exported. The development repository cannot be made public because its history contains the original Delphi program and data files, which may not be redistributed. Removing them from the history would change every commit identifier.

This folder therefore documents the cited commits so that readers can check what was archived at each stage. The commit times are taken from the development repository and are the author's record; Git timestamps are not independent evidence.

## Contents

| File | What it shows |
|---|---|
| `commits.tsv` | Every commit of the development repository made on 11 November 2026 between 08:00 and 21:00 UTC, plus `c75ea8f` and `ecc08a0`: identifier, time (UTC), commit message and changed files (files under `runs/` omitted). |
| `analysis-plan/analyseplan-workspace_<commit>.md` | The analysis plan of the workspace study (paper 2) as committed in `68bd418` (plan), `b82aca9` (amendment 1), `4cb532d` (amendment 2) and `c0194b6` (amendment 3). The plan is unchanged from `c0194b6` to the screening commit `0d78571`. |
| `diffs/c0194b6_to_v1.0.0.patch` | All changes between the confirmatory code state `c0194b6` and the archived version v1.0.0 in the files that define the workspace, the conditions and the analysis (`src/psi_gw/state.py`, `src/psi_gw/variant.py`, `src/psi_gw/workspace/`, `scripts/workspace_analysis.py`, `docs/analyseplan-workspace.md`). |
| `diffs/c75ea8f_to_v1.0.0.patch` | The same for the state `c75ea8f` used for the additional runs with random tie-breaking. |
| `c75ea8f_src_tests.sha256` | SHA-256 checksums of all 75 files in `src/` and `tests/` at `c75ea8f`, the reconstruction described in paper 1. |

## Checks a reader can run

All 75 files of `src/` and `tests/` at `c75ea8f` are contained unchanged in this repository:

```
sha256sum -c provenance/c75ea8f_src_tests.sha256
```

The confirmatory code can be restored from the archived version by applying the patch in reverse:

```
git apply -R provenance/diffs/c0194b6_to_v1.0.0.patch
```

The analysis plan as it stood at each commit can be compared with `diff`, for example:

```
diff provenance/analysis-plan/analyseplan-workspace_68bd418.md provenance/analysis-plan/analyseplan-workspace_c0194b6.md
```

## Statements in paper 2 and how they relate to this record

- Between `c0194b6` (10:12 UTC) and the confirmatory analysis `523588f` (19:56 UTC), the files in `src/`, the analysis plan and `scripts/workspace_analysis.py` are identical on the line of history that leads to the confirmatory analysis. The 20 commits on that line in this interval add the screening results, the finished lives, notes in the hand-over file and two helper scripts for storing runs (`scripts/sync_workspace_runs.py`, `scripts/paper_artifacts.py`); none of them changes the agent, the plan or the analysis script.
- `commits.tsv` also lists commits made in the same interval on a parallel branch. They changed only modules of the PiCrawler robot (`src/psi_gw/body/picrawler/`), which the island agent does not use, and are not part of the history of the confirmatory analysis.
- On 27 November 2026, the reproduction script `scripts/reproduce_revision.sh` was run in a fresh clone of the archived version v1.0.0 without the original program files. It reproduced all values of both papers (2,027 values, no differences).
