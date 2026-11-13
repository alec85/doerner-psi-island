# Messlauf des Originals unter Wine

Ein Lauf des Originals (Psi 4.9.1.200) am 2026-11-10 mit

```bash
python scripts/run_original.py --seed 16 --max-life 1000000 --out <dir> --timeout 3600
```

im Cloud-Arbeitsbereich (Wine 9.0, Xvfb, 2 CPU-Kerne). Zweck: Laufzeit und Alter pro Zyklus messen, statt sie aus kurzen Läufen hochzurechnen (`docs/analyseplan-referenzlaeufe.md`, Fassung 2).

Ergebnis: 316 Zyklen, 3.118 Ereignisse, drei Exitus (Zyklen 150, 220, 304), 7,5 Minuten Gesamtdauer. Wanduhrzeit pro Zyklus im Mittel 1,27 s ohne Trend; Alter pro Zyklus steigt von etwa 1.250 auf etwa 6.100 Einheiten. Die Zyklen 1 bis 71 sind identisch mit den Referenzläufen unter `../2026-11-09-determinismus/`.

`raw/` enthält alle Protokolle unverändert; die `.jsonl.gz`-Datei ist daraus konvertiert (ADR 0006).
