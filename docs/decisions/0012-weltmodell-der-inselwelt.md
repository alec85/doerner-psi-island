# ADR 0012: Weltmodell der Inselwelt

- Status: angenommen (Alec, 2026-11-10, für die Portierung des Originals)
- Datum: 2026-11-10
- Autor: Claude Code
- Bezieht sich auf: ADR 0008, ADR 0010 (`Body` mit Ereigniswarteschlange und `pump()`), ADR 0011; Issue #20; Analyse in `docs/inselwelt-analyse.md`

## Kontext

Bevor ein ganzer Zyklus Zug für Zug gegen das Original laufen kann, braucht Psi seine Welt. Im Original sind Welt (`UPsiServer`) und Psis Anbindung (`UPsiClient`) über einen Socket getrennt, laufen aber im selben Prozess und tauschen Textnachrichten aus. Die Analyse ergab vier Punkte, die das Weltmodell festlegen:

1. Psi sieht Pixel. Die Wahrnehmung sucht schwarze Linien in einem Bild aus den Objektbitmaps der Situation. Ein Weltmodell aus Objektlisten allein reicht nicht.
2. Bedürfniswirkungen der Welt kommen als Text an und werden dabei auf zwei Nachkommastellen gerundet (`Format('%f')`). Die Rundung gehört zum Verhalten.
3. Die Welt zieht aus demselben Zufallsgenerator wie die Kognition (`MoveToSituation`, Unfall).
4. Antworten der Welt und zeitversetzte Objektänderungen (`OnTimer3`) kommen nur an den Stellen an, an denen die Kognition die Nachrichtenschleife durchläuft.

## Entscheidung

1. **Aufteilung.** `psi_gw.body.island` enthält die Welt (`TReality`, `TSituation`, Serverseite von `TPsi`) und die weltseitigen Teile des Clients: Aufbau des Situationsbildes, Liste der fälligen Objektänderungen, Teileliste für die Namen der Objekte. Die Kognition spricht die Insel nur über die `Body`-Schnittstelle an.
2. **Nachrichten im Originalformat.** Im Referenzmodus tauschen Kognition und Insel die Textnachrichten des Originals aus, über eine Warteschlange im selben Prozess statt über einen Socket. Formatierung und Zerlegung folgen dem Original, damit Rundungen wie bei `SetMotivation` exakt gleich ausfallen. Dasselbe Textformat eignet sich später als Übertragungsformat zur Bridge des PiCrawlers.
3. **`pump()`.** Jede Stelle, an der das Original `Application.ProcessMessages` oder eine Warteschleife des Clients durchläuft, ruft `body.pump()` auf. `pump()` stellt alle wartenden Nachrichten der Insel zu und löst den Timer für zeitversetzte Objektänderungen aus. Arbeitshypothese: Der Timer feuert bei jedem Durchlauf. Sie wird am Mitschnitt geprüft, bevor darauf aufgebaut wird; trifft sie nicht zu, folgt eine eigene ADR.
4. **Bilder.** Das Situationsbild wird mit NumPy aus den Bitmaps unter `reference/delphi-runtime/PsiCode/Bitmaps` zusammengesetzt (maskierte Bitmaps an ganzzahligen Positionen). Boden und Himmel werden als Polygone gefüllt; für die Wahrnehmung zählen nur die schwarzen Pixel der Objekte. Schwerpunkte der Bitmaps (`GravityPoint`) werden aus denselben Dateien berechnet statt als Tabelle mitgeliefert. Abweichend von ADR 0010 entfällt damit die Tabelle; die Bitmaps sind ohnehin im Repository (ADR 0007).
5. **Prüfung der Bilder.** Golden-Master-Bilder werden aus dem laufenden Original unter `winedbg` gelesen (Pixeldaten von `bmActSit` und der Objektbitmaps) und mit dem Python-Renderer verglichen. Gefordert ist Gleichheit aller schwarzen Pixel.
6. **Zufall.** Im Referenzmodus erhält die Insel dieselbe `RandomSource` wie die Kognition (ADR 0010).
7. **Wanduhr.** Die Wanduhr des Servers (`TReality.msec`) wird nur für auskommentierte Funktionen und Protokolle gebraucht. Sie wird durch Psis Alter ersetzt und mit `DEVIATION(ADR-0012)` markiert, wo sie in Ausgaben eingeht.

## Betrachtete Alternativen

- **Abstrakte Welt aus Objektlisten, Wahrnehmung als Nachschlagen.** Verworfen für den Referenzmodus: Die Wahrnehmung des Originals lernt Linienschemata aus Pixeln; ohne Bilder gäbe es keine Vergleichbarkeit. Für den PiCrawler wird ohnehin eine andere Wahrnehmung gebraucht; das ist eine spätere Entscheidung.
- **Strukturierte Nachrichten statt Text.** Verworfen für den Referenzmodus, weil die Rundung durch das Textformat sonst nachgebaut werden müsste und leicht vergessen wird. Im modernen Modus möglich.
- **Original-Welt per Wine als Server weiterverwenden.** Verworfen: langsam, nicht parallelisierbar (Port 2000), und der gemeinsame Zufallsgenerator ließe sich nicht teilen.

## Konsequenzen

- Vor dem Bau von `body.island` sind zu klären: die genauen Stellen von `pump()` in Kognition und Client, die Hypothese zu `OnTimer3`, der Ausschnitt von `bmActSit` und die übrigen Timer (`docs/inselwelt-analyse.md`, offene Fragen).
- Für die Golden-Master-Bilder wird das Mitschnittwerkzeug um das Auslesen von Bitmapdaten erweitert.
- Die `Body`-Schnittstelle in `psi_gw.body.base` wird um Senden, Warteschlange und `pump()` erweitert; `observe()`/`act()` bleiben für einfache Körper.

## Ausblick (keine Entscheidung)

Alec hat bei der Annahme festgehalten, dass er die Abtastung des Originals später durch eine vorgeschaltete neuronale Bildverarbeitung ersetzen möchte, etwa die ersten Schichten eines YOLO-Netzes, weil das voraussichtlich deutlich schneller ist. Das betrifft den modernen Modus (Stufe 2 nach ADR 0010) und den PiCrawler und wird dann in einer eigenen ADR entschieden. Für die Portierung bleibt es bei der Pixelabtastung des Originals.
