# Kritischer Review: Hysterese im PSI-Workspace

**Urteil: grundlegende Überarbeitung; derzeit nicht einreichungsreif.** Die archivierten Hypothesentests sind numerisch nachvollziehbar, und das Manuskript berichtet das Scheitern seines kombinierten Erfolgskriteriums ausdrücklich. Das ist eine wichtige Stärke. Die theoretische Rahmung, mehrere Operationalisierungen und besonders die Interpretation der Nullbefunde halten einer strengen Prüfung jedoch noch nicht stand. Ein wissenschaftlich tragfähiger Beitrag muss enger und präziser formuliert werden.

- Reviewdatum: 12. November 2026; Reviewer: Codex.
- Geprüfter Stand: `alec85/psi-gw`, Commit `ef15fb05becdfcd8a149b182e63da8690e955756`.
- Gegenstand: `manuskript.tex`, das neunseitige PDF, Methoden- und Literaturdateien, Analyseplan mit Nachträgen, ADRs, Workspace- und Statistikcode, Kennzahlentabelle und archivierte Auswertungen. Zusätzlich wurde das komprimierte Workspace-Protokoll B/Seed 1001 gelesen. Zeilenangaben beziehen sich auf diesen Stand.
- **Blocker** betreffen die zentrale Schlussfolgerung; **Major** betreffen Versuchslogik, Messung oder Reproduzierbarkeit. Die Aufträge unterscheiden notwendige Korrekturen dieser Arbeit von optionalen neuen Experimenten.

## Prioritäten

| ID | Gewicht | Problem | Erforderliches Ergebnis |
|---|---|---|---|
| P2-01 | Blocker | Nichtsignifikanz wird als unverändertes Verhalten verkauft | Titel, Abstract und Diskussion korrigieren oder Äquivalenz nachweisen |
| P2-02 | Blocker | GWT-Bezug und Verallgemeinerung der Motivschwelle sind zu weit | Tatsächliche Architektur und Reichweite formal darstellen |
| P2-03 | Major | Abgrenzung zur zustandsabhängigen Vorarbeit ist nicht haltbar | Dossa und Bach mechanistisch vergleichen; Neuheit enger definieren |
| P2-04 | Major | Stabilisierung hängt vom gewählten Vergleich ab | Ausgangsbasis A sichtbar in die Interpretation einbeziehen |
| P2-05 | Major | Präregistrierung und Pilotwiederverwendung brauchen präzise Chronologie | Versions-/Datenzugriffstabelle; getrennte Sensitivitätsanalyse |
| P2-06 | Major | W1/W5 behandeln laufende Aufenthalte wie abgeschlossene Dauern | Zensierung, Laufdauer und Inhaltswechsel offenlegen und prüfen |
| P2-07 | Major | H3 identifiziert keinen allgemeinen kausalen Arousal-Effekt | Endogene Kopplungen und Reichweite des Nullbefunds trennen |
| P2-08 | Major | W3/W4 messen nicht eindeutig Intentionsschutz bzw. Ablenkbarkeit | Codegenaue Definitionen, Expositionsnenner und zusätzliche Kontrollen |
| P2-09 | Major | H6 ist ein lokaler Selektorvergleich, kein unabhängiger Theorienachweis | Manipulationsprüfung behalten; Hysterese analytisch präzisieren |
| P2-10 | Major | Gleichstände und Score-Skalen können die Effekte bestimmen | Sensitivität und Entscheidungsmargen berichten |
| P2-11 | Major | Statistik und Reproduktionsumfang sind unvollständig beschrieben | Schätzgrößen, Intervalle, Konfiguration und tatsächliche Logzahl angeben |
| P2-12 | Minor/Major | Abbildungen und Theoriebezug überinterpretieren die Messungen | Legenden, Aggregation und Generalisierungsgrenzen schärfen |

## P2-01 — „Unchanged behaviour“ ist nicht nachgewiesen

**Fundstellen:** `manuskript.tex:18,26,98,107–127`; `analysis/workspace/bestaetigung/leistung.json`; Tabelle T2.

Der Titel und mehrere Schlusssätze behaupten unverändertes Verhalten bzw. Leistungen ohne Veränderung. Die Analyse prüft dagegen Unterschiede. Nach Holm nicht signifikant bedeutet nicht, dass die Bedingungen äquivalent sind. Das betrifft auch die Aussage, die positive Arousal-Korrelation sei „thus not a consequence“ der Kopplung: Der nicht signifikante Unterschied zwischen B und D beweist die Abwesenheit eines Beitrags nicht.

