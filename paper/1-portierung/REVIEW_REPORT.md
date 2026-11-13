# Kritischer Review: Portierung des PSI-Inselagenten

**Urteil: grundlegende Überarbeitung; in der vorliegenden Fassung nicht einreichungsreif.** Die Arbeit hat einen plausiblen Beitrag als dokumentierte Software-Rekonstruktion. Ihre stärksten Befunde sind die detaillierten Referenzvergleiche und die aufgedeckten Implementierungseffekte. Mehrere zentrale Sätze behaupten aber mehr, als diese Belege zeigen. Sprachliche Glättung allein reicht nicht.

- Reviewdatum: 12. November 2026; Reviewer: Codex.
- Geprüfter Stand: `alec85/psi-gw`, Commit `ef15fb05becdfcd8a149b182e63da8690e955756`.
- Gegenstand: `manuskript.tex`, das achtseitige PDF, Literaturdateien, Methodenbausteine, Tabellen, Analysepläne, ADRs, Auswertungscode und archivierte Auswertungen. Zeilenangaben beziehen sich auf diesen Stand.
- Zweck: konkrete Überarbeitungsaufträge für Claude. **Blocker** gefährden die zentrale Aussage; **Major** betreffen Belegführung oder Reproduzierbarkeit; **Minor** betreffen Darstellung.

## Was belastbar ist und erhalten bleiben sollte

Die Beschränkung auf eine konkrete historische Implementierung ist wissenschaftlich sinnvoll. Der Bericht über Seed 16 benennt beeindruckend genaue Vergleichsgrößen. Auch das ausdrückliche Beibehalten unerwünschter Effekte im Referenzmodus, die Trennung vom modernen Modus und die Offenlegung der Heap-Abweichung sind Stärken. Diese Befunde tragen ein enger gefasstes Paper bereits besser als die weitergehende Behauptung einer allgemein originalgetreuen PSI-Implementierung.

## Prioritäten

| ID | Gewicht | Problem | Erforderliches Ergebnis |
|---|---|---|---|
| P1-01 | Blocker | Verteilungsgleichheit wird ohne Nachweis behauptet | Aussage zurücknehmen oder echte Äquivalenzstudie vorlegen |
| P1-02 | Blocker | „draw for draw“ verallgemeinert einen begrenzten Trace-Vergleich | Nachweise nach Seed, Messgröße und Laufabschnitt trennen |
| P1-03 | Major | Öffentliches Paket wäre ohne `reference/` nicht ohne Weiteres ausführbar | Abhängigkeits- und Reproduktionsplan konkretisieren |
| P1-04 | Major | Abstürze und vollständige Fälle werden unzureichend getrennt | Softwareausfälle separat berichten; Effekte auf 97 vollständige Paare begrenzen |
| P1-05 | Major | Variantenprovenienz und Einzelursachen sind nicht sauber belegt | Manifest pro Lauf und vorsichtige Interpretation des Screenings |
| P1-06 | Major | Leistungsraten hängen an einer selbst veränderten Zeitskala | Exposition und Robustheit der Leistungsinterpretation prüfen |
| P1-07 | Major | Aussagen über die Software früherer Humanstudien sind unbelegt | Historische Versionszuordnung nachweisen oder Aussage streichen |
| P1-08 | Major | Zentrale Artefaktbefunde brauchen unmittelbar prüfbare Belegketten | Code-, Buch- und Laufbelege je Befund zusammenführen |
| P1-09 | Major | Geltungsbereich und Motivdominanz sind zu pauschal | Parameter, Gewichtung und Generalisierungsgrenzen offenlegen |
| P1-10 | Minor/Major | Literatur- und Darstellungsdefizite | Recherche schließen, Tabellen reparieren, Ergebnisübersicht ergänzen |

## P1-01 — Verteilungsgleichheit ist ausdrücklich noch offen

**Fundstellen:** `manuskript.tex:50,86,122`; `docs/analyseplan-referenzlaeufe.md`, Nachtrag 3, Punkt 2; `analysis/referenzlaeufe/stichprobe/README.md`.

