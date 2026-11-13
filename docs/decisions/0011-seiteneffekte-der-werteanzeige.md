# ADR 0011: Seiteneffekte der Werteanzeige im Referenzmodus

- Status: angenommen (Alec, 2026-11-10)
- Datum: 2026-11-10
- Autor: Claude Code
- Bezieht sich auf: ADR 0008, ADR 0010 (Prinzip „Oberfläche nur lesend“); Issue #18

## Kontext

ADR 0010 legt fest, dass die Oberfläche der Portierung nur liest und keine Zufallszahlen zieht. Sie nahm an, dass im Original allenfalls EEG-Anzeige und Sprachausgabe davon abweichen.

Beim Portieren der Hauptschleife (`TFPsi.Simulation`, UFPsi.pas ab Zeile 232) zeigte sich eine weitere, tatsächlich wirksame Stelle. Am Ende jedes Zyklus schreibt das Original die epistemische Kompetenz aller sieben Bedürfnisse in Eingabefelder des Parameterfensters (`FValChange.EditeKoHu.text := FloatToStr(EpiKomp(Hunger))` und sechs weitere, Zeilen 493 bis 499). `EpiKomp` ist keine reine Berechnung: Die Funktion durchläuft die Zielverbindungen des Bedürfnisses mit `Junction`, zieht dabei Zufallszahlen, verändert Synapsengewichte und erhöht über `LiftInc` das Alter.

Belege:

- Im Maschinencode ruft die Anzeige an sieben Stellen die Funktion bei 0x47B250 auf, dieselbe, die auch `MotiveStrength` aufruft (Rücksprungadressen 0x49F95F, 0x49F990, 0x49F9C1, 0x49F9F2, 0x49FA23, 0x49FA54, 0x49FA85).
- Im Zufallsmitschnitt mit Seed 16 (20.000 Züge, Zyklen 1 bis 29) stammen 101 `Junction`-Züge aus diesen Aufrufen, dazu je ein `Decay`-Zug.
- Die Argumente im Maschinencode (`mov al, n` vor jedem Aufruf) ergeben die Reihenfolge 1, 2, 3, 4, 6, 5, 7, also Kompetenz vor Bestimmtheit, wie im Quelltext. `tests/test_agent.py` prüft das direkt an `Psi.exe`.
- Der Block wird unabhängig davon ausgeführt, ob das Fenster sichtbar ist.

## Entscheidung

1. Im Referenzmodus gehört die Werteanzeige zum Verhaltenszyklus. `psi_gw.agent.value_display` ruft am Ende jedes Zyklus `epistemic_competence` für die sieben Bedürfnisse in der Reihenfolge der Anzeige auf (Hunger, Durst, Nukleo, Schaden, Kompetenz, Bestimmtheit, Affiliation) und verwirft die Ergebnisse. Der Name der Funktion und ihre Dokumentation sagen ausdrücklich, dass es sich um einen Seiteneffekt der Anzeige des Originals handelt.
2. Das Prinzip aus ADR 0010 bleibt für alles Neue bestehen: Eine Visualisierung der Portierung liest nur.
3. Ein späterer moderner Modus kann den Aufruf entfernen. Das ist eine Verhaltensänderung nach Stufe 2 von ADR 0010 und wird dort mit `DEVIATION(ADR-0011)` markiert und statistisch geprüft.

## Betrachtete Alternativen

- **Weglassen, weil es Oberfläche ist.** Verworfen: Der zugweise Vergleich nach ADR 0008 liefe ab dem ersten Zyklus mit gelernten Zielen auseinander, und Gewichte und Alter wichen ab.
- **Als Teil der Motivation verstecken.** Verworfen: Wer den Code liest, soll sehen, woher diese Züge kommen.

## Konsequenzen

- Die Beschreibung des Originals für Paper 1 muss erwähnen, dass das Verhalten von der Anzeige abhängt: Die epistemische Kompetenz wird pro Zyklus mindestens zweimal berechnet (in `Motivation` und in der Anzeige), bei einem Hauptziel ein drittes Mal für `QuickMove`, und jede Berechnung lässt das Gedächtnis altern und verstärkt Zielverbindungen.
- Beim Portieren weiterer Units werden Anzeigeaufrufe auf dieselbe Weise geprüft: im Quelltext auf Aufrufe von Funktionen mit Seiteneffekten, im Mitschnitt auf Züge mit Rücksprungadressen im Oberflächencode.
