# Ausgeführte Navigationstests vom 2026-11-13

Bewegungsprofil, aktive Raumabtastung und lokale Navigation sind implementiert.
**Die aktive v1 erreicht über zwei getrennte Prüfserien 22 von 24 Zielen im
Langhorizont. Das vollständige Robustheitsziel bleibt verfehlt.** Die zusätzlich
geprüfte bildgestützte Richtungskorrektur bringt keinen zuverlässigen Vorteil
und bleibt ein ausdrücklich experimenteller, nicht voreingestellter Controller.

Issue #49, Draft-PR #52, gestapelt auf #43. Kein Merge und kein Eingriff in Claudes
PSI-/Paper-Arbeit. MuJoCo-Modell und die alten Controller bleiben unverändert.
Alle Messungen beziehen sich auf das angenommene Modell, nicht auf echte Hardware.

## Prüfstand und Code

977 Tests bestanden, keine übersprungen, finaler Lauf 46,53 s: 917 vorhandene plus
60 neue Tests. Darunter Datenabgrenzung, empirische Profilgrenzen, kausale Zuordnung
verzögerter Captures, Duplikate/Reihenfolge, Bildgates, weiche lokale Hüllen,
Scanzustände, Snapshotvalidierung, tickweise Fortsetzung und frische Prozesse.
Die unveränderten alten Baselines werden im neuen Evaluator auf gleichen Body-,
Controller- und Zustellungszustand nach jedem verglichenen Tick geprüft.

- Erste unabhängige Prüfung: Freeze `31f6ecf7df481d3967db639b752a97c93202dbca`.
- Getrennter Kameraversuch: Freeze `cbba33d0d75444a2fec4e60826ba6ff05a042366`.
- Alle v1-Laufzeitdateien bleiben auch beim zweiten Versuch unverändert;
  dessen neue Module sind zusätzlich und getrennt. Quellfingerprints gespeichert.
- Kriterien: [NAVIGATION-VALIDATION.md](NAVIGATION-VALIDATION.md) und vor dem
  Folgeversuch [ADR-visual-heading.md](ADR-visual-heading.md).

## Bewegungswirkung

36 Entwicklungsfälle, 24 getrennte Profilprüffälle; unterschiedliche Reibung,
Gangphasen und Befehlsrichtungen/-größen. Alle 60 wurden nach Behebung einer
NumPy-Skalar-Berichtserialisierung vollständig erneut ausgeführt und sind exakt
gleich. Das Profil lässt sich aus den archivierten Entwicklungsdaten exakt refitten.

Die mittleren Gains liegen je Richtung zwischen 0,869 und 0,953; der effektive
Verzugsansatz beträgt 70,8 ms. Alle 24 Profilprüffälle liegen im empirischen Bereich,
größte relative Abweichung vom mittleren Gain 7,48 %, kein Sturz. Bereiche und
Stopwegrand sind technische Modellannahmen, keine statistischen Konfidenzintervalle.
Konstante Befehlswirkung reicht nicht zur sicheren Vorhersage aller intermittierenden
Stop-/Startfolgen. Das wird in den geschlossenen Fahrten ausdrücklich sichtbar.

## Erste unabhängige Matrix: 48 Fahrten

Neue Seeds 2000/2001 × offen/Slalom × nominal/verrauscht/verzögert × vier Varianten.
Entwicklung nur auf 10/11. Alle Varianten erhalten dasselbe Budget. Alte Prüfseeds
1000/1001 und deren 24 erfolglose 900er-Fahrten aus #43 bleiben unverändert.

| Variante | Fälle | Ziele ≤900 Entscheidungen | Ziele ≤2400 | Kontaktbudget-Abbruch | Stop bestanden |
|---|---:|---:|---:|---:|---:|
| Reaktiv, unverändert | 12 | 2 | 8 | 4 | 12 |
| Gedächtnis, unverändert | 12 | 4 | 8 | 4 | 12 |
| Gedächtnis, nur schneller | 12 | 6 | 8 | 4 | 12 |
| Aktive Navigation v1 | 12 | 6 | **10** | 2 | 12 |

Der Vergleich beurteilt die Gesamtsteuerung, nicht isoliert den Scanmechanismus.
Die schnelle Gedächtnisbaseline ändert ausschließlich den Vorwärtsbefehl von 0,025
auf 0,03 m/s. Der 900er-Vorteil darf deshalb nicht allein der aktiven Abtastung
zugeschrieben werden. **Ein Ziel nach 900 bleibt am alten Endpunkt ein Fehlschlag.**
Die Langhorizontwerte sind eine separate Diagnose, kein umetikettierter Erfolg
im früheren Zeitbudget. Alle sechs offenen aktiven Fälle erreichen das Ziel bis 900;
die vier erfolgreichen aktiven Slalomfälle benötigen zusätzliche Zeit.

Beide verrauschten aktiven Slalomfälle erreichen das Kontaktbudget. Die reine
Befehlsschätzung driftet dabei deutlich von der Modellpose ab. Das vollständige
vorab festgelegte Abnahmeziel von 12/12 Langhorizontzielen ist damit nicht erfüllt.
Es gab keine Stürze, Stromabschaltungen oder numerischen Fehler.

## Getrennter Kamera-Folgeversuch: 24 Fahrten

Aufgrund der bereits in Entwicklung sichtbaren Schätzdrift wurde ein separater
relativer RGB-Richtungsabgleich implementiert. Die v1 und ihre Ergebnisse wurden
nicht nachgestellt. Neue Prüfseeds 3000/3001, gleiche Familien/Sensorprofile,
eingefrorene aktive v1 gegen visuelle Variante.

