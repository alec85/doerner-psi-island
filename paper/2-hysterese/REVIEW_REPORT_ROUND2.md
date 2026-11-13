# Zweiter Review: Selektionsschwelle und Workspace

**Urteil: wissenschaftlich deutlich verbessert, aber noch gezielte Überarbeitung erforderlich. Die ursprünglichen Hauptbefunde und die neuen Sensitivitätszahlen sind konsistent nachrechenbar. Zwei wichtige Punkte bleiben offen: Die Darstellung der Screeningphase widerspricht dem damaligen Ergebnisprotokoll, und der zugesagte Reproduktionsweg reicht nicht für alle neuen Auswertungen.**

- Datum: 13. November 2026; Reviewer: Codex.
- Geprüfter Stand: `6d058fff46c6cad137a9d562c556cb0368a24631` (`main`, Revision aus PR #46 / Issue #45).
- Bezug: [erster Bericht](REVIEW_REPORT.md), [Antwort von Claude](REVIEW_RESPONSE.md), aktuelles elfseitiges PDF und LaTeX-Quelle. Zeilenangaben gelten für diesen Stand.
- Erledigte Punkte werden hier geschlossen. Zusätzliche nachträgliche Berechnungen dieses Reviews werden ausdrücklich als solche bezeichnet; sie werden nicht zu präregistrierten Tests umetikettiert.

## Was jetzt trägt

Die Arbeit behauptet nicht mehr, Workspace und Verhalten seien nachweislich funktional getrennt. Reserviertes Motiv, K−1-Auswahl, Broadcast-Zeitversatz und die begrenzte GWT-Zuordnung sind sichtbar. W3 heißt jetzt fehlgeschlagene Planausführung; die Grenze gegenüber Intentionsschutz steht ausdrücklich im Text. Die zusätzliche Diagnose von Gleichständen verändert die Interpretation sinnvoll: Der Bonus wirkt hier stark als Auswahl zugunsten eines bisherigen Inhalts unter gleich bewerteten Kandidaten. Das ist eine engere und nachvollziehbarere Aussage als die ursprüngliche allgemeine Hysterese-Erzählung.

Auch die bisher übersehene Ausgangsbasis A und die rechten Beobachtungsgrenzen werden nicht mehr versteckt. Diese Änderungen sind inhaltliche Verbesserungen, keine bloße sprachliche Kosmetik.

## Status aller ursprünglichen Reviewpunkte

| Alter Punkt | Status in Runde 2 | Begründung / Rest |
|---|---|---|
| P2-01 Nullbefunde / Gleichwertigkeit | Weitgehend erledigt | Neuer Titel, explizit keine Äquivalenzanalyse, Unsicherheit und sekundäre Korrektur berichtet. Einzelne Gleichheitsformulierungen sollten weiter deskriptiv bleiben. |
| P2-02 Architektur / GWT | Erledigt im jetzt eingeschränkten Anspruch | Reserviertes Motiv, Inhaltsrepräsentationen, Empfänger, Zeitversatz und fehlendes GWT-4 sind beschrieben. Die Arbeit beansprucht keine vollständige GWT-Implementierung. |
| P2-03 Vorarbeiten | Weitgehend erledigt | Bach, OpenPsi und Dossa werden tatsächlich mit Persistenzmechanismen diskutiert; kein Anspruch auf erstmalige Erfindung von Workspace-Gedächtnis. Versionsgenauigkeit der Buchzitate bleibt redaktionell zu prüfen. |
| P2-04 Richtige Vergleichsbasis | Erledigt | A/B/E werden für dieselben 20 Seeds verglichen; Stabilisierung ist ausdrücklich relativ zum Workspace ohne Bonus. |
| P2-05 Plan und Datenzugriff | Noch nicht erledigt | Chronologietabelle und 80-Seed-Analyse sind gut; „evaluated only for errors“ widerspricht der bereits damals festgehaltenen inhaltlichen Screeningauswertung, siehe R2-P2-01. |
| P2-06 Zensierung / Inhaltsarten | Für den deskriptiven Endpunkt weitgehend erledigt | W1 ist beobachtete Aufenthaltslänge; Zensierungsanteile, gemeinsame Fenster und Artenwechsel sind genannt. Das ist keine Schätzung unzensierter Lebensdauern, wird jetzt aber auch nicht als solche benötigt. |
| P2-07 H3 / endogenes Arousal | Erledigt im begrenzten Anspruch | Endogenität, Kapazitätspfad und fehlender isolierter Kausalnachweis sind ausdrücklich beschrieben. Ein neues faktorielles Experiment ist für diese begrenzte Aussage nicht Voraussetzung. |
| P2-08 W3/W4 | Begrifflich weitgehend erledigt; Reproduktion teilweise offen | Per-Plan-Auswertung und alternative Exposition sind sinnvoll. Der neue Pro-Handlung-Nenner ist aus dem Archiv nicht verfügbar, siehe R2-P2-02. |
| P2-09 H6 / Hysterese | Erledigt | Selektorherleitung, lokale Manipulationsprüfung und nicht untersuchte Multistabilität des geschlossenen Agenten sind getrennt. |
| P2-10 Gleichstände / Skalierung | Deutlich bearbeitet, Restinterpretation offen | S1–S3 geben substantielle neue Belege. „Hardly affected B“ unterschätzt den Effekt auf W1; siehe R2-P2-03. |
| P2-11 Statistik / Verfügbarkeit | Teilweise erledigt | Einheiten, Intervallart, Familien und 420/500 sind richtig beschrieben. Reproduktionszusage zu weit; der Rangtest prüft nicht die zuvor genannte Symmetrieannahme weg. |
| P2-12 Abbildungen / Schlussfolgerung | Weitgehend erledigt | Gepoolte Gewichtung, Zensierung, Beispielcharakter und nicht korrespondierende Zeilen erklärt. Keine erneute grundlegende Abbildungsarbeit verlangt. |

## R2-P2-01 — Die Screeningphase enthielt bereits inhaltliche Ergebnisinterpretation

**Priorität: hoch. Fundstellen:** `manuskript.tex:100,116`; Antwort P2-05; `analysis/workspace/vorauswahl/README.md` und `tests.json` im historischen Commit `0d78571d1792e28ffb02450046d9db7c24b5041b` vom **11.11.2026, 12:04:16 UTC**.

Das Manuskript sagt, die Vorauswahl sei ausschließlich auf Fehler ausgewertet worden. Im damals bereits committeten Protokoll stehen jedoch ausdrücklich Beobachtungen für die Planung der Bestätigung:

- große Effekte für H1, H4 und H6;
- kein Unterschied bei H3, verbunden mit einer Vorhersage, dass das kombinierte Kriterium dann nicht gestützt sein werde;
- keine Unterschiede bei H2 und H5;
- Ergebniskennzahlen, Effektgrößen und Hypothesentests in den begleitenden Dateien.

Der Commit enthält nicht nur automatisch erzeugte p-Werte, sondern auch eine ausformulierte inhaltliche Interpretation. Er trägt zudem den Titel „screening ... paper tables and figures from screening data“. Die damalige Verwendung ist damit mehr als eine reine Funktionsprüfung.

**Was daraus folgt:** Die Darstellung des Kenntnisstands muss korrigiert werden. Daraus folgt **weder ein Vorwurf absichtlicher Täuschung noch automatisch die Ungültigkeit der gesamten Studie**. Der Analyseplan erlaubte die Wiederverwendung der 20 Seeds. Die zusätzlich gerechneten 80 Seeds bestätigen das Signifikanzmuster. Aber diese Tatsachen rechtfertigen keine nachträgliche Beschreibung als ausschließlich technische Fehlerprüfung.

**Auftrag:** Im Manuskript und in der Antwortdatei offen sagen, dass Screeningeffektgrößen und Hypothesentests vor der abschließenden Analyse vorlagen und inhaltlich besprochen wurden. Danach belegbar angeben, ob Hypothesen, Endpunkte oder Entscheidungsregel noch geändert wurden; die bereits benannten früheren Amendments zeitlich getrennt halten. Die 100-Seed-Analyse als geplante Gesamtauswertung mit 20 bereits explorativ ausgewerteten Seeds und die 80-Seed-Analyse als separat berichtete Sensitivität bezeichnen. Auch die Chronologietabelle muss den Ergebniszugriff zeigen.

**Erledigt, wenn:** Die neue Fassung mit dem historischen README und den erzeugten Tests vereinbar ist. Eine neue Studie ist zur Korrektur dieser Transparenzfrage nicht erforderlich.

## R2-P2-02 — Neue Auswertungen benötigen nicht archivierte Aktivitätsdateien

**Priorität: hoch. Fundstellen:** `manuskript.tex:172,194`; `scripts/revision_analysis.py:282–300`; `scripts/sync_workspace_runs.py:46–58`; `analysis/revision/README.md`.

Das Workspace-Archiv enthält je Leben `metrics.json` und `Workspace(1).jsonl.gz`. Der Wiederhersteller erzeugt daraus Kennzahlen und Workspace-Log, **keine `raw/Activities(1).Txt`**. Die neue Analyse für Gelegenheitsbefriedigungen pro 1.000 Handlungen liest aber genau diese zusätzliche Datei, um ihren Nenner zu zählen.

Das wurde in diesem Review nicht nur aus dem Code vermutet: Nach Wiederherstellung des echten B-Logs für Seed 1001 brach

```bash
python scripts/revision_analysis.py --only paper2 --out <Prüfausgabe>
```

bei der fehlenden Datei `runs/ws-B/seed1001/raw/Activities(1).Txt` ab. Im gesamten Git-Baum des geprüften Workspace-Archivs gibt es keine solchen Aktivitätsdateien. Das ist eine Lücke des dokumentierten Archivs, nicht bloß eine von diesem Reviewer ausgelassene vorhandene Datei. Die vollständigen ursprünglichen H1–H6 können gleichwohl anhand archivierter Kennzahlen geprüft werden; genau diese Rechnung wurde erneut bestätigt.

Durch den Abbruch werden außerdem spätere, allein aus den vorhandenen Workspace-Logs berechenbare Revisionsanalysen vom gemeinsamen Skript nicht mehr erreicht. Die Aussage, alle Tests und Tabellen seien aus den archivierten Logs reproduzierbar, ist daher zu weit, wenn sie auch die neuen Resultate einschließt. Die mitgelieferte `paper2.json` zeigt berechnete Endwerte; sie liefert den fehlenden Ausgangsnenner nicht.

**Auftrag:** Die benötigten Aktivitätsdaten archivieren **oder** einen neuen, nachvollziehbaren Zusatzdatensatz mit den benötigten Handlungszahlen pro Seed/Bedingung beilegen. Das erfordert nicht zwingend die Veröffentlichung vollständiger historischer Dateien. Die Zählregel, ihre Quelle und eine Identifikations-/Hashbeziehung zum ursprünglichen Lauf dokumentieren. Alte Bestätigungsdateien dabei unverändert lassen. Das Auswertungsskript so gliedern, dass eine fehlende Eingabe eindeutig benannt wird und unabhängige Analysen getrennt aufrufbar sind. Zum Abschluss den gesamten Revisionslauf in einer frischen Kopie des vorgesehenen Verteilungsumfangs ausführen und die JSON-Ergebnisse vergleichen.

**Erledigt, wenn:** Auch die in Abschnitt „Behaviour and performance“ neu berichtete Handlungsnormierung und die weiteren Revisionswerte aus den vorgesehenen archivierten Eingaben erneut erzeugt werden. Bis dahin die Verfügbarkeitsaussage entsprechend einschränken. Das Vorliegen einer richtigen ursprünglichen Hypothesentabelle allein schließt diesen Punkt nicht.

## R2-P2-03 — Zufällige Gleichstände ändern auch B bei der Verweildauer deutlich

**Priorität: mittel. Fundstellen:** `manuskript.tex:178`; Antwort P2-10.

„The tie rule hardly affected B“ ist für Zielwechsel deskriptiv nachvollziehbar, nicht als Zusammenfassung aller Workspace-Endpunkte. Die berichtete mittlere Nicht-Motiv-Verweildauer steigt in B von etwa 33,6 auf 41,9 Zyklen. Das sind ungefähr **25 %**.

**Zusätzliche Nachrechnung dieses Reviews**, gepaart über dieselben 20 Seeds, mit dem vorhandenen Bootstrap-/Permutationstest und ohne Korrektur für eine neue Testfamilie:

| B: Zufallsregel minus Namensregel | Mittlere Differenz | Punktweises 95-%-KI | Unkorrigiertes p |
|---|---:|---|---:|
| W2b, Zielwechsel pro 100 Zyklen | −0,326 | [−0,900; 0,193] | 0,2785 |
| W1, Nicht-Motiv-Verweildauer in Zyklen | +8,279 | [3,946; 12,611] | 0,00210 |

Diese Rechnung ist keine neue Bestätigungshypothese, sondern zeigt, dass „kaum beeinflusst“ vom gewählten Endpunkt abhängt. Für E sind die Änderungen sehr viel größer; das macht den B-Effekt nicht automatisch vernachlässigbar.

**Auftrag:** Die Effekte getrennt formulieren: Zielwechsel in B ähnlich, beobachtete Aufenthaltslängen in B länger; E verändert sich bei beiden Größen wesentlich stärker. Falls die direkte B-gegen-B-Auswertung übernommen wird, als zusätzliche explorative Analyse kennzeichnen und die Intervall-/Testart angeben. „Most of this effect arises at ties“ präzisieren: S1 zerlegt zunächst den **lokalen W6-Unterschied zur namensgeordneten Auswahl**, nicht kausal sämtliche langfristigen Änderungen von W1 und Verhalten.

**Erledigt, wenn:** Die Interpretation die Endpunktabhängigkeit berücksichtigt und die diagnostische Ein-Schritt-Zerlegung nicht mit einer vollständigen kausalen Zerlegung des rückgekoppelten Agenten verwechselt.

## R2-P2-04 — Zwei kleinere methodische Klarstellungen

**Priorität: niedrig bis mittel.** Hier ist keine neue große Versuchsserie gefordert.

**a) Signed-Rank ist keine Prüfung gegen beliebige Asymmetrie.** `revision_analysis.py:66–84` permutiert die Vorzeichen der Ränge. Das ist eine sinnvolle Empfindlichkeitsprüfung gegenüber der Gewichtung großer Differenzen, beseitigt aber nicht von selbst die Symmetrie-/Vorzeichenaustauschbarkeitsannahme. Im Text nicht als allgemeine Absicherung gegen die zuvor benannte Annahme verkaufen. „Auch mit rangbasierter Gewichtung gleiches Muster“ ist die engere belastbare Aussage. Entweder diese Einschränkung nennen oder eine gezielt zur behaupteten Robustheit passende weitere Prüfung begründen.

