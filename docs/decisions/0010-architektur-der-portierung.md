# ADR 0010: Architektur der Portierung: Modernisierung, Modulstruktur, Persistenz

- Status: angenommen (Alec, 2026-11-10)
- Datum: 2026-11-10
- Autor: Claude Code, auf Wunsch von Alec
- Bezieht sich auf: ADR 0002, 0005, 0008, 0009; Issue #16

## Kontext

Alec wünscht, dass die Portierung den Code modernisiert: stärker modular, objektorientiert, mit funktionalen Elementen und mit paralleler Verarbeitung, weil das System dadurch pflegeleichter und schneller werden soll. Außerdem soll Psi später seinen Zustand über einen Neustart oder einen leeren Akku des PiCrawlers hinweg behalten.

Das Original zeigt dazu ein gemischtes Bild (`docs/delphi-inventar.md`, `docs/zufallsmitschnitt.md`):

- **Schwach modularisiert.** Die Hauptschleife steckt in der Formular-Unit `UFPsi.pas` (`TFPsi.Simulation`). Der Zustand liegt in rund 80 globalen Variablen im Interface von `UStrukturen`, dazu kommen weitere in anderen Units. `UPsiClient` mischt Netzwerkverbindung, Vorwissen, Inventar und Anzeige. Die Kognition schreibt ihre Protokolle direkt mit `writeln(prn, ...)` aus allen Prozeduren heraus.
- **An einer Stelle gut getrennt.** Welt und Kognition sind über einen TCP-Socket mit dokumentiertem Textprotokoll entkoppelt.
- **Eng verschränkt im Ablauf.** Im gebauten Programm wird an 21 Stellen die Nachrichtenschleife durchlaufen (`Application.ProcessMessages`: 6 in `UPSIMain`, 6 in `UFPsi`, 1 in `UAction`, 7 in Client und Server, 1 in der Netzanzeige `UFNetMon`; Zählung per Textsuche, einzelne Treffer können in Kommentaren stehen). Dort treffen Antworten der Welt ein, und die Welt zieht dabei aus demselben Zufallsgenerator wie die Kognition. Die Reihenfolge der Zufallszüge hängt also davon ab, an welcher Stelle der Überlegung die Welt zum Zug kommt.
- **Lesen ist Schreiben.** 93 % aller Zufallszüge entstehen beim Durchlaufen von Synapsen. `Junction` prüft zufällig, ob eine Synapse überträgt, und lässt sie über `Decay` vorher zufällig vergessen. Jeder Gedächtniszugriff verändert Gewichte und verbraucht Zufallszahlen in einer Reihenfolge, die von der Reihenfolge der Synapsenlisten abhängt.
- **Keine Persistenz.** Jeder Lauf beginnt mit leerem Gedächtnis. Geladen werden nur Parameter und Vorwissen (welche Handlungen an welchen Objekten möglich sind).

Gleichzeitig verlangen ADR 0008 und 0009, dass die Neuimplementierung Zug für Zug mit dem Original verglichen werden kann.

## Entscheidung

### Zwei Stufen

**Stufe 1** portiert in eine moderne, modulare Struktur, deren Verhalten in einem **Referenzmodus** Zug für Zug mit dem Original übereinstimmt. Modernisiert werden hier Struktur, Zustandshaltung, Typen und Schnittstellen; das Verhalten bleibt gleich.

**Stufe 2** umfasst Modernisierungen, die das Verhalten verändern: getrennte Zufallsquellen, parallele Prozesse, andere Datenstrukturen oder Algorithmen. Jede davon wird als `DEVIATION(ADR-NNNN)` im Code markiert, in einer eigenen ADR begründet und statistisch gegen das Original geprüft (Ebene 2, Analyseplan). Der Referenzmodus bleibt erhalten, solange er sich mit vertretbarem Aufwand pflegen lässt, und dient als Regressionstest.

Der exakte Vergleich ist damit das Sicherheitsnetz für den Umbau: Jede Strukturänderung in Stufe 1 ist sofort darauf prüfbar, ob sie das Verhalten unbeabsichtigt verändert.

### Prinzipien

