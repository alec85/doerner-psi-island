# ADR 0018: Zufall bei Gleichstand im Workspace

- Status: angenommen (Alec, 2026-11-12)
- Datum: 2026-11-12
- Autor: Claude Code

## Kontext

Im Wettbewerb um den Workspace (ADR 0016) entscheidet bei gleicher effektiver Stärke der Neuronenname (`Workspace.choose`). Auf der Insel ist das kein Randfall: Alle Ziele des Nukleo-Motivs haben bei voller Bedürfnisaktivität denselben Wert, und welche davon in den Workspace kommen, hängt dann von der alphabetischen Ordnung ihrer Namen ab. Die gedächtnislose Auswahl ist dadurch künstlich stabil, was den Kontrast der Bedingung E zu B mitbestimmt. In Paper 1 wird das als Grenze berichtet (`paper/methoden/workspace.md`).

## Entscheidung

Für künftige Experimente entscheidet bei Gleichstand der Zufall.

- Der Zufall kommt aus einer eigenen `RandomSource` des Workspace, abgeleitet aus dem Seed des Lebens (z. B. `numpy.random.SeedSequence(seed).spawn` mit festem Index für den Workspace). Der Hauptstrom von Psi wird dadurch nicht berührt, und Bedingung A bleibt bytegleich mit dem modernen Modus.
- Gezogen wird nur, wenn tatsächlich ein Gleichstand an der Grenze der Kapazität vorliegt (sonst wäre die Zahl der Züge von irrelevanten Gleichständen abhängig).
- Der Zustand der Workspace-Quelle gehört in den Schnappschuss.
- Umgesetzt wird das als Schalter in `Variant` (Vorschlag: `workspace_ties=name|random`, Standard `name`), damit die Läufe von Paper 1 mit dem bestehenden Code reproduzierbar bleiben. Neue Analysepläne legen `random` fest.

## Betrachtete Alternativen

- Namensordnung beibehalten: deterministisch ohne zusätzliche Quelle, aber willkürlich und mit Einfluss auf die Ergebnisse.
- Zufall aus dem Hauptstrom von Psi: würde jede Workspace-Bedingung schon durch die Zahl der Züge vom modernen Modus entfernen und Effekte des Workspace mit Effekten verschobener Zufallszahlen vermischen.
- Gleichstand nach Eintrittszeit oder Stärke der Vorperiode: bringt selbst eine Form von Gedächtnis in die gedächtnislose Auswahl und widerspricht damit Bedingung E.

## Konsequenzen

- Die bestätigten Ergebnisse von Paper 1 bleiben unverändert gültig; sie gelten für die Namensordnung und werden so berichtet.
- Eine Folgestudie (z. B. zu H3) läuft mit `workspace_ties=random` und braucht einen eigenen Analyseplan.
- Umsetzung offen: Schalter, eigene Quelle, Schnappschuss, Tests (Bedingung A unverändert, Wiederaufnahme gleich ununterbrochenem Lauf, Züge nur bei Gleichstand).