Die vorhandenen Unsicherheiten sind inhaltlich relevant. Für B minus A beträgt die Differenz des mittleren Schadensbedürfnisses −1,941 Prozentpunkte mit punktweisem 95-%-Bootstrapintervall [−3,418; −0,587] und Holm-p = 0,0534. Für den Anteil Versuch-und-Irrtum-Zyklen sind es −0,0181, Intervall [−0,0374; −0,0023], Holm-p = 0,2005. Punktweise Intervalle und korrigierte Tests müssen nicht dieselbe Entscheidung ergeben. Sie zeigen hier aber gerade, warum die dichotome Erzählung „kein Verhaltenseffekt“ unzulässig ist.

**Auftrag:** Überall formulieren: kein nach der festgelegten Korrektur statistisch gesicherter Effekt auf die untersuchten Leistungsmaße. Nicht von unverändertem Verhalten, fehlender Wirkung oder funktionaler Entkopplung als bewiesenem Resultat sprechen. Wenn praktische Gleichwertigkeit die zentrale Aussage bleiben soll, sinnvolle Äquivalenzgrenzen begründen und eine entsprechend ausgewiesene Äquivalenzanalyse durchführen. Grenzen dürfen nicht so gewählt werden, dass die schon sichtbaren Daten gerade hineinfallen. Eine spätere Analyse wäre eine zusätzliche Analyse, keine ursprüngliche Bestätigung.

**Erledigt, wenn:** Titel und Abstract ohne Nullwirkungsbehauptung auskommen. Ein ehrlicher Titel wäre etwa **“An incumbency bonus stabilizes workspace contents in a PSI island agent: limited evidence for arousal coupling and performance effects.”** Die schon korrekt berichtete Nichtstützung von H1+H3+H4 bleibt erhalten.

## P2-02 — Die Architektur ist noch kein hinreichend belegter globaler Informationsengpass

**Fundstellen:** `manuskript.tex:35,39,43–49,125`; `src/psi_gw/workspace/__init__.py:94–100,170–207,211–277`; `src/psi_gw/agent.py:228–233,257–274`; ADR 0016.

Ein begrenzter Prioritätsspeicher mit drei Auswirkungen auf die Handlungsregulation ist nicht automatisch ein globaler Engpass zwischen spezialisierten Modulen. Wahrnehmung, Motivation, Gedächtnis und Planung verarbeiten weiterhin Informationen außerhalb des Workspace. Das aktuelle Motiv wird vorab von der bestehenden Motivwahl bestimmt und erhält einen reservierten Platz. Es gewinnt seinen Platz daher nicht in demselben Wettbewerb wie Ziele oder Objekte. Andere Motive können Workspace-Inhalt sein, ohne dadurch zum aktuellen Motiv zu werden.

Auch der Broadcast ist heterogen: Die Zielliste erhält Inhalte der Vorperiode; danach wird der Workspace aktualisiert; `LookAround` und Exploration können den neuen Zustand lesen. `goal_neurons()` liefert neben Zielen auch die Neuronen von Erinnerungen und Planenden. Diese werden als Ziele mit ggf. neuem Linkgewicht 1 in die Zielliste eingefügt. Ein gespeicherter Endort des letzten Plans ist zudem kein vollständiger ausführbarer Plan und muss nicht eine noch aktuelle Absicht repräsentieren. Die Benennung der Inhaltsarten legt hier mehr psychologische Bedeutung nahe, als die Implementierung sichert.

**Auftrag:** Eine vollständige Aktualisierungsgleichung bzw. knappen Pseudocode pro Zyklus ergänzen: Motivation, `GoalGen`, alter Broadcast, Kandidaten, Auswahl, neuer Broadcastzugriff, Handlungsregulation, Logging. Für jede Inhaltsart festhalten: repräsentiertes Neuron, Score, Gültigkeits-/Verfallsregel, Empfängermodule und tatsächliche Wirkung. Reserviertes Motiv und K−1-Wettbewerb sichtbar unterscheiden. GWT-1 bis GWT-4 jeweils am konkreten Informationsfluss prüfen; eine variable Kapazität allein erfüllt GWT-4 nicht. Dieser Indikator verlangt zusätzlich zustandsabhängiges aufeinanderfolgendes Abfragen von Modulen, wie auch die eigene ADR erst für einen späteren Schritt vorsieht.

Die Arbeit kann den implementierten Speicher als **an GWT orientierte Erweiterung** untersuchen. Eine vollständige GWT-Architektur oder eine allgemeine Identifikation der PSI-Motivschwelle mit deren Selektionsmechanismus ist durch die vorliegenden Vergleiche nicht gezeigt.

**Erledigt, wenn:** Die Leser das tatsächliche Modell einschließlich Zeitversatz und Informationsumgehungen rekonstruieren können. Neue Architekturteile sind für eine enger formulierte Veröffentlichung nicht zwingend erforderlich.

