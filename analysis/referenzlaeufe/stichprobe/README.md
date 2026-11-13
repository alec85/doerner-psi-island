# Stichprobe des Originals (Nachtrag 1 zum Analyseplan)

Stand 2026-11-11. Sieben Leben des Originals unter Wine (`scripts/original_sample.sh`), verglichen mit denselben Seeds der Portierung (`scripts/compare_raw.py`, Ergebnis je Seed als JSON in diesem Ordner). Wanduhrzeiten sind ausgeblendet. Die Rohprotokolle des Originals liegen unter `runs/original/`; archiviert in `traces/original-runs/2026-11-11-stichprobe/`.

| Seed | Ergebnis |
|---|---|
| 1041 | Identisch in allen Protokollen. Zwei Zeilen in `IntTimes` unterschieden sich in der fünften Nachkommastelle eines Mittelwerts; das ist seither behoben (80-Bit-Quotient, Halbe aufrunden). |
| 1061 | Identisch bis Zyklus 204. Dort bricht die Portierung mit einem nil-Zugriff in `ActivateAuto` ab. Das Original bleibt an derselben Stelle stehen: Danach schreibt es nur noch `IntTimes`-Zeilen für Zyklus 204, über 13.000 bis zur Zeitgrenze. Vorhersage bestätigt. |
| 1035 | Eine Zeile nach ADR 0014 in Zyklus 39 (Richtung `lN` als Nordwest gelesen), gleiche Lokomotion gewählt. Sonst identisch bis Zyklus 380, wo die Portierung abbricht und das Original stehen bleibt. Vorhersage bestätigt. |
| 1001 | Identisch bis Zyklus 310. Dort wählt das Original wegen ADR 0014 eine andere Lokomotion (`lSW` statt `lSO`); danach laufen die Leben auseinander. |
| 1073 | Wie 1001, Abweichung nach ADR 0014 in Zyklus 396. Der vorhergesagte Abbruch in Zyklus 679 wird dadurch nicht erreicht; das Original lebt regulär zu Ende. |
| 1081 | Wie 1001, Abweichung nach ADR 0014 in Zyklus 415 (`lNO` statt `lNW`). |
| 1021 | Wie 1001, Abweichung nach ADR 0014 in Zyklus 663. |

Dazu die früheren Vergleiche: Seed 16 vollständig identisch, Seed 901 eine Zeile nach ADR 0014 ohne Folgen.

## Bewertung

Jede beobachtete Abweichung gehört zu genau einer bekannten Ursache: dem Byte einer Heapadresse, das `RememberDir` für `lN` und `lS` als dritten Buchstaben liest (ADR 0014). Andere Abweichungen kamen in rund 7.000 verglichenen Zyklen nicht vor. Beide vorhergesagten Abbrüche traten im Original an derselben Stelle auf.

Die Heap-Ursache wirkt aber häufiger, als die Zählung bei Seed 16 und 901 vermuten ließ. In vier von sieben Leben änderte sie eine Entscheidung, im Mittel nach etwa 450 Zyklen, und ab da verlaufen Original und Portierung verschieden. Die Kennzahlen der Portierung sind damit nicht Seed für Seed die des Originals. Sie stammen aus demselben Mechanismus mit einem Unterschied: Das Original liest bei `lN`/`lS` gelegentlich eine Diagonale, die Portierung nie. Siehe Nachtrag 3 zum Analyseplan.
