#!/bin/bash
# Measurement queue for Issue #28/#29. Resumable: finished seeds are skipped, so just start it again.
# Order: each artefact switch alone on seeds 1001-1020, then the baseline up to seed 1100.
cd "$(dirname "$0")/.." && source .venv/bin/activate
for v in no_display_side_effects clean_direction_names goal_in_current_situation aversion_check_in_aversions background_goals_as_described real_umlaut_bitmaps; do
  python scripts/baseline.py --seeds 1001-1020 --variant $v --runs runs/variant-$v --jobs 2
done
python scripts/baseline.py --seeds 1021-1100 --runs runs/baseline --jobs 2