## P2-03 — Der Neuheitsanspruch muss nach Lektüre der nächstliegenden Vorarbeiten neu geschrieben werden

**Fundstelle:** `manuskript.tex:35`; `literatur.md`, letzter Absatz; ADR 0016, Kontext.

Die Einleitung beschreibt jüngere GWT-Agenten als bei jedem Schritt neu entscheidend, ohne Vorteil des bisherigen Inhalts. Dossa et al. (2024), Abschnitt 2.4 und Abbildung 1C, verwenden ausdrücklich das vorige Arbeitsgedächtnis sowohl im Aufmerksamkeitsmechanismus als auch bei der rekurrenten Fortschreibung. Damit ist die pauschale Gegenüberstellung zu gedächtnisloser Auswahl nicht haltbar. Das beweist umgekehrt **nicht**, dass Dossa denselben additiven Amtsinhaberbonus implementiert. Genau diese beiden Aussagen müssen getrennt werden.

Noch näher liegt ein Punkt aus der eigenen ADR 0016: Dort wird Bachs *Principles of Synthetic Intelligence* mit „Access Memory (Workspace)“ und Selektionsschwelle als Bonus der aktiven Absicht, also Hysterese, beschrieben. Diese mögliche Vorwegnahme der Verbindung darf im Paper nicht hinter einer allgemeinen PSI-Zitation verschwinden. Der Primärtext wurde in diesem Review nicht geprüft; die ADR ist ein konkreter Prüfauftrag, kein bereits abschließender Prioritätsnachweis.

**Auftrag:** Vergleichstabelle für Bach, LIDA, Shanahan, neuronale Workspace-Modelle, Goyal und Dossa: Zustandsweitergabe, Persistenzmechanismus, Konkurrenzregel, expliziter Bonus, Arousal-Kopplung, empirische Fragestellung. Neuheit gegebenenfalls auf die einheitliche additive Regel über mehrere neuronale Inhaltsarten, die kontrollierten Ablationen und den Test im portierten Inselagenten begrenzen. Keine erste Erfindung von Workspace-Gedächtnis oder Persistenz behaupten.

**Erledigt, wenn:** Die Abgrenzung anhand der jeweiligen Methoden und nicht nur anhand von Abstracts oder einer erfolglosen Schlagwortsuche erfolgt.

## P2-04 — Gegenüber welcher Ausgangsbasis ist die Aufmerksamkeit stabiler?

**Fundstellen:** `manuskript.tex:55,82,114`; `analysis/workspace/bestaetigung/kennzahlen.csv`.

Der Vergleich B gegen E belegt geringeren Wechsel innerhalb der Workspace-Architektur. Er belegt keine Stabilisierung gegenüber dem unveränderten modernen PSI-Agenten. Für die **gleichen Seeds 1001–1020**, für die A ein Workspace-Log besitzt, ergeben sich folgende lebensweise gemittelten Zielwechsel pro 100 Zyklen:

| Bedingung | W2b, Seeds 1001–1020 |
|---|---:|
| A: kein Workspace | 0,583 |
| B: allgemeiner Schwellenbonus | 3,670 |
| E: Workspace ohne Bonus | 8,079 |

Damit ist B gegenüber A deskriptiv wechselhafter, obwohl B gegenüber E stabiler ist. Die A-Werte liegen nur für 20 Seeds vor; sie dürfen nicht unmarkiert wie 100 vollständige W-Beobachtungen behandelt werden. Für B und E über alle 100 Seeds sind die berichteten 3,736 bzw. 8,517 korrekt.

**Auftrag:** Dieses Muster in die Ergebnisdarstellung und Diskussion aufnehmen. Präzise zwischen Einführung eines Workspace und zusätzlichem Amtsinhaberbonus unterscheiden. Wenn eine ursprüngliche Motivation lautet, PSI vor thematischem Vagabundieren zu schützen, muss der schon sehr stabile Agent ohne Erweiterung als Bezugspunkt sichtbar sein. W2b bezeichnet eine Listenposition, nicht automatisch eine ausgeführte oder psychologisch neue Absicht.

**Erledigt, wenn:** „Stabilisierung“ jedes Mal einen klaren Vergleichsarm hat und keine allgemeine Verbesserung gegenüber PSI suggeriert.

## P2-05 — Die Prospektivität ist teilweise dokumentiert, aber nicht mit „vor jeder Datenerhebung“ gleichzusetzen

**Fundstellen:** `manuskript.tex:18,26,57`; `docs/analyseplan-workspace.md` samt Nachträgen; Commit-Historie dieser Datei.