Das Manuskript erklärt nach dem Auseinanderlaufen einzelner Trajektorien die zweite Treuestufe für erreicht und behauptet „distributional equivalence“. Der Analyseplan hält dagegen ausdrücklich fest, dass offen ist, ob das systematisch anders behandelte Heapbyte die Verteilungen verschiebt. Vier der sieben zusätzlich verglichenen Leben laufen ab einer anderen Richtungsentscheidung auseinander. Eine gemeinsame mechanistische Herkunft beweist keine gleichen Verteilungen, insbesondere bei einer systematisch entfernten Fehlerquelle.

**Auftrag:** Diese Formulierungen in Abstract, Ergebnissen und Diskussion konsistent auf den erreichten Nachweis begrenzen. Eine zulässige Kernaussage lautet: ausgewählte vollständige oder partielle Referenzverläufe werden exakt reproduziert; für andere Seeds ist eine bekannte Abweichungsursache dokumentiert; Verteilungsgleichheit über vollständige Leben ist nicht nachgewiesen. Soll die stärkere Aussage bleiben, braucht es ausreichend viele tatsächliche Originalläufe, begründete Äquivalenzgrenzen und eine entsprechend geplante Analyse. Ein Unterschiedstest ohne Signifikanz ersetzt diese nicht.

**Erledigt, wenn:** Kein Satz eine ungeprüfte Verteilungsgleichheit als Resultat ausgibt. Neue Daten sind für eine ehrlich begrenzte Fassung nicht zwingend erforderlich. Eine neue Studie darf nicht nachträglich als Bestandteil der bisherigen Bestätigung erscheinen.

## P1-02 — Die Reichweite des exakten Vergleichs muss überall identisch beschrieben sein

**Fundstellen:** `manuskript.tex:25,36,64,76,84`; `tests/test_life.py`; `src/psi_gw/regulation/recall.py:57–68,153–163`; ADR 0014.

Im Abstract heißt es, die Portierung reproduziere das Original „draw for draw“. Individuell verglichen wurden aber die ersten 75.000 Ziehungen bis ungefähr Zyklus 70. Die vollständigen 739 Zyklen sind durch Protokolle, Handlungen und Abschlussdateien abgesichert, nicht durch einen vollständigen Mitschnitt aller internen Ziehungen und Zustände. Gleichheit beobachteter Ausgaben und Gleichheit aller internen Entscheidungen sind unterschiedliche Nachweise.

Außerdem sagt Zeile 84 pauschal, die Portierung lese kein drittes Zeichen. Im Referenzmodus bildet `continue_direction` den Stapelrest gerade nach; nur das nicht reproduzierte Heapbyte in `remember_dir` und die bereinigte Variante sind anders zu beschreiben. Auch „identisch bis zum Absturz“ braucht eine Einschränkung: Für Seed 1035 dokumentiert die Stichprobenauswertung bereits in Zyklus 39 eine abweichende Protokollzeile ohne Änderung der gewählten Lokomotion.

**Auftrag:** Eine Evidenzmatrix ergänzen: Seed; Entwicklungs- oder Prüfrolle; maximale Laufdauer; verglichene Protokolle; tatsächlicher Random-Trace-Umfang; erste Abweichung; Auswirkung auf Handlungen; bekannte Normalisierungen. Ausgeblendete Wanduhrdaten und vereinheitlichte Protokollzeilen müssen genannt werden. Die Behauptung vollständiger Identität muss jeweils die verglichenen Observablen benennen.

**Erledigt, wenn:** Abstract, Tabelle 1, Diskussion und die Beschreibung in Paper 2 dieselbe Reichweite angeben. „Alle beobachteten Abweichungen“ bleibt eine Aussage über die geprüfte Stichprobe, keine Vollständigkeitsgarantie für alle Seeds oder Programmteile.

## P1-03 — Verfügbarkeit ist Teil des Beitrags, nicht nur ein späterer URL-Platzhalter

**Fundstellen:** `manuskript.tex:60,130,134`; `src/psi_gw/params.py:21–23`; `src/psi_gw/body/island/world.py:22–23`; `src/psi_gw/body/island/bitmaps.py:28–29`.

Die Standardausführung liest Parameter und Weltdateien aus `reference/delphi-original/...` und Bitmaps aus `reference/delphi-runtime/...`. Viele Tests brauchen zusätzlich historische Rohprotokolle oder die Originaldatei `Psi.exe`. Gleichzeitig soll das öffentliche Repository ausdrücklich ohne `reference/` entstehen. Daraus folgt derzeit keine selbstständig ausführbare öffentliche Referenz. Ob sich benötigte Dateien rechtmäßig beilegen lassen, ist hier nicht entschieden; das technische Abhängigkeitsproblem besteht unabhängig davon.

