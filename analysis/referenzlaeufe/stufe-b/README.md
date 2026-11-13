# Stufe B: Verhalten des Originals über 100 Seeds

Stand 2026-11-11. Seeds 1001 bis 1100, je ein volles Leben (`MaxLife` 5.000.000), gerechnet mit der Portierung im Referenzmodus nach Nachtrag 1 zum Analyseplan. Erzeugt mit

```bash
scripts/measure_variants.sh            # bzw. python scripts/baseline.py --seeds 1001-1100 --runs runs/baseline --jobs 2
python scripts/baseline.py --seeds 1001-1100 --runs runs/baseline --report analysis/referenzlaeufe/stufe-b
```

Dateien: `kennzahlen.csv` (je Seed), `beschreibung.json`, `abgebrochen.json`, `erster_exitus.json`.

## Kennzahlen (97 Leben)

| Kennzahl | Mittel | SD | Median | IQR | 95-%-KI des Mittels (Bootstrap) |
|---|---:|---:|---:|---:|---|
| Zyklen pro Leben | 925,5 | 72,0 | 917,0 | 95,0 | [911,4; 939,6] |
| P1 Exitus pro 1.000 Zyklen | 11,95 | 1,43 | 12,04 | 1,70 | [11,66; 12,23] |
| P2 Nukleotide pro 100 Zyklen | 13,86 | 1,32 | 13,99 | 1,62 | [13,60; 14,12] |
| P3 entdeckte Orte | 96,6 | 3,3 | 97,0 | 4,0 | [95,9; 97,2] |
| P4 Erfolgsquote Manipulationen | 0,378 | 0,018 | 0,377 | 0,026 | [0,374; 0,381] |
| P5 Anteil Zyklen mit Versuch und Irrtum | 0,855 | 0,012 | 0,855 | 0,016 | [0,853; 0,858] |
| P6 mittlere Bedürfnisstärke Schaden (%) | 75,5 | 2,8 | 75,7 | 3,9 | [75,0; 76,1] |

Zeit bis zum ersten Exitus: Alle 97 Leben enthalten mindestens einen Exitus, es gibt also keine Zensierung; die Kaplan-Meier-Kurve fällt mit der empirischen Verteilung zusammen. Median Zyklus 165, Quartile 149 und 179, Spannweite 109 bis 221.

## Abgebrochene Leben

Drei Leben brachen ab, weil das Programm dort einem Zeiger auf nil folgt: Seed 1035 in Zyklus 380 und Seed 1061 in Zyklus 204 (`ActivateAuto`, Protokollkette endet vor dem Ziel), Seed 1073 in Zyklus 679 (`Confirmation`). Im Original ist das eine Zugriffsverletzung: Der Zyklus bricht ab, `StartSimul` bleibt falsch, und das Leben steht still, ohne zu enden. Sie gehen nicht in die Beschreibung ein. Ob das Original an genau diesen Stellen stehen bleibt, prüft die Stichprobe (`../stichprobe/`).

Damit endet etwa jedes dreißigste Leben des Originals nicht regulär. Für die Grundlinie der weiteren Experimente ist das ein Argument für den modernen Modus mit `guard_nil_dereferences` (ADR 0015).

## Vergleich mit der Pilotphase

Die Mittel liegen nahe an denen der fünf Pilot-Seeds (Nachtrag 2). Die Streuung der Zyklenzahl und der entdeckten Orte ist kleiner als im Pilot (SD 72 statt 131 Zyklen, 3,3 statt 14,2 Orte); der Pilot enthielt mit Seed 903 ein kurzes Leben (677 Zyklen, 68 Orte).
