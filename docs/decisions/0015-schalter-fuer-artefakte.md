# ADR 0015: Schalter für Implementierungsartefakte des Originals

- Status: angenommen (Claude Code, 2026-11-10, im Rahmen von Alecs Auftrag; Reihenfolge von Alec am 2026-11-10 17:04 bestätigt)
- Datum: 2026-11-10
- Autor: Claude Code
- Bezieht sich auf: ADR 0010 (Stufe 2, moderner Modus), ADR 0011, ADR 0013, ADR 0014; Issue #29

## Kontext

Der Referenzmodus bildet das Original einschließlich seiner Zufälle der Implementierung nach. Beim Portieren sind Stellen aufgefallen, an denen das Verhalten des Programms nicht aus Dörners Theorie folgt, sondern aus Eigenheiten von Delphi, Wine oder der Oberfläche. Bevor der Global Workspace hinzukommt (Phase 3), soll messbar sein, welche dieser Stellen Psis Verhalten prägen. Sonst lässt sich ein Effekt der Erweiterung nicht von einem Effekt der Bereinigung trennen.

## Entscheidung

`psi_gw.variant.Variant` enthält je Artefakt einen Schalter. `Variant()` ist der Referenzmodus; jeder gesetzte Schalter schaltet genau ein Artefakt ab. Der Zustand trägt die Variante (`PsiState.variant`, im Schnappschuss enthalten), Läufe schreiben sie in den Kopf der Trace-Datei.

Aufgenommen sind Stellen, die eindeutig Implementierungsartefakte sind:

| Schalter | Artefakt | Beleg |
|---|---|---|
| `no_display_side_effects` | Die Werteanzeige ruft `EpiKomp` auf und verändert Gedächtnis, Zufallsfolge und Alter | ADR 0011 |
| `clean_direction_names` | `DirArtWert` liest für `lN`/`lS` einen Speicherrest | ADR 0014, HANDOFF |
| `goal_in_current_situation` | Parameter `situation` verdeckt in `PlanenUndTun` die globale Situation | Zufallsmitschnitt mit Neuronennamen, Zyklus 65 |
| `aversion_check_in_aversions` | `Consum` prüft eine bekannte Aversion in der Zielliste; Aversionen werden nie verstärkt | `UAction.pas`, `Consum` |
| `background_goals_as_described` | `GoalGen` nimmt Hintergrundziele mit `random < r − s` auf, das ist `random < Motivstärke × Selektionsschwelle`. Je stärker das aktuelle Motiv, desto mehr Nebenziele. Das Buch beschreibt das Gegenteil: `random < BedIn − MotivStärke × SelectSchwelle`, und „je reinrassiger die Zielliste, desto konzentrierter“ | Dörner, Die Mechanik des Seelenwagens, S. 29 und 99 |
| `guard_nil_dereferences` | Das Original folgt an mehreren Stellen Zeigern ohne Prüfung auf nil. Trifft es nil, bricht der Zyklus mit einer Zugriffsverletzung ab, `StartSimul` bleibt falsch, das Leben steht still. Mit dem Schalter endet der betroffene Regulationsschritt als Misserfolg | Zuerst aufgetreten mit `background_goals_as_described`, Seed 1019 (`ActivateAuto`, Protokollkette endet vor dem Ziel) |
| `real_umlaut_bitmaps` | Unter Wine fehlen die Bilder mit Umlaut im Namen | ADR 0013 |

Nicht aufgenommen, weil unklar ist, ob es sich um Absicht handelt: das Speichern des Winkels statt der Winkeldifferenz in `NextCont` und das Ende der zweiten Schleife von `LookAround` nach der ersten gefundenen Assoziation. Das Buch beschreibt beide nicht so genau, dass sich eine Absicht ablesen ließe (Abgleich am 2026-11-10: `LookAround` S. 182 bis 186). Die Annahmeregel für Hintergrundziele war ursprünglich ebenfalls in dieser Gruppe; der Abgleich mit S. 99 hat sie als Artefakt eingeordnet. Uninitialisierte Werte, deren Inhalt nicht vorhersagbar ist (`SpatSit`, Ergebnis von `ConSumFin` beim Abbruch), sind bereits auf 0 bzw. `FALSE` gesetzt; dafür gibt es keinen Referenzzustand zum Abschalten.

## Messung

Je Schalter einzeln und alle zusammen laufen dieselben Seeds wie die Vergleichsbasis (`scripts/baseline.py --variant <schalter> --runs runs/variant-<schalter>`). Verglichen werden die Kennzahlen P1 bis P6 gepaart je Seed mit der Vergleichsbasis: mittlere Differenz mit Bootstrap-Konfidenzintervall und Vorzeichen-Permutationstest (exakt bis 16 Paare, sonst 10.000 Ziehungen), Holm-korrigiert über die sechs Kennzahlen je Schalter. Zusätzlich wird je Seed der erste Zyklus berichtet, ab dem sich der Lauf vom Referenzlauf unterscheidet.

Leben, die ohne `guard_nil_dereferences` an einer solchen Stelle abbrechen, werden in den Vergleichen nicht beschrieben, sondern mit Seed und Stelle gemeldet (`abgebrochen.json`, `vergleich.md`).

## Konsequenzen

- Der Referenzmodus bleibt unverändert und wird weiter durch die Golden-Master-Tests geschützt.
- Der moderne Modus für die weiteren Phasen ist die Variante mit allen Schaltern, sofern die Messung nichts anderes nahelegt.
- Weitere Artefakte kommen als neue Schalter hinzu; jeder braucht einen Beleg wie in der Tabelle.