**Kein globaler Zustand.** Der gesamte Zustand von Psi liegt in einem Objekt `PsiState`: Gedächtnisnetz, Bedürfnisse und Speicher, Modulatoren, Handlungstendenzen, Arbeitsgedächtnis (`KZG`, `Prefront`, `GoalList`, aktuelle Situation, aktuelles Objekt), Leistungszähler, Alter und Takt. Der Zustand der Welt liegt im jeweiligen `Body`. Prozeduren erhalten den Zustand ausdrücklich als Argument oder sind Methoden der Objekte, denen er gehört. Das ist die Voraussetzung für Persistenz, für viele Läufe parallel und für isolierte Tests.

**Schichten mit Abhängigkeiten nach innen.** Das Gedächtnisnetz kennt nichts außer sich selbst. Motivation, Wahrnehmung und Handlungsregulation bauen darauf auf. Der Verhaltenszyklus (`agent`) verbindet sie und spricht die Welt nur über die `Body`-Schnittstelle an. Läufe, Protokollierung und Oberfläche liegen außen und hängen sich über Beobachter an. Der Kern schreibt keine Dateien und gibt nichts aus; statt `writeln(prn, ...)` meldet er strukturierte Ereignisse, die `psi_gw.tracing` aufzeichnet.

**Objektorientiert, wo Identität und Zustand im Spiel sind.** Gedächtnisnetz, Neuronen, Synapsen, der Agent, Körper und Welten sind Objekte mit klarer Verantwortung. Die Aufzählungstypen des Originals (`TMotiv`, `TModulat`, `TAxon`, `TTendenz`, `TIntProc`, `TLeistung`) werden zu Python-Enums mit Dörners Begriffen im Docstring.

**Funktional, wo gerechnet wird.** Motivstärke, Handlungstendenzen, Fortschreibung der Modulatoren, die Mathematik der Zielauswahl und die Bewertung von Plänen (`S_Nutzen`, `S_Aufwand`, `S_Gewissheit` und Verwandte) werden reine Funktionen auf unveränderlichen Werten. Sie lassen sich einzeln testen und später gefahrlos austauschen.

**Nebenwirkungen gebündelt.** Dass Lesen im Gedächtnis schreibt, wird nicht versteckt. Die Übertragung über eine Synapse (heute `Junction` mit `Decay`) ist die einzige Stelle, an der Gewichte beim Lesen verändert und Zufallszahlen gezogen werden, und sie heißt im Code auch so (`transmit`). Alle Such- und Assoziationsverfahren gehen über diese Stelle.

**Zufall nur über `RandomSource`.** Im Referenzmodus teilen sich Welt und Kognition eine einzige Quelle (`DelphiRandom`), wie im Original. Eine protokollierende Hülle (`RecordingSource`) hält jeden Zug mit einer Aufrufstelle fest, deren Namen denen in `psi_gw.tracing.delphi_random_sites` entsprechen, sodass sich die Züge direkt mit dem Mitschnitt des Originals vergleichen lassen. Im modernen Modus bekommt jede Komponente einen eigenen Strom, abgeleitet aus dem Seed (`numpy.random.SeedSequence.spawn`).

**Abgleich von Welt und Kognition.** Damit der Referenzmodus die Zugreihenfolge trifft, ruft der Agent an denselben Stellen wie das Original einen Abgleich mit der Welt auf (`body.pump()`), an dem eingetroffene Rückmeldungen verarbeitet werden. Die `Body`-Schnittstelle wird dafür um eine Ereigniswarteschlange erweitert. Für die Inselwelt ist das synchron und deterministisch; für den PiCrawler entspricht es dem Abholen eingegangener Sensordaten.

**Parallelität dort, wo sie nichts verfälscht.** Innerhalb eines Psi läuft Stufe 1 sequenziell, weil die Durchlaufreihenfolge des Netzes Zufallsfolge und Gewichte bestimmt. Viele Läufe mit verschiedenen Seeds laufen dagegen von Anfang an parallel in eigenen Prozessen; das ist der größte praktische Gewinn. Für den Global Workspace (Phase 3), in dem spezialisierte Prozesse gleichzeitig um Zugang konkurrieren, wird Parallelität so gebaut, dass Ergebnisse nicht vom zeitlichen Zufall der Threads abhängen: eigener Zufallsstrom je Prozess, Abarbeitung in Takten, feste Reihenfolge beim Zusammenführen. Threads oder `asyncio` gibt es nur an der Grenze zur Hardware, etwa in der Bridge zum Crawler.

