# doerner-psi-island

A reconstruction in Python of Dietrich Dörner's PSI island agent (Delphi program, version 4.9.1.200, 2003), validated against the original program running under Wine, and an extension of the agent by a limited-capacity workspace.

This repository accompanies two papers:

1. Sproten, A. *Reconstructing Dörner's 2003 PSI island agent: trace-level validation and implementation-dependent behaviour.* Preprint, PsyArXiv, DOI to be added. Manuscript: `paper/1-portierung/`.
2. Sproten, A. *Generalising Dörner's selection threshold to a limited-capacity workspace: an incumbency bonus makes contents history-dependent in a PSI island agent.* Preprint, PsyArXiv, DOI to be added. Manuscript: `paper/2-hysterese/`.

Project documentation (decision records, analysis plans, notes) is written in German; code, docstrings and the papers are in English.

The repository also contains work in progress that is not part of the two papers: a simulation of the SunFounder PiCrawler robot driven by the agent (`src/psi_gw/body/picrawler/`, `docs/picrawler/`, optional MuJoCo backend via `pip install -e ".[mujoco]"`) and an offline viewer for run traces (`docs/trace-viewer.md`).

## What is included, and what is not

Included: the reconstruction (`src/psi_gw/`), its tests (`tests/`), the analysis and reproduction scripts (`scripts/`), the archived runs of the reconstruction (`traces/port-runs/`), the protocols of all runs of the original program that the papers compare (`traces/original-runs/`), the analysis plans and their amendments (`docs/`), and all analysis results (`analysis/`).

Not included: the original Delphi source code, the executable and its data files (parameter file, world files, bitmaps). They are not ours to publish. `analysis/revision/eingaben.sha256` lists the 274 files of the original distribution that the reconstruction reads, with their SHA-256 sums, so that anyone with a copy can verify it with `sha256sum -c`. Place such a copy under `reference/`, with the paths listed in `analysis/revision/eingaben.csv`, to run new lives.

## Installation

Python 3.12 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,paper]"
```

## Reproducing the papers

Every number, table and figure in both papers can be recomputed from the archived data, without the original program:

```bash
scripts/reproduce_revision.sh /tmp/reproduction
```

The script verifies the archives against their checksums, restores the runs, recomputes all analyses and tables, and compares every value with the committed results. It takes about three minutes.

## Tests

```bash
pytest
```

Without the files of the original distribution, the tests that read them fail or cannot be set up; all other tests pass. With the original files under `reference/`, all tests pass.

## How this work was done

The code, the experiments, the analyses and the manuscript drafts were produced by an AI coding agent (Claude Code, Anthropic, model Claude Opus 5.5) working in this repository under the author's direction; OpenAI Codex (model GPT 6.1 Sol) provided two rounds of critical review. The author set the research questions, the analysis plans and all decisions recorded in `docs/decisions/`. `AGENTS.md` and `CLAUDE.md` contain the working rules given to the agents. The full history of the work is in the private development repository; this repository starts from an export of it, recorded in `EXPORTED_FROM_COMMIT`.

## Licence

Code: MIT License (`LICENSE`). Data, results and documents: CC BY 4.0 (`LICENSE-DATA.md`).
