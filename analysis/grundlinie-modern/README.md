# Grundlinie für Phase 3: moderner Modus über 100 Seeds

Stand 2026-11-11. Seeds 1001 bis 1100, je ein volles Leben (`MaxLife` 5.000.000), Variante mit allen Schaltern aus ADR 0015 (`Variant.from_names("all")`). Das ist die Ausgangsbasis für die Workspace-Experimente (ADR 0016, Frage 4).

Dateien: `kennzahlen.csv` (je Seed), `beschreibung.json` (Mittel, SD, Median, IQR, Bootstrap-KI), `abgebrochen.json` (leer: kein Leben brach ab).

Herkunft: Die Seeds 1001 bis 1020 liefen, bevor es den Schalter `guard_nil_dereferences` gab; in diesen 20 Leben trat kein nil-Zugriff auf (sonst wären sie abgebrochen), die Ergebnisse sind daher dieselben wie mit dem Schalter. In den Seeds 1021 bis 1100 griff der Schalter zweimal. Die Trace-Dateien liegen im GitHub-Release `baseline-referenzmodus-2026-11-11`, der Vergleich mit dem Referenzmodus unter `analysis/varianten/all-100/`.

Neu erzeugen:

```bash
python scripts/baseline.py --seeds 1001-1100 --variant all --runs runs/variant-all --jobs 2
python scripts/baseline.py --seeds 1001-1100 --runs runs/variant-all --report analysis/grundlinie-modern
```