Die datierten Git-Commits sind hilfreich: Ausgangsplan `68bd418` (11.11., 09:12 UTC), H1-Änderung `b82aca9` (09:31), D-Kalibrierung `4cb532d` (10:00), Bewertungs-/W1-Korrektur `c0194b6` (10:12). Die spätere Zustimmung zu Nachtrag 1 wurde in `5051a79` am 12.11. dokumentiert. Bereits vor H1-Änderung gab es aber eine Funktionsprobe in allen Bedingungen; vor Nachtrag 3 gab es drei fertige B-Leben. Der Nachtrag änderte neben Kandidatenscores auch die Definition der Aufenthalte bei wechselnder Inhaltsart.

Das Manuskript legt einen Teil davon offen, doch „report them in full“ trifft nicht zu: Die Änderung der W1-Artenzuordnung fehlt. Auch „before collecting data“ ist pauschal falsch. Zudem werden die 20 Screeningseeds in den abschließenden 100 wiederverwendet. Das war im Plan vorgesehen und macht die Analyse nicht automatisch ungültig; sie ist aber keine unabhängige Replikation auf 100 neuen Seeds. Ob Zwischenbefunde Entscheidungen beeinflussten, muss aus der Chronologie nachvollziehbar sein.

**Auftrag:** Tabelle mit Commit, Änderung, bis dahin erzeugten/angesehenen Daten, verworfenen Daten und Beginn der später ausgewerteten Läufe. Begriff „repository-timestamped analysis plan“ prüfen, statt eine öffentliche Registrierung mit zusätzlicher Unveränderlichkeit zu suggerieren. Alle Nachträge vollständig im Supplement verlinken. Archivierten Stand `c0194b6` für die Studie fixieren.

**Bereits im Review nachgerechnet:** Eine zusätzliche Auswertung nur der Seeds 1021–1100 ergibt mit derselben implementierten Statistik weiterhin H1, H4, H6 in vorhergesagter Richtung signifikant; H2, H3, H5 bleiben nicht signifikant. H1: Δ = −4,874, 95-%-KI [−5,361; −4,389]; H4: Δ = 20,424, KI [18,520; 22,539]; H6: Δ = 0,37394, KI [0,35861; 0,38981]; jeweils Holm-p = 0,000600. H3: Δρ = 0,00945, KI [−0,02499; 0,04495], Holm-p = 0,595. Diese nachträgliche Robustheitsanalyse stärkt die begrenzte Aussage, ersetzt aber keine rückwirkende Präregistrierung. Die Seeds sind gegenüber der Vorauswahl getrennt; aus diesem Review folgt nicht, dass sie zuvor nie von den Autoren angesehen wurden.

**Erledigt, wenn:** Plan, Datenzugriff und Amendments transparent sind. Die Originalanalyse bleibt erhalten; zusätzliche Auswertungen werden als solche bezeichnet.

## P2-06 — Verweildauer ist rechtszensiert und von der Lebenslänge abhängig

**Fundstellen:** `src/psi_gw/analysis/workspace_metrics.py:34–54,88–109`; `manuskript.tex:53,82`; Analyseplan W1/W5 und Nachtrag 3.

`spells()` übernimmt bei Lebensende noch laufende Aufenthalte mit ihrer bisher erreichten Länge und ohne Zensierungskennzeichen in den Mittelwert. Für die vorab festgelegte beobachtete Aufenthaltslänge ist das nachvollziehbar; als Schätzer einer vollständig beobachteten Verweildauer ist es verzerrt. Das betrifft besonders lange stabile Inhalte in B und D. Gleichzeitig schwankt die Zahl der Zyklen erheblich: A 777–1089, B 428–2618, C 369–1256, D 696–2416, E 594–1376. Alle Leben enden beim gleichen Alter, nicht nach gleicher Anzahl von Auswahlgelegenheiten.

W5 korreliert diese teilweise zensierten Dauern mit Arousal beim Eintritt. Späte Eintritte können allein wegen des verbleibenden Beobachtungsfensters kürzer erscheinen. Ein Inhaltsneuron kann außerdem während seines Aufenthalts die Art wechseln; der gesamte Aufenthalt wird der Art beim Eintritt zugeordnet. „Der Effekt erstreckt sich auf jede Inhaltsart“ bedeutet daher nicht notwendig, dass Ziele, Erinnerungen und Pläne jeweils über ihren ganzen gemessenen Aufenthalt dieselbe Funktion hatten.

**Auftrag:** Primären Endpunkt exakt als mittlere beobachtete Spell-Länge definieren; Zahl und Anteil terminaler Aufenthalte pro Arm berichten. Sensitivitäten mit gemeinsamem Zyklusfenster und zensierungsbewusster Darstellung prüfen. Das bloße Entfernen unvollständiger Aufenthalte wäre ebenfalls selektiv und reicht nicht als einzige Lösung. Die H3-Sensitivität muss zusätzlich Eintrittszeit/Laufphase berücksichtigen. Artenwechsel und lebensweise statt gepoolter Gewichtung erklären.