**Erst messen, dann beschleunigen.** Ob die Portierung Leistungsprobleme hat, ist offen. Optimiert wird erst nach einer Messung, und zuerst der heiße Pfad (Synapsenübertragung), etwa mit NumPy, Numba oder einer Erweiterung in Rust. Die Schnittstelle bleibt dabei gleich, und der Referenzmodus muss danach weiterhin Zug für Zug stimmen.

**Oberfläche nur lesend.** Eine spätere Visualisierung arbeitet auf Schnappschüssen und aufgezeichneten Ereignissen. Sie verändert keinen Zustand und zieht keine Zufallszahlen; im Original tun EEG-Anzeige und Sprachausgabe beides potenziell.

### Modulstruktur

| Modul | Inhalt | Herkunft im Original |
|---|---|---|
| `psi_gw.random_source` | `RandomSource`, `DelphiRandom`, `NumpySource`, `ReplaySource`, neu `RecordingSource` | Delphi-Laufzeitbibliothek |
| `psi_gw.state` | `PsiState`, Schnappschuss und Wiederherstellung | globale Variablen in `UStrukturen` und weiteren Units |
| `psi_gw.params` | Parameter, Startwissen, Vorwissen | `UParam`, `Psi.Ini`, `PsiDaten/*.Dat`, Vorwissen aus `UPsiClient` |
| `psi_gw.memory.network` | `Neuron`, `Synapse`, Achsen (`por`, `ret`, `sub`, `sur`, `toSatis`, `toGoal`, `toNeed`, `ToAvers`, `Lan`, `Pic`), `MemoryNetwork` mit `connect`, `reinforce`, `transmit`, `trace`, `look_for` | `UStrukturen` (Netzoperationen) |
| `psi_gw.memory.lists` | geordnete Synapsenlisten mit der Reihenfolgesemantik des Originals, `section`, `random_choice` und Verwandte | `UStrukturen` (Listenoperationen) |
| `psi_gw.memory.protocol` | Protokollgedächtnis | `UStrukturen` (`Protocoll`, `GenProtEl`, `ReInforceRetro`) |
| `psi_gw.motivation` | Bedürfnisse, Modulatoren, Handlungstendenzen, `need_and_competence`, `motivation`, `goal_gen`, `intermediate_goals` | `UStrukturen`, `UPSIMain` |
| `psi_gw.perception` | Wahrnehmung, sensorische Schemata | `UPercept` |
| `psi_gw.regulation` | Rasmussen-Leiter: `look_around`, `association`, `confirmation`, `automatism`, `plan`, `plan_and_do`, `what_could_be_done`, `rest` | `UPSIMain` |
| `psi_gw.action` | Ausführung über den Körper, Inventar | `UAction`, `UBag` |
| `psi_gw.agent` | Verhaltenszyklus | `TFPsi.Simulation` in `UFPsi` (ohne Oberfläche) |
| `psi_gw.body` | `Body`-Schnittstelle mit Ereigniswarteschlange; `body.island` als Inselwelt | `UPsiServer`, weltseitige Teile von `UPsiClient` |
| `psi_gw.tracing` | Formate, Konverter, Aufzeichnung strukturierter Ereignisse | `USmallProtokoll` und die `writeln(prn, ...)`-Ausgaben |
| `psi_gw.persistence` | Checkpoints | neu |
| `psi_gw.workspace` | Global Workspace | neu, Phase 3 |
| `psi_gw.ui` | optionale, nur lesende Visualisierung | `UF*`-Formulare, `UFace` als Vorbild |

Nicht portiert werden Oberflächen-Units als solche, Sprachausgabe (`USound`), HTML- und Info-Ausgabe (`UHtml`, `UInfo`). Hilfsfunktionen aus `Menue.Pas` (Geometrie) und `UGeneral` wandern, soweit gebraucht, in ein kleines Hilfsmodul.