**Auftrag:** Eine Tabelle aller notwendigen Eingaben erstellen: Dateiart, Zweck, Herkunft, Hash, öffentlicher Lieferstatus, erlaubter Beschaffungsweg und betroffene Befehle. Klären, welche Auswertungen ohne proprietäre Ausgangsdateien ausführbar sein werden und welche Referenzprüfungen nur mit einer eigenen Originalkopie möglich sind. Versionsstände für Python, NumPy, Wine, Schriftbestand und Laufkonfiguration festhalten. Ein aufgeräumtes privates Repository ist noch kein geprüftes öffentliches Reproduktionspaket.

**Erledigt, wenn:** Eine frische Umgebung mit genau dem vorgesehenen Veröffentlichungsumfang dokumentierte Beispielausführung und Tabellenreproduktion erfolgreich ausführt, oder die verbleibenden Beschränkungen ausdrücklich im Paper stehen. Keine Veröffentlichung oder Lizenzentscheidung allein zur Erledigung dieses Reviews vornehmen.

## P1-04 — 3/100 Softwareausfälle sind kein belegter allgemeiner Absturzanteil des Originals

**Fundstellen:** `manuskript.tex:25,112–114`; `analysis/varianten/all-100/vergleich.json`; `analysis/referenzlaeufe/stichprobe/README.md`.

Die drei Ausfälle stammen aus 100 Referenzmodus-Läufen der Portierung. Zwei konnten im Original an derselben Stelle bestätigt werden. Beim dritten Seed erreicht das Original aufgrund der Heap-Abweichung den vorhergesagten Fehler nicht. Die Abstractformulierung „about one life in thirty“ verwischt diese Unterscheidung und behandelt eine kleine, konfigurationsabhängige Stichprobenquote wie eine Eigenschaft des historischen Programms.

Die Leistungsanalyse schließt die drei unvollständigen Baseline-Leben aus. Damit schätzt sie den Effekt unter der Bedingung eines vollständigen Referenzlaufs. Gerade eine Robustheitsverbesserung durch den Nil-Schutz wird mit dieser Auswahl nicht als vollständiger Nutzen erfasst. Ein Softwarestillstand ist zudem kein biologisch interpretierter `Exitus`; beides darf nicht vermischt werden.

**Auftrag:** Flusstabelle aller 100 Seeds, Ausfälle nach Bedingung und Grund, klare Trennung von Laufende, Exitus und Programmstillstand. 3/100 als beobachtete Quote der Portierung berichten und Originallaufbestätigungen getrennt angeben. P1–P6 als vollständige-Paare-Analyse kennzeichnen. Eine sinnvolle Sensitivität kann gemeinsame Beobachtungsfenster bis zum Abbruch prüfen; fehlende Restläufe nicht willkürlich imputieren.

**Erledigt, wenn:** Abstract, Tabellenlegende und Schlussfolgerung die bedingte Analyse korrekt benennen und keine ungemessene allgemeine Absturzrate des Originals behaupten.

## P1-05 — Variantenlisten und kausale Zuschreibung müssen genauer werden

**Fundstellen:** `manuskript.tex:90,114,128`; `analysis/varianten/all-100/vergleich.json`; `analysis/grundlinie-modern/README.md`; `scripts/compare_variants.py:70–72`.

Die Metadaten des Vergleichs „all-100“ listen sechs Schalter und lassen `guard_nil_dereferences` aus. Das ist **noch kein Beweis für einen falschen Versuchsarm**: Die Baseline-README erklärt, dass die ersten 20 modernen Läufe vor Einführung dieses Schalters entstanden und dort keinen Nil-Zugriff erreichten; in den späteren 80 Läufen griff der Schutz zweimal. `compare_variants.py` übernimmt jedoch die Variantenliste nur aus dem ersten gemeinsamen Seed. Das summarische Manifest beschreibt somit eine heterogene Entstehung unzureichend.

Aus Einzelschalter-Screenings mit 20 Seeds und einem Gesamtvergleich lassen sich ferner keine belastbaren Anteile am Gesamteffekt bestimmen. Wechselwirkungen zwischen korrigierter Zielregel, Planung, Wahrnehmung und Zufallsfolge bleiben möglich. „Attributes most of this effect“ und die anschließende kausale Überlebensgeschichte sind dafür zu stark.