**Erledigt, wenn:** Die ursprüngliche Kennzahl reproduzierbar bleibt, ihre Messgrenzen sichtbar werden und die Schlussfolgerung nicht von einer unbeachteten Zensierungsentscheidung abhängt.

## P2-07 — Der H3-Nullbefund identifiziert keinen fehlenden Arousal-Mechanismus

**Fundstellen:** `manuskript.tex:45,49,98,114–118`; Workspace-/Motivationscode.

Arousal beeinflusst gleichzeitig den Bonus in B, den Auflösungsgrad und damit die Kapazität sowie weitere PSI-Prozesse. In D und E ändert sich zusätzlich die Motivwechselregel. Arousal selbst ist ein endogener Zustand des interagierenden Agenten. Die Korrelation von Arousal beim Eintritt mit der späteren Aufenthaltsdauer ist deshalb kein isolierter Test des kausalen Bonuspfads. Auch 0,064642 ist das zyklusgewichtete Mittel aus 20 A-Läufen, nicht zwangsläufig der tatsächlich erreichte mittlere Bonus in B.

Die Erklärung „auf der Insel variiert die Schwelle zu wenig“ ist plausibel, aber nach dem Nullbefund nicht bereits bewiesen. Die Diskussion menschlicher Affektbefunde begründet auch keinen Austausch von Arousal gegen Valenz in diesem Modell: unterschiedliche Aufgaben, Ebenen und Operationalisierungen müssen sichtbar bleiben.

**Auftrag für dieses Paper:** H3 als genau den geplanten Unterschied lebensweiser Korrelationen beschreiben; Mittel, Streuung und Verteilung der realisierten Boni, Kapazitäten und Eintrittszustände je Arm berichten. „Kein nachgewiesener zusätzlicher Effekt unter dieser Parametrisierung“ statt „Arousal spielt keine Rolle“. Das Nichtbestehen des kombinierten Erfolgskriteriums ist eine Entscheidungsregel dieses Experiments, keine Widerlegung der gesamten PSI- oder GWT-Theorie.

**Optionaler neuer Test:** Bonus-Arousal, Kapazitäts-Arousal und Motivregel in einem gekreuzten Design getrennt manipulieren, ggf. mit festgehaltenen oder zeitlich verschobenen Arousal-Reihen und geeigneten Positivkontrollen. Dies braucht einen neuen Plan; es darf nicht still in die abgeschlossene Bestätigung eingebaut werden.

## P2-08 — Die Verhaltenskennzahlen erfassen ihre theoretischen Konstrukte nur indirekt

**Fundstellen:** `src/psi_gw/regulation/ladder.py:929–970`; `src/psi_gw/action.py:82–95`; `src/psi_gw/analysis/workspace_metrics.py:102–106`; `manuskript.tex:53,55,107,120`.

W3 zählt Pläne, deren Ausführung nicht erfolgreich endet, einschließlich nicht erwarteter Situationen. Das ist zunächst ein Ausführungsfehlschlag, nicht spezifisch ein Abbruch durch eine konkurrierende Absicht. Pläne werden innerhalb einer Regulationsroutine ausgeführt; ein zusätzlicher stabiler Speicher schützt sie deshalb nicht notwendigerweise vor einer mehrzyklischen Ablenkung, wie es die Theoriegeschichte nahelegt. Pro 100 Zyklen ist zudem nicht dasselbe wie der Anteil gescheiterter ausgeführter Pläne: weniger Planversuche können die Rate senken, ohne einen Plan besser zu schützen.

W4 zählt jede negative Bedürfniswirkung für ein nicht aktuelles Motiv. Das kann ein Nebeneffekt einer ohnehin verfolgten Handlung sein und muss keine bewusst ergriffene Gelegenheit darstellen. Auch hier verändern Handlungszahl, Planhäufigkeit und Laufdauer die Zahl der Gelegenheiten.

**Auftrag:** W3 als fehlgeschlagene Planausführungen definieren, Ursachen und Zahl ausgeführter Pläne berichten; ergänzend Fehlschläge pro Plan prüfen. Für W4 Anzahl relevanter Handlungen und Mehrfachbefriedigungen erklären. Das Rohlog B/Seed 1001 enthält beispielsweise 80 ausgeführte und 36 fehlgeschlagene Pläne — der zusätzliche Nenner ist bereits vorhanden. Wenn tatsächlich keine Konkurrenz innerhalb laufender Pläne möglich ist, die Aussage über Intentionsschutz entsprechend zurücknehmen. Eine gezielte Ablenkungskontrolle wäre ein neues Experiment.

