#!/usr/bin/env bash
# Post-hoc sensitivity runs (docs/analyseplan-sensitivitaet.md, with amendment 1: S1-E dropped). Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
SEEDS=${1:-1001-1020}
JOBS=${2:-2}
python scripts/baseline.py --seeds "$SEEDS" --runs runs/sens-S1-B --jobs "$JOBS" --variant all,workspace=threshold
python scripts/baseline.py --seeds "$SEEDS" --runs runs/sens-S2-B --jobs "$JOBS" --variant all,workspace=threshold,workspace_ties=random
python scripts/baseline.py --seeds "$SEEDS" --runs runs/sens-S2-E --jobs "$JOBS" --variant all,workspace=none,workspace_ties=random
python scripts/baseline.py --seeds "$SEEDS" --runs runs/sens-S3-lo --jobs "$JOBS" --variant all,workspace=fixed,workspace_fixed_bonus=0.02
python scripts/baseline.py --seeds "$SEEDS" --runs runs/sens-S3-hi --jobs "$JOBS" --variant all,workspace=fixed,workspace_fixed_bonus=0.2
