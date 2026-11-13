# Vorab festgelegte Navigationsprüfung v1 (2026-11-13)

Issue #49, gestapelt auf #43. Dieses Dokument wird vor Zugriff auf Seeds 2000/2001
gepusht. MuJoCo-Modell, alte Controller und frühere Abnahmen bleiben unverändert.

## Bewegungsprofil

36 Entwicklungsfälle: Reibung 0,4/0,8/1,2 × Gangphase 0/0,5 × drei Achsen × beide
Vorzeichen. Startgierwinkel 0,2 bzw. −0,3 rad. Befehle Vor-/Rückwärts 0,03 m/s,
seitwärts 0,02 m/s, Drehung 0,3 rad/s. Zwei Sekunden Stand, sechs Bewegung, zwei Stop.
Je Richtung mittlerer stationärer Verstärkungsfaktor; Bereich aus Minimum/Maximum
plus 5 % Rand. Mittlerer positiver effektiver Anfahrverzug als erster Ordnungsansatz,
Stopwegmaximum plus 25 % und 2 mm Rand. Diese Ränder sind empirische Modellannahmen,
keine statistischen Konfidenzintervalle oder zugesicherten Sicherheitsgrenzen.

24 getrennte Profilprüffälle: Reibung 0,6/1,0, Phase 0,13/0,63, kleinere Befehle
0,02/0,015/0,2. Die Prüfdaten gehen nicht in den Fit ein. Alle 24 liegen im empirischen
Bereich, größte relative Abweichung vom mittleren Gain 7,48 %, kein Sturz.
Eine NumPy-Skalar-Serialisierung im ersten Bericht wurde korrigiert; die vollständige
Messreihe danach unter gesichertem Code neu ausgeführt. Keine Fit-Änderung anhand
der Prüfdaten. Profil und alle Rohmessungen werden archiviert.

## Navigation: Entwicklung und Datenabgrenzung

Controllerentwicklung nur auf Seeds 10/11 und isolierten Sensorfixtures. Mehrere
Entwicklungsfassungen wurden ausgeführt und mit Fehlschlägen aufbewahrt. Kein Zugriff
auf die bisherigen Prüfseeds 1000/1001 zur Abstimmung; deren Ergebnisse bleiben
unverändert. Neue Prüfseeds 2000/2001 erst nach Code-/Parameter-Freeze ausführen.

Sensorvertrag: Echo, RGB, Erwerbszeit, Hunger/Schaden, eigene letzte Aktion.
Keine echte Pose, Gelenke, Kontakte, Hindernisgeometrie, Erfolg oder Zielkoordinate.
Das Profil wird nur als Befehlswirkungsschätzung benutzt, nicht als Odometrie.
Karte/Hüllen sind lokale technische Schätzungen und haben Ablaufzeiten. Einzelne
freie Echo-Strahlen löschen keine benachbarten Hindernispunkte. Pixelhinweise
liefern ausschließlich Abtastrichtungen, keine erfundene Tiefe. Neue/schon bekannte
Blickbereiche werden unterschieden, um stationäre Scanschleifen zu begrenzen.

## Unabhängige Matrix

48 Fälle: Seeds 2000/2001 × offene Arena/Slalom × nominal/verrauscht/verzögert ×
reaktiv/Gedächtnis/schnelles Gedächtnis/aktive Navigation. Gleiche Kurse, MuJoCo-Geometrie, 16×12-Kamera,
Rauschparameter und DeliveryBuffer; zwei Sekunden Anfangsstand je Fall.
Die beiden alten Baselines laufen ohne Profilkompensation unverändert. Eine zusätzliche
schnelle Gedächtnisbaseline ändert ausschließlich den Vorwärtsbefehl von 0,025 auf
0,03 m/s. Damit wird ein Geschwindigkeitsvorteil in offener Fläche nicht der aktiven
Abtastung zugeschrieben. Alle vier Varianten erhalten dasselbe Budget.

- **900er-Endpunkt:** Ziel x≥0,35 m bis Entscheidung 900. Früherer Sturz, Ausfall
  oder Erreichen des Kontaktbudgets ist ein Fehlschlag. Dieser Wert bleibt direkt
  erkennbar und wird nicht durch spätere Zielerreichung ersetzt.
- **Getrennte Langhorizont-Diagnose:** maximal 2400 Entscheidungen, Zielgeometrie
  unverändert. Ein Erfolg nach 900 wird ausschließlich hier als Erfolg gezählt.
  Baselines erhalten dieselbe zusätzliche Zeit. Keine Behauptung fairer Verbesserung
  bei ungleichen Budgets.
- Abbruch wie #43: Höhe <35 mm oder Neigung >45°, Stromabschaltung, numerischer
  Fehler, 25 nicht unterstützende Kontakt-Ticks oder Zeitbudget. Fuß-Boden-Tragkräfte
  zählen nicht als Fehler. Kontaktmessung am Tickende kann kurze Zwischenkontakte
  übersehen. Keine Änderung an alten Toleranzen.
- Nach jedem Ausgang 40 Stop-Ticks: lineare Geschwindigkeit ≤5 mm/s,
  Winkelgeschwindigkeit ≤0,05 rad/s und zusätzliche Drift ≤30 mm; kein Sturz.
  Zielstatus und Stopprüfung bleiben getrennt.

Enges technisches Abnahmeziel für die neue Variante: alle sechs offenen Fälle
innerhalb 900, alle zwölf Fälle innerhalb 2400, alle Stopprüfungen bestanden,
keine Stürze/Abschaltungen. Wird das verfehlt, wird kein vollständiger Erfolg
behauptet. Auch eine erfüllte Matrix wäre kein Nachweis allgemeiner Robustheit,
keine Hardwarevalidierung und keine Paper-Hypothese. Paarvergleiche bleiben deskriptiv.

## Integrität und Wiederaufnahme

Code-/Profilhash vor jedem Lauf speichern. Drei vollständige aktive Slalomepisoden
(je Sensorprofil) aus Entscheidung 250 in frischen Prozessen fortsetzen; Ergebnis,
Körperzustands- und Verlaufshash müssen exakt gleich sein. Zusätzlich in Unit-Tests
jeden Tick nach Wiederaufnahme sowie abgeschlossene Scans und fehlerhafte Snapshots
prüfen. Alte Baselines werden im neuen Evaluator tickweise auf unveränderten Body-,
Controller- und Zustellungszustand gegengeprüft.

Replays stammen aus tatsächlichen Fällen; das JavaScript wird separat ausgeführt.
Native MuJoCo-/Plotbilder sind keine Browser-Sichtabnahme. Die bereits dokumentierte
Browserblockade bleibt bestehen. Alle Fehlschläge, Endpunkte und Quellfingerprints
werden gespeichert; nach Beginn der unabhängigen Prüfung keine Parameteroptimierung
auf diesen Ergebnissen. Korrekturen an realen Fehlern werden ausdrücklich dokumentiert.
