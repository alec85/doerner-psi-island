# ADR 0008: Exakte Vergleiche ganzer Läufe

- Status: angenommen
- Datum: 2026-11-09
- Autor: Alec (Zustimmung), Claude Code
- Ergänzt: ADR 0005

## Kontext

ADR 0005 ging davon aus, dass ganze Läufe des Originals nicht reproduzierbar sind, und sah für das Gesamtverhalten nur statistische Vergleiche vor. Unter Wine sind Läufe mit gleichem Seed aber bit-identisch, geprüft über 72 Zyklen und 647 Ereignisse (`docs/delphi-build.md`, `traces/original-runs/2026-11-09-determinismus/`).

Der Zufallsgenerator des Originals ist vollständig bekannt. Die Maschinenbefehle in `Psi.exe` (Adressen `0x402B88` und `0x402BA0`, Konstante `2⁻³²` bei `0x4A602C`) zeigen den Generator der Delphi-Laufzeitbibliothek:

- Fortschreibung: `RandSeed := RandSeed * $08088405 + 1` (modulo 2³²),
- reell: `Random = RandSeed / 2³²`, mit `RandSeed` als vorzeichenlose 32-Bit-Zahl,
- ganzzahlig: `Random(n) = (n * RandSeed) shr 32`, was genau `floor(Random * n)` entspricht.

## Entscheidung

1. Zusätzlich zu den beiden Ebenen aus ADR 0005 gibt es **exakte Ganzlauf-Vergleiche**: Die Python-Implementierung läuft mit nachgebildetem Delphi-Generator und demselben Seed wie ein Referenzlauf des Originals. Verglichen wird Ereignis für Ereignis und Zyklus für Zyklus. Ergebnis ist der erste Zyklus, in dem die Läufe auseinandergehen, und die Art der Abweichung.
2. `psi_gw.random_source.DelphiRandom` bildet den Generator bit-genau nach. Wie im Original zieht die Kognition aus einem einzigen Generator in derselben Reihenfolge; jede Abweichung der Zugreihenfolge zeigt sich im Vergleich.
3. Referenzläufe dafür werden unter Wine wie in `docs/delphi-build.md` beschrieben erzeugt und unter `traces/original-runs/` abgelegt.
4. Die Zufallszüge der Oberfläche (EEG-Anzeige, Sprachausgabe) gehören nicht zur Kognition. Ob sie im Wine-Modus tatsächlich Zufallszahlen verbrauchen und damit die Folge der Kognition verschieben, ist offen. Die Python-Implementierung zieht sie nicht; zeigt der Vergleich früh eine Verschiebung, wird ein Ausgleich als Abweichung nach ADR 0005 markiert und begründet.
5. Das Ziel ist ein möglichst später erster Unterschied, aber kein Zwang zur Gleichheit über beliebig lange Läufe. Unterschiede durch 80- gegen 64-Bit-Rechnung werden nach ADR 0005 behandelt (dokumentieren, markieren, Toleranz nicht pauschal erhöhen). Ab dem ersten Unterschied gilt für den Rest des Laufs der statistische Vergleich.

## Betrachtete Alternativen

- **Nur statistischer Vergleich.** Verworfen, weil exakte Vergleiche möglich sind und Fehler auf den Zyklus genau eingrenzen.
- **Zahlenstrom aus dem Original mitschneiden** statt den Generator nachzubilden. Nicht nötig, weil der Generator vollständig bekannt ist; bleibt für das Testgerüst aus ADR 0005 der Weg der Wahl, weil dort einzelne Prozeduren ohne Lauf-Kontext getestet werden.

## Konsequenzen

- Die Python-Implementierung muss die Zugreihenfolge des Originals genau einhalten. Das ist bei der Portierung eine zusätzliche Anforderung, macht aber auch Fehler sichtbar, die statistisch untergehen würden.
- Die Regel `floor(value * n)` aus ADR 0006 ist mit dem Delphi-Generator identisch, Prozedur-Testfälle und Ganzlauf-Vergleiche nutzen also dieselbe Logik.
- Der Analyseplan für Issue #7 berücksichtigt, dass Läufe des Originals mit gleichem Seed keine Streuung haben; Variabilität entsteht nur über verschiedene Seeds.
