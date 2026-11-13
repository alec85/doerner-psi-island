# ADR 0014: Verhalten, das von Heapadressen des Originals abhängt

- Status: angenommen (Claude Code, 2026-11-10, im Rahmen von Alecs Auftrag vom 2026-11-10 14:31)
- Datum: 2026-11-10
- Autor: Claude Code
- Bezieht sich auf: ADR 0003 (Golden Master), ADR 0008 (exakte Ganzlauf-Vergleiche), ADR 0010 (Referenzmodus)

## Kontext

Das volle Leben mit Seed 16 stimmt in allen Protokollzeilen mit dem Original überein. Beim zweiten Seed (901, 912 Zyklen) stimmen Handlungen, Alter, Zähler und Abschlussdateien ebenfalls überein, im Aktivitätsprotokoll aber eine von 90.698 Zeilen nicht:

```
original:   5 OD:3.927 LokoMotion:       lS
portierung: 6 OD:4.712 LokoMotion:       lS
```

Ursache ist `DirArtWert` (`UStrukturen.Pas`, Zeile 603). Für die zweibuchstabigen Lokomotionen `lN` und `lS` liest das Original das dritte Zeichen eines lokalen `string[30]`, in das nur die Länge kopiert wurde (Maschinencode bei 0x477D14). In `ContinueDirection` steht dort das dritte Zeichen des zuletzt geprüften längeren Namens; das bildet die Portierung nach. In `RememberDir` liegt an dieser Stapelstelle dagegen der Rest des unmittelbar vorher aufgerufenen `Junction`: Byte 2 der Adresse der gefundenen Synapse (`[ebp-0x20]` in `Junction`). Ist dieses Byte `'W'` (0x57) oder `'O'` (0x4F), zählt `lS` als Südwest bzw. Südost, `lN` entsprechend als Nordwest bzw. Nordost.

Die Adresse hängt von der Speicherverwaltung von Delphi 7 und von der Reihenfolge aller Speicheranforderungen des Programms ab, einschließlich Zeichenketten und VCL. Unter Wine ist sie reproduzierbar (zwei Läufe mit Seed 16 waren identisch), aus der Portierung heraus aber nicht vorhersagbar.

## Entscheidung

Die Speicherverwaltung des Originals wird nicht nachgebaut. In `RememberDir` behandelt die Portierung das Restbyte als „kein Zeichen“ (`lS` = Süd, `lN` = Nord), markiert mit `DEVIATION(ADR-0010)`. Der Golden Master für Seed 16 bleibt unverändert exakt.

Für weitere Seeds gilt: Abweichungen an dieser Stelle sind bekannt und erklärt. `scripts/compare_life.py` meldet die erste Abweichung; liegt sie in einer `OD:`-Zeile nach `RememberDir`, ist das dieser Fall.

## Betrachtete Alternativen

- **Speicherverwaltung von Delphi 7 nachbauen.** Verworfen: Dafür müsste jede Speicheranforderung des Originals in Größe und Reihenfolge nachgebildet werden, auch die der Oberfläche. Der Aufwand stünde in keinem Verhältnis zu einer Stelle, die selten zum Tragen kommt.
- **Adressbyte aus einem Mitschnitt des Originals einspielen.** Möglich für einzelne Vergleichsläufe, aber kein Modell. Zurückgestellt.

## Konsequenzen

- Läufe mit anderen Seeds können ab einer solchen Stelle vom Original abweichen, wenn die andere Richtung eine andere Lokomotion wählt. Bei Seed 901 wählte das Original trotzdem dieselbe Lokomotion, und der Lauf blieb in allen Handlungen gleich.
- Für statistische Vergleiche über viele Seeds ist das ein bekannter, seltener Unterschied; er ist bei der Auswertung zu nennen.

## Nachtrag vom 2026-11-11: Häufigkeit

Die Stichprobe des Originals (`analysis/referenzlaeufe/stichprobe/`) zeigt die Ursache häufiger als oben geschätzt. In sechs von neun verglichenen Leben (Seeds 16, 901 und sieben aus Stufe B) las das Original mindestens einmal eine Diagonale; in vier davon änderte das die gewählte Lokomotion, und die Leben liefen ab dort (Zyklen 310 bis 663) verschieden weiter. Andere Abweichungsursachen kamen nicht vor. Die Entscheidung bleibt bestehen; die Folgen für die Beschreibung des Originals stehen in Nachtrag 3 zum Analyseplan.
