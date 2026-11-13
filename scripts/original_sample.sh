#!/bin/bash
# Sample of the original under Wine (analysis plan, amendment 1): seeds 1001, 1021, 1041, 1061, 1081,
# plus the seeds whose life broke off in the port (1035, 1061, 1073: nil access where the original
# should raise an access violation and stand still; a short timeout keeps its protocols).
# Each full original life takes 18 to 25 minutes; runs one after the other (port 2000). Resumable.
cd "$(dirname "$0")/.." && source .venv/bin/activate
for s in 1061 1035 1073 1001 1021 1041 1081; do
  case $s in 1035|1061|1073) timeout=1500 ;; *) timeout=5400 ;; esac
  if [ ! -d "runs/original/seed$s/raw/seed$s" ]; then
    python scripts/run_original.py --seed $s --max-life 5000000 --out runs/original/seed$s --timeout $timeout
  fi
  if [ -d "runs/baseline/seed$s/raw" ]; then
    python scripts/compare_raw.py --seed $s --original runs/original/seed$s/raw/seed$s --port runs/baseline/seed$s/raw \
      --json analysis/referenzlaeufe/stichprobe/seed$s.json
  fi
done
