# MuJoCo: vorab festgelegte dynamische Abnahme v1

Status: Kriterien vor den unten beschriebenen Validierungsfahrten festgelegt.
Die früheren kinematischen 432 Episoden werden weder ersetzt noch umbewertet.

## Modell und Entwicklung

MuJoCo 3.3.7, Physikschritt 2 ms, Body-Tick 50 ms, Modell v1 mit freiem Chassis
und zwölf Gelenken. Alle Massen, Reibungen, Drehmomentgrenzen und PD-Werte sind
Annahmen. Parameter und Modellhash stehen in jedem Report.

Entwicklung ausschließlich bei Start (0,0,0), Reibung 0,8: zwölf Varianten aus
Zykluszeit 1,2/2 s, Hub 4/8/12 mm, Standanteil 0,75/0,85 mit anfänglichem Kd=0,08.
Anschließend fünf Dämpfungen 0,005/0,01/0,02/0,04/0,08 bei sonstiger Grundkonfiguration.
Kd=0,02 wurde gewählt; Zyklus 1,2 s, Hub 12 mm und Standanteil 0,85 bleiben erhalten.
Diese explorativen Rohdaten sind kein unabhängiger Validierungssatz.

## Offene Gangabnahme

Jeder Fall beginnt mit zwei Sekunden `stand`, danach acht Sekunden Bewegung,
danach zwei Sekunden `stop`. Validierung verwendet Anfangsgierwinkel +0,3 und
−0,4 rad und Reibungskoeffizienten 0,4/0,8/1,2 (sechs Startbedingungen).
Fünf Befehle je Startbedingung: vorwärts/rückwärts 0,02 m/s, seitwärts links/rechts
0,015 m/s und Drehung links 0,15 rad/s. Insgesamt 30 Fälle.

Vorab festgelegte Kriterien:

- Stand nach zwei Sekunden: Höhe 60–75 mm, aufrecht, lineare Geschwindigkeit
  höchstens 1 mm/s, Winkelgeschwindigkeit höchstens 0,01 rad/s; vier tragende Füße.
- Während Bewegung: kein Sturz (Höhe <35 mm oder Körper-z-Achse mehr als 45°
  gegen Welt-z), keine numerische Warnung; tatsächliche Antriebe höchstens 0,35 Nm.
- Vor-/Rückwärts: signierter Fortschritt entlang anfänglicher Körper-x-Achse
  0,10–0,22 m, Querfehler höchstens 25 mm, Gieränderung höchstens 0,12 rad.
- Seitwärts: signierter Fortschritt entlang anfänglicher Körper-y-Achse
  0,07–0,16 m, Querfehler höchstens 40 mm, Gieränderung höchstens 0,15 rad.
- Drehung: Gierfortschritt 0,5–1,8 rad, Translation höchstens 50 mm.
- Nach zwei Sekunden stop: lineare Geschwindigkeit höchstens 5 mm/s,
  Winkelgeschwindigkeit höchstens 0,05 rad/s, Drift ab stop höchstens 30 mm.

Die vollständigen Messwerte werden auch bei Nichterfüllung gespeichert. Es
werden weder Startpose noch Körpergeschwindigkeit während `act` gesetzt.

## Geschlossener Sensorbenchmark

24 Fälle: Seeds 1000/1001 × offene Arena/Slalom × reaktiv/Gedächtnis × nominale,
verrauschte und verzögerte Sensoren. Derselbe Kursgenerator, Referenzcontroller
und DeliveryBuffer wie PR #38; Anfangsstand zwei Sekunden. Danach höchstens
900 Controllerentscheidungen. Ziel: tatsächliche Körpermitte x≥0,35 m.
Abbruch: erster Sturz, 25 Body-Ticks mit nicht unterstützendem Kontakt,
Stromabschaltung oder Zeitbudget. Boden-Fuß-Tragkontakte zählen nicht als Fehler.
Ein Tick wird als Kontakt gezählt, wenn am Tickende ein anderer positiver
Kontaktimpuls vorliegt; sehr kurze Kontakte zwischen Abtastpunkten können fehlen.

Nach dem Abbruch oder Ziel 40 Stop-Ticks; dieselben Restgeschwindigkeits- und
Driftgrenzen wie oben. Zielerfolg und Stop-Abnahme bleiben getrennte Ergebnisse.
Der Agent erhält nur Echo, Pixel und Bedürfniswerte, keine Kontakte oder Pose.
Der dynamisch schließende Gate-Kurs wird in v1 nicht eingesetzt: Modelländerung
und kollisionsfreie Schließung sind noch nicht implementiert. Exploration und
Energie-Stopp werden nicht als ausgeführte geschlossene Aufgaben ausgegeben.

## Wiederaufnahme und Darstellung

Snapshot: vollständiger `mjSTATE_INTEGRATION`, lokale Regel-/Gangzustände,
Energie, Sensorcache/RNG, Peripherie und wartende Taster. Gleiche Engine-Version
und Modellhash sind zwingend. Exaktheit wird in frischen Python-Prozessen geprüft.
Reports enthalten Quellfingerabdruck; abgeschlossene Codebasis wird vor Ausführung
gepusht. Replays speichern reale Modellpunkte und volle Sensororientierung.
Eine Browser-Sichtabnahme ist in dieser Umgebung weiterhin blockiert und wird
nicht durch einen erfolgreichen JavaScript-Test behauptet.
