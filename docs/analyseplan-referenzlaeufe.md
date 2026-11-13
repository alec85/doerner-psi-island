# Analyseplan: Referenzläufe des Originals und Vergleich mit der Neuimplementierung

- Status: Entwurf, Fassung 4 vom 2026-11-10 (Issue #7) mit Nachträgen 1 bis 3 (Issue #28); Änderungen gegenüber früheren Fassungen am Ende
- Grundlage: ADR 0005 (zweistufiger Abgleich), ADR 0006 (Formate), ADR 0008 (exakte Ganzlauf-Vergleiche)
- Regel: Dieser Plan wird committet, bevor bestätigende Läufe ausgewertet werden. Änderungen nach Beginn der bestätigenden Läufe werden als datierte Nachträge am Ende festgehalten und begründet; sie gelten nur für danach erhobene Daten.

## Zweck

Der Plan legt fest, wie das Verhalten des Delphi-Originals auf der Insel quantitativ beschrieben wird und wie die Python-Implementierung dagegen geprüft wird. Er dient zugleich als Methodenteil für Paper 1 (Reproduktion von PSI und Erweiterung um einen Global Workspace).

## Was vorab bekannt ist

Diese Befunde stammen aus Vorläufen und gehen nicht in die bestätigende Auswertung ein:

1. Unter Wine sind Läufe mit gleichem Seed bit-identisch (`docs/delphi-build.md`); der Messlauf aus Punkt 3 stimmt in den Zyklen 1 bis 71 mit den beiden Referenzläufen überein. Wiederholungen eines Seeds liefern keine Information; jede Variabilität entsteht über verschiedene Seeds.
2. Ein kurzer Lauf ist exakt der Anfang eines längeren Laufs mit gleichem Seed. `MaxLife` beeinflusst das Verhalten demnach nicht, es schneidet den Lauf nur ab. Kennzahlen für kürzere Horizonte lassen sich deshalb aus längeren Läufen ableiten.
3. Messlauf vom 2026-11-10 (Seed 16, `MaxLife` 1.000.000, `traces/original-runs/2026-11-10-messlauf/`): 316 Zyklen in 7,5 Minuten. Die Wanduhrzeit pro Zyklus bleibt über den ganzen Lauf ungefähr gleich (Mittel 1,27 s, in Blöcken von 40 Zyklen zwischen 0,97 und 1,85 s), dazu kommen gut 20 s für die Abschlussprotokolle. Das Alter pro Zyklus steigt dagegen von etwa 1.250 auf etwa 6.100 Einheiten. Ein Teil davon ist Denkzeit: Die Zeit der Rasmussen-Stufen, die das Original in Alterseinheiten verbucht, steigt von etwa 250 auf etwa 2.800 Einheiten pro Zyklus, ihr Anteil am Alterszuwachs von 20 % auf 46 %. Der Rest wächst ebenfalls; woran das liegt, ist ungeklärt.
4. Im Messlauf gab es drei Exitus, in den Zyklen 150, 220 und 304. Die Bedürfnisstärke für Schaden erreicht wiederholt 100 %.
5. Volles Leben vom 2026-11-10 (Seed 16, `MaxLife` 5.000.000, `traces/original-runs/2026-11-10-volles-leben/`): 739 Zyklen, acht Exitus, rund 19 Minuten ohne Stillstand. Die Wanduhrzeit pro Zyklus steigt von 1,2 bis 1,5 s in den ersten 400 Zyklen auf etwa 2 s in den letzten 100. Das Alter pro Zyklus steigt bis auf über 30.000 Einheiten, gegen Lebensende zu etwa 80 % Denkzeit. Die Zyklen 1 bis 315 sind identisch mit dem Messlauf.
6. Im vollen Leben blockierte in Zyklus 571 ein Fehlerdialog des Originals den Lauf, bis er bestätigt wurde (Wettlaufsituation in `UPsiServer.pas`). Der Runner bestätigt solche Dialoge inzwischen automatisch und protokolliert sie. Eine Wiederholung zeigte: Der Dialog tritt wieder in Zyklus 571 auf, und der Lauf bleibt in allen 739 Zyklen identisch, unabhängig davon, wie lange der Dialog stand. Läufe mit Dialog taugen damit für den exakten Vergleich nach ADR 0008.
7. Läufe des Originals müssen nacheinander laufen, solange sie sich einen Rechner teilen (Port 2000).

## Stufe A: Pilotphase

**Ziel.** Zahl der Seeds und Äquivalenzgrenzen für Stufe B festlegen und die Streuung der Kennzahlen schätzen. Die Lauflänge ist entschieden (siehe unten).

**Läufe.** Seeds 901 bis 905, je ein Lauf mit `MaxLife` 5.000.000, also der Lebensdauer aus Dörners eigenen Parameterdateien in `Execute/`. Gemessen mit Seed 16: 739 Zyklen, rund 19 Minuten. Andere Seeds können abweichen; die Pilotläufe liefern die Streuung.

**Auszuwerten.**

- Dauer pro Zyklus (Wanduhr) und Alterseinheiten pro Zyklus,
- Zyklus des ersten Exitus und Zahl der Exitus pro 1.000 Zyklen,
- Zahl der Zyklen pro Leben und ihre Streuung über Seeds,
- Verlauf der Kennzahlen aus Stufe B über das Leben (gleitende Mittel über 100 Zyklen), beschreibend,
- Standardabweichungen der primären Kennzahlen über die fünf Seeds als grobe Grundlage der Fallzahlplanung.

**Lauflänge (entschieden von Alec, 2026-11-10).** Analyseeinheit ist ein volles Leben nach Dörner: `MaxLife` 5.000.000, ausgewertet werden alle Zyklen dieses Lebens. Begründung: Das ist die Versuchseinheit der Parameterdateien des Originals, und ein Leben umfasst mit rund 740 Zyklen (Seed 16) genug Exitus für die Kennzahlen. Die Entscheidungsregel über `L` aus Fassung 1 bis 3 entfällt. Weil die Zahl der Zyklen je Seed schwanken kann, sind die Ratenkennzahlen pro Zyklus normiert.

**Ergebnis.** Ein Nachtrag zu diesem Plan mit `N` und den Äquivalenzgrenzen, committet vor Beginn von Stufe B.

## Stufe B: Bestätigende Referenzläufe des Originals

**Läufe.** Seeds 1001 bis 1000 + `N`, je ein volles Leben mit `MaxLife` 5.000.000. Ausgewertet werden alle Zyklen des Lebens. Seed 16 und die Pilot-Seeds sind ausgeschlossen.

**Fallzahl.** Vorgabe `N` = 100. Begründung: Für einen Äquivalenztest zweier unabhängiger Stichproben (TOST, α = 0,05, Power 0,80, wahre Differenz 0) bei einer Äquivalenzgrenze von ±0,4 Standardabweichungen braucht es nach der Normalapproximation etwa 108 Läufe pro Gruppe, bei ±0,5 etwa 69. Weil Original und Neuimplementierung mit denselben Seeds laufen, ist der gepaarte Test anwendbar und in der Regel deutlich stärker; die Vorgabe ist also konservativ. Liefert die Pilotphase Hinweise auf sehr große Streuungen, wird `N` im Nachtrag erhöht, nicht gesenkt.

## Kennzahlen

Alle Kennzahlen werden je Lauf aus den Trace-Dateien (ADR 0006) über alle Zyklen des Lebens berechnet.

### Primär (bestätigend)

| Kürzel | Kennzahl | Quelle |
|---|---|---|
| P1 | Exitus pro 1.000 Zyklen | `cycle.counters.exitus` |
| P2 | Gesammelte Nukleotide pro 100 Zyklen | `cycle.counters.nucleotides_collected` (abzüglich Startwert 5) |
| P3 | Entdeckte Orte am Ende | `cycle.counters.locations_discovered` |
| P4 | Erfolgsquote der Manipulationen | `successful_manipulations / (successful + unsuccessful)` |
| P5 | Anteil der Zyklen, in denen Versuch und Irrtum lief | `cycle.stage_times.what_could_be_done > 0` |
| P6 | Mittlere Bedürfnisstärke Schaden | Mittel von `cycle.need_pct.damage` |

Die Auswahl deckt Überleben (P1, P6), Zielerreichung (P2), Exploration (P3), Lernen über Objekte (P4) und die Handlungsorganisation (P5) ab.

### Sekundär (beschreibend)

- Verteilung der Rasmussen-Stufen: Anteile von LookAround, Automatismus, Planung, Versuch und Irrtum an der Zeit (`stage_times`),
- Zähler der internen Prozesse `TIntProc` (`summary.extra.inpro`),
- Verbrauch und Zugewinn je Motiv (`summary.extra.consum`),
- Verteilungen der drei Modulatoren und der sieben Bedürfnisse über alle Ereignisse,
- Häufigkeiten der Aktionen und Motivwechsel.

## Statistische Verfahren

### Beschreibung des Originals (Stufe B allein)

Für jede Kennzahl: Mittelwert, Standardabweichung, Median, Interquartilsabstand, 95-%-Konfidenzintervall des Mittelwerts per Bootstrap (10.000 Ziehungen über Seeds). Für P1 zusätzlich eine Kaplan-Meier-Kurve der Zeit bis zum ersten Exitus, mit Zensierung am Lebensende.

### Exakter Vergleich (ADR 0008)

Die Neuimplementierung läuft mit `DelphiRandom` und denselben Seeds. Je Seed wird der erste Zyklus bestimmt, in dem sich Ereignisse (Aktion, Status, Parameter, Situation, Objekt) oder Bedürfnis- und Modulatorwerte über die Toleranz aus ADR 0005 hinaus unterscheiden. Berichtet werden die Verteilung dieses Zyklus über alle Seeds und eine Kategorisierung der ersten Unterschiede (diskrete Entscheidung, numerische Abweichung, Zugreihenfolge des Zufalls).

### Äquivalenz des Gesamtverhaltens

Für jede primäre Kennzahl ein gepaarter Äquivalenztest (TOST) auf den Differenzen je Seed, mit symmetrischer Äquivalenzgrenze ±Δ. Δ wird im Nachtrag nach der Pilotphase als Bruchteil der Standardabweichung des Originals über Seeds festgelegt, Vorgabe 0,4. Multiples Testen über die sechs primären Kennzahlen wird nach Holm korrigiert. Äquivalenz gilt als gezeigt, wenn alle sechs Tests nach Korrektur signifikant sind.

Ergänzend je Kennzahl: Verteilungsvergleich mit dem Anderson-Darling-Test für zwei Stichproben und standardisierte Effektgröße mit 95-%-Konfidenzintervall. Ein nicht signifikanter Unterschiedstest gilt nicht als Beleg für Gleichheit.

Zusätzlich wird derselbe Vergleich mit `NumpySource` statt `DelphiRandom` durchgeführt. Er prüft, ob die Neuimplementierung auch unabhängig vom konkreten Zufallsgenerator dasselbe Verhalten zeigt; hier ist nur der ungepaarte Test sinnvoll.

### Auswertungsweg

Alle Auswertungen laufen per Skript aus den Trace-Dateien, ohne Handarbeit. Skripte, Ausgaben und Abbildungen werden unter `analysis/referenzlaeufe/` versioniert. Abweichungen vom Plan werden im Bericht benannt.

## Rechenaufwand und Ausführungsort

Die Laufzeit wächst vor allem mit der Zahl der Zyklen. Ein volles Leben nach Dörner dauerte im Arbeitsbereich rund 19 Minuten; fünf Pilotläufe sind damit gut anderthalb Stunden, 100 bestätigende Läufe über volle Leben rund 32 Stunden. Wie schnell die Rechner von GitHub Actions sind, ist nicht gemessen; der erste Testlauf dort liefert die Zahl. Im Agenten-Arbeitsbereich laufen Programme nur während einer aktiven Antwort weiter; lange Serien sind dort unpraktisch. Vorgesehen ist deshalb ein GitHub-Actions-Workflow, der `scripts/setup_wine.sh` und `scripts/run_original.py` in einer Matrix über Seeds ausführt (jede Matrix-Instanz ist ein eigener Rechner, der Port-Konflikt entfällt) und die Trace-Dateien als Artefakte ablegt. Kontingent und Kosten der Actions-Minuten für das private Repository sind vorher zu prüfen; bei Bedarf wird `N` im Nachtrag begründet angepasst, oder die Läufe werden auf mehrere Monate verteilt.

## Änderungen gegenüber früheren Fassungen

**Fassung 4.** Lauflänge nach Entscheidung von Alec auf ein volles Leben nach Dörner festgelegt (`MaxLife` 5.000.000, alle Zyklen); die Entscheidungsregel über `L` und der offene Punkt dazu entfallen.

**Fassung 3.** Ein volles Leben mit `MaxLife` 5.000.000 gemessen. Laufzeit der Pilotläufe und Rechenaufwand durch diese Messung ersetzt, offenen Punkt zur Lauflänge mit der gemessenen Zyklenzahl präzisiert, Fehlerdialoge des Originals als bekannte Eigenschaft aufgenommen und per Wiederholungslauf als deterministisch belegt.

**Fassung 2.**

Fassung 1 enthielt eine Laufzeit von 1,3 bis 1,7 Stunden pro Pilotlauf und rund 75 Stunden für die bestätigende Phase. Beides war aus 72 Zyklen hochgerechnet, unter der Annahme gleichbleibender Kosten pro Zyklus und gleichbleibenden Alters pro Zyklus. Der Messlauf hat die erste Annahme für die Wanduhrzeit bestätigt und die zweite widerlegt. Fassung 2 ersetzt die Zahlen durch Messwerte, kennzeichnet die verbleibende Hochrechnung und nennt den daraus folgenden offenen Punkt bei der Entscheidungsregel. Weder Pilot- noch bestätigende Läufe hatten begonnen.

## Nachträge

### Nachtrag 1 vom 2026-11-10: Läufe mit der Portierung statt mit dem Original

Geschrieben und committet, bevor Ergebnisse der Pilotphase eingesehen wurden. Bestätigende Läufe hatten nicht begonnen.

**Anlass.** Die Python-Portierung im Referenzmodus (ADR 0010) reproduziert das Original exakt. Mit Seed 16 stimmen über das volle Leben alle Zeilen des Aktivitätsprotokolls, alle Handlungen mit ihrem Alter, die ach-Datei, `IntTimes` und die Abschlussdateien überein. Mit Seed 901 gilt dasselbe bis auf eine Zeile des Aktivitätsprotokolls, deren Ursache bekannt ist und das weitere Verhalten nicht änderte (ADR 0014). Ein Leben dauert in der Portierung etwa 4 Minuten statt 18 bis 25, und Läufe können ohne Port-Konflikt parallel laufen.

**Änderungen.**

1. Pilotphase und Stufe B laufen mit der Portierung (`scripts/baseline.py`). Ausgewertet werden ihre Trace-Dateien mit demselben Konverter und demselben Auswerteskript wie Läufe des Originals (`psi_gw.analysis.metrics`).
2. Das Original läuft als Stichprobe. Aus den Seeds der Stufe B werden fünf vorab festgelegt (1001, 1021, 1041, 1061, 1081) und unter Wine gerechnet. Für sie wird der exakte Vergleich nach ADR 0008 berichtet: erster abweichender Zyklus und Art der Abweichung. Erwartet sind höchstens Abweichungen nach ADR 0014.
3. Der Äquivalenztest Original gegen Portierung (TOST über alle Seeds) entfällt. An seine Stelle tritt der exakte Vergleich der Stichprobe. Bleibt die Stichprobe bis auf Fälle nach ADR 0014 identisch, gelten die Kennzahlen der Portierung als Kennzahlen des Originals.
4. Der Vergleich mit `NumpySource` statt `DelphiRandom` bleibt als Robustheitsprüfung (ungepaart, TOST mit derselben Grenze Δ).
5. Hauptzweck von Stufe B ist damit die Beschreibung des Originalverhaltens über Seeds. Sie dient als Grundlinie für die Experimente mit Global Workspace (Phase 3) und für das Abschalten von Implementierungsartefakten des Originals (Issue #29).
6. Die Portierung schreibt kein Ereignisprotokoll (`Protokoll.Dat`). Sekundäre Kennzahlen, die darauf beruhen (Verteilungen der Modulatoren und Bedürfnisse über Ereignisse, Häufigkeiten der Aktionen), werden aus den Zyklus- und Handlungsdaten (`Activities.Txt`) berechnet oder entfallen.

`N` und Δ werden wie vorgesehen nach der Pilotphase in einem weiteren Nachtrag festgelegt.

### Nachtrag 2 vom 2026-11-10: Ergebnis der Pilotphase, `N` und Δ

Pilotläufe: Seeds 901 bis 905 mit der Portierung (Referenzmodus), je ein volles Leben. Ergebnisse unter `analysis/referenzlaeufe/pilot/` (`kennzahlen.csv`, `beschreibung.json`). Seed 901 wurde zusätzlich im Original gerechnet und ist bis auf eine Zeile nach ADR 0014 identisch.

| Kennzahl | Mittel | SD über 5 Seeds |
|---|---:|---:|
| Zyklen pro Leben | 879,6 | 130,7 |
| P1 Exitus pro 1.000 Zyklen | 11,65 | 1,61 |
| P2 Nukleotide pro 100 Zyklen | 14,22 | 1,42 |
| P3 entdeckte Orte | 92,8 | 14,2 |
| P4 Erfolgsquote Manipulationen | 0,370 | 0,028 |
| P5 Anteil Zyklen mit Versuch und Irrtum | 0,859 | 0,007 |
| P6 mittlere Bedürfnisstärke Schaden | 74,8 | 3,7 |

Die Variationskoeffizienten liegen zwischen 1 % (P5) und 15 % (Zyklen, P3). Nichts spricht für ungewöhnlich große Streuungen. Festlegungen:

- `N` = 100 (Seeds 1001 bis 1100), wie vorgegeben.
- Δ = 0,4 Standardabweichungen des Originals, wie vorgegeben, für den Robustheitsvergleich mit `NumpySource`.
- Für die Varianten nach ADR 0015 wird zuerst mit den Seeds 1001 bis 1020 gemessen (gepaart, Vorzeichen-Permutationstest). Zeigt ein Schalter dort keinen Effekt auf die primären Kennzahlen, wird er mit allen 100 Seeds bestätigt, bevor „kein Effekt“ berichtet wird; ein nicht signifikanter Test gilt nicht als Beleg für Gleichheit.
- Stichprobe des Originals: Seeds 1001, 1021, 1041, 1061, 1081 (Nachtrag 1).

### Nachtrag 3 vom 2026-11-11: Ergebnis der Stichprobe des Originals

Ergebnisse in `analysis/referenzlaeufe/stichprobe/`. Zusätzlich zu den fünf festgelegten Seeds wurden die Seeds 1035 und 1073 gerechnet, deren Leben in der Portierung an einem nil-Zugriff abbricht (Stufe B).

Alle Abweichungen gehen auf ADR 0014 zurück. Beide überprüfbaren Abbrüche (1035, 1061) treten im Original an derselben Stelle auf. Die Bedingung aus Nachtrag 1, Punkt 3, ist damit formal erfüllt. In vier von sieben Leben ändert die Heap-Ursache allerdings eine Entscheidung, danach verlaufen die Leben verschieden.

Folgerungen:

1. Die Beschreibung des Originals in Stufe B (`analysis/referenzlaeufe/stufe-b/`) wird als Beschreibung des Originals bis auf ADR 0014 berichtet, nicht als Seed-für-Seed-Wiedergabe.
2. Ob die systematische Abweichung (die Portierung liest `lN`/`lS` nie als Diagonale) die Verteilungen verschiebt, ist offen. Prüfbar wäre das mit mehr Läufen des Originals (TOST nach dem ursprünglichen Plan) oder mit einer Variante, die das Heapbyte als seltenes Zufallsereignis nachbildet. Beides ist nicht beschlossen.
3. Für die weiteren Experimente (Artefakte, Global Workspace) ist die Grundlinie ohnehin die Portierung selbst, gepaart nach Seed; dort spielt die Frage keine Rolle.
