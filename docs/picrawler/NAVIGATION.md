# Bewegungsprofil und sensorbeschränkte Navigation

Issue #49 / Draft-PR #52, auf dem optionalen MuJoCo-Backend aus #43.
Installation bleibt `pip install -e ".[dev,mujoco]"`; keine neue Laufzeitabhängigkeit.
Die Beispiele greifen ausschließlich auf die bestehende Body-Schnittstelle zu.

## Messung und Profil

```bash
.venv/bin/python -m psi_gw.body.picrawler.motion_experiment --output /tmp/motion-new
```

Zwei Sekunden Stand, sechs Bewegung, zwei Stop je Fall. Das Skript trennt
36 Entwicklungs- und 24 Profilprüffälle. Nur die Messung verwendet wahre Modellpose;
der spätere Controller bekommt ausschließlich das aggregierte Profil. Die komplette
60er-Reihe wurde nach Korrektur einer Berichtserialisierung erneut gerechnet und
stimmt exakt überein. Reibung, Massen und Servowerte bleiben Modellannahmen.

Das gespeicherte [Profil](navigation-results-2026-11-13/motion-profile.json) enthält
positive/negative Gains je Achse, empirische Bereiche, einen mittleren effektiven
Anfahrverzug und Stopwegrand. Die Identifikations-Provenienz nennt den damaligen
Quellfingerabdruck; zusätzliche später eingeführte Module ändern diesen Ursprung nicht.
Ein neuer Lauf mit neuer Codebasis erhält bewusst einen anderen Herkunftshash.
Die Fitparameter lassen sich aus den archivierten Entwicklungsfällen exakt neu bilden.

| Wirkung | Positiver Befehl | Negativer Befehl |
|---|---:|---:|
| Vorwärtsachse | 0,869 | 0,953 |
| Seitwärtsachse | 0,936 | 0,934 |
| Gierachse | 0,879 | 0,877 |

Effektiver mittlerer Verzugsansatz 70,8 ms, Stopwegrand 8,36 mm. Die Bereiche
beruhen auf beobachteten Extrema plus technischen Rändern, nicht auf einem
Konfidenzintervall. Alle 24 getrennten Profilprüffälle liegen darin; größter
relativer Gainfehler gegenüber dem Mittel 7,48 %. Das gilt für diese konstanten
Modellbefehle, nicht automatisch für verrauschte Stop-/Startfolgen oder Hardware.

## Aktive Navigation v1

```bash
.venv/bin/python -m psi_gw.body.picrawler.navigation_experiment \
  --profile docs/picrawler/navigation-results-2026-11-13/motion-profile.json \
  --split development --output /tmp/navigation-new-development
```

`ActiveNavigator` integriert die profilierte Befehlswirkung. Seine Position und
Richtung sind Schätzungen aus eigenen Befehlen, keine gemessene Odometrie.
Aktuelle Echos werden dem geschätzten Zustand bei **Erwerb** zugeordnet, nicht
blind der Auslieferungszeit. Duplikate sind keine neue Evidenz; widersprüchliche
Captures führen zum Halt. Bei umsortierten Paketen darf ein tatsächlich noch
frischer akzeptierter Capture weiterwirken, ohne sein Alter zurückzusetzen.
Fehlende/veraltete Messung oder unbekannte Bedürfnisse führen zum Halt; hoher
Hunger/Schaden verriegelt den Energiehalt.

Farb-/Dunkelheitsregionen im unteren Bild sind Abtast-Hinweise, keine Tiefen oder
bekannten Objektidentitäten. Neue Blickbereiche können einen Körperscan auslösen.
Die Echos bilden einen befristeten lokalen Hindernisspeicher, keine bekannte Karte.
Eine schmale freie Messung löscht keine benachbarte Hindernisevidenz. Hüllen und
lokale Wegauswahl berücksichtigen die Körperausdehnung; ein langsamer Abstand
vergrößernder Schritt kann einen eingeschlossenen Schätzrand verlassen.

Rohdaten bleiben auf 512 Hindernispunkte, 768 Abtaststrahlen und 64 zeitliche
Poseschätzungen begrenzt. Punkte laufen nach 28 s aus. Bewegungsunsicherheit und
Abstandsränder sind heuristisch, keine garantierte Kollisionsfreiheit. Holonome
kleine Seitwärtsschritte nutzen vorhandene Aktionen. Die gewünschte ursprüngliche
Fortschrittsrichtung ist keine dem Controller mitgeteilte Zielkoordinate.