**Auftrag:** Konfiguration und Erzeugungscommit pro Seed prüfen; insbesondere die zwei Eingriffe des Nil-Schutzes dokumentieren. Im Paper entweder die Gleichwertigkeit früherer Läufe für diese Konfiguration nachweisen oder die Provenienz einschränken. Einzelschalterbefunde ausdrücklich explorativ mit ihren eigenen Effekten, Unsicherheiten und Ausfällen berichten. Für Aussagen über Beiträge zum Bündeleffekt braucht es gezielte Interaktions- oder Ablationsvergleiche.

**Erledigt, wenn:** Jeder numerische Vergleich einer überprüfbaren Laufmenge und Konfiguration zugeordnet ist. Eine nachträglich vereinheitlichte Metadatenliste darf die ursprüngliche Entstehung nicht verdecken.

## P1-06 — „Besseres Überleben“ braucht eine definierte Exposition

**Fundstellen:** `manuskript.tex:44,58,114,122`; `src/psi_gw/analysis/metrics.py:30–43`; Tabelle T3.

Die Bedingungen enden beim selben modellinternen Alter, während Eingriffe wie das Entfernen der Werteanzeige gerade dieses Alter und die Zahl bzw. Art der Operationen verändern. P1 und P2 normieren anschließend pro Zyklus. Das ist eine legitime Kennzahl, aber keine automatisch vergleichbare Überlebenszeit oder Effizienz. Auch der zyklusweise Mittelwert des Schadensbedürfnisses ist kein zeitgewichteter Mittelwert.

**Auftrag:** Für Referenz und modernen Modus Mittelwerte und Streuungen der Zyklenzahl, Exituszahlen und Alterszuwächse berichten. Raten pro Zyklus ausdrücklich als solche interpretieren. Mindestens eine begründete ergänzende Expositionssicht prüfen, etwa pro Handlung, über ein gemeinsames Zyklusfenster oder gewichtet mit modellinternen Zeitintervallen; die Wahl muss zur behaupteten Eigenschaft passen. Wiederholte Todesereignisse mit anschließendem Neustart sind keine unabhängigen Überlebensbeobachtungen.

Gleiche Seeds rechtfertigen die Paarbildung als Vergleich über identische Initialisierungen. Sobald ein Eingriff die Anzahl der Ziehungen verändert, erhalten spätere Entscheidungen aber andere Zufallszahlen. Daraus folgt kein ungültiger Vergleich, wohl aber eine Grenze für die Erklärung einzelner Trajektorien als isolierter lokaler Mechanismuseffekt.

**Erledigt, wenn:** Relative Aussagen wie „more than a fifth“ eine sichtbare Bezugsgröße haben und Aussagen über Effizienz oder Überleben nicht weiter reichen als die gewählte Exposition.

## P1-07 — Die Humanstudie darf nicht rückwirkend mit den gefundenen Fehlern verbunden werden

**Fundstelle:** `manuskript.tex:124`.

Der Absatz behauptet zunächst, die Agenten der Studie von 2004 hätten deshalb die invertierte Hintergrundzielregel, die verdeckte Situation und die Anzeigeeffekte enthalten. Erst danach räumt er ein, dass die Softwareversion abweichen könne. Der zweite Satz liefert gerade keinen Beleg für den ersten. Auch die kanonische Korrelation .88 ist kein allgemeiner Validierungsnachweis aller Architekturmechanismen.

**Auftrag:** Versionsidentität durch belegte Quellstände, Binärdateien oder zeitgenössische Dokumentation nachweisen. Andernfalls die konkrete Zuschreibung streichen und nur die allgemeine Konsequenz für zukünftige Modellvalidierung diskutieren. Die frühere Korrelation mit Studiendesign, Aggregation und Beschränkung auf die dortigen Maße einordnen.

**Erledigt, wenn:** Keine Aussage über die tatsächliche Fehlerausstattung früherer Studien ohne Versionsbeleg verbleibt.

## P1-08 — Für die wichtigsten Artefakte fehlt im Paper die unmittelbare Belegkette

**Fundstellen:** `manuskript.tex:94–112`; ADRs 0011, 0014, 0015; Methodenbausteine.