**Erledigt, wenn:** Die Resultate über die tatsächlich gezählten Ereignisse sprechen und nicht als direkter Nachweis einer Trennung von Aufmerksamkeit und Volition verkauft werden.

## P2-09 — H6 bestätigt die implementierte Historienabhängigkeit, nicht unabhängig die Theorie

**Fundstellen:** `src/psi_gw/workspace/__init__.py:237–251,255–268`; `manuskript.tex:37,55,82,112,125`.

H6 vergleicht den ausgewählten Satz mit den bonusfreien Top-K−1 **derselben aktuellen Kandidatenliste**. Diese Kandidaten und ihre Scores können bereits von früheren Broadcasts geprägt sein. Das ist eine sinnvolle lokale Manipulationsprüfung des direkten Bonusbeitrags. Es ist kein Vergleich zweier vollständiger Welthistorien bei identischem gegenwärtigem Gesamtzustand und kein unabhängiger Beleg für mehrere Attraktoren des gesamten Agenten. In E ist die Abweichung bei der deterministischen Namensregel exakt null, nicht nur ungefähr null.

**Auftrag:** Die bisher bereits richtige Bezeichnung als Manipulationsprüfung überall beibehalten. Hysterese formal am Selektor zeigen: Bei einem freien Platz, zwei Kandidaten mit Scores x und 0 und Bonus b>0 gewinnt der erste beim Anstieg aus einem Zustand mit zweitem Amtsinhaber erst für x>b; aus seinem eigenen Amtsinhaberzustand verliert er beim Abstieg erst für x<−b, vorbehaltlich der Gleichstandsregel. Das belegt einen Hysteresebereich des Auswahloperators. Ein kontrollierter Auf-/Abwärtssweep mit identischen Scores und verschiedenen Anfangsinhalten kann die Herleitung illustrieren.

**Erledigt, wenn:** Der Text lokale Historienabhängigkeit, analytische Hysterese des Selektors und eventuelle Multistabilität des geschlossenen Agenten sauber unterscheidet. H6 darf nicht als zusätzlich unabhängige Stütze eines psychologischen Mechanismus gezählt werden.

## P2-10 — Namensordnung und Score-Skalierung sind mögliche Determinanten des Effekts

**Fundstellen:** `manuskript.tex:45,125`; `src/psi_gw/workspace/__init__.py:122–207,263–268`; ADR 0018.

Alle Kandidaten konkurrieren mit Zahlen aus unterschiedlichen Regeln: Bedürfnis-/Zielwerte, Neuigkeit und Aversionen. Ein additiver Bonus von ungefähr 0,065 hat nur relativ zu diesen Skalen Bedeutung. Gleiche Nukleo-Zielwerte machen die lexikografische Ordnung besonders wirksam. Auch die Namen entstehen im lernenden Netz und sind keine neutrale fachliche Eigenschaft der Ziele. Die Einschränkung ist bereits genannt, ihre tatsächliche Größenordnung aber nicht quantifiziert.

**Auftrag:** Pro Inhaltsart Score-Verteilungen, Zahl konkurrierender Kandidaten, freie Plätze, Gleichstände an der Kapazitätsgrenze und Abstand zwischen letztem Gewinner und erstem Verlierer berichten. Umbenennung bei gleichen Scores als Invarianzprüfung und die bereits beschlossene Zufalls-Gleichstandsregel als getrennte Sensitivität prüfen. Bonusgrößen relativ zu typischen Score-Abständen darstellen; ein kleiner Bonus-Sweep wäre informativer als eine einzelne willkürliche Zahl.

**Erledigt, wenn:** Der Befund ausdrücklich für die untersuchte Skalierung und Namensregel gilt. Die vorhandenen Läufe müssen unverändert reproduzierbar bleiben. ADR 0018 nicht still zum Standard der alten Studie machen; neue Läufe mit eigener Workspace-Zufallsquelle und dokumentierter Konfiguration ausweisen.

## P2-11 — Statistik und Datenverfügbarkeit brauchen vollständige Spezifikation

**Fundstellen:** `src/psi_gw/analysis/metrics.py:48–115`; `scripts/workspace_analysis.py:52–69,119–144`; `manuskript.tex:55,65,134`.

Die sechs Tests einschließlich Mittelwertdifferenzen, Bootstrapgrenzen, p-Werten und Holm-Korrektur wurden in diesem Review aus `kennzahlen.csv` mit `paired_comparison` exakt reproduziert: maximale numerische Abweichung jeweils 0. Auch die deskriptive alte H1 ist so reproduzierbar. Das bestätigt die Konsistenz von Tabelle und implementierter Auswertung, nicht automatisch die Messvalidität oder alle Testannahmen.