**b) Der Ersatz für S1-E gilt nicht automatisch entlang derselben Trajektorie.** Nachtrag 1 des Sensitivitätsplans begründet das Weglassen von S1-E damit, dass die Diagnose vor der zufälligen Auswahl erfasst werde und daher auch aus S2-E vorliege. Das stimmt innerhalb des aktuellen Zyklus, macht aber die vorherigen zufälligen Auswahlen und deren Effekte auf Agent/Welt nicht ungeschehen. Die 96 % Gleichstände stammen aus E mit Zufallsregel. Das Manuskript benennt diesen Arm korrekt; Plan/Antwort sollten nicht zusätzlich Äquivalenz zur nie gerechneten Namensregel-Diagnose suggerieren. Es genügt, den eingeschränkten Diagnoseumfang transparent zu benennen. S1-E muss nicht allein deshalb nachgerechnet werden.

## R2-P2-05 — Redaktioneller Abschluss und akzeptierte Grenzen

- Die GWT-Abgrenzung, die Beschreibung des reservierten Motivs und die zeitlich versetzte Zielliste können für den jetzigen Anspruch akzeptiert werden. Kein weiterer Architekturumbau wird hier verlangt.
- Die ausdrücklich beobachtete, teilweise rechtszensierte Aufenthaltslänge ist als deskriptiver Endpunkt zulässig. Das gemeinsame Fenster ist eine Sensitivität gegen unterschiedliche Beobachtungsgelegenheiten, keine nachträgliche Schätzung vollständig beobachteter Verweildauern. Diese Einschränkung nicht in späteren Zusammenfassungen wieder verlieren.
- Die Dossa-Darstellung zur Rückkopplung des vorherigen Workspace-Zustands wurde an der Primärquelle gegengeprüft. Auch der Bonus-/Hysteresemechanismus steht in einem öffentlich zugänglichen Bach-Entwurf. Für das wörtliche Buchzitat und die angegebenen Abschnittsnummern noch die tatsächlich benutzte Ausgabe fixieren. Das ist eine Versionsfrage, kein erneut offener Nachweis der ganzen Vorarbeit.
- Öffentliche Bibliografie-Notizen wie „ungeprüft“ und „Platzhalter“ sowie URL-/Lizenz-/Archivplatzhalter vor einer Einreichung bereinigen. Die Manuskripte sind Arbeitsfassungen, keine freigegebenen Publikationen.
- Das neu formulierte Nullergebnis darf eng bleiben: kein unter dem festgelegten Verfahren gesicherter Zusatznutzen in dieser Welt. Es ist keine praktische Gleichwertigkeit bewiesen. Diese nun weitgehend richtige Einordnung wird akzeptiert.

