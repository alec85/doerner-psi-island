# HANDOFF

Letzte Aktualisierung: 2026-11-13, Agent: Claude Code

## Aktueller Stand

**Zeitschriftenformat und Preprint vorbereitet (2026-11-13, Issue #55, Branch `claude/55-journal-format`).** Paper 1 im Format von Cognitive Systems Research (`elsarticle`, Highlights in `paper/1-portierung/highlights.txt`, Elsevier-Erklärungen), Paper 2 im Format von Adaptive Behavior (APA mit `apacite`, „Statements and declarations“). Beide mit Affiliation DHBW Ravensburg, ORCID, KI-Erklärung (Forschungsprozess im Verfügbarkeitsabschnitt, Schreibprozess in den Erklärungen) und Abstract von höchstens 250 Wörtern. Stil an einzelnen Stellen an Alecs Veröffentlichungen angelehnt (`paper/schreibstil.md`); Struktur und Zahlen unverändert (automatischer Zahlenabgleich vorher/nachher). Plan für Preprint (PsyArXiv), Zeitschriften-KI-Richtlinien und öffentliches Repository in `paper/einreichung.md`. Neues Skript `scripts/public_export.sh` (Export ohne `reference/` und ohne Git-Historie); im Export reproduziert `reproduce_revision.sh` alle Werte und Tabellen. Nebenbei behoben: `pytest` brach auf `main` bei der Sammlung ab (gleicher Dateiname `test_perception.py` in `tests/` und `tests/picrawler/`); jetzt `--import-mode=importlib` in `pyproject.toml`.

**Trace-Viewer und Projektdokumentation umgesetzt (2026-11-13, Issue #54, Branch `codex/54-trace-viewer-docs`).** `python -m psi_gw.ui.trace_viewer` erzeugt aus ein/zwei ADR-0006-JSONL(.gz)-Läufen eine rein lesende Offline-HTML-Datei. Alter-/Zyklusachse, einzelne Messwertreihen, Ereignisfilter, Seitennavigation und Detailansicht; fehlende Daten werden nicht erfunden. README, Roadmap und Architektur entsprechen jetzt Implementierungen und angenommenen ADRs; die ungemergten Robotik-PRs #38/#43/#52 und die offene semantische PSI-Anbindung bleiben klar abgegrenzt. Eigener PR, noch kein Merge dieses Pakets.

**Vergleichswerkzeuge umgesetzt (2026-11-13, Issue #51, Branch `codex/51-comparison-tools`).** `compare_raw.py` und `compare_life.py` liefern eindeutige Exitcodes und versioniertes JSON mit Prüfumfang, Längen und erster Abweichung. Vollständige Gleichheit ist Code 0, Abweichung 1, Eingabe-/Ausführungs-/Berichtsfehler 2, nur teilweise geprüfte Gleichheit 3. Anleitung: `docs/comparison-tools.md`. Ausschließlich Diagnosewerkzeuge, eigene Tests und Dokumentation; PSI-Kern, Paper, Robotik, CI und Referenzdaten sind unverändert. Über PR #53 auf ausdrücklichen Auftrag Alecs nach `main` gemergt (34235e7).

**Vergleichswerkzeuge umgesetzt (2026-11-13, Issue #51, Branch `codex/51-comparison-tools`).** `compare_raw.py` und `compare_life.py` liefern eindeutige Exitcodes und versioniertes JSON mit Prüfumfang, Längen und erster Abweichung. Vollständige Gleichheit ist Code 0, Abweichung 1, Eingabe-/Ausführungs-/Berichtsfehler 2, nur teilweise geprüfte Gleichheit 3. Anleitung: `docs/comparison-tools.md`. Ausschließlich Diagnosewerkzeuge, eigene Tests und Dokumentation; PSI-Kern, Paper, Robotik, CI und Referenzdaten sind unverändert. Kein Merge.

**Zweite Review-Runde eingearbeitet (2026-11-13, Issue #48, Branch `claude/48-paper-revision2`).** Antworten am Ende beider `paper/*/REVIEW_RESPONSE.md`. Alle Analysen beider Paper laufen jetzt ohne `reference/` aus archivierten Daten; `scripts/reproduce_revision.sh` hat in einer frischen Kopie ohne `reference/` am Analysecode-Stand `ecc08a0` jeden Wert und jede Tabelle identisch reproduziert. Eingabenmanifest je Datei (`analysis/revision/eingaben.sha256`). Paper 2 stellt den Kenntnisstand der Vorauswahl richtig (Tests und Einschätzung lagen vor der Bestätigung vor; danach keine Änderung an Plan, Analysecode oder Agent). Offen vor Einreichung: Affiliation, URL, Lizenz, Archiv-DOI; Bach 2009 gegen gedruckte Ausgabe; einige Seitenangaben (`paper/*/literatur.md`).

**Zweiter Review-Durchgang abgeschlossen (Alec, 2026-11-13).** Geprüft wurde `main` auf `6d058fff46c6cad137a9d562c556cb0368a24631` nach Claudes Revision aus PR #46. Neue Berichte: `paper/1-portierung/REVIEW_REPORT_ROUND2.md` und `paper/2-hysterese/REVIEW_REPORT_ROUND2.md`, Commit `4390f86d29b93ef1fa1146836585c05aa8e9faaf`, Branch `codex/45-paper-review-round2`. Die bisherigen Berichte und Claudes Antwortdateien bleiben erhalten. Die meisten grundlegenden Punkte sind erledigt; es braucht keine neue große Versuchsserie allein zur Erledigung dieser Reviewrunde.

Wichtige Restpunkte: (1) Paper 2 beschreibt das Screening als nur auf Fehler ausgewertet, obwohl im damaligen Commit `0d78571d1792e28ffb02450046d9db7c24b5041b` bereits H1–H6, Effektgrößen und eine inhaltliche Interpretation vorliegen. Kenntnisstand transparent richtigstellen; daraus folgt kein automatisches Verwerfen der 100-Seed-Analyse. (2) Neue Revisionsauswertungen benötigen `raw/Activities(1).Txt`, das im Workspace-Archiv nicht enthalten ist. Der tatsächliche Reproduktionsversuch bricht daran ab. Zusätzlich liest die Paper-1-Archivauswertung noch die Parameterdatei aus `reference/`. Reproduktionszusage und vorgesehener Datenumfang müssen zusammenpassen. (3) Zufällige Gleichstände ändern in B die beobachtete Verweildauer um rund 25 %; die pauschale Formulierung „hardly affected B“ ist endpunktabhängig und zu stark. Weitere konkrete Restkorrekturen stehen in den Berichten.

Die ursprünglichen H1–H6 und die 80-Seed-Sensitivität wurden exakt aus CSV reproduziert. S2/S3 wurden aus 80 neuen Kennzahlendateien nachgerechnet (ausgegebene Werte identisch). 20 S1-Diagnoselogs stimmen in Inhalten, führendem Ziel und Alter mit den 20 Bestätigungslogs überein; die Diagnosehäufigkeiten wurden aus 18.736 Zyklen nachgerechnet. Es wurden keine neuen Agenten- oder Originalläufe gerechnet. Manuskripte, wissenschaftlicher Code und Daten wurden durch diesen Review nicht geändert.

**Beide Paper nach den Reviews überarbeitet (2026-11-12, Issue #45, Branch `claude/45-paper-revision`).** Antwortdateien `paper/*/REVIEW_RESPONSE.md` beantworten jede Review-ID mit Änderung, Fundstelle, Nachweis und verbleibender Grenze. Neue Titel: Paper 1 *Reconstructing Dörner's 2003 PSI island agent: trace-level validation and implementation-dependent behaviour*; Paper 2 *Generalising Dörner's selection threshold to a limited-capacity workspace: an incumbency bonus makes contents history-dependent in a PSI island agent*. Nachträgliche Analysen unter `analysis/revision/` (README dort). Sensitivitätsläufe nach `docs/analyseplan-sensitivitaet.md`: Der Bonus wirkt vor allem als Auflösung von Gleichständen (strikt schwächerer Amtsinhaber nur in rund 6 % der Zyklen); mit zufälliger Gleichstandsauflösung (ADR 0018, jetzt umgesetzt als Schalter `workspace_ties=random`) wechselt E sein führendes Ziel 68-mal je 100 Zyklen; Bonus sättigt ab 0,02; keine Leistungseffekte. Ohne `reference/` laufen 131 Tests, die Analysen beider Paper sind aus archivierten Daten reproduzierbar.


**Kritischer Review der beiden Paper abgeschlossen (Alec, 2026-11-12).** Auf Branch `codex/40-critical-paper-reviews` liegen `paper/1-portierung/REVIEW_REPORT.md` und `paper/2-hysterese/REVIEW_REPORT.md`, mit Fundstellen, Prioritäten, Überarbeitungsaufträgen und Erledigungskriterien. Geprüfter Manuskript-/Codestand: `ef15fb05becdfcd8a149b182e63da8690e955756`; Reviewberichte: Commit `2ccaf1499e5523f53176073404d4ae7ef37d91b7`. Urteil für beide: grundlegende Überarbeitung, derzeit nicht einreichungsreif. Manuskripte, wissenschaftlicher Code, Daten und ADRs wurden nicht geändert.

Zentrale Punkte: Paper 1 behauptet Verteilungsgleichheit, obwohl der Referenzanalyseplan diese ausdrücklich offenlässt, und überdehnt den begrenzten Random-Trace-Nachweis. Paper 2 interpretiert Nichtsignifikanz zu stark als unverändertes Verhalten, grenzt Vorarbeiten unzureichend ab und muss Architektur, Zensierung, Endpunkte und Planänderungen genauer beschreiben. Die Variantenmetadaten aus dem ersten Seed erfassen die spätere Einführung des Nil-Schutzes nicht vollständig; dies ist laut Baseline-README erklärbar und kein bereits nachgewiesener falscher Versuchsarm.

**Arbeitspaket C (Global Workspace, Issue #33, PR #34) ist rechnerisch abgeschlossen.** Die sechs archivierten Tests H1 bis H6 wurden aus `analysis/workspace/bestaetigung/kennzahlen.csv` mit der vorhandenen Statistik exakt reproduziert (maximale Abweichung 0). H1, H4, H6 sind in vorhergesagter Richtung signifikant, H2, H3, H5 nicht; das kombinierte Kriterium ist nicht erfüllt. Eine zusätzliche, nachträgliche Auswertung nur für Seeds 1021–1100 ergibt dasselbe Signifikanzmuster. Auf den gleichen 20 geloggten A-Seeds beträgt W2b A 0,583, B 3,670, E 8,079 Wechsel pro 100 Zyklen: B stabilisiert gegenüber E, nicht gegenüber A. Diese Zusatzanalysen sind im Review ausdrücklich als nachträglich gekennzeichnet. Im Workspace-Archiv liegen 420 Workspace-Logs (A 20, B bis E je 100), nicht 500.

**Arbeitsauftrag ab 2026-11-10 14:31 (Alec):** Das Programm weiter portieren, bis das Ziel erreicht ist (Referenzmodus: ein ganzes Inselleben läuft in Python und lässt sich Zug für Zug bzw. statistisch mit dem Original vergleichen) oder eine kritische Entscheidung ansteht. Bis dahin dürfen Agenten ADRs selbst annehmen und PRs selbst mergen (Abweichung von AGENTS.md „Gemergt wird durch Alec“, befristet auf diesen Auftrag). Alec will am Ende eine Zusammenfassung. Kritisch und damit Alec vorzulegen sind: Abschwächung von Golden-Master-Toleranzen, neue schwere Abhängigkeiten, Veröffentlichung, Lizenz, alles mit Kosten.

**Auftrag verlängert (Alec, 2026-11-10 17:04):** Reihenfolge Vergleichsbasis, dann Artefakte abschaltbar, dann Global Workspace ist bestätigt. ADRs dürfen Agenten weiter selbst annehmen, PRs selbst mergen; die Architektur-ADR zum Global Workspace geht an Alec. Lizenz bleibt ausgeklammert. Wichtig für Alec: Wenn eine Session ins Limit läuft, soll Codex mit „mach weiter“ nahtlos übernehmen können. Deshalb steht unter „Nächster Schritt“ immer der aktuelle Teilschritt mit Befehlen, und jeder Teilschritt wird sofort committet und gepusht.

**Ziel des Auftrags für Seed 16 erreicht (2026-11-10).** `psi_gw.life.IslandLife` lässt ein ganzes Inselleben in Python laufen. Das volle Leben mit Seed 16 und `MaxLife` 5.000.000 (739 Zyklen) stimmt mit dem Original unter Wine überein: alle 109.140 Zeilen des Aktivitätsprotokolls `actu16(1).Prt`, alle 2.802 Handlungen mit ihrem Alter (`Activities.Txt`), die Abschlussdateien `eAch`, `Inpro` (alle 43 Prozesszähler, `ProcTimes`, `CheckFreq`) und `Consum`. Zug für Zug geprüft sind die ersten 75.000 Zufallszüge (Mitschnitt bis Zyklus 70); die übrigen 6,3 Millionen Züge sind durch die übereinstimmenden Protokolle belegt, aber nicht einzeln mitgeschnitten. Prüfung: `scripts/compare_life.py`, `scripts/run_port.py`, Tests in `tests/test_life.py` (70 Zyklen mit allen 75.000 mitgeschnittenen Zügen immer, die ganzen Leben mit `PSI_GW_FULL_LIFE=1`, etwa 8 Minuten).

**Zweiter Seed (901, Issue #26):** 912 Zyklen. Handlungen mit Alter, Zähler und Abschlussdateien identisch; im Aktivitätsprotokoll weicht eine von 90.698 Zeilen ab. Ursache: `RememberDir` liest für `lS`/`lN` ein Byte einer Heapadresse des Originals (ADR 0014, angenommen). Das trat in Seed 16 bei 90 und in Seed 901 bei 125 Gelegenheiten auf, abweichend nur einmal; die gewählte Lokomotion blieb dieselbe.

Handlungsregulation (Issue #24, Branch `claude/24-regulation`): `psi_gw.regulation.recall` (Erinnerungsroutinen aus `UStrukturen`), `psi_gw.regulation.ladder` (`UPSIMain.Pas` vollständig: `Confirmation`, `Association`, `ActiVerPro`, `ActivateAuto`, `Planen`, `Actiplan`, `TryAsso`, `Automatismus`, `PlanenUndTun`, `ConSumFin`, `WhatCouldBeDone`, `LookAround`, `Ruhe`), `psi_gw.life` (Faculties, Start, `CheckMaxLife`, Abschlussdateien). `Motivation`, `GoalGen` und der Zyklus schreiben ihre Protokollzeilen.

Inselwelt (Issue #20): `psi_gw.body.island` mit `delphi_strings` (Vergleich und Sortierung wie Delphi unter Wine, gegen eine Vergleichsmatrix aus Wine geprüft), `bitmaps`, `x87` (80-Bit-Rechnung und `Format('%f')` der Bedürfniswirkungen), `world` (Server), `client` (Psis Seite), `body` (Warteschlangen, `pump`, `wait`). Eine Wiederholung aller 2.802 Handlungen des vollen Lebens mit Seed 16 ergibt nach jeder Handlung dieselbe Situation, dasselbe Objekt und dieselben Bedürfniswirkungen wie das Ereignisprotokoll des Originals, einschließlich 58 nachwachsender Objekte und 99 Unfälle.

Portiert sind (Issue #18, abgeschlossen):

- **Zufall und Zeit:** `random_source` mit Aufrufstellen (`site`), `RecordingSource`, Schnappschüssen; `clock` (Altersanteil von `LiftInc`); `counters` (`NIntProc`, `Leistung`).
- **Parameter:** `params.read_param_dat` liest `Param.Dat` wie `ReadParameter`.
- **Gedächtnis:** `memory.lists` (Listen mit Reihenfolgesemantik), `memory.network` (`Connect`, `ReInforce`, `Decay`, `Junction` als `transmit`, `Trace`, `Boss`, `Kopf`, `GenSitList`), `memory.names` (`NextName`), `memory.protocol` (`NewProt`, `GenProtEl`, `Protocoll`, `ReInforceRetro`, `LookFor`).
- **Motivation:** `motivation.system` (`Consumption`, `NeedAndCompetence`, `EpiKomp`, `MotiveStrength`, `SetModulat`, `S_Beduerfnisse`, `KompBestConsumption` mit den 29 Stationsgewichten, `Motivation` mit Arousal, Modulatoren, Handlungstendenzen und lateraler Hemmung), `motivation.goals` (`GoalGen`, `InterMedGoals`).
- **Verhaltenszyklus:** `agent.run_cycle` bildet `TFPsi.Simulation` ab (Buchführung, Exitus mit Wiederversorgung, Neuorientierung und Protokoll, `NeedAndCompetence`, `Motivation`, `GoalGen`, `LookAround`, `QuickMove`, Rasmussen-Leiter, Werteanzeige). Noch nicht portierte Teile (Wahrnehmung, Handlungsregulation, Welt, `pump`) kommen über die Schnittstelle `agent.Faculties`; Tests nutzen Platzhalter. `triple.Triple` für die dreiwertigen Ergebnisse.
- **Gesamtzustand:** `state.PsiState` baut alles in der Reihenfolge von `InitPsi` auf (Neuronen, Aktorlisten, Bedarfsindikatoren, KZG, Kontrollneuronen) und sichert alles in einem JSON-fähigen Schnappschuss.

Prüfungen:

- Tests je Prozedur aus der Pascal-Semantik mit Zeilenangaben und exakten Zugzahlen.
- Gegen den Mitschnitt des Originals: Zugstruktur von `Junction`/`Decay`/`ReInforce`, `ReInforceRetro` läuft immer bis zum Ende der Verstärkung.
- Gegen das Aktivitätsprotokoll des Originals (`actu16(1).Prt`, Zyklus 1): Bei einem Alter zwischen 1414 und 1445 reproduziert `Motivation` alle 14 gedruckten Bedürfnisaktivitäten und Motivstärken, die drei Modulatoren und das gewählte Motiv (Nukleo) auf drei Stellen. Das genaue Alter steht nicht im Protokoll.
- Abnahmetest Persistenz auf Ebene `PsiState`: gesichert, in frischem Prozess fortgesetzt, Züge und vollständiger Zustand **nach jedem Schritt** gleich. Der Vergleich nur des Endzustands war zu schwach: Eine absichtlich weggelassene Variable (`AgeMotOld`) fiel nicht auf, weil ihr Effekt später durch das Kappen eines Bedürfnisspeichers bei 1 verschwand. Mit dem Vergleich nach jedem Schritt wird sie erkannt.

Befunde beim Portieren:

- **Vergessen ist in den Referenzläufen abgeschaltet** (Vergessensrate 0 in `PsiDaten/InselIII/Param.Dat`); `Decay` zieht trotzdem.
- **Motivwahl im vollen Leben (Seed 16):** In 737 von 739 Zyklen ist Nukleo das aktuelle Motiv, je einmal Durst und Hunger (Zyklen 684 und 685). Archivierte Läufe älterer Versionen zeigen meist ebenfalls Nukleo als häufigstes Motiv, einer (`Protokoll/Test/actu1.prt`) aber Kompetenz. Ein leeres Motiv kam im vollen Leben nie vor.
- **Bereichsprüfung an:** `Psi.cfg` und `Psi.dof` setzen `$R+` und `$Q+`. `GoalGen` indiziert `BedIn[ActualMotiv]`; beim leeren Motiv wäre das ein Bereichsfehler. Die Portierung wirft dort `IndexError`.
- `ReInforceRetro` verstärkt das Situationsschema (beide Aufrufer übergeben die aktuelle Situation).
- Uninitialisierte Felder des Originals sind hier 0 (`DEVIATION(ADR-0010)`); geprüft, dass sie nicht gelesen werden, offen nur `SpaTAdd` in `Kopf`.
- 80- gegen 64-Bit-Rechnung ist an den betroffenen Stellen mit `DEVIATION(ADR-0005)` markiert. Für alle Werte der Insel-`Param.Dat` ergibt die Umwandlung über 80 Bit dieselbe Gleitkommazahl wie die direkte (mit exakten Brüchen geprüft, unter der Annahme korrekt gerundeter Textumwandlung in Delphi).
- `Utter` (Sprachausgabe) zieht nur bei eingeschaltetem Ton; im Referenzlauf ist er aus, nicht portiert.
- **Die Werteanzeige verändert das Gedächtnis (ADR 0011, angenommen).** Am Ende jedes Zyklus ruft die Anzeige `EpiKomp` für alle sieben Bedürfnisse auf; das zieht Zufallszahlen, verstärkt Zielverbindungen und erhöht das Alter. Belegt im Quelltext, im Maschinencode (sieben Aufrufe von 0x47B250, Reihenfolge Hunger, Durst, Nukleo, Schaden, Kompetenz, Bestimmtheit, Affiliation) und im Mitschnitt (101 `Junction`-Züge aus diesen Aufrufen). Der Referenzmodus behält das als `agent.value_display`.
- **Auswertungsreihenfolge bei `QuickMove`:** In `random < EpiKomp(ActualMotiv)` wird laut Mitschnitt zuerst `EpiKomp` berechnet, dann gezogen (alle 21 Fälle).
- **Bereichs- und Überlaufprüfung sind im Programm:** `GoalGen` prüft `BedIn[ActualMotiv]` mit `BoundErr` (0x402EA4), Zählererhöhungen prüfen auf Überlauf (0x402EAC). Ein leeres Motiv würde in `GoalGen` eine Ausnahme auslösen; danach bliebe `StartSimul` auf `false`, und der Zyklus liefe nie wieder an. `Ruhe` ist damit praktisch unerreichbar.
- **Parameter verdeckt globale Variable:** `PlanenUndTun(situation, ...)` sucht das Ziel nach einer Fortbewegung in seinem Parameter `situation`, also in der Situation vor der Fortbewegung, nicht in der globalen `Situation`. Gefunden mit einem Mitschnitt, der bei `Junction` die Neuronennamen protokolliert (`PSI_TRACE_NAMES` in `scripts/gdb_random_trace.py`).
- **Stapelrest in `DirArtWert`:** Für `lN` und `lS` liest das Original das dritte Zeichen aus einem lokalen `string[30]`, in das nur die Länge kopiert wurde (0x477D14). In `ContinueDirection` steht dort das dritte Zeichen des letzten längeren Namens; `lS` nach `lSO` zählt als Südost (Zyklus 9).
- **`OutActivities` setzt `StartActivity`** vor jeder Handlung; die Zeiten der Regulationsstufen im Protokoll messen deshalb ab der letzten Handlung.
- **Kurzschlussauswertung:** `and`/`or` werten in Delphi nur so weit aus wie nötig (z. B. `RememberDir`, `AddToFan` hinter `Junction`). Bei Portierung immer die Auswertungsreihenfolge mitnehmen.
- **`SchemaGravity(nil)` ist (0, 0):** `ConSumFin` kann mit `Objekt = nil` annähern.
- **`ConSumFin` liefert beim Abbruch ein uninitialisiertes Byte** (`[ebp-0xd]`); hier `FALSE`, im vollen Leben ohne Folgen.
- **Umlaut-Bitmaps unter Wine (ADR 0013):** Die Dateien `Bergdurchhämmern1–4.bmp` findet das Original unter Wine nicht und zeichnet stattdessen Rahmen und Namen als Text. Nachgebaut mit `scripts/wine_build_bitmap.c`, Daten in `src/psi_gw/body/island/data/wine_text_bitmaps.txt`.
- `SpatSit`, die Raumrelation für den Protokolleintrag der Neuorientierung, ist im Original eine uninitialisierte lokale Variable. `Connect` überschreibt `z` und `t`; `x` und `y` landen mit dem, was gerade auf dem Stapel steht, in den Protokollverbindungen. Ob sie gelesen werden, ist offen.

## Nächster Schritt

**Zeitschriftenformat und Preprint (Auftrag Alec 2026-11-13, Issue #55, Branch `claude/55-journal-format`).** Entscheidungen Alec: Preprints auf PsyArXiv; Paper 1 an Cognitive Systems Research (Elsevier), Paper 2 an Adaptive Behavior (SAGE); Affiliation DHBW Ravensburg; KI-Erklärung ja; Literatur verifiziert Alec selbst; öffentliches Repository ja. Plan (erledigt bis auf die Punkte für Alec in `paper/einreichung.md`, Abschnitt „Was vor dem Hochladen noch fehlt“):

1. [x] Stilnotiz `paper/schreibstil.md` aus Alecs Veröffentlichungen (Heidelberg DP 508 / JBEE 2018, Arbeitspapier Parallel Coordinates, Kapitelentwurf 2025).
2. [x] Paper 1 auf `elsarticle` (Paket `texlive-publishers`, per apt installierbar), Highlights (3–5, je höchstens 85 Zeichen), Keywords, Abstract höchstens 250 Wörter, Erklärungen (generative KI, Interessen, CRediT, Datenverfügbarkeit), Affiliation, ORCID.
3. [x] Paper 2 nach SAGE-Richtlinien (APA mit `apacite` aus `texlive-bibtex-extra`, Abstract höchstens 250 Wörter, 2–6 Keywords, „Statements and Declarations“ mit allen Unterpunkten, KI-Erklärung, Wortzahl).
4. [x] Stil: nur Wortlaut, Struktur bleibt; Zahlen vorher/nachher automatisch abgleichen.
5. [x] PDFs bauen und ansehen, pytest, HANDOFF, PR.
6. [x] Öffentliches Repository: Empfehlung und Exportskript ohne `reference/` vorbereiten, nicht veröffentlichen (Veröffentlichung entscheidet Alec).

Nächster technischer Schritt, falls Alec nichts anderes sagt: Tests, die `reference/` oder `traces/original-runs/` brauchen, bei fehlenden Dateien mit klarer Meldung überspringen (im Export derzeit 64 fehlgeschlagen, 16 Fehler beim Aufsetzen). Prüfen mit `scripts/public_export.sh /tmp/export && cd /tmp/export && pip install -e ".[dev,paper]" && pytest`.

**Diagnosepaket #51:** Über PR #53 gemergt, Issue #51 geschlossen. Bestehende Aufrufer beachten das versionierte JSON (`checks`) und Code 3 für Teilvergleiche.

**Viewer-/Dokumentationspaket #54:** Eigenen PR prüfen und durch Alec zusammenführen lassen. Anleitung `docs/trace-viewer.md`; weder Kern-/Paper- noch Robotikänderungen erforderlich.

**Zweite Review-Runde einarbeiten (Auftrag Alec 2026-11-13, Issue #48, Branch `claude/48-paper-revision2`, Reviews aus PR #47 hineingemergt).** Plan:

1. [x] Eingangsdaten der Revisionsanalysen archivieren (`analysis/revision/eingangsdaten/`: je Leben Handlungszahl, Motivzählung, Stillstand, nil-Eingriffe, Hashes der Quelldateien; Parameterschnappschuss), `scripts/revision_analysis.py` darauf umstellen, Teile getrennt aufrufbar, fehlende Eingaben mit klarer Meldung.
2. [x] Reproduktionsskript `scripts/reproduce_revision.sh` für eine frische Kopie ohne `reference/`; in einer solchen Kopie ausführen, JSON vergleichen.
3. [x] Eingabenmanifest je Datei mit gewöhnlichem SHA-256, harter Abbruch bei fehlenden Pfaden.
4. [x] Paper 1: Reproduktions- und Versionsangaben (gemessene Laufzeit mit Hardware, Commit-Angaben, „nicht gespeichert“), Reichweitenformulierungen, Bibliografie ohne Arbeitsnotizen.
5. [x] Paper 2: Screening-Kenntnisstand richtigstellen (Chronologie, Text), B unter Zufallsregel nach Endpunkten getrennt (explorativer B-gegen-B-Vergleich), S1-Zerlegung präzisieren, Vorzeichen-Rang-Test enger, S1-E-Ersatz im Plan präzisieren, Bach-Ausgabe fixieren, Bibliografie.
6. [x] Antworten auf Runde 2 in beiden `REVIEW_RESPONSE.md`, Tests, PDFs, HANDOFF, PR.


## Offene Fragen an Alec

- **Veröffentlichung (Issue #55):** Repository `alec85/doerner-psi-island` (MIT für Code, CC BY 4.0 für Daten) von Alec angelegt; erster Stand per `scripts/public_export.sh` aus `main` gepusht (2026-11-13). Offen: Zenodo verbinden, Releases `paper1-v1` und `paper2-v1`, DOIs in beide Manuskripte. Ablauf in `paper/einreichung.md`.
- **MuJoCo (PR #43, gemergt 2026-11-13 auf Alecs Anweisung):** optionale Abhängigkeit `mujoco==3.3.7` (Extra `mujoco`), laut PR von Alec am 2026-11-12 gewählt; eine ADR dazu fehlt noch. Entschieden 2026-11-13: Kontaktadresse alec.sproten@aol.be, Codex-Modell GPT 6.1 Sol, Literatur von Alec geprüft, Protokolle der Originalläufe werden veröffentlicht (Stichprobe jetzt archiviert unter `traces/original-runs/2026-11-11-stichprobe/`). Vor der Einreichung bei den Zeitschriften: eigene Überarbeitung des Textes wegen der KI-Richtlinien von Elsevier und SAGE (`paper/einreichung.md`).

Für Diagnosepaket #51 und Viewer-/Dokumentationspaket #54 keine neue Architektur-, Abhängigkeits- oder Toleranzentscheidung.

Entschieden am 2026-11-12: Nachtrag 1 bestätigt; ADR 0018 ist in PR #46 als optionaler Schalter umgesetzt. Die ursprüngliche bestätigende Workspace-Studie (Paper 2) behält die Namensregel; Zufallsregel-Läufe sind zusätzliche Sensitivitäten.

- **Titel und Rahmung beider Paper:** Die Reviewberichte schlagen engere, durch die Daten gedeckte Titel vor. Die früheren Vorschläge für Paper 1 stehen in `paper/1-portierung/gliederung.md`; die Rahmung ist bei der Überarbeitung zu klären.

- Actions-Kontingent: 12 USD pro Monat, rund 2.000 Linux-Minuten (GitHub Free). Pilot passt, Hauptphase braucht voraussichtlich zwei Monate.
- Existiert bereits Code aus einem früheren `psi_gw`-Ansatz (CLI, deterministischer Tick/Seed, Workspace-Trägheit)? Falls ja: wo liegt er? (Issue #5)
- Rechte am Delphi-Quellcode und an den Laufzeitdateien: Bis das geklärt ist, bleibt das Repository privat. Eine Veröffentlichung wäre eher ein neues Repository ohne `reference/` (ADR 0007).
- Lizenz für den eigenen Code (z. B. MIT, Apache-2.0, GPL-3.0) ist noch nicht gewählt.

## Bekannte Fallstricke

- Trace-Viewer (#54): ADR-0006-Läufe sind nicht das Format von `Workspace(1).jsonl` oder Robotik-Replays. Ein Abschlussdatensatz beweist keine Vollständigkeit. Eingebettete Daten gehören beim Weitergeben zum Bericht; `NaN`/Infinity werden mit Hinweis nur in der Darstellung zu `null`. Browser-Sichtabnahme war hier wegen gesperrter Chromium-Sockets nicht möglich; DOM-/JavaScript-Prüfung siehe Teststatus.

- Vergleichswerkzeuge (#51): Code 3 bedeutet nur teilweise geprüfte Gleichheit. Zufallsmitschnitte können innerhalb eines Zyklus enden. Eine abgeschnittene letzte Textzeile wird nicht automatisch toleriert. Fehler beim JSON-Schreiben liefern Code 2 und eine Konsolenmeldung; ein eventuell vorhandener alter Bericht ist dann kein neues Ergebnis.

- Zweiter Review: Die Screening-README von Commit `0d78571` dokumentiert bereits eine inhaltliche Hypothesen-/Effektgrößeninterpretation. Eine Formulierung als ausschließlich technische Fehlerprüfung ist damit nicht vereinbar.
- Das Workspace-Archiv und `sync_workspace_runs.py restore` enthalten/erzeugen keine `Activities(1).Txt`. Die neuen Pro-Handlung-Auswertungen benötigen zusätzliche archivierte Nenner. Ein erfolgreicher Lauf der alten H1–H6 bestätigt nicht automatisch alle neuen Revisionsanalysen.
- `input_manifest.digest` liefert für fehlende Pfade derzeit den leeren Baumhash statt eines Fehlers. Die vorhandene CSV enthält Kategorie-/Baumhashes, keine gewöhnlichen Einzeldatei-Hashes; vor Verwendung als öffentlicher Prüfweg korrigieren oder eindeutig beschreiben.

- Review 2026-11-12: Verteilungsgleichheit Original/Portierung ist nicht nachgewiesen; Nichtsignifikanz ist kein Äquivalenznachweis. Die lokalen Hypothesentests bestätigen die archivierten Zahlen, nicht automatisch deren theoretische Interpretation.
- `compare_variants.py` übernimmt die Variantenliste aus dem ersten gemeinsamen Seed; die ersten 20 modernen Läufe entstanden vor Einführung von `guard_nil_dereferences`. Laufmanifeste pro Seed prüfen, bevor die summarische Liste als homogene Konfiguration interpretiert wird.
- Die Review-Prüfkopie enthält nicht alle binären und historischen Fixtures. Ihr unvollständiger pytest-Lauf ist kein Ersatz für die vollständige Golden-Master-Prüfung.

- In Claude-Code-Cloud-Sessions ist die GitHub-GraphQL-API gesperrt. Für Issues und PRs `gh api repos/alec85/psi-gw/...` (REST) verwenden, nicht `gh issue create` oder `gh pr create`.
- Dateien unter `reference/` sind Windows-1252 kodiert mit CRLF. Zum Lesen `iconv -f cp1252 -t utf-8 <datei> | tr -d '\r'` bzw. in Python `encoding="cp1252"`. Nie zurückschreiben.
- `UPsiMainxy.Pas` deklariert denselben Unit-Namen wie `UPSIMain.Pas`, ist aber nicht im Build. Beim Suchen im Code nicht verwechseln.
- Das Ereignisprotokoll älterer Versionen (4.9.0.100) hat keine Spalte `Nr`; Parser immer über die Kopfzeile, nie über Spaltenpositionen.
- Datumsangaben in den Protokollen kommen deutsch (`26.05.2003 12:07:01`) und US-amerikanisch (`3/9/2014 7:42:08 PM`); `parse_start_time` kann beides.
- Das Original nutzt `TClientSocket`/`TServerSocket` aus Delphis ScktComp. Für das Testgerüst egal (Client wird gestubbt), für einen Lazarus-Build der Oberfläche vermutlich ein Hindernis.
- Das Firmennetz blockiert Downloads von Archiven mit ausführbaren Dateien. Seit ADR 0007 liegen die Laufzeitdateien im Repo; neue Binärdateien müssen von Alecs privatem Rechner kommen.
- Das Original kann mit modalen Fehlerdialogen stehen bleiben (Titel „Fehler“). Läufe nur über `run_original.py` starten, das sie bestätigt.
- `rm -rf` auf das aktuelle Arbeitsverzeichnis blockiert die Agentenumgebung; neue Laufverzeichnisse anlegen statt alte zu löschen.
- Original nie mit dem Schalter `Start` starten (Fehler im Original, siehe `docs/delphi-build.md`).
- Läufe des Originals nur nacheinander: Der Weltserver belegt immer Port 2000.
- Laufzeiten und Zyklenzahlen nie aus kurzen Läufen hochrechnen: Das Alter pro Zyklus steigt im Lauf stark an (Messlauf 2026-11-10). Im Agenten-Arbeitsbereich laufen Hintergrundprozesse nach dem Ende einer Antwort nicht weiter. Lange Läufe des Originals deshalb über GitHub Actions, nicht per `nohup`.
- `ach*.Prt` endet einen Zyklus vor den übrigen Protokollen; der Konverter legt die Daten des letzten Zyklus unter `summary.extra.trailing_cycles` ab.
- Rohprotokolle unter `traces/**/raw/` sind wie `reference/` Windows-1252 mit CRLF und werden nicht verändert.
- Workspace-Läufe: rund 2,5 Minuten je Leben mit 2 Kernen parallel. `scripts/workspace_runs.sh` überspringt fertige Seeds; nach einem Abbruch einfach erneut starten. Zwischen Vorauswahl und Bestätigung den Code unter `src/` nicht ändern, sonst alle Läufe neu (Analyseplan).
- `metrics.json` enthält `NaN` für nicht definierte W-Kennzahlen (z. B. W1 einer Art, die nie im Workspace war); Python liest das, strenge JSON-Parser nicht.

## Teststatus

**Issue #55, Nachtrag (2026-11-13):** Export mit Originalprotokollen (1.469 Dateien, 96 MB): 927 passed, 50 failed, 13 errors, 2 skipped; die Fehler brauchen `reference/`.

**Issue #55 (2026-11-13):** Gesamtsuite im Repository mit `reference/`: 990 passed, 2 skipped (nach Umstellung auf `--import-mode=importlib`; vorher Abbruch bei der Sammlung). Öffentlicher Export ohne `reference/` und ohne Originalspuren: 910 passed, 64 failed, 16 errors, 2 skipped; `reproduce_revision.sh` dort vollständig identisch.

**Viewer-/Dokumentationspaket #54 (2026-11-13):** 21 neue Viewer-Tests bestanden; zusammen mit Tracing- und Vergleichswerkzeugen 74 passed. Gesamtsuite mit `--import-mode=importlib`: 992 passed, 19 failed, 2 skipped. Keine neu fehlgeschlagenen Tests gegenüber dem zuvor geprüften Ausgangsstand; zwei frühere Fehler entfallen nach Materialisierung der beiden JSONL-Beispiele. Fehlende/unvollständige historische Fixtures verhindern weiterhin eine vollständige Golden-Master-Abnahme.

Zwei per Git-Blob-Hash geprüfte Originalwiederholungen (je 72 Zyklus-/647 Ereignisdatensätze) tatsächlich exportiert. Das eingebettete JavaScript in jsdom 31.0.1 ausgeführt: beide Laufkarten, alle 26 Messwertreihen, Lauf-/Aktions-/Suchfilter, gültige/ungültige Bereiche, Reset, Seitenwechsel und Detail-/Cursornavigation geprüft. Zusätzliche Fälle: fehlende Messwerte unterbrechen Kurven, fehlende Zeitkoordinaten, Seed 0, NaN-Hinweis, inerte Scriptzeichenfolgen und Header ohne Daten. Kein Browser-Rendering behauptet: Chromium scheitert an gesperrten Socket-Aufrufen. 29 lokale Dokumentationslinks geprüft, keine gebrochenen Links; compileall und diff --check bestanden.

**Diagnosepaket #51 (2026-11-13):** 43 gezielte Regressionstests bestanden. Echter Seed-16-Lauf über 28 Zyklen gegen das unveränderte, per Git-Blob-Hash geprüfte Originalarchiv: 2.016 Protokollzeilen, 108 Handlungen und 19.208 Zufallszüge im gemeinsamen Präfix exakt gleich; korrekt Code 3. Gesamtsuite in unvollständig materialisierter Arbeitskopie mit `--import-mode=importlib`: Ausgangsstand 926 passed, 21 failed, 2 skipped; abschließende Prüfung mit 43 neuen Tests 969 passed, dieselben 21 failed, 2 skipped. Keine zusätzlichen fehlgeschlagenen Bestandstests; fehlende/unvollständige historische Referenz-/Trace-Fixtures verhindern die vollständige Abnahme. Default-Importmodus hat bereits am Bestand eine Namenskollision zwischen den beiden `test_perception.py`. Keine Bestandstests oder Toleranzen geändert.

**Zweiter Review (2026-11-13):** `pytest` in unvollständig materialisierter Prüfkopie: 114 passed, 64 failed, 16 errors, 2 skipped. Die 80 Fehler-/Fehlschlagmeldungen sind ausschließlich `FileNotFoundError` wegen fehlender Original-, Welt- oder Trace-Dateien. Daraus wird kein neuer Implementierungsfehler abgeleitet; der Umfang unterscheidet sich von Claudes vollständiger Arbeitsumgebung und seiner Kopie im Veröffentlichungsumfang. Die zwei Stringvergleichsfixtures wurden vor dem Testlauf auf ihre originalen Git-Blob-Hashes geprüft. Keine Tests abgeschwächt; keine wissenschaftlichen Codeänderungen im Review.

**Zahlenprüfung:** H1–H6 und die 80-Seed-Auswertung exakt reproduziert; S2-/S3-Mittelwerte und die ausgegebenen Vergleiche aus Kennzahlendateien nachgerechnet, maximale Abweichung 0. S1-Inhalte, führendes Ziel und Alter in 20 Leben identisch mit Bestätigung. Diagnoseanteile aus 18.736 Rohlogzyklen: Grenzgleichstand 9,9274 %, Abweichung von jeder bonusfreien Gleichstandsauswahl 6,0739 %, von der Namensauswahl 35,9629 %. Zusätzlicher explorativer Vergleich B zufällig minus B Name: W1 +8,279 Zyklen, punktweises 95-%-KI [3,946; 12,611], unkorrigiertes p 0,00210; W2b −0,326, KI [−0,900; 0,193], p 0,2785.

**Reproduktionsgrenze:** `revision_analysis.py --only paper2` bricht nach Wiederherstellung des echten ersten B-Logs an fehlender `raw/Activities(1).Txt` ab. Kein vollständig erfolgreicher Lauf sämtlicher neuer Revisionsauswertungen bestätigt. Die Originalsoftware und keine neue Agentenserie wurden ausgeführt. PDFs beider Paper vollständig gerendert und visuell geprüft (10 bzw. 11 Seiten).

**Vorher von Claude dokumentiert (2026-11-12):** 194 passed, 2 skipped in vollständiger Arbeitsumgebung; ohne `reference/` 131 passed, 50 failed, 13 errors, 2 skipped. Die zwei Ganzlebentests mit `PSI_GW_FULL_LIFE=1` zuletzt am 2026-11-10 grün. Diese vollständigen Status wurden in der zweiten Review-Sitzung nicht neu nachgestellt.

## Log

### 2026-11-09, Claude Code
- Repository-Gerüst angelegt: AGENTS.md, CLAUDE.md, HANDOFF.md, Roadmap, Architektur, ADRs 0001 bis 0004, Issue- und PR-Vorlagen, initiale Issues, Python-Paket `psi_gw` mit `Body`-Schnittstelle und Smoke-Tests.
- Branch: `main`
- Repository auf GitHub (`alec85/psi-gw`, privat) gepusht, Issues #1 bis #5 angelegt. `gh issue create` scheitert in Claude-Code-Sessions an gesperrtem GraphQL, das Skript nutzt deshalb die REST-API.

### 2026-11-09, Claude Code
- Issue #1: Delphi-Original eingecheckt (Auszug aus `CPS.zip` per Google Colab, ohne Binärdateien, Medien und PDFs), Inventar und Inventarskript erstellt, Zufallsquellen und Echtzeitabhängigkeiten analysiert.
- ADR 0005 (zweistufiger Abgleich) nach Zustimmung von Alec angenommen; ADR 0003 verweist darauf. Roadmap Phase 1 und 2 und AGENTS.md angepasst. Issues #2 und #4 neu zugeschnitten, #7 für die statistischen Referenzläufe angelegt.
- Branch: `claude/1-delphi-original`, PR #6

### 2026-11-09, Claude Code
- Issue #3: ADR 0006, Formatspezifikation, `psi_gw.tracing` mit Writer/Reader und Prozedur-Testfällen, Konverter für `ach*.Prt` und `Protokoll*.Dat` mit Tests an den echten Protokollen. Inventar zu Spaltenbedeutung und Programmversionen der Seed-16-Läufe korrigiert. Wine und Free Pascal im Arbeitsbereich als installierbar festgestellt.
- Branch: `claude/3-trace-format`

### 2026-11-09, Claude Code
- Issue #2 Teil 1: vollständiges `CPS.zip` von Alec erhalten, Laufzeitdateien nach ADR 0007 eingecheckt, Wine-Einrichtung und Runner geschrieben, Fehler mit dem Schalter `Start` gefunden und per Disassemblierung belegt, Determinismus des Originals unter Wine nachgewiesen und als Referenzläufe mit Tests abgelegt.
- Branch: `claude/2-wine-runtime`

### 2026-11-09, Claude Code (abends, Alec nicht anwesend)
- ADR 0008 nach Zustimmung von Alec, `psi_gw.random_source` mit bit-genauem Delphi-Generator, Konverter für alle Protokolle, Analyseplan für Issue #7, ungetesteter Actions-Workflow für Läufe des Originals.
- Branch: `claude/7-referenzlaeufe` (Basis `claude/2-wine-runtime`)

### 2026-11-10, Claude Code
- Nach Rückfrage von Alec Laufzeitangaben im Analyseplan überprüft: waren Hochrechnungen. Messlauf durchgeführt (316 Zyklen), Analyseplan auf Fassung 2 und `docs/delphi-build.md` korrigiert, Messlauf mit Test abgelegt.
- Branch: `claude/7-messlauf`

### 2026-11-10, Claude Code
- Volles Leben (Seed 16, `MaxLife` 5.000.000) gemessen: 739 Zyklen, rund 19 min. Fehlerdialog des Originals in Zyklus 571 gefunden und analysiert, Runner um automatische Bestätigung ergänzt, Analyseplan Fassung 3. Wiederholungslauf: vollständig identisch, Dialog deterministisch, automatische Bestätigung funktioniert.
- Branch: `claude/7-volles-leben`

### 2026-11-10, Claude Code
- Issue #14: Zufallsmitschnitt unter winedbg und gdb gebaut, 20.000 Züge mit Seed 16 aufgezeichnet und geprüft, alle 44 Aufrufstellen zugeordnet (Zuordnung über Quelltextreihenfolge, bestätigt durch Textkonstanten; zwei fehlende Aufrufe durch Linker-Entfernung erklärt). ADR 0009.
- Branch: `claude/14-zufallsmitschnitt`

### 2026-11-10, Claude Code
- ADR 0010 (vorgeschlagen) zu Modernisierung, Modulstruktur und Persistenz nach Alecs Wünschen entworfen; Issue #16.
- Branch: `claude/16-architektur` (Basis `claude/14-zufallsmitschnitt`)

### 2026-11-10, Claude Code
- Issue #18: ADR 0010 angenommen, Architekturdokument angepasst. `RecordingSource` und Snapshots der Zufallsquellen, `Clock`, `psi_gw.memory.lists` und `psi_gw.memory.network` aus `UStrukturen` portiert, Tests gegen Pascal-Semantik und gegen die Zugstruktur des Originalmitschnitts, Abnahmetest für Wiederaufnahme in frischem Prozess.
- Branch: `claude/18-memory` (Basis `claude/14-zufallsmitschnitt`)

### 2026-11-10, Claude Code
- Issue #18 fortgesetzt: Protokollgedächtnis portiert (`NameGenerator`, `ProtocolMemory` mit `NewProt`, `GenProtEl`, `Protocoll`, `ReInforceRetro`, `LookFor`), `NilDereference` eingeführt, Abnahmetest um das Protokollgedächtnis erweitert, Test gegen den Mitschnitt zu `ReInforceRetro`. Offenen Punkt zu uninitialisierten Feldern am Quelltext geklärt.
- Branch: `claude/18-memory`

### 2026-11-10, Claude Code
- Issue #18 fortgesetzt: `params`, `counters`, `motivation` (Bedürfnisse, Modulatoren, Motivwahl, `GoalGen`, `InterMedGoals`), `PsiState` nach `InitPsi`. Test gegen Zyklus 1 des Aktivitätsprotokolls. Abnahmetest auf `PsiState` verlagert und auf Vergleich nach jedem Schritt verschärft.
- Branch: `claude/18-memory`

### 2026-11-10, Claude Code
- Issue #18 fortgesetzt: Hauptschleife `TFPsi.Simulation` gelesen und als `agent.run_cycle` mit Schnittstelle `Faculties` portiert; Buchführung des Zyklus in `PsiState`. Seiteneffekte der Werteanzeige gefunden und belegt (ADR 0011, angenommen), Auswertungsreihenfolge bei `QuickMove` und Bereichsprüfung im Maschinencode bestätigt.
- Branch: `claude/18-memory`

### 2026-11-10, Claude Code
- Auf Alecs Anweisung ADR 0011 angenommen, PR #15 und PR #19 nach `main` gemergt (vorher Tests auf beiden Köpfen grün), Issue #16 geschlossen, Issue #20 (Inselwelt) angelegt.
- Branch: `claude/20-inselwelt`

### 2026-11-10, Claude Code
- Issue #20: Inselwelt analysiert (`docs/inselwelt-analyse.md`): Wahrnehmung arbeitet auf Pixeln der Objektbitmaps, Bedürfniswirkungen der Welt werden durch das Textformat auf zwei Stellen gerundet, Welt zieht aus dem gemeinsamen Generator, zeitversetzte Objektänderungen hängen an einem Timer. ADR 0012 (vorgeschlagen).
- Branch: `claude/20-inselwelt`

### 2026-11-10, Claude Code
- ADR 0012 von Alec angenommen (Ausblick auf neuronale Bildverarbeitung in ADR und Roadmap vermerkt). Inselwelt weiter analysiert: Timer bei `Geschwindigkeit=0.0` mit 1 ms Intervall, `Timer1` nie aktiv, `Timer2` und Zoom-Timer nur in Warteschleifen, Wahrnehmungsbild ohne Streckung, alle Durchläufe der Nachrichtenschleife inventarisiert, Anzeigeroutinen von `OnSituationChanged` ohne Seiteneffekte.
- Branch: `claude/20-inselwelt`

### 2026-11-10, Claude Code (Auftrag: selbstständig portieren)
- Inselwelt portiert (`psi_gw.body.island`), Wiederholung des vollen Lebens ohne Abweichung. Befunde: Bedürfniswirkungen hängen an 80-Bit-Rechnung plus Rundung auf `real` vor `Format('%f')` (fünf Grenzfälle im Protokoll bestätigt); Sortierung der Manipulationen nach Windows-Regeln (`Säen` vor `Saugen`); Dateinamen mit Umlauten im Archiv in Codepage 437; `Zuenden` an `Aeste`/`Aeste1` steht doppelt in `Manipulation.Dat` und wirkt doppelt.
- mingw (`gcc-mingw-w64-i686`) im Arbeitsbereich installiert, nur für das Hilfsprogramm `scripts/wine_compare_strings.c`; keine Abhängigkeit des Pakets.
- Branch: `claude/20-inselwelt`

### 2026-11-10, Claude Code (Auftrag: selbstständig portieren)
- Wahrnehmung und Handlung portiert. Befunde: Wahrnehmung vergleicht Winkel auf Gleichheit, 80-Bit-Rest von 2π ist entscheidend; FPATAN ist für die Richtung (13,−17) nicht korrekt gerundet; `TXYList` sortiert Punkte als Zeichenketten; `Percept` setzt die globale Variable `Objekt` und hinterlässt sie `nil`; `Aggress`, `Regress` usw. ersetzen die Wahrnehmungszeit im Alter durch pauschal 120; `Consum` prüft bei Schmerz die Zielliste, legt aber eine Aversion an.
- Branch: `claude/22-wahrnehmung`
- 2026-11-10, Claude Code: `ConSumFin`, `WhatCouldBeDone`, `LookAround`, `Ruhe` portiert; `psi_gw.life` (Faculties, Start wie das Original), Protokollzeilen von Zyklus, `Motivation`, `GoalGen`; `Activities.Txt`; Funde: Stapelrest in `DirArtWert`, Kurzschluss-`and` in `RememberDir`, `OutActivities` setzt `StartActivity`. Golden-Master-Test `tests/test_life.py` (Zyklen 1–29). Branch `claude/24-regulation`.
- 2026-11-10, Claude Code: Volles Leben Seed 16 identisch mit dem Original (Protokoll, Handlungen, Abschlussdateien). Funde: Parameter `situation` verdeckt globale Variable in `PlanenUndTun`, Umlaut-Bitmaps unter Wine (ADR 0013), `SchemaGravity(nil)`. Branch `claude/24-regulation`.
- 2026-11-10, Claude Code: Seed 901 gegen das Original verglichen, ADR 0014 (heapabhängiges Verhalten), Läufe unter `traces/original-runs/2026-11-10-seed901` und `…-zufallsmitschnitt-75k`, `scripts/run_port.py`. Branch `claude/26-zweiter-seed`.
- 2026-11-11, Claude Code: Arbeitspakete A und B. Portierung schreibt ach und IntTimes wie das Original, Trace-Dateien, Kennzahlen P1 bis P6, wiederaufnehmbare Serien. Pilot (901 bis 905), Stufe B (1001 bis 1100, drei Leben brechen an nil-Zugriffen ab), Stichprobe des Originals (sieben Leben, alle Abweichungen nach ADR 0014, Abbrüche bestätigt). Schalter für Artefakte (ADR 0015) einschließlich der Hintergrundziel-Regel aus Dörners Buch und eines nil-Schutzes, gemessen. Persistenz eines ganzen Lebens samt Insel. Vorschlag ADR 0016 (Global Workspace) für Alec. Branch `claude/28-vergleichsbasis`.

### 2026-11-11, Claude Code
- Arbeitspaket C: Baseline gesichert (Branch `baseline/referenzmodus-2026-11-11`, Archive), ADR 0016 nach Alecs Entscheidungen angenommen, ADR 0017 (matplotlib), Analyseplan Workspace mit Nachträgen 1 bis 3, `psi_gw.workspace` mit Broadcast und Kennzahlen, Leistungsverbesserungen ohne Verhaltensänderung, Paper-Gerüst `paper/`, Skripte für Läufe, Ablage, Auswertung und Abbildungen.
- Vorauswahl und Bestätigung gerechnet (500 Leben), Ergebnis siehe Aktueller Stand.
- Branch: `claude/33-global-workspace`, PR #34

### 2026-11-12, Claude Code
- Entscheidungen Alec: Nachtrag 1 bestätigt, Zufall bei Gleichstand künftig (ADR 0018), zwei Paper statt einem, öffentliches Repo ohne `reference/` erst zur Einreichung.
- `paper/` in `1-portierung/` und `2-hysterese/` geteilt, Literaturrecherche je Paper (`literatur.md` mit Prüfstand, `referenzen.bib`), erste Entwürfe als LaTeX mit PDF, Skript `scripts/motive_dominance.py`.
- Branch: `claude/40-zwei-paper`

### 2026-11-12, Codex
- Auf Alecs Auftrag zwei kritische Reviewberichte in den Paperordnern erstellt (10 priorisierte Punkte für Portierung, 12 für Hysterese), mit Code-/Datenfundstellen, konkreten Überarbeitungsaufträgen und Abnahmekriterien.
- Manuskripte, Literatur, Analysepläne samt Historie, relevante ADRs, Statistik- und Workspace-Code sowie archivierte Kennzahlen geprüft; Dossa, Butlin und methodische Äquivalenzliteratur gezielt gegengeprüft.
- H1 bis H6 exakt aus CSV reproduziert; zusätzliche 80-Seed-Sensitivität und A/B/E-Vergleich der gleichen 20 Seeds berechnet. Ergebnisse und Grenzen in den Berichten festgehalten.
- PDFs visuell auf relevante Tabellen und Abbildungen geprüft. Vollständige Golden-Master-Prüfung mangels vollständiger lokaler Fixtures nicht bestätigt; siehe Teststatus.
- Branch: `codex/40-critical-paper-reviews`, Bezug Issue #40. Änderungen per PR; keine Zusammenführung und keine Veröffentlichung.

### 2026-11-12 (Abend), Claude Code
- Reviews von Codex (PR #44) eingearbeitet: beide Manuskripte neu geschrieben, Antwortdateien je Review-ID, nachträgliche Analysen (`scripts/revision_analysis.py`), Eingaben-Manifest mit Hashes, Reproduktion ohne `reference/` geprüft.
- ADR 0018 umgesetzt (`workspace_ties=random`, eigene Zufallsquelle) und Diagnosefelder im Workspace-Protokoll; Sensitivitätsläufe S1 bis S3 (100 Leben) gerechnet und archiviert.
- Branch: `claude/45-paper-revision`

### 2026-11-13, Codex
- Zweiten Review-Durchgang für beide überarbeiteten Paper durchgeführt; Berichte `REVIEW_REPORT_ROUND2.md` in den jeweiligen Ordnern, alte Reviewpunkte einzeln als erledigt/teilweise/offen bewertet.
- Haupttests, 80-Seed-Sensitivität, neue S2/S3-Kennzahlen und 20 S1-Diagnoseläufe geprüft. Screeninginterpretation am historischen Commit und fehlende Rohnenner am Reproduktionsweg nachgewiesen. Weiterer explorativer Vergleich der Gleichstandsregeln innerhalb B berechnet.
- Aktuelle PDFs gerendert und geprüft; eingeschränkten pytest-Lauf und Grenzen dokumentiert. Keine neuen Simulationsleben und keine Änderungen an wissenschaftlichem Code, Daten oder Manuskripten.
- Branch: `codex/45-paper-review-round2`, Bezug Issue #45. Reviewberichte und Übergabe per PR; kein Merge und keine Veröffentlichung.

### 2026-11-13, Claude Code
- Zweite Review-Runde (PR #47) eingearbeitet: archivierte Eingangsdaten und Reproduktionsskript mit Vergleich, Eingabenmanifest je Datei, Versions- und Laufzeitangaben, Reichweitenformulierungen, Bibliografie ohne Arbeitsnotizen (Paper 1); Screening-Kenntnisstand, endpunktgetrennte Gleichstandsbefunde mit explorativem B-gegen-B-Vergleich, Einordnung der S1-Diagnose und des Rangtests, Bach-Ausgabe (Paper 2).
- Branch: `claude/48-paper-revision2`

### 2026-11-13, Codex
- Issue #51: Vergleichswerkzeuge um eindeutige Exitcodes, versioniertes JSON, genaue Präfixabdeckung, Längen-/Inhaltsabweichungen, Eingabeprüfung, Ausführungsfehler und Schutz vor Überschreiben der Eingaben ergänzt.
- 43 Regressionstests und eigene Anleitung; echten 28-Zyklen-Präfixvergleich ausgeführt. Bestandssuite gegen unveränderte Werkzeuge gegengeprüft, identische fehlgeschlagene Tests in unvollständiger Kopie.
- Branch: `codex/51-comparison-tools`; Änderungen per PR, kein Merge und keine Änderung an Kern, Robotik, Paper-Analysen, CI oder Referenzdaten.

### 2026-11-13, Codex
- Issue #54: Lesenden Offline-Trace-Viewer mit einem/zwei Läufen, Herkunfts-/Hashangaben, wählbaren Messwerten, Zeitbereich, Ereignisfiltern und Detailnavigation implementiert; 21 eigene Tests und Anleitung.
- README, Roadmap und Architektur an tatsächliche Implementierungen und angenommene ADRs angepasst: zurückgestelltes Pascal-Gerüst, begrenzte Referenznachweise, Workspace-/Paperstand, tatsächliche Inselbindung und getrennte Robotik-PRs. Keine wissenschaftlichen Aussagen oder Ergebnisse verändert.
- Echte Archive exportiert, JavaScript-/DOM-Prüfung ausgeführt; Browser-Sichtprüfung durch Socket-Restriktion blockiert. Gesamtprüfung und Grenzen siehe Teststatus.
- Branch: `codex/54-trace-viewer-docs`; eigener PR, kein Merge, keine Änderung an Kern, Paper-Analysen, Robotik, Referenzdaten, Abhängigkeiten oder CI.

### 2026-11-13 (Nachmittag), Claude Code

- Paper in Zeitschriftenformate gebracht (Cognitive Systems Research, Adaptive Behavior), KI-Erklärungen, Affiliation DHBW Ravensburg, Stilnotiz, Einreichungsplan, Exportskript für das öffentliche Repository, pytest-Sammlung repariert.
- Branch: `claude/55-journal-format`, Issue #55.

### 2026-11-13 (Mittag), Claude Code

- Auf Alecs Anweisung alle offenen PRs gemergt: #57 (Konflikt in HANDOFF.md durch Zusammenführen beider Seiten gelöst), #38, #43, #52 (PiCrawler-Stapel; je `main` hineingemergt, Basis auf `main` umgestellt, Draft aufgehoben). Tests nach jedem Merge grün, zuletzt 1.221 passed, 2 skipped mit MuJoCo-Extra.
- Öffentliches Repository `alec85/doerner-psi-island` befüllt; README um Hinweis auf PiCrawler und Trace-Viewer ergänzt.
- Branch: `claude/55-public-release`.
