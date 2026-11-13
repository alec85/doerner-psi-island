# ADR 0005: Zweistufiger Abgleich mit dem Original

- Status: angenommen
- Datum: 2026-11-09
- Autor: Alec, Claude Code
- Ergänzt: ADR 0003; ergänzt durch ADR 0008 (exakte Ganzlauf-Vergleiche); Ebene 1 geändert durch ADR 0009

## Kontext

ADR 0003 sieht Golden-Master-Tests gegen Referenz-Traces des Delphi-Originals vor. Das Inventar (`docs/delphi-inventar.md`, Abschnitte „Zufallsquellen“ und „Echtzeitabhängigkeiten“) zeigt, dass ein fester Seed das Original nicht reproduzierbar macht:

- Kognition, Welt und Oberfläche ziehen aus einem einzigen globalen Zufallsgenerator. Die EEG-Anzeige verbraucht beim Neuzeichnen Zufallszahlen, die Zufallsfolge der Kognition hängt also davon ab, wie oft Windows ein Fenster zeichnet.
- Kognition und Welt kommunizieren asynchron über einen TCP-Socket, die Hauptschleife verarbeitet zwischendurch Fensternachrichten.
- Timer, Warteschleifen und das Alter `Age` hängen an der Wanduhr.

Zwei archivierte Läufe mit Seed 16 weichen ab dem dritten Zyklus voneinander ab. Exakte Traces ganzer Inselläufe sind deshalb nur mit tiefen Eingriffen ins Original zu bekommen, und jeder solche Eingriff verändert genau das Verhalten, das wir als Referenz brauchen.

Dazu kommt ein numerisches Problem: Das Original rechnet teils mit `extended` (80 Bit), Python mit 64-Bit-Gleitkommazahlen. Kleine Rundungsunterschiede können Vergleiche wie `random < modulat[ResolutionLevel]` kippen und Läufe danach auseinanderlaufen lassen, selbst wenn beide Implementierungen korrekt sind.

## Entscheidung

Der Abgleich erfolgt auf zwei Ebenen mit unterschiedlichen Werkzeugen.

### Ebene 1: Exakte Tests einzelner Prozeduren

Gegenstand sind einzelne Prozeduren und Funktionen mit klar abgegrenzten Ein- und Ausgaben, etwa `NeedAndCompetence`, `Motivation`, `GoalGen`, `SetModulat`, Netzoperationen aus `UStrukturen` (`Connect`, `ReInforce`, `Decay`, Listenoperationen) und später Teile von `Planen` und `Association`.

1. Ein Testgerüst in Free Pascal (`reference/delphi-harness/`, Kopie der benötigten Units) kompiliert die Kern-Units ohne Oberfläche. Oberflächen- und Client-Units werden durch Stubs ersetzt, die nichts zeichnen und keine Zufallszahlen verbrauchen.
2. **Zufall wird injiziert.** In der Kopie werden alle `Random`-Aufrufe der Kern-Units durch eine Funktion ersetzt, die aus einem vorgegebenen Zahlenstrom liest. Derselbe Strom wird dem Python-Code über eine `RandomSource`-Abstraktion zugeführt. Damit ist der Vergleich unabhängig vom Algorithmus des Zufallsgenerators.
3. Für jeden Testfall schreibt das Gerüst Eingangszustand, Zahlenstrom und Ergebnis als JSON. Die Python-Tests lesen diese Fälle und vergleichen.
4. Toleranzen: Diskrete Ergebnisse (gewähltes Motiv, Zielliste, Rückgabewerte vom Typ `Triple`, Listenreihenfolgen) müssen exakt übereinstimmen. Reelle Werte dürfen relativ um höchstens 1e-9 abweichen. Kippt eine diskrete Entscheidung nachweislich wegen eines Rundungsunterschieds, wird der Fall dokumentiert und mit `DEVIATION(ADR-0005)` markiert, statt die Toleranz pauschal zu erhöhen.

Jede Änderung an den kopierten Units im Gerüst ist als Diff zum Original nachvollziehbar (ADR 0003).

### Ebene 2: Statistischer Vergleich des Gesamtverhaltens

Gegenstand ist das Verhalten ganzer Inselläufe.

