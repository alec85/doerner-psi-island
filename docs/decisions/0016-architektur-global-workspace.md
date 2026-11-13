# ADR 0016: Architektur des Global Workspace

- Status: angenommen (Alec, 2026-11-11)
- Datum: 2026-11-10
- Autor: Claude Code
- Bezieht sich auf: Roadmap Phase 3, ADR 0010 (Referenzmodus, Parallelität), ADR 0015 (Schalter für Artefakte), Analyseplan mit Nachträgen 1 und 2

## Kontext

Phase 3 erweitert PSI um einen Global Workspace. Die Roadmap nennt als Hypothese, dass sich Dörners Selektionsschwelle als Hysterese im Wettbewerb um den Workspace deuten lässt, und als Bewertungsrahmen die Indikatoreigenschaften der Global Workspace Theory nach Butlin et al. (2023):

- GWT-1: mehrere spezialisierte Systeme, die parallel arbeiten können (Module),
- GWT-2: ein Workspace mit begrenzter Kapazität, also ein Engpass im Informationsfluss und ein Mechanismus selektiver Aufmerksamkeit,
- GWT-3: globaler Broadcast, der Inhalt des Workspace steht allen Modulen zur Verfügung,
- GWT-4: zustandsabhängige Aufmerksamkeit, mit der der Workspace Module nacheinander befragen kann, um komplexe Aufgaben zu lösen.

Was das portierte Original davon schon hat:

- Spezialisierte Prozesse gibt es (Wahrnehmung mit `HyPercept`, Bedürfnisse und Motivbildung, Erinnern mit `Association` und den `Rem…`-Routinen, Planen, Manipulieren und Fortbewegen). Sie laufen aber streng nacheinander, in der festen Abfolge der Rasmussen-Leiter.
- Einen Engpass mit Hysterese gibt es genau an einer Stelle: das aktuelle Motiv. Ein anderes Motiv gewinnt nur, wenn es das aktuelle um die Selektionsschwelle übertrifft (`select_motive`).
- Die Zielliste (`GoalList`) wirkt wie ein schwacher Broadcast: Sie bestimmt, wonach `LookAround`, `Automatismus`, `PlanenUndTun` und `WhatCouldBeDone` suchen. Ihre Zusammensetzung hängt aber nur vom Motiv ab, nicht von einem Wettbewerb der Inhalte.
- In Bachs MicroPsi (Bach, Principles of Synthetic Intelligence, Abb. 8.2) gibt es einen „Access Memory (Workspace)“ zwischen Wahrnehmung, Gedächtnis und Handlungsauswahl; dort wirkt die Selektionsschwelle ausdrücklich als Bonus der aktiven Absicht, also als Hysterese.

Die Erweiterung muss im Referenzrahmen messbar bleiben: abschaltbar, deterministisch bei festem Seed, gepaart gegen die Vergleichsbasis auswertbar.

## Vorschlag

**1. Workspace als eigener Zustand mit begrenzter Kapazität.** `psi_gw.workspace` hält bis zu `K` Inhalte. Ein Inhalt ist ein Verweis auf ein Neuron mit Art und Herkunft: Motiv (Bedarfsindikator), Ziel (Schema aus der Zielliste), Objekt der aktuellen Situation, Erinnerung (Start- und Zielprotokoll einer Assoziation), Plan. `K` ist ein Parameter; der Vorschlag ist, ihn mit dem Auflösungsgrad zu koppeln (hoher Auflösungsgrad, mehr Plätze), was Dörners Beschreibung der „Breite der Aufmerksamkeit“ entspricht.

**2. Module schlagen vor, der Workspace wählt.** In jedem Takt reichen die Module Kandidaten mit einer Stärke ein: Bedürfnisse mit ihrer Motivstärke, Objekte der Situation mit Neuigkeit (`ManipUncertainty`) und Schmerzerwartung (`ExpectPain`), Ziele mit dem Gewicht ihrer Zielverbindung, Erinnerungen mit `S_Nutzen` × `S_Gewissheit`. Gewählt werden die `K` stärksten. Inhalte, die schon im Workspace sind, erhalten einen Bonus. Kernhypothese: Dieser Bonus ist die Selektionsschwelle. Für das Motiv reproduziert das die bisherige laterale Hemmung; neu ist, dass dieselbe Hysterese für alle Arten von Inhalten gilt.

**3. Broadcast als Vorrang, nicht als Ersatz.** Die Prozeduren des Originals bleiben, sie lesen aber den Workspace: `GoalGen` nimmt Ziele im Workspace immer auf, `LookAround` und `WhatCouldBeDone` prüfen Objekte im Workspace zuerst, `Association` beginnt bei Erinnerungen im Workspace. Damit bleibt der Abstand zum Referenzmodus klein und der Effekt jeder Broadcast-Stelle einzeln messbar, wie bei den Schaltern aus ADR 0015.