**Aufträge:**

1. Analyseeinheit ist der Seed; die Schätzgröße ist der Mittelwert lebensweiser Kennzahlendifferenzen. Keine Zyklen oder Aufenthalte als unabhängige Stichproben behandeln. Endogene Laufdauern und unterschiedliche Spell-Zahlen bleiben als Gewichtungsentscheidung zu begründen.
2. Anzahl Bootstrapziehungen (10.000), Perzentilmethode und Zufallsseed (Standard 0) nennen. Die 95-%-Intervalle sind punktweise; Holm korrigiert die sechs p-Werte, nicht diese Intervalle. Das gilt auch für Paper 1.
3. Der Sign-Flip-Test ist nicht für jede beliebige Verteilung von gepaarten Differenzen allein aufgrund der Paarbildung exakt. Die verwendete Symmetrie-/Austauschbarkeitsannahme begründen und bei stark schiefen Differenzen eine robuste Sensitivität zeigen. Keine pauschale Verwerfung des aktuellen Tests, aber auch keine unbegründete Exaktheitsbehauptung.
4. Bei Artenspezifität und Spearman-Korrelationen Zahl gültiger Leben und Ausschlussregeln berichten. Der Code verwirft NaN-Paare. Aktuell liegen für H1–H6 jeweils 100 gültige Paare vor; das sollte sichtbar sein. Eine tatsächliche JSON-Schnittstelle sollte fehlende Werte nicht als nicht standardkonformes `NaN` exportieren.
5. Die P-Vergleiche sind sekundär/deskriptiv, mit Holm innerhalb von jeweils sechs Maßen je Bedingung, nicht über alle 24 Vergleiche. Diese Familienentscheidung offen benennen und nicht als vollständige kontrollierte Suche nach Verhaltenseffekten ausgeben.
6. „All 500 logged lives“ in Availability ist zu pauschal. Im archivierten Workspace-Verzeichnis liegen **420 Workspace-Logs: A 20, B–E je 100**. Für die restlichen 80 A-Leben werden P-Kennzahlen aus der modernen Grundlinie übernommen. 500 Kennzahlensätze sind nicht 500 vollständige Workspace-Protokolle. Das Manuskript muss die tatsächlichen Dateien unterscheiden.
7. Laufcode `c0194b6`, Analyse-/Artefaktcode, Parameter, Seeds, fixe Bonuszahl 0,064642, Originalnamen-Gleichstandsregel und Hashes der notwendigen Eingabedaten festhalten. Der Verweis auf Paper 1 ersetzt die benötigten Angaben nicht; dessen Reproduktionsabhängigkeit von `reference/` betrifft auch dieses Paper.

**Erledigt, wenn:** Eine neue Person die sechs Tests und alle Abbildungen vom dokumentierten Datenstand erzeugen kann und die unterschiedlich großen Informationsmengen je Arm korrekt erkennt.

## P2-12 — Abbildungen und Schlussfolgerungen schärfen

- **Abbildung 1/A2:** Zahl gültiger Leben und Zahl der Aufenthalte je Art ergänzen; Art beim Eintritt und Zensierung erklären. Längere Aufenthalte sind keine unabhängige Bestätigung über fünf Arten, wenn dieselben Neuronen zwischen Arten wechseln.
- **Abbildung 2/A4:** Seed 1001 war im Analyseplan als Beispiel festgelegt; das ist positiv. Die Zeilen zwischen B und E repräsentieren jedoch nicht automatisch dieselben Inhalte. Identitäten/Sortierregel und K ergänzen; die Grafik als Illustration dieses Beispiels, nicht als repräsentativen Effektbeweis behandeln. Im PDF auf Seite 6 ist die qualitative Stabilität sichtbar, die semantische Identität der langen Zielstreifen bleibt unklar.
- **Abbildung 3/A3:** Die gepoolte Punkt-/Dichteansicht gewichtet Leben mit vielen Aufenthalten stärker. Sie ist deskriptiv und testet nicht das lebensweise W5-Modell. Anzahl Leben, Aufenthalte, Achsenskalen, Zensierung und ggf. Dichte-Normalisierung angeben.
- **Haupttabelle:** Einheiten von W1 (Zyklen), W6 (Anteil, alternativ Prozentpunkte) und W5 (Korrelation) explizit aufnehmen. Tabellenquellen automatisieren; die Hypothesentabelle ist derzeit im Manuskript manuell gesetzt, obwohl `T1.tex` generiert wird.
- **Theoretischer Schluss:** Die Nullbefunde rechtfertigen kein allgemeines Argument, dass Stabilität von Aufmerksamkeit und Verhalten funktional separierbar seien. Dazu fehlen ein ausreichend wirksamer Broadcast und sensitive Aufgaben-/Messkontrollen. Als Hypothese für weitere Arbeit ist diese Deutung zulässig.
- **Sprache:** „A bonus ... must reduce turnover“ ist für einen rückgekoppelten Agenten nicht allgemein bewiesen; Feedback kann Kandidaten, Scores und Verhalten verändern. Als unmittelbare Selektortendenz formulieren. „No measurable consequences“ durch die konkret beobachteten Schätzungen und Unsicherheiten ersetzen.

