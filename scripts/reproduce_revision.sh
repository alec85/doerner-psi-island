#!/usr/bin/env bash
# Reproduce every analysis of both papers from the archived data, without reference/.
#
# Works in a fresh copy of the repository (also one without reference/ and without runs/):
#   1. checks the baseline archives against SHA256SUMS,
#   2. extracts them into runs/ and restores the workspace and sensitivity logs,
#   3. recomputes the confirmatory analysis, the revision analyses and the sensitivity analyses
#      into a separate directory,
#   4. compares every result with the committed one and fails on any difference,
#   5. regenerates the tables of both papers and checks that they are unchanged (figures are not
#      compared byte for byte, since PDF/PNG output depends on the matplotlib version).
# New lives of the agent are not run; that needs the original files in reference/.
#
# Usage: scripts/reproduce_revision.sh [output-directory]
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=${1:-$(mktemp -d)}
mkdir -p "$OUT" runs
PY=${PYTHON:-python}

echo "== 1. archives"
(cd traces/port-runs/2026-11-11-baseline && sha256sum -c --quiet SHA256SUMS)

echo "== 2. runs"
tar -xzf traces/port-runs/2026-11-11-baseline/runs-referenzmodus-1001-1100.tar.gz -C runs
tar -xzf traces/port-runs/2026-11-11-baseline/runs-moderner-modus-1001-1100.tar.gz -C runs
$PY scripts/sync_workspace_runs.py restore

echo "== 3. analyses into $OUT"
$PY scripts/workspace_analysis.py --seeds 1001-1100 --stage bestaetigung --out "$OUT/bestaetigung" > /dev/null
$PY scripts/revision_analysis.py --out "$OUT/revision"
$PY scripts/sensitivity_analysis.py --out "$OUT/sensitivitaet" > /dev/null

echo "== 4. comparison with the committed results"
status=0
for f in tests.json leistung.json beschreibung.json; do
  $PY scripts/compare_json.py "analysis/workspace/bestaetigung/$f" "$OUT/bestaetigung/$f" || status=1
done
$PY scripts/compare_json.py analysis/revision/paper1.json "$OUT/revision/paper1.json" || status=1
$PY scripts/compare_json.py analysis/revision/paper2.json "$OUT/revision/paper2.json" || status=1
cmp analysis/revision/laufmanifest-paper1.csv "$OUT/revision/laufmanifest-paper1.csv" || status=1
$PY scripts/compare_json.py analysis/revision/sensitivitaet/ergebnis.json "$OUT/sensitivitaet/ergebnis.json" || status=1
echo "== 5. paper tables regenerated from the reproduced inputs"
before=$(sha256sum paper/*/tabellen/*.tex)
$PY scripts/paper_artifacts.py --stage bestaetigung > /dev/null
after=$(sha256sum paper/*/tabellen/*.tex)
if [ "$before" != "$after" ]; then echo "tables differ"; status=1; else echo "tables identical"; fi
if [ "$status" -ne 0 ]; then echo "REPRODUCTION FAILED"; exit 1; fi
echo "all results reproduced"
