# Methodenbaustein: Portierung und Treue zum Original

Grundlage für Abschnitt 3.1 und Tabelle T1. Alle Angaben mit Fundstelle im Repository.

## Ausgangspunkt

Delphi-Quelltext von PSI 4.9.1.200 (Dörner und Gerdes) aus dem Umfeld von „Die Mechanik des Seelenwagens“, Inselwelt `InselIII`, Parameter `PsiDaten/InselIII/Param.Dat`. Das Original läuft unter Wine; Läufe werden mit `scripts/original_sample.sh` erzeugt. Der Quelltext liegt schreibgeschützt unter `reference/`.

## Vorgehen

- Prozedur für Prozedur portiert, mit Tests aus der Pascal-Semantik (Zeilenangaben, exakte Zahl der Zufallszüge).
- Zufall nur über eine durchgereichte `RandomSource` mit Aufrufstellen (ADR 0005). Mitschnitte der Zufallszüge des Originals mit `gdb` (`scripts/gdb_random_trace.py`) erlauben den Vergleich Zug für Zug.
- 80-Bit-Rechnung des x87 dort nachgebildet, wo Ergebnisse als Text gedruckt und wieder eingelesen werden (`psi_gw.body.island.x87`); sonst 64 Bit, markiert mit `DEVIATION(ADR-0005)`.
- String-Vergleich und Sortierung wie Delphi unter Wine, geprüft gegen eine Vergleichsmatrix aus Wine über alle Paare von 453 Zeichenketten der Welt (`psi_gw.body.island.delphi_strings`).
- Seiteneffekte der Benutzeroberfläche, die das Verhalten ändern, bleiben im Referenzmodus erhalten (ADR 0011: die Werteanzeige ruft `EpiKomp` für alle Bedürfnisse auf).

## Ergebnisse (Tabelle T1)

| Prüfung | Ergebnis | Beleg |
|---|---|---|
| Volles Leben Seed 16 (`MaxLife` 5.000.000, 739 Zyklen) | Alle 109.140 Zeilen des Aktivitätsprotokolls, alle 2.802 Handlungen mit Alter, alle 43 Prozesszähler und die Abschlussdateien identisch | `tests/test_life.py` (`PSI_GW_FULL_LIFE=1`), `scripts/compare_life.py` |
| Zufallszüge Seed 16 | Erste 75.000 Züge (bis Zyklus 70) Zug für Zug identisch | `tests/test_life.py::test_first_70_cycles_of_the_full_life` |
| Volles Leben Seed 901 (912 Zyklen) | Handlungen, Zähler, Abschlussdateien identisch; 1 von 90.698 Protokollzeilen abweichend (ADR 0014) | `tests/test_life.py::test_full_life_seed_901` |
| Stichprobe von sieben Leben (Seeds 1001 bis 1081) | Jede Abweichung geht auf genau eine bekannte Ursache zurück (ADR 0014). Zwei vorhergesagte Abbrüche traten im Original an derselben Stelle auf. In vier Leben änderte die Ursache eine Entscheidung (nach 310 bis 663 Zyklen), danach verlaufen die Leben verschieden | `analysis/referenzlaeufe/stichprobe/README.md` |
| Fortsetzung aus Schnappschuss | Gesichert, in frischem Prozess fortgesetzt: Zustand und Züge nach jedem Schritt gleich | `tests/test_state_snapshot.py`, `tests/test_life.py` |

## Bekannte, bewusst nicht nachgebildete Ursache

`RememberDir` und `DirArtWert` lesen für die Richtungen `lN` und `lS` ein drittes Zeichen aus nicht initialisiertem Speicher, im Original ein Byte einer Heapadresse (ADR 0014). Die Portierung liest dort nichts. Seed-für-Seed-Gleichheit langer Leben ist deshalb nicht erreichbar; die Kennzahlen stammen aus demselben Mechanismus mit diesem einen Unterschied.

## Grundlinien

- Referenzmodus, Seeds 1001 bis 1100: `analysis/referenzlaeufe/stufe-b/`.
- Moderner Modus, Seeds 1001 bis 1100: `analysis/grundlinie-modern/`.
- Eingefrorener Code: Branch `baseline/referenzmodus-2026-11-11`; Läufe als Archive unter `traces/port-runs/2026-11-11-baseline/` (Prüfsummen in `SHA256SUMS`).
