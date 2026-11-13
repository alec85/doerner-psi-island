#!/usr/bin/env bash
# Runs of the workspace experiments, conditions B to E (docs/analyseplan-workspace.md).
# Resumable: finished seeds are skipped. Usage: scripts/workspace_runs.sh 1001-1020 [jobs]
set -euo pipefail
cd "$(dirname "$0")/.."
SEEDS=${1:?seeds, e.g. 1001-1020}
JOBS=${2:-2}
FIXED=0.064642   # Nachtrag 2
python scripts/baseline.py --seeds "$SEEDS" --runs runs/ws-B --jobs "$JOBS" --variant all,workspace=threshold
python scripts/baseline.py --seeds "$SEEDS" --runs runs/ws-C --jobs "$JOBS" --variant all,workspace=motive_only
python scripts/baseline.py --seeds "$SEEDS" --runs runs/ws-D --jobs "$JOBS" --variant all,workspace=fixed,workspace_fixed_bonus=$FIXED
python scripts/baseline.py --seeds "$SEEDS" --runs runs/ws-E --jobs "$JOBS" --variant all,workspace=none