## Getrennter visueller Folgeversuch

Die erste unabhängige v1-Prüfung blieb unverändert: 10/12 Ziele bei 2400
Entscheidungen, beide verrauschten Slalomfälle am Kontaktbudget. Damit wurde das
vollständige Abnahmeziel verfehlt. [Eigene Entscheidung](ADR-visual-heading.md)
legt einen getrennten Versuch mit neuen Prüfseeds fest.

```bash
.venv/bin/python -m psi_gw.body.picrawler.visual_experiment \
  --profile docs/picrawler/navigation-results-2026-11-13/motion-profile.json \
  --split development --output /tmp/visual-new-development
```

`VisualNavigator` vergleicht RGB-Spaltenprofile vor/nach einem annähernd
stationären Echo-Scan. Die bekannte synthetische Pinhole-Intrinsik (60° horizontal)
bildet Spalten auf Winkel ab. Helligkeitsnormalisierte Farbprofile im oberen
Bildteil begrenzen den Einfluss kleiner vertikaler Gangbewegungen. Geprüft wird
±0,30 rad mit 0,005-rad-Schritt; mehrdeutige/gleichförmige Bilder werden verworfen.
Kosten ≤0,035 und Abstand zu getrennten Alternativen ≥0,004 sind technische
Heuristiken. Übernommen werden höchstens 0,25 rad Korrektur bei höchstens 50 mm
geschätzter Translation zwischen den Bildern. Das setzt eine unveränderte Szene
und annähernd stationäre Kamera voraus; es erkennt unbekannten echten Schlupf nicht
zuverlässig als Translation.

Die bildgestützte relative Richtung wird am Erwerbszeitpunkt verglichen und zur
aktuellen Schätzung fortgeschrieben. Die Translation bleibt geschätzt. Eine
angenommene Intrinsik oder ein Bildabgleich ersetzt weder IMU/Encoder noch
allgemeines Visual-SLAM. Historische Kartenfehler können fortbestehen.

## Vergleich und Wiederaufnahme

Der 900er-Endpunkt bleibt separat. Zusätzliche Zeit bis 2400 ist eine eigene
Langhorizont-Diagnose, die auch allen Vergleichsvarianten gewährt wird. Neben den
unveränderten reaktiven/Gedächtnis-Baselines gibt es eine schnelle Gedächtnisbaseline
mit ausschließlich 0,025→0,03 m/s geändertem Vorwärtsbefehl. Ein Vorteil in offener
Fläche darf damit nicht allein der Abtastung zugeschrieben werden.

Die visuelle Variante erhält einen eigenen Vergleich gegen eingefrorene aktive v1
auf neuen Seeds. Nach jedem Ausgang zwei Sekunden Stop, mit unveränderten Sturz-,
Kontakt- und Restgeschwindigkeitsgrenzen aus #43. Alle Berichte und Fehlschläge
stehen im [Ergebnisbericht](NAVIGATION-RESULTS.md).

```bash
.venv/bin/python -m psi_gw.body.picrawler.navigation_experiment \
  --resume /tmp/checkpoint-v1.json --output /tmp/resumed-v1.json
.venv/bin/python -m psi_gw.body.picrawler.visual_experiment \
  --resume /tmp/checkpoint-visual.json --output /tmp/resumed-visual.json
```

Checkpoints sichern Body/Engine, Profil, Zustellung, Controller, Schätz-/Karten-
und Abtastzustand, Aktionscache und Auswertung; visuell zusätzlich Referenzbild,
Erwerbszeit und Korrekturzustand. Prozessfortsetzung ist eine neue Python-Laufzeit,
kein bereits integrierter dauerhafter Controller-RPC oder Hardwaretransport.

Die HTMLs zeigen gespeicherte reale Modellframes. Der JS-Harness prüft ihre
Funktionen; Auswertungsgrafiken vergleichen tatsächliche Wege mit Schätzungen.
Diese Prüfungen sind keine Browser-Sichtabnahme der weiterhin lokal blockierten
HTML-Dateien. PSI-/Workspace-/Paper-Code und Hardware-Sensorvertrag bleiben getrennt.