## Konkreter Überarbeitungsablauf für Claude

1. P2-01 und P2-02 zuerst lösen: engerer Titel, korrekte Nullbefundsprache, vollständige Modellbeschreibung und begrenzte GWT-Zuordnung.
2. Vorarbeiten nach P2-03 lesen und die Neuheitsbehauptung neu formulieren. Den Bezug auf Bachs vorhandenen Workspace ausdrücklich prüfen.
3. Protokollchronologie, A-Vergleich und die oben nachgerechnete 80-Seed-Sensitivität transparent ergänzen. Keine nachträgliche Analyse als präregistriert etikettieren.
4. Mit vorhandenen Logs zunächst Zensierung, Artenwechsel, Exposition, Gleichstandshäufigkeit und Score-Margen untersuchen; W3/W4 codegenau definieren. Prüfen, welche Interpretationen danach noch tragfähig sind.
5. Nur für danach bewusst beibehaltene stärkere Aussagen neue Experimente planen: isolierter Arousal-Pfad, zufällige Gleichstände, Bonusgrößen, Verhalten unter echten Ablenkungen. Bestehende Studie und neue Untersuchung getrennt halten.
6. Antwortdatei mit Review-ID, Änderung, Beleg und verbleibender Grenze erstellen. Paper 1 und Paper 2 müssen die Portierungstreue und Datenverfügbarkeit konsistent beschreiben. Wissenschaftlicher Gewinn entsteht hier durch bessere Identifikation und begrenzte Aussagen, nicht durch nachträgliches Erreichen signifikanter Ergebnisse.

## Prüfprotokoll und externe Belege

Die Haupttests wurden tatsächlich aus der archivierten Kennzahlentabelle erneut berechnet; die zusätzlichen 80-Seed- und 20-Seed-Vergleiche oben sind ausgeführte Sekundärauswertungen dieser Sitzung. Es wurden keine 500 Simulationsleben neu gerechnet. Die genannten Architektur- und Messprobleme stammen aus dem gelesenen Code; sie sind keine behaupteten Ergebnisse neuer Interventionen.

Eine vollständige neue Bestätigung der Golden-Master-Suite war in der unvollständig materialisierten Prüfkopie nicht möglich: `pytest` ergab 147 bestandene Tests, 40 Fehlschläge, drei Setupfehler und zwei übersprungene Tests. Fehlende historische/Welt-/Trace-Dateien sowie ein nicht bytegetreu übertragener Textfixture begrenzen diesen Lauf. Daraus wird kein neuer Codefehler abgeleitet; eine vollständig grüne Suite wurde in diesem Review nicht behauptet. Es wurden ausschließlich Reviewdokumente und die Übergabe geändert.

Gezielt geprüfte Quellen, keine vollständige neue Literaturübersicht:

- [Dossa et al. (2024), DOI 10.3389/fncom.2024.1352685](https://www.frontiersin.org/journals/computational-neuroscience/articles/10.3389/fncom.2024.1352685/full), Abschnitt 2.4 und Abbildung 1C: Der frühere Workspace-Zustand geht in Aufmerksamkeit und rekurrente Aktualisierung ein. Daraus folgt die notwendige engere Abgrenzung, nicht die Gleichheit mit einem additiven Bonus.
- [Butlin et al., arXiv:2308.08708, Version 3](https://arxiv.org/html/2308.08708v3), GWT-Indikatoren und deren Erläuterung: globale Verfügbarkeit und zustandsabhängige sequenzielle Modulabfrage sind weitergehende Anforderungen als eine variable Listenkapazität. Für die endgültige Zitierung die tatsächlich benutzte Fassung festlegen.
- [Lakens (2017), DOI 10.1177/1948550617697177](https://doi.org/10.1177/1948550617697177): methodische Unterscheidung von Nichtsignifikanz und Evidenz für praktische Äquivalenz.
- Bach (2009), *Principles of Synthetic Intelligence*: gezielter noch offener Primärquellenauftrag aus ADR 0016, insbesondere die dort genannten Abschnitte 4.6.2/6.2.3 und Abbildung 8.2. Nicht als in dieser Sitzung verifiziert ausgeben.
