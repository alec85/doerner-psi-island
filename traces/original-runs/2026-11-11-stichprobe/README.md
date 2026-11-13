# Stichprobe des Originals: Rohprotokolle (Seeds 1001, 1021, 1035, 1041, 1061, 1073, 1081)

Archiviert 2026-11-13 (Issue #55) aus `runs/original/`, wie es am 2026-11-11 von `scripts/original_sample.sh` unter Wine erzeugt wurde. Diese Läufe sind die Grundlage der Vergleiche in `analysis/referenzlaeufe/stichprobe/` und der Zeilen 1001 bis 1081 in Tabelle 3 von Paper 1.

Inhalt je Seed: der konvertierte Lauf (`inseliii__seed-<seed>.jsonl.gz`) und unter `raw/` die unveränderten Protokolle des Originals (Windows-1252, CRLF). Die stehen gebliebenen Leben 1035 und 1061 haben keine Abschlussdateien (`eAch`, `Inpro`, `Consum`).

Geprüft vor dem Archivieren: `scripts/compare_raw.py` gegen die Läufe der Portierung aus `traces/port-runs/2026-11-11-baseline/` ergibt für die Seeds 1041 und 1001 je Datei dieselbe Zahl abweichender Zeilen wie die archivierten Ergebnisse in `analysis/referenzlaeufe/stichprobe/`.

Wiederherstellen im Repository-Wurzelverzeichnis:

```bash
(cd traces/original-runs/2026-11-11-stichprobe && sha256sum -c SHA256SUMS)
mkdir -p runs && tar -C runs -xzf traces/original-runs/2026-11-11-stichprobe/runs-original-stichprobe-7-seeds.tar.gz
```