| Variante | Fälle | Ziele ≤900 | Ziele ≤2400 | Kontaktbudget-Abbruch | Stop bestanden |
|---|---:|---:|---:|---:|---:|
| Eingefrorene aktive v1 | 12 | 6 | **12** | 0 | 12 |
| Mit relativer Bildkorrektur | 12 | 6 | **11** | 1 | 12 |

Der Kameraversuch ist **kein nachgewiesener Fortschritt**. Beim verrauschten Slalom
mit Seed 3001 erreicht die v1 das Ziel mit zehn Kontakt-Ticks; die visuelle Variante
bricht mit 25 Kontakt-Ticks ab. Beide Fälle wurden zusätzlich unter eingefrorenem
Code für echte Replays erneut ausgeführt; vollständiger Bericht, Body- und Tracehash
müssen mit der ursprünglichen Prüfung exakt übereinstimmen.

Über die sechs Slalomfälle sinkt die mittlere Positionsabweichung nach Stop zwar
von 0,177 auf 0,102 m, während die mittlere absolute Richtungsabweichung von 0,210
auf 0,238 rad steigt. Diese kleinen deskriptiven Zahlen begründen keine allgemeine
Überlegenheit. Der Endfehler enthält auch den letzten noch nicht beobachteten
Aktionsschritt und zwei Sekunden Ausrollen, keine reine Odometrie-Fehlermessung.
Die Endpunkte liegen zu unterschiedlichen Zeiten; der Kontaktabbruch ist enthalten.
Dieser einfache Spaltenabgleich trennt Translation, Teilverdeckung und Rotation
nicht verlässlich; die heuristischen Gates haben einen schädlichen Eingriff nicht
zuverlässig verhindert. Die genaue Ursache ist damit nicht abschließend identifiziert.

## Reproduzierbarkeit und Ausführung

72 unabhängige Prüffahrten, zusammen 85.822 Controllerentscheidungen. Alle 72
Stopprüfungen bestanden; größte zusätzliche Stopdrift 8,54 mm (Grenze 30 mm).
Auch Zielerfolge sind nicht automatisch kontaktfrei; Kontakte werden separat
aufgezeichnet. Fuß-Boden-Tragkontakte zählen nicht zum Fehlerbudget.

Sechs vollständige Slalomfortsetzungen aus Entscheidung 250 wurden jeweils in
einem frischen Python-Prozess bis zum Endzustand ausgeführt: drei v1- und drei
visuelle Fälle, je nominal/verrauscht/verzögert. 9.897 weitere Entscheidungen plus
je 40 Stop-Ticks; Endberichte, Body- und Verlaufshashes exakt gleich. Zusätzlich
prüfen Unit-Tests vollständige Zustände nach jedem weiteren Tick sowie Snapshots
nach abgeschlossenen Scans. Kein Anspruch auf plattformübergreifende Bitidentität.

14 gespeicherte HTMLs mit 969 tatsächlichen Frames wurden mit ihrem eigenen
JavaScript im bestehenden DOM/Canvas-Harness erfolgreich ausgeführt. Zwei Weggrafiken
wurden zusätzlich visuell geprüft. Die Weggrafiken zeigen
Beobachterwahrheit und Controller-Schätzung getrennt. Diese Auswertung ist keine
Browser-Sichtabnahme; die lokale Browserblockade bleibt bestehen.

## Ergebnis und verbleibende Arbeit

Der empfohlene Ausgangspunkt ist `ActiveNavigator`; `VisualNavigator` ist ein optionaler
negativer/teilweise hilfreicher Versuch, kein stillschweigender Ersatz. Über die
zwei unabhängigen Seedsätze erreicht die Standardvariante 22/24 Langhorizontziele
und 12/24 Ziele bis 900; dies sind beschreibende Ergebnisse in einem kleinen,
festen Modellparcours. Die erste verfehlte Abnahme bleibt verfehlt, auch wenn der
zweite Seedsatz günstiger ausfällt. Keine Behauptung allgemeiner Robustheit,
Hardwaretauglichkeit, statistischer Signifikanz oder erfolgreicher Navigation in
Sackgassen, dynamischen Toren und unbekannten Umgebungen.

Für den nächsten qualitativen Schritt muss Bewegungsrückmeldung bei Stop-/Start-
und Schlupfzuständen belastbarer werden: eine bessere Trennung von Bildtranslation
und Rotation prüfen und intermittierende Bewegungsregimes separat identifizieren.
Neue reale Bewegungs-/Lagesensoren wären eine eigene Hardware-/Schnittstellenentscheidung.
Hier wurden weder Sensoren erfunden noch der PSI-Kern eingebunden.

## Dateien

Unter [navigation-results-2026-11-13](navigation-results-2026-11-13/) stehen Profil,
komprimierte komplette Bewegungsmessung, Fit-/Wiederholungsprüfung, alle sieben
v1-Entwicklungsberichte und beide Kamera-Entwicklungsberichte, JUnit/Testlog,
beide unabhängigen Prüfserien, Checkpoints und Fortsetzungen, reale Replays und
Hashmanifest. Die Entwicklung enthält bewusst auch Timeouts und Kontaktfehler;
ihre Zwischenfingerprints können uncommittete Dateien bezeichnen. Die formalen
Prüfungen verwenden dagegen die oben genannten gesicherten Stände.

[Einstieg/Befehle](NAVIGATION.md), [eigene Übergabe](HANDOFF-navigation.md).