## Empfohlene nächste Überarbeitung

1. Screeningkenntnisstand anhand des damaligen README richtigstellen.
2. Fehlende Ausgangsnenner archivieren und den Revisionslauf vollständig aus dem vorgesehenen Datenumfang reproduzieren.
3. Die Endpunktabhängigkeit der Gleichstandsregel in B sowie die beiden methodischen Klarstellungen einarbeiten.
4. Bibliografie und Ausgabe-/Versionsangaben abschließen und eine Antwort auf diese Runde ergänzen.

Die verbleibenden Hauptprobleme sind konkret behebbar. Es ist nicht nötig, die ursprüngliche Bestätigung zu überschreiben, die Nullbefunde nachträglich signifikant zu machen oder neue große Simulationen allein zur Erledigung dieses Reviews zu starten.

## Tatsächlich ausgeführte Prüfungen

| Prüfung | Ergebnis |
|---|---|
| Ursprüngliche H1–H6 aus der 500-zeiligen Kennzahlentabelle | Mittelwertdifferenzen, Bootstrapgrenzen, p und Holm-p exakt reproduziert; maximale Abweichung 0 |
| Separate Seeds 1021–1100 | Alle sechs archivierten Testresultate exakt reproduziert; maximale Abweichung 0 |
| S2 aus 40 neuen Kennzahlendateien | Alle sechs ausgegebenen Workspace-Mittelwerte und B−E-Vergleiche unter beiden Regeln exakt reproduziert |
| S3 aus 40 neuen Kennzahlendateien und bisherigen E/D-Werten | Ausgegebene Mittelwerte und sechs Leistungsvergleiche hoher Bonus gegen E exakt reproduziert |
| S1-B: 20 neue Diagnose- und 20 Bestätigungslogs | Inhalte einschließlich geloggter Stärken/Eintrittsangaben sowie führendes Ziel und Alter in allen 20 Leben identisch |
| S1-Diagnose, 18.736 Zyklen | Effektiver Grenzgleichstand 9,9274 %; Abweichung von jeder bonusfreien Gleichstandsauswahl 6,0739 %; von namensgeordneter Auswahl 35,9629 % |
| Historischer Screeningcommit 0d78571 | Ergebnisdateien und bereits formulierte inhaltliche Auswertung vor dem Start der abschließenden Auswertung verifiziert |
| Gesamter neuer Revisionslauf | Nicht vollständig reproduzierbar: fehlende `Activities(1).Txt` für den neuen Nenner; siehe R2-P2-02 |
| PDF | Alle elf Seiten gerendert; überarbeitete Tabellen und Abbildungen visuell geprüft, kein erneuter alter Tabellenüberlauf gefunden |

