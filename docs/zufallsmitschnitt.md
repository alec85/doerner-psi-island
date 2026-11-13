# Zufallsmitschnitt des Originals

Stand: 2026-11-10, Issue #14, Grundlage ADR 0008 und ADR 0009.

## Zweck

Für den exakten Vergleich nach ADR 0008 muss die Neuimplementierung dieselben Zufallszahlen in derselben Reihenfolge ziehen wie das Original. Der Mitschnitt protokolliert jeden Zug des Originals mit Aufrufstelle. Damit lässt sich die Portierung Zug für Zug prüfen, und eine Abweichung zeigt nicht nur den Zyklus, sondern die Prozedur, in der sie entsteht.

## Verfahren

`scripts/trace_random.py` startet `Psi.exe` unter `winedbg --gdb` und verbindet `gdb` mit `scripts/gdb_random_trace.py`. Das Skript setzt Haltepunkte auf die beiden Zufallsroutinen der Delphi-Laufzeitbibliothek:

| Adresse | Routine | Rückgabe |
|---|---|---|
| `0x402B88` | `Random(n)` | ganze Zahl, `n` in EAX |
| `0x402BA0` | `Random` | reelle Zahl in [0, 1) |
| `0x4A803C` | `RandSeed` | Zustand des Generators |

Je Zug werden Art, `n`, `RandSeed` vor dem Zug, die Rücksprungadressen auf drei Ebenen des Aufrufstapels und die Größe des Ereignisprotokolls festgehalten. Danach startet das Skript die Simulation über das Menü und beendet Psi am Haltepunkt, sobald die gewünschte Zahl von Zügen erreicht ist.

```bash
apt-get install gdb        # zusätzlich zu scripts/setup_wine.sh
python scripts/trace_random.py --seed 16 --max-draws 20000 --out <ordner>
```

Unter dem Debugger läuft Psi etwa fünfmal langsamer; 20.000 Züge (29 Zyklen) dauern rund fünf Minuten.

## Prüfungen

- **Vollständigkeit.** Die `RandSeed`-Werte aller Züge folgen exakt der Folge von `DelphiRandom(16)`. Würde ein Zug fehlen, bräche die Kette an dieser Stelle. Das Skript prüft das bei jedem Lauf und bricht sonst ab.
- **Rückwirkungsfreiheit.** Das Verhalten unter dem Debugger ist identisch mit dem Referenzlauf ohne Debugger (geprüft über 40 Zyklen).
- **Wiederholbarkeit.** Zwei Mitschnitte mit Seed 16 lieferten dieselben 20.000 Züge mit denselben Aufrufstellen.

## Zuordnung der Aufrufstellen

Debug-Symbole gibt es nicht. Die Zuordnung beruht darauf, dass Delphi den Code einer Unit in der Reihenfolge des Quelltexts ablegt. Im Maschinencode gibt es genau 44 feste Aufrufe der beiden Zufallsroutinen. Im Quelltext der gebauten Units stehen 46 `Random`-Aufrufe (gezählt mit einem Pascal-Lexer, der Kommentare und Zeichenketten korrekt überspringt). Die Differenz von zwei erklärt sich vollständig: `LUnion` und `LDifferenz` in `UStrukturen` werden von keiner gebauten Unit aufgerufen, nur aus der nicht gebauten Datei `UPsiMainxy.Pas`, und der Delphi-Linker hat sie entfernt. Die übrigen 44 Aufrufe stimmen in Reihenfolge und Art (`Random` gegen `Random(n)`) mit den Aufrufstellen im Programm überein. Bestätigt wird das unabhängig durch Textkonstanten im Code, die Delphi jeweils hinter einer Prozedur ablegt.

Die Tabelle steht maschinenlesbar in `src/psi_gw/tracing/delphi_random_sites.py`.

| Unit | Prozedur | Aufrufe | Rolle |
|---|---|---:|---|
| `UFEEG.pas` | `TFEEG.PBEEGPaint` | 16 | Oberfläche (EEG-Anzeige) |
| `UStrukturen.Pas` | `RandomChoice` | 1 | Kognition |
| | `LiftInc` | 2 | Kognition |
| | `Decay` | 1 | Kognition |
| | `Junction` | 1 | Kognition |
| | `LSection` | 1 | Kognition |
| | `AddToFan` | 1 | Kognition |
| | `RememberDir` | 1 | Kognition |
| `USound.Pas` | `SpeakRandom`, `Utter` | 3 | Oberfläche (Sprachausgabe) |
| `UPSIMain.Pas` | `Confirmation` | 3 | Kognition |
| | `Association` | 2 | Kognition |
| | `GoalGen` | 1 | Kognition |
| | `WhatCouldBeDone` | 6 | Kognition |
| | `LookAround` | 2 | Kognition |
| `UFPsi.pas` | `TFPsi.Simulation` | 2 | Kognition (Hauptschleife) |
| `UPsiServer.pas` | `SetMotivation` | 1 | Welt |