Interne ADRs sind gute Arbeitsnotizen, ersetzen aber keine nachvollziehbare wissenschaftliche Darstellung. Gerade „das Buch beschreibt das Gegenteil“ ist ein zentraler, prüfungsbedürftiger Befund. In diesem Review wurde die betreffende Buchseite nicht aus einer Primärkopie überprüft; die Seitenangabe im Literaturprotokoll verweist selbst auf ein Projektdokument.

**Auftrag:** Für die Hintergrundziele eine kurze Gegenüberstellung von Originalausdruck, Variablenbedeutung, algebraischer Vereinfachung und der auf S. 99 beschriebenen Regel ergänzen, einschließlich zulässigem Wertebereich der resultierenden Wahrscheinlichkeit. Für Anzeige und Planung je eine minimale Ablaufsequenz mit nachweisbarem Zustandsunterschied zeigen. Für Speicherreste sauber zwischen beobachtetem Maschinencode, reproduziertem Stapelrest, nicht reproduziertem Heapbyte und weiteren bereits deterministisch ersetzten uninitialisierten Werten unterscheiden. Wine-Dateinamensverhalten separat als Umgebungseffekt behandeln.

**Erledigt, wenn:** Ein Leser jeden Hauptbefund bis zu einer konkreten Funktion, Primärquelle und gemessenen Beobachtung zurückverfolgen kann. Die Bezeichnung „theoretisch korrigiert“ darf nicht suggerieren, dass damit schon die einzig richtige Interpretation der gesamten PSI-Theorie feststeht.

## P1-09 — Die Motivdominanz braucht Parameter und einen präzisen Nenner

**Fundstellen:** `manuskript.tex:40,44,118,126,128`; `analysis/referenzlaeufe/motivdominanz.json`.

Die 99,89 % sind über 89.775 protokollierte Motiveinträge von 97 vollständigen Referenzmodus-Läufen gepoolt. Längere Läufe tragen mehr bei. Das ist nicht dasselbe wie der Mittelwert von 97 Anteilen. Für den modernen Modus sind 100 Läufe die Grundlage. Zudem gehört Affiliation zu den sieben implementierten Bedürfnissen, fehlt aber in der Aufzählung des Agenten. Die Konfiguration mit Vergessensrate null ist für die Interpretation eines lernenden Gedächtnisses relevant.

**Auftrag:** Alle sieben Bedürfnisse mit Gewicht, Zu- und Abnahmerate sowie Setzungen der Modulatoren aufführen; Startwissen und Vergessensrate nennen. Gepoolten Anteil, Verteilung der lebensweisen Anteile und 65/97 bzw. 99/100 Leben ohne Wechsel getrennt berichten. Entwicklungsseed, Pilotseeds und spätere Auswertungsseeds unterscheiden. Die beiläufige Spanne „700 bis 1.000 Zyklen“ durch die tatsächliche Spanne der betreffenden Konfiguration ersetzen.

**Erledigt, wenn:** Die Dominanz als Befund dieser Welt und Parameter erklärt wird und nicht als generelle Schwäche oder Eigenschaft von PSI.

## P1-10 — Literatur und Darstellung müssen den wissenschaftlichen Beitrag tragen

1. **Forschungsstand:** „Little known“ und „none ... reproduces“ brauchen einen dokumentierten Suchumfang. Eine negative Suche ist kein vollständiger Prioritätsnachweis. Vergleichstabelle: Original, MicroPsi, MicroPsi 2, OpenPsi, weitere Umsetzungen; Quellbezug, Reproduktionsziel und tatsächlich belegte Abgrenzung. Keine Konkurrenzarbeit anhand eines Titels charakterisieren.
2. **Bibliografie:** Alle als ungeprüft markierten Angaben schließen oder betroffene Aussagen entfernen. Stichprobenprüfung dieses Reviews bestätigt Lim et al., 24(2), 287–311, DOI `10.1007/s10458-010-9161-2`; für Cai et al. lässt sich das Autoren-PDF prüfen, und DOI/Seiten `10.1007/978-3-642-22887-2_22`, 212–221 sind als nachzuprüfende Ergänzung verfügbar. Das ist keine Vollprüfung aller Referenzen.
3. **Ergebnistabelle:** T3 zeigt nur Differenzen. Baseline- und Variantenmittelwerte mit Einheiten ergänzen; bei Raten/Anteilen Prozentpunkte von relativen Prozenten unterscheiden. Bootstrapintervalle sind punktweise und nicht automatisch simultan Holm-korrigiert.
4. **PDF:** Auf Seite 5 läuft `background_goals_as_described` sichtbar in die zweite Spalte von Tabelle 2. Lange Schalternamen umbrechen oder kürzen und im Text zuordnen. Eine kleine Architektur- oder Ablaufabbildung würde die Interaktion von Agent, Welt, Zufallsquelle und Anzeige besser erklären als zusätzliche Einleitungssätze.
5. **Reproduktion:** Feste Versionskennung statt bloß „190 tests“, Befehle, Laufzeitmessungen mit Hardware, Hashes der Ausgangsdateien und eindeutig getrennte Entwicklungs-/Validierungsläufe ergänzen. Die Companion-Paper-Verweise aktualisieren; keine Beweislast auf einen unveröffentlichten Begleittext verschieben.