### Persistenz

**Jetzt, weil es in Stufe 1 fast nichts kostet:** Der gesamte Zustand liegt nachweislich in `PsiState` und im Zustand der Welt. Dafür gibt es einen Abnahmetest, der vom ersten portierten Modul an mitläuft: Ein Lauf wird nach `k` Zyklen in einen Schnappschuss geschrieben, in einem frischen Prozess wiederhergestellt und fortgesetzt. Die Fortsetzung muss Zug für Zug mit einem ununterbrochenen Lauf übereinstimmen, einschließlich Zufallszustand. Vergisst die Implementierung irgendwo verborgenen Zustand, schlägt dieser Test fehl. Später nachzurüsten wäre deutlich teurer, weil verborgener Zustand dann schon im Code verteilt wäre.

**Später, in einer eigenen ADR:** Dateiformat mit Versionsnummer und Migrationen (kein `pickle`, weil es zerbrechlich ist und beim Laden Code ausführt; eher komprimiertes JSON oder MessagePack, für große Netze SQLite), atomares Schreiben (temporäre Datei, dann Umbenennen), mehrere aufbewahrte Checkpoints, Auslöser: alle `N` Zyklen, beim regulären Beenden und auf ein Signal des Körpers, etwa niedrigen Akkustand.

**Bedeutung des Fortsetzens.** In der Simulation wird die Welt mitgesichert, und der Lauf geht exakt weiter. Beim realen Crawler lässt sich die Welt nicht sichern: Psi wacht mit seinem Gedächtnis auf, nimmt die Situation neu wahr, und das Protokollgedächtnis erhält eine gekennzeichnete Lücke. Alter und Takt laufen weiter. Ob der Akkustand des Crawlers später als Dörners Energiebedarf (Hunger) in die Motivation eingeht, ist eine eigene Entscheidung.

### Bekannte Risiken der Portierung

- **Reihenfolge der Synapsenlisten.** Das Original arbeitet mit verketteten Listen, in die vorn (`AddListEl`) oder hinten (`AppListEl`) eingefügt wird. Diese Semantik muss exakt erhalten bleiben, weil sie die Zugreihenfolge bestimmt.
- **Abgleichstellen mit der Welt.** Die 21 Stellen mit `Application.ProcessMessages` müssen einzeln geprüft und als `body.pump()` nachgebildet werden. Fehler zeigen sich als verschobene Züge von `SetMotivation` im Vergleich.
- **Rechengenauigkeit.** Das Original rechnet teils mit 80 Bit. Behandlung nach ADR 0005.
- **Welt hängt an Bildern.** Die Welt bestimmt Positionen von Objekten über Schwerpunkte von Bitmaps (`UBitmaps.GravityPoint`). Diese Werte werden einmal aus den Bildern berechnet und als Tabelle mitgeliefert.

## Betrachtete Alternativen

- **Erst wörtlich übersetzen, später umbauen.** Verworfen: Die globalen Variablen und die Verschränkung mit der Oberfläche würden in Python festgeschrieben und müssten in einem zweiten großen Schritt wieder aufgelöst werden. Der Referenzmodus bietet dieselbe Sicherheit, ohne diesen Umweg.
- **Neuentwurf nach dem Buch ohne Bezug auf den Code.** Verworfen, weil damit keine Reproduktion belegt werden kann (ADR 0003).
- **Parallele Netzdurchläufe sofort.** Verworfen, weil sie die Vergleichbarkeit zerstören und der Nutzen ungemessen ist. Bleibt eine Option für Stufe 2.

## Konsequenzen

- Die Portierung beginnt mit `psi_gw.memory` aus `UStrukturen`, zusammen mit `RecordingSource` und dem Abnahmetest für Schnappschuss und Wiederherstellung.
- Die `Body`-Schnittstelle wird um die Ereigniswarteschlange und `pump()` erweitert; das geschieht mit der Inselwelt.
- `docs/architecture.md` wird nach Annahme dieser ADR an die Modulstruktur angepasst.
- Der Referenzmodus kostet zusätzlichen Aufwand, solange er gepflegt wird. Dafür bleibt jeder spätere Umbau gegen das Original prüfbar.