**4. Takte statt Nebenläufigkeit.** Die Module rechnen innerhalb eines Takts in fester Reihenfolge mit je eigenem, aus dem Seed abgeleiteten Zufallsstrom, und die Kandidaten werden in fester Reihenfolge zusammengeführt (ADR 0010). Damit ist GWT-1 als logische Parallelität erfüllt, ohne dass Ergebnisse vom Zeitverhalten von Threads abhängen.

**5. GWT-4 erst in einem zweiten Schritt.** Das Befragen von Modulen nacheinander ist in der Rasmussen-Leiter schon angelegt (`LookAround`, dann `Automatismus`, dann `PlanenUndTun`, dann `WhatCouldBeDone`). Ein zweiter Schritt kann diese Abfolge vom Workspace-Inhalt abhängig machen statt fest. Das gehört nicht in den ersten Schritt, damit zuerst die Wirkung von Engpass und Broadcast allein gemessen wird.

**6. Ausgangsbasis.** Der Workspace wird auf dem modernen Modus aufgesetzt (alle Schalter aus ADR 0015 an), sofern die laufende Messung der Schalter keinen Grund dagegen liefert. Verglichen wird gepaart: moderner Modus gegen moderner Modus mit Workspace, dieselben Seeds wie die Vergleichsbasis.

**7. Messung.** Neben P1 bis P6 kommen Kennzahlen hinzu, die die Hypothese direkt prüfen: Verweildauer von Inhalten im Workspace, Motivwechsel pro 100 Zyklen, Abbrüche begonnener Pläne, Anteil der Zyklen mit Hintergrundziel-Erfüllung („en passant“-Befriedigung). Die Hysterese-Hypothese wird geprüft, indem der Bonus einmal gleich der Selektionsschwelle, einmal fest und einmal null gesetzt wird.

## Betrachtete Alternativen

- **Nur das Motiv als Workspace deuten.** Das wäre eine Umbenennung ohne neue Vorhersage. Verworfen als Erweiterung, aber als Grenzfall `K = 1` und nur Motive im Experiment enthalten.
- **Echte Nebenläufigkeit (Threads, asynchrone Module).** Verworfen: Ergebnisse hingen vom Zeitverhalten ab, Läufe wären nicht reproduzierbar (ADR 0005, ADR 0010).
- **Workspace ersetzt die Rasmussen-Leiter.** Verworfen für den ersten Schritt: zu großer Abstand zum Original, Effekte nicht mehr einzelnen Änderungen zuzuordnen.
- **Neuronale Umsetzung (Aktivierungsausbreitung mit Schwelle statt Liste).** Theoretisch näher an Dörners Quads, aber schwer zu parametrieren und zu messen. Kandidat für Phase 6 (SNN).

## Entscheidungsfragen an Alec

1. Ist die Hysterese-Hypothese (Bonus im Workspace = Selektionsschwelle) die zentrale Aussage von Paper 1?
2. Welche Inhalte sollen konkurrieren: nur Motive und Ziele, oder auch Objekte, Erinnerungen und Pläne wie vorgeschlagen?
3. Soll die Kapazität `K` fest sein oder mit dem Auflösungsgrad wachsen?
4. Ausgangsbasis moderner Modus (Vorschlag) oder Referenzmodus?

## Entscheidungen (Alec, 2026-11-11)

- Frage 2: Es konkurrieren Motive, Ziele, Objekte, Erinnerungen und Pläne, wie vorgeschlagen.
- Frage 3: Die Kapazität `K` wächst mit dem Auflösungsgrad.
- Frage 4: Ausgangsbasis ist der moderne Modus (`Variant.from_names("all")`).
- Frage 1: Die Hysterese-Hypothese (Bonus im Workspace = Selektionsschwelle, für alle Inhaltsarten) ist die Kernaussage von Paper 1.

## Konsequenzen

- Neues Paket `psi_gw.workspace`, Schalter `Variant.workspace` mit Parametern, Golden-Master-Tests bleiben unberührt.
- Der Analyseplan bekommt einen Nachtrag mit den neuen Kennzahlen, bevor die Workspace-Läufe ausgewertet werden.

## Quellen

- Butlin, P. et al. (2023): Consciousness in Artificial Intelligence: Insights from the Science of Consciousness. arXiv:2308.08708, Tabelle 1.
- Bach, J.: Principles of Synthetic Intelligence (Entwurf im Projekt, `psi-oup-version-draft-jan-08.pdf`), Abschnitte 4.6.2 und 6.2.3, Abb. 8.2.
- Dörner, D.: Die Mechanik des Seelenwagens, S. 29, 98 f. (Nebenziele, Selektionsschwelle), S. 182 bis 186 (Orientierung).