## Konkreter Überarbeitungsablauf für Claude

1. Zuerst P1-01, P1-02 und P1-07 textlich korrigieren; Titel und Abstract an den tatsächlich erreichten Nachweis anpassen. Vorschlag: **“Reconstructing Dörner’s 2003 PSI island agent: trace-level validation and implementation-dependent behaviour.”**
2. Evidenzmatrix, Laufmanifest und vollständige-Fälle-Flussdiagramm/Tabelle erstellen; damit P1-03 bis P1-05 bearbeiten.
3. Exposition und Parametrisierung ergänzen; verfügbare Sensitivitätsauswertungen klar als solche kennzeichnen. Neue Originalläufe nur für konkret beibehaltene stärkere Aussagen planen.
4. Belegketten und Literatur schließen, dann PDF und automatisch erzeugte Tabellen neu prüfen.
5. In einer Antwortdatei jeden Reviewpunkt mit Änderung, Datei/Abschnitt und Nachweis beantworten. Ungeklärte Punkte ausdrücklich offen lassen. Keine neuen Ergebnisse erfinden und keine bestehenden Referenztests abschwächen.

## Prüfprotokoll und Grenzen dieses Reviews

Die Auswertung T3 wurde mit den archivierten Vergleichswerten abgeglichen; die Problematik der nicht belegten Verteilungsgleichheit ergibt sich unmittelbar aus dem eigenen Analyseplan. Die PDFs wurden in den relevanten Tabellenbereichen gerendert und visuell geprüft. Das historische Original wurde in dieser Sitzung nicht unter Wine ausgeführt; die behaupteten vollständigen Golden-Master-Läufe wurden nicht unabhängig neu gerechnet.

`pytest` wurde in einer aus GitHub zusammengestellten, unvollständigen Prüfkopie ausgeführt: 147 Tests bestanden, 40 schlugen fehl, drei hatten Setupfehler, zwei waren übersprungen. Fehlende Original-/Welt-/Trace-Dateien und ein nicht bytegetreu übertragener Textfixture verhindern eine vollständige Bestätigung; daraus wird hier **kein neuer Fehler des Repository-Codes** abgeleitet. Die Zahl 190 bestandener Tests ist in diesem Review deshalb nur ein früher dokumentierter Projektstatus, kein neu bestätigtes Ergebnis. Am wissenschaftlichen Code wurde nichts geändert.

Extern geprüfte bzw. herangezogene Quellen:

- [Universität Bamberg: bibliografischer Datensatz zum Seelenwagen](https://fis.uni-bamberg.de/handle/uniba/11279) — bestätigt Buchdaten, nicht die hier diskutierte Buchseite.
- [Lim et al.: Autorenfassung](https://www.macs.hw.ac.uk/~ruth/Papers/agents-affect/JAAMAS-final.pdf) und [institutioneller Datensatz](https://researchportal.hw.ac.uk/en/publications/creating-adaptive-affective-autonomous-npcs/) — bibliografische Stichprobe und Einordnung als Integration von FAtiMA und PSI.
- [Cai et al.: Autorenfassung OpenPsi](https://www.goertzel.org/OpenPsi_agi_11.pdf) — Primärtext für die Abgrenzung zur Portierung heranziehen.
- [Lakens (2017), DOI 10.1177/1948550617697177](https://doi.org/10.1177/1948550617697177) — methodische Grundlage für die Unterscheidung von fehlender Signifikanz und Äquivalenz.