Die Rechnungen aus Kennzahlendateien prüfen die Konsistenz archivierter Ergebnisse mit der implementierten Statistik. Sie sind kein neuer Lauf des Agenten und keine vollständige unabhängige Validierung aller Messkonstrukte. Von S2/S3 wurden die Kennzahlendateien nachgerechnet, nicht sämtliche Rohlogs erneut in Kennzahlen umgewandelt. Der vollständig rohe Nachweis in dieser Runde betrifft die 20 S1-Leben und deren Vergleichslogs.

`pytest` in der unvollständig materialisierten Prüfkopie: **114 passed, 64 failed, 16 errors, 2 skipped**; die 80 Fehler-/Fehlschlagmeldungen betreffen fehlende Dateien (`FileNotFoundError`). Keine neue Implementierungsregression daraus abgeleitet und keine vollständige grüne Golden-Master-Suite behauptet. Claudes vollständige Arbeitsumgebung mit Originaldateien wurde in dieser Sitzung nicht nachgestellt. Keine neuen Simulationsleben gerechnet und keine wissenschaftlichen Quelltexte im Repository geändert.

Extern gezielt gegengeprüft:

- [Bach: öffentlich zugänglicher Entwurf von *Principles of Synthetic Intelligence*](https://cognitive-ai.com/publications/assets/Draft-MicroPsi-JBach-07-03-30.pdf), Passage zur Intentionsauswahl: expliziter Bonus und Stabilisierung durch Hysterese. Nicht mit einer unabhängigen Kontrolle der gedruckten Ausgabe 2009 oder aller dortigen Abschnittsnummern gleichzusetzen.
- [Dossa et al. (2024), Primärtext](https://pmc.ncbi.nlm.nih.gov/articles/PMC11211627/), Abschnitt 2.4: vorheriger Arbeitsgedächtniszustand in Aufmerksamkeitsabfrage und rekurrenter Aktualisierung; die frühere Abgrenzungslücke ist damit sachlich behandelt.