1. Das Original läuft **möglichst unverändert** mit Oberfläche unter Windows, gestartet über `Execute` bzw. Kommandozeile (`Daten=InselIII PsiDaten=InselIII Protokoll=<Kennung> Geschwindigkeit=0.0 Start`), mit vielen Seeds. Ausgewertet werden die Protokolldateien, die das Original ohnehin schreibt (`ach*.Prt`, `consum.Prt`, `actu*.prt` und weitere, beschrieben im Buch, Kapitel 6).
2. Die Python-Implementierung läuft auf der portierten Inselwelt mit denselben Startdaten und derselben Zahl an Läufen und schreibt dieselben Kennzahlen.
3. Kennzahlen (vorläufig, werden mit Issue #3 festgelegt): Lebensdauer bis zum ersten Exitus, Zahl der Exitus pro 10.000 Zyklen, erfolgreiche und erfolglose Fortbewegungen und Manipulationen, gesammelte Nukleotide, mittlere Bedürfnispegel, Anteile der Rasmussen-Stufen (LookAround, Automatismus, Planung, Versuch und Irrtum, Ruhe), Verteilungen der Modulatoren.
4. Statistik: Weil wir **Gleichheit** belegen wollen, werden Äquivalenztests verwendet (TOST mit vorab festgelegten Äquivalenzgrenzen je Kennzahl), ergänzt um Verteilungsvergleiche (Kolmogorov-Smirnov bzw. Anderson-Darling) und Effektstärken mit Konfidenzintervallen. Ein nicht signifikanter Unterschiedstest gilt ausdrücklich nicht als Beleg für Gleichheit. Äquivalenzgrenzen und Zahl der Läufe werden vor der ersten Auswertung in einem Analyseplan festgelegt (`docs/analyseplan-referenzlaeufe.md`), die Zahl der Läufe per Poweranalyse; als Ausgangswert dienen 50 Läufe je Implementierung.
5. Als Vorabprüfung wird die Streuung des Originals zwischen Läufen mit gleichem Seed gemessen. Sie zeigt, wie viel Variabilität allein aus den Echtzeiteffekten stammt, und dient als Untergrenze für sinnvolle Äquivalenzgrenzen.

### Folgen für die Python-Implementierung

- Zufall läuft ausschließlich über eine `RandomSource`-Schnittstelle. Standard ist ein `numpy.random.Generator`, für Ebene-1-Tests ein Wiedergabestrom. Die Regel aus `AGENTS.md` (expliziter Generator, kein globaler Zustand) bleibt bestehen und wird damit konkretisiert.
- Optional kann eine Implementierung des Delphi-Generators (lineare Kongruenz mit `RandSeed`) ergänzt werden, um Ebene-1-Fälle auch ohne Zahlenstrom nachzustellen. Das ist optional.
- Die Python-Inselwelt läuft synchron und taktbasiert. Wo das Original Wanduhrzeit verwendet, wird sie durch Zyklen bzw. simulierte Zeit ersetzt und mit `DEVIATION(ADR-0005)` markiert.

## Betrachtete Alternativen

- **Exakte Traces ganzer Läufe aus einem umgebauten Original.** Verworfen als alleiniger Weg: Synchrone Welt, eigener Zufallsgenerator und Taktzähler verändern das Original so stark, dass unklar wäre, wogegen wir eigentlich testen. Außerdem würden Rundungsunterschiede lange Läufe trotzdem auseinanderlaufen lassen.
- **Nur statistischer Vergleich.** Verworfen als alleiniger Weg: Fehler in einzelnen Prozeduren würden erst spät und unscharf sichtbar, und eine Abweichung im Gesamtverhalten ließe sich kaum einer Ursache zuordnen.

## Konsequenzen

- Issue #2 (Original lauffähig machen) umfasst zwei Ziele: einen Windows-Build mit Oberfläche für Ebene 2 und ein Free-Pascal-Gerüst ohne Oberfläche für Ebene 1. Für das Gerüst ist die Abhängigkeit von Delphis Socket-Komponenten unerheblich, weil der Client durch einen Stub ersetzt wird.
- Issue #4 wird auf Ebene 1 zugeschnitten (Zufallsinjektion und Testfälle aus dem Gerüst). Für Ebene 2 gibt es ein eigenes Issue.
- Das Trace-Format aus Issue #3 muss beides tragen: Testfälle einzelner Prozeduren und Kennzahlen ganzer Läufe.
- Die Abschlusskriterien von Phase 1 und 2 in der Roadmap werden entsprechend angepasst.
- Ebene 2 liefert nebenbei Material für Paper 1: eine quantitative Beschreibung des Originalverhaltens, die es so bisher nicht gibt.
