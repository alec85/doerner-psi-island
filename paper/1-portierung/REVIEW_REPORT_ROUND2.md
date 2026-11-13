# Zweiter Review: Rekonstruktion des PSI-Inselagenten

**Urteil: deutlich verbessert; die grundlegenden inhaltlichen Einwände sind überwiegend erledigt. Vor Einreichung ist noch eine gezielte Überarbeitung nötig, besonders der Reproduktionszusage und der endgültigen Versionsangaben. Eine neue große Originallaufstudie ist für die jetzt enger formulierte Aussage nicht erforderlich.**

- Datum: 13. November 2026; Reviewer: Codex.
- Geprüfter Stand: `6d058fff46c6cad137a9d562c556cb0368a24631` (`main`, Revision aus PR #46 / Issue #45).
- Bezug: [erster Bericht](REVIEW_REPORT.md), [Antwort von Claude](REVIEW_RESPONSE.md), aktuelles zehnseitiges PDF und LaTeX-Quelle. Zeilenangaben beziehen sich auf diesen Stand.
- Prüfprinzip: Erledigte Punkte werden geschlossen. Offengelegte Grenzen werden nicht durch die Forderung nach immer neuen Experimenten ersetzt. Die verbliebenen Punkte unten sind konkrete Korrekturen der vorliegenden Fassung.

## Fortschritt gegenüber Runde 1

Der zentrale Unterschied ist jetzt korrekt: Exakte Übereinstimmung bestimmter beobachteter Größen ist belegt; Verteilungsgleichheit über vollständige Leben ist es nicht. Das steht nicht mehr nur in den Einschränkungen, sondern bereits im Abstract. Ebenso sind die 97 vollständigen Paare, die Softwarestillstände und die nicht bekannte Version der früheren Humanstudie sauber getrennt. Die neue Evidenzmatrix, Parameterübersicht, Laufprovenienz und Architekturabbildung verbessern die Nachvollziehbarkeit wesentlich.

Die ursprünglichen schwersten Einwände P1-01, P1-02 und P1-07 erfordern deshalb **keine erneute grundlegende Überarbeitung**. Die Arbeit kann als nachvollziehbar begrenzte Software-Rekonstruktion beurteilt werden, ohne zusätzlich eine ungeprüfte Äquivalenzbehauptung verteidigen zu müssen.

## Status aller ursprünglichen Reviewpunkte

| Alter Punkt | Status in Runde 2 | Begründung / Rest |
|---|---|---|
| P1-01 Verteilungsgleichheit | Erledigt | Abstract und Abschnitte 3/4 verneinen den Nachweis ausdrücklich. |
| P1-02 Reichweite der exakten Vergleiche | Weitgehend erledigt | 75.000 Ziehungen, beobachtete vollständige Ausgaben, Stapel-/Heaprest und Seed 1035 sind getrennt. Kleine Reichweitenformulierungen verbleiben, siehe R2-P1-04. |
| P1-03 Verfügbarkeit | Teilweise erledigt | Die Abhängigkeit von nicht mitgelieferten Originaldateien ist jetzt ehrlich genannt. Die weitergehende Reproduktionszusage braucht einen vollständigen ausführbaren Weg; siehe R2-P1-01/02. |
| P1-04 Ausfälle und vollständige Fälle | Erledigt | 3/100 beziehen sich auf die Rekonstruktion; zwei Fälle sind im Original bestätigt. Der Leistungsvergleich ist ausdrücklich bedingt auf vollständige Referenzleben. |
| P1-05 Variantenprovenienz und Einzelursachen | Weitgehend erledigt | 200 Manifestzeilen, sechs/sieben Schalter und die zwei Eingriffe des Nil-Schutzes sind dokumentiert. Keine unbelegte Zerlegung des Bündeleffekts mehr. Historische Erzeugungscommits bleiben unbekannt und dürfen nicht nachträglich erfunden werden. |
| P1-06 Exposition | Weitgehend erledigt | Zusätzliche Nenner und gemeinsame Fenster sind berichtet und als nachträglich gekennzeichnet. Die Neuberechnung aller Rohdaten konnte hier nicht vollständig geprüft werden; siehe Prüfprotokoll. |
| P1-07 Historische Humanstudie | Erledigt | Die konkrete Zuschreibung der gefundenen Fehler an die unbekannte Studienversion ist gestrichen. |
| P1-08 Belegketten | Weitgehend erledigt | Codeorte, Buchregel, algebraischer Ausdruck und Beispiele sind im Text nachvollziehbar. Die Buchseiten wurden in dieser Sitzung nicht aus einer Primärkopie geprüft; diese Grenze wird nicht als bestätigter Fehler gewertet. |
| P1-09 Parameter und Motivdominanz | Erledigt mit kleiner Klarstellung | Sieben Bedürfnisse, Vergessensrate, gepoolte und lebensweise Anteile stehen im Text. Die Zyklenspanne braucht eine explizite Stichprobenbezeichnung. |
| P1-10 Literatur und Darstellung | Teilweise erledigt | Tabellenüberlauf behoben, Abbildung und Vergleichstabelle ergänzt. Bibliografische Prüfnotizen und Publikationsplatzhalter sind noch offen. |

## R2-P1-01 — Reproduktion der zusätzlichen Ergebnisse durchgehend ermöglichen

**Priorität: hoch vor Einreichung. Fundstellen:** `manuskript.tex:210`; `scripts/revision_analysis.py:129–200`, insbesondere Zeile 188; `analysis/revision/README.md`; außerdem der zweite Reviewbericht zu Paper 2, R2-P2-02.

Die Einschränkung, dass neue Agentenläufe Originaldateien benötigen, ist akzeptabel und nun transparent. Davon getrennt behauptet das Paper, Tabellen und Auswertungen archivierter Läufe seien ohne diese Dateien reproduzierbar. Für die neue Revisionsanalyse ist der Weg noch nicht durchgehend hergestellt:

- `revision_analysis.py --only paper1` liest nach der Auswertung der archivierten Leben zusätzlich `read_param_dat()` aus `reference/`. Das verhindert einen erfolgreichen vollständigen Lauf gerade in dem beschriebenen Umfang ohne `reference/`, obwohl die Ergebnisanalyse selbst keine erneute Simulation verlangt.
- Für Paper 2 benutzt dieselbe Datei zusätzlich nicht im Workspace-Archiv enthaltene Aktivitätsdateien. Die erfolgreiche Prüfung der ursprünglichen H1–H6 und P-Vergleiche bestätigt deshalb noch nicht alle neu aufgenommenen Analysen.
- Bereits berechnete Werte aus `paper1.json` in eine Tabelle zu setzen und diese Werte aus archivierten Ausgangsdaten erneut zu berechnen sind zwei unterschiedliche Reproduktionsleistungen. Das Manuskript muss sagen, welche davon jeweils geprüft wurde.

**Auftrag:** Einen dokumentierten Ablauf für eine frische Kopie ohne `reference/` ergänzen: Archiv entpacken, Analysen rechnen, Tabellen erzeugen, Resultate vergleichen. Den Parameterblock der reinen Archivauswertung von der Laufzeitdatei entkoppeln, etwa durch einen archivierten Parameterschnappschuss oder einen getrennten optionalen Metadatenschritt. Die Aussage zur Reproduzierbarkeit auf tatsächlich geprüfte Ergebnisse begrenzen, solange ein Teil noch nicht ausführbar ist. Originalmaterial muss dafür nicht veröffentlicht oder neu lizenziert werden.

**Erledigt, wenn:** Der dokumentierte Reproduktionslauf endet erfolgreich und reproduziert die berichteten Schätzungen und Intervalle aus den vorgesehenen Eingaben. Fehlende Eingaben müssen einen verständlichen Fehler auslösen, kein stilles Überspringen und keine nur scheinbare vollständige Reproduktion.

## R2-P1-02 — Das Eingabenmanifest enthält Kategorie-Hashes, keine Einzeldatei-Hashes

**Priorität: mittel. Fundstellen:** `manuskript.tex:210`; `scripts/input_manifest.py:18–45`; `analysis/revision/eingaben.csv`.

Das Manifest hat fünf Zeilen für Eingabekategorien. Die Bitmapkategorie umfasst 267 Dateien; die Weltkategorie fünf. Das Skript bildet einen eigenen Hash über relative Dateinamen und die jeweiligen Inhalts-Hashes. Selbst für einen einzelnen Dateipfad ist dies nicht der gewöhnliche SHA-256 der Dateibytes. Die CSV bezeichnet das zutreffend als `sha256_tree`, während die Formulierung „lists each with a SHA-256 hash“ nach Einzeldatei-Hashes klingt.

Zusätzlich behandelt `digest()` einen nicht existierenden Pfad wie ein leeres Verzeichnis. Der direkte Aufruf mit einem fehlenden Pfad ergab in dieser Sitzung **0 Dateien und den SHA-256 des leeren Bytestroms**, ohne Fehler. Ein Leser kann so ein scheinbar gültiges, tatsächlich leeres Manifest erzeugen.

**Auftrag:** Entweder ein echtes Einzeldateimanifest mit gewöhnlichem Inhalts-Hash erzeugen oder die vorhandenen Kategorie-Hashes samt Algorithmus eindeutig beschreiben. Für fehlende erforderliche Dateien/Verzeichnisse hart abbrechen; ein legitim leeres Verzeichnis von einem nicht existierenden Pfad unterscheiden. Die Formulierung „four inputs“ durch „vier Kategorien benötigter Eingaben“ ersetzen und die nur für Originalausführung/Binärtests benötigte EXE von den Eingaben eines Python-Laufs trennen.

**Erledigt, wenn:** Ein Leser die Hashes mit dokumentierten Befehlen prüfen kann und fehlende Originaldateien nicht als leere, erfolgreiche Prüfung erscheinen.

## R2-P1-03 — Versions- und Umgebungsangaben fertigstellen

**Priorität: mittel vor Einreichung. Fundstellen:** `manuskript.tex:123,210`; Antwort P1-03/P1-05.

Die Quelle enthält weiterhin Platzhalter für Erzeugungscommit, Laufzeit, Hardware, öffentliche Adresse, Lizenz und archivierte Version. „At the revision commit“ identifiziert keinen eindeutigen Stand, wenn weitere Revisionen folgen. Hashes archivierter Läufe sichern die Datenidentität, ersetzen aber keine Identifikation des Codes, der neue Leser ausführen sollen.

**Auftrag:** Den überprüfbaren Analyse-/Artefaktstand und einen getesteten Umgebungsstand festlegen. Für historische Erzeugungscommits ausdrücklich „nicht gespeichert“ berichten, soweit sie nicht rekonstruierbar sind; keinen falschen Präzisionsanspruch erzeugen. Laufzeit nur aus einer wirklichen Messung mit Hardwareangabe nennen oder die Platzhalterforderung streichen, falls die Zahl für den Beitrag nicht benötigt wird. URL und Lizenz erst nach den dafür vorgesehenen Entscheidungen ergänzen.

**Erledigt, wenn:** Die finale Fassung keine wissenschaftlich relevanten Versionsplatzhalter mehr enthält. Dieser Review autorisiert keine Veröffentlichung oder Lizenzentscheidung.

## R2-P1-04 — Einige Restformulierungen reichen noch über die eigene Evidenz hinaus

**Priorität: niedrig bis mittel. Fundstellen:** `manuskript.tex:29,57,67,157`.

1. **„Most complete realisation“ / „only under emulation“:** Für die Rangbehauptung und die universelle Aussage zur Ausführbarkeit liefert die Arbeit keinen Nachweis. Die eigene Untersuchung erfolgte unter Wine. „Wir betrieben die vorliegende Distribution unter Wine“ ist belegt; eine Aussage über alle anderen Laufumgebungen ist es nicht. Beschränken oder separat belegen.
2. **786–1170 Zyklen:** Die Spanne beschreibt die 97 vollständigen Referenzmodus-Läufe der Hauptstichprobe 1001–1100. Sie umfasst nicht alle im Paper beschriebenen vollständigen Referenzverläufe: Seed 16 hat 739 Zyklen. Den Nenner/Stichprobenbereich direkt im Satz angeben.
3. **„Keeps all of them in the reference mode“:** Der Text erklärt vorher korrekt, dass der Heaprest bereits im Referenzmodus nicht nachgebildet wird. Die pauschale Erhaltungsbehauptung anschließend entsprechend einschränken. Der moderne Richtungsschalter entfernt zusätzlich den nachgebildeten Stapelrest; er ist keine erstmalige Entfernung eines im Referenzmodus vollständig erhaltenen Heapverhaltens.

**Erledigt, wenn:** Die enger gefasste Evidenzmatrix auch in den zusammenfassenden Sätzen ohne widersprechende Universalformulierungen wiedererkennbar ist.

## R2-P1-05 — Bibliografie abschließen; Darstellung im Wesentlichen akzeptiert

**Priorität: niedrig vor Einreichung.** Die LaTeX-Dateien und das PDF zeigen die früher kollidierende Schaltertabelle jetzt mit kontrollierten Umbrüchen; eine erneute grundlegende Layoutänderung ist nicht nötig. Die Architekturabbildung und die Mittelwerte beider Arme sind hilfreiche Ergänzungen.

In `referenzen.bib` stehen allerdings weiter öffentliche `note`-Felder wie „ungeprüft“, „Seiten ungeprüft“ und „Platzhalter“. Solche Arbeitsnotizen erscheinen im Literaturverzeichnis. Bibliografische Angaben prüfen und diese Notizen aus der Einreichungsfassung entfernen; offene Prüfungen können im internen Literaturprotokoll bleiben. Die Aussage „Literatur geschlossen“ in der Arbeitsplanung ist dafür zu weit.

## Priorisierte nächste Überarbeitung

1. Den Archiv-Reproduktionsweg nach R2-P1-01 herstellen und die Zusage bis dahin präzisieren.
2. Manifestfehler und Versionsangaben bearbeiten.
3. Die wenigen Reichweitenformulierungen und bibliografischen Arbeitsnotizen korrigieren.
4. Antwortdatei um diese Runde ergänzen; je Punkt tatsächlichen Nachweis oder ausdrücklich verbleibende Grenze nennen.

**Nicht erforderlich für diese engere Fassung:** Eine neue Äquivalenzstudie, eine neue historische Humanvalidierung oder das Offenlegen nicht freigegebener Originaldateien. Diese früheren Einwände sind durch die begrenzte Aussage bzw. transparente Einschränkung behandelt.

## Prüfprotokoll und Grenzen

- Gelesen: aktuelles Manuskript, vollständige Antwortdatei, erster Bericht, neue Analyseskripte, Eingaben- und Laufmanifest, zugehörige Ergebnisdateien und relevante Änderungen an Quelle/Tests. Das Laufmanifest enthält 200 Datensätze; das Eingabenmanifest fünf Kategorien.
- Die PDFs beider Paper wurden erneut gerendert (Paper 1: zehn Seiten) und visuell auf die überarbeiteten Tabellen, Abbildung und grobe Layoutfehler geprüft. Kein alter Tabellenüberlauf festgestellt.
- Für die gemeinsame Prüfung mit Paper 2 wurden H1–H6 und die 80-Seed-Sensitivität erneut exakt aus CSV reproduziert, S2/S3 aus 80 neu archivierten Kennzahlendateien nachgerechnet und 20 S1-Diagnoselogs mit 20 Bestätigungslogs verglichen. Das bestätigt diese abgegrenzten Zahlenprüfungen, nicht eine vollständige Neuberechnung aller Paper-1-Expositionsanalysen.
- `pytest` in der weiterhin unvollständig materialisierten Prüfkopie: **114 passed, 64 failed, 16 errors, 2 skipped**. Sämtliche 80 Fehler-/Fehlschlagmeldungen sind `FileNotFoundError` für fehlende Original-, Welt- oder Trace-Dateien. Das ist **kein neu nachgewiesener Fehler der wissenschaftlichen Implementierung** und wegen des anderen Materialisierungsumfangs kein Gegenbeweis zu Claudes dokumentierten Testzahlen. Eine vollständige grüne Golden-Master-Suite wurde hier nicht neu bestätigt. Die beiden über GitHub gelesenen Stringvergleichsfixtures wurden vor dem Lauf auf ihre originalen Git-Blob-Hashes geprüft.
- Keine neuen Original- oder Agentenleben gerechnet; keine Manuskripte, Tests oder wissenschaftlichen Quelltexte im Repository geändert. Die historische Buchseite 99 und die gedruckte Bach-Ausgabe wurden in dieser Sitzung nicht unabhängig geprüft.