## Befunde aus 20.000 Zügen (Seed 16, Zyklen 1 bis 29)

| Aufrufstelle | Züge | Anteil |
|---|---:|---:|
| `Decay` | 10.017 | 50,1 % |
| `Junction` | 8.500 | 42,5 % |
| `AddToFan` | 675 | 3,4 % |
| `Association` (beide Stellen) | 458 | 2,3 % |
| `GoalGen` | 101 | 0,5 % |
| `RandomChoice` | 77 | 0,4 % |
| `WhatCouldBeDone` (zwei Stellen) | 62 | 0,3 % |
| `LSection` | 35 | 0,2 % |
| `LookAround` (beide Stellen) | 32 | 0,2 % |
| `TFPsi.Simulation` | 21 | 0,1 % |
| `RememberDir`, `SetMotivation`, `Confirmation` | 22 | 0,1 % |

**Synaptische Übertragung dominiert.** 93 % aller Züge entstehen beim Durchlaufen von Synapsen: `Junction` prüft, ob eine Synapse überträgt (`random < Gewicht`), und ruft davor `Decay` auf, das das Gewicht um einen zufälligen, altersabhängigen Betrag vergessen lässt. Jede Synapse, die Psi beim Erinnern, Assoziieren oder Planen berührt, kostet zwei Züge und verändert dabei ihr Gewicht. Für die Portierung heißt das: Die Reihenfolge, in der das Gedächtnisnetz durchlaufen wird, muss exakt der des Originals entsprechen, sonst laufen Zufallsfolge und Gewichte sofort auseinander.

**Welt und Kognition teilen sich einen Generator.** `SetMotivation` in `UPsiServer` (Unfälle bei Fortbewegung) zieht aus derselben Folge wie die Kognition. Eine Neuimplementierung mit getrennten Zufallsquellen für Körper und Kognition kann deshalb nur in einem Kompatibilitätsmodus mit gemeinsamer Quelle exakt verglichen werden.

**Oberfläche zieht in diesem Abschnitt nicht.** EEG-Anzeige und Sprachausgabe haben zusammen 19 Aufrufstellen, keine davon wurde in den 29 Zyklen getroffen. Das EEG-Fenster ist im Standardlayout geschlossen. Ob die Sprachausgabe später zieht, ist mit längeren Mitschnitten zu prüfen.

**`LiftInc` zieht nicht.** Die zwei Aufrufe in `LiftInc` (Aktivierung der EEG-Neuronen) wurden ebenfalls nicht getroffen.

**Kognition und Welt laufen gegeneinander versetzt.** Bei rund 10 % der Züge ist der interne Zyklus schon weiter als das zuletzt geschriebene Ereignis: Das Ende einer Handlung meldet die Welt über den Socket, und die Kognition denkt in der Zwischenzeit bereits im nächsten Zyklus weiter. Deshalb enthält der Mitschnitt keine einzelne Zyklusnummer, sondern die exakte Zahl der vorher geschriebenen Ereignisse (`events_before`) und die Zyklen der umgebenden Ereignisse (`prev_event_cycle`, `next_event_cycle`).

## Format

`random_draws.tsv.gz`, tabulatorgetrennt, eine Zeile pro Zug:

| Spalte | Bedeutung |
|---|---|
| `nr` | laufende Nummer ab 1 |
| `kind` | `R` für `Random`, `I` für `Random(n)` |
| `n` | Obergrenze bei `Random(n)`, sonst leer |
| `randseed` | `RandSeed` vor dem Zug, vorzeichenlos |
| `site` | Aufrufstelle, z. B. `UStrukturen.Junction#1` |
| `events_before` | Zahl der Ereignisse im Ereignisprotokoll vor dem Zug (exakt, weil das Original die Datei nach jedem Ereignis schließt) |
| `prev_event_cycle`, `next_event_cycle` | Takt des letzten Ereignisses davor und des ersten danach |
| `ret0`, `ret1`, `ret2` | Rücksprungadressen: direkter Aufrufer und zwei weitere Ebenen über die EBP-Kette |

## Offene Punkte

- Der interne Taktzähler `cnr` ist noch nicht im Speicher lokalisiert. Mit ihm ließe sich jeder Zug exakt einem Zyklus zuordnen. Zwei Kandidaten (`0x4A8C38`, `0x4A931C`) zählen synchron zu den Zyklen, werden im Code aber nur indirekt adressiert; `scripts/gdb_random_trace.py` kann beliebige Adressen über `PSI_TRACE_WATCH` mitprotokollieren.
- Die Rücksprungadressen der Ebenen 1 und 2 sind noch nicht Prozeduren zugeordnet. Sie zeigen, aus welchem Kontext `Decay` und `Junction` aufgerufen werden (35 verschiedene Aufrufer von `Junction` in 20.000 Zügen).
- Längere Mitschnitte, um seltene Aufrufstellen (Sprachausgabe, `LiftInc`, weitere Stellen in `WhatCouldBeDone` und `Confirmation`) zu erfassen.
