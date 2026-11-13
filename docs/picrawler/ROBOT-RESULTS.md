# Ausgeführte Robotik-Vorarbeit: Ergebnisse und Grenzen

2026-11-11. Issue #37, Draft-PR #38. Plan vorab in `3248fee` gespeichert;
Implementierung `76c923b89897f036a5693e266ab69b7bf5013965` für die Serien
eingefroren. Keine Controllerparameter anhand der Prüffahrten nachoptimiert.

## Tests und tatsächlich ausgeführte Serien

Python 3.12.14, NumPy 2.5.4, pytest 9.2.0. **864 Tests bestanden**, keine
übersprungen: 850 PiCrawler- und 14 gemeinsame Body-/RNG-Fälle; 97 neue Tests.
Keine Insel-/Workspace-/Golden-Master-Serien oder CI gestartet.

| Serie | Episoden | Körperticks | Aufgabe bestanden | Kontaktbudget | Zeitbudget |
|---|---:|---:|---:|---:|---:|
| Entwicklung, Seeds 0/1 | 144 | 78.185 | 84 | 52 | 8 |
| Zurückgehaltene Prüfung, Seeds 1000..1003 | 288 | 154.946 | 168 | 98 | 22 |

Zusammen 432 Episoden und 233.131 tatsächlich simulierte Körperticks.
Jede der sechs Task-/Policy-Kombinationen wurde über alle vier Familien und
drei Sensorprofile ausgeführt. Aufgaben-Nichterfüllung ist kein Programmabbruch.
Keine Arbeitsraumverletzung, kein verspäteter Energiehalt und kein unerwarteter
Modellstromausfall wurden in diesen Serien gefunden.

## Zurückgehaltene Aufgaben nach Policy

| Aufgabe | Reaktiv | Mit Gedächtnis |
|---|---:|---:|
| Fortschritt | 12 / 48 | 12 / 48 |
| Exploration | 24 / 48 | 24 / 48 |
| Energiehalt | 48 / 48 | 48 / 48 |

Die zeitliche Baseline verbessert hier **nicht** die Erfolgszahl. Beide schaffen
den offenen Fortschrittsparcours. Auf schwierigeren Geometrien begrenzen
Kontakte oder das unveränderte 900-Tick-Budget den Erfolg. Ein geometrisch
vorhandener Rasterweg garantiert weder Beobachtbarkeit noch rechtzeitige
Erreichbarkeit durch diese einfachen Referenzcontroller.

In den Prüffahrten wurden 44.353 konservative Körperkontakte gezählt. Bei allen
lag der der Policy verfügbare vordere Entfernungswert oberhalb ihrer
Naheschwelle. Das ist eine Diagnose der räumlich schmalen Beobachtung gegenüber
der breiteren Körperhülle; keine Aussage, dass ein reales Gerät kollisionsfrei
wäre. Die Hülle verhindert im Modell das Eindringen. Erinnerung allein ergänzt
die seitlich fehlende Geometrie nicht.

Die zusätzliche Richtungsdiagnose erreicht maximal rund 0,011 rad. Sie
vergleicht die Pose nach einer Aktion mit der vorher gespeicherten
Entscheidungsschätzung; bereits ein regulärer Drehtick erklärt diesen Wert.
Er darf nicht als isolierte Drift oder Fehler einer gemessenen Odometrie
interpretiert werden und geht nicht in die Erfolgskriterien ein.

Reaktiv entstanden 24.797 Kontakt-Ticks, mit Gedächtnis 19.556; Laufzeiten und
frühzeitiges Aufgabenende unterscheiden sich teilweise. Diese Rohzählung ist
kein kontrollierter kausaler Überlegenheitsnachweis. Alle 144 gepaarten
Prüfvergleiche bleiben im vollständigen Bericht sichtbar. Gruppierte
`mean_energy_j` beschreiben Kosten aller Episoden, nicht Effizienz bei gleichem
Erfolg. Gepaarte Energieunterschiede werden nur bei beiderseitigem Erfolg angegeben.

## Zeitliche Wahrnehmung und Prozessgrenze

Separater synthetischer Korpus, Seeds 0/1/42: 18 Distanz- und 12 Bildsequenzen.
Positive Ausreißer erzeugen 17 falsche „frei“-Frames in Einzelmessungen und null
in der konservativen Historie. Bei kurzen Ausfällen sind 354/360 bzw. 360/360
Distanzwerte verfügbar. Längere Ausfälle bleiben nach Ablauf ausdrücklich
unbekannt. Konservative Biaswerte und Positionsfehler gehaltener Farbregionen
sind ebenfalls ausgewiesen; keine pauschale Wahrnehmungsüberlegenheit behauptet.

Sechs Episoden lieferten direkt und im echten Python-Kindprozess identische
Ergebnisse. Zwei tatsächliche Kill-/Restart-Experimente bestanden: beim nächsten
Hostschritt Stop, unveränderte Pose, Sperre bis zum expliziten Neustart und neue
Sitzung/neuer Prozess. Zusätzliche Tests erzwingen Teilantworten, Schreibstau,
Timeouts, falsche Antworten und nichtendliche/out-of-envelope-Aktionen.
Diese Prüfung ersetzt weder einen Netzwerktransport noch einen Hardware-Watchdog.

## Wiederaufnahme und Replays

19.740 Folgeticks nach vollständigen Episoden-Checkpoints identisch, je 9.870
in Entwicklungs- und Prüfserie. Die Suite prüft dazu standardmäßig alle
Tor-/Policy-/Sensor-/Task-Fälle des ersten Seeds; andere Episoden sind nicht
als vollständig doppelt ausgeführt ausgegeben. Sechs zusätzliche Fälle wurden
im frischen Python-Prozess aus anderem Arbeitsverzeichnis fortgesetzt.

Resume ließ alle 144 Entwicklungs- und 288 Prüffallberichte bytegleich.
Vier Beispiele wurden unabhängig neu gefahren und stimmen exakt mit ihren
gespeicherten Prüfergebnissen überein. Ihre tatsächlichen HTML-Skripte wurden
über alle 179 gespeicherten Frames ausgeführt: 149.507 Canvasaufrufe, 195
Kamerabild-Schreibvorgänge; keine Assertion fehlgeschlagen. Der Tortest enthält
Frames mit zwei und drei Hindernissen. Eine zusätzliche Regression prüft
Hinzufügen **und Entfernen** eines framebezogenen Hindernisses.

**Keine visuelle Browserabnahme:** Die bekannte Socket-/URL-Richtliniengrenze
aus PR #31 bleibt bestehen. Keine Screenshots oder visuelle Freigabe behauptet.

## Archiv und Nachstellen

- [Maschinenlesbarer Prüfbericht](robot-results-2026-11-11/results.json)
- [Entwicklungsmanifest](robot-results-2026-11-11/development-manifest.json),
  [Zusammenfassung](robot-results-2026-11-11/development-summary.json),
  [alle 144 Fallberichte](robot-results-2026-11-11/development-cases.json.gz)
- [Prüfmanifest](robot-results-2026-11-11/validation-manifest.json),
  [Zusammenfassung](robot-results-2026-11-11/validation-summary.json),
  [alle 288 Fallberichte](robot-results-2026-11-11/validation-cases.json.gz)
- [Wahrnehmung](robot-results-2026-11-11/perception-summary.json),
  [Prozessversuche](robot-results-2026-11-11/process-summary.json),
  [Replay-Prüfung](robot-results-2026-11-11/replay-checks.json)

Vollständige HTML-Beispiele samt Episodenbericht und Parcours:
[offen](robot-results-2026-11-11/examples/open/replay.html),
[Slalom](robot-results-2026-11-11/examples/slalom/replay.html),
[Sackgasse](robot-results-2026-11-11/examples/dead_end/replay.html),
[Tor](robot-results-2026-11-11/examples/gate/replay.html).
Die Dateien herunterladen und in einer autorisierten Browserumgebung öffnen.
Das [Tor-Checkpoint](robot-results-2026-11-11/examples/gate/checkpoint.json.gz)
ist zusätzlich komprimiert archiviert. Die vollständigen Tickspuren entstehen
beim erneuten Beispiel-Export; das Archiv enthält keine selektierte Erfolgsserie.

```python
import gzip, json
from psi_gw.body.picrawler.robot_benchmark import Episode

with gzip.open("docs/picrawler/robot-results-2026-11-11/examples/gate/checkpoint.json.gz", "rt") as f:
    episode = Episode.restore(json.load(f))
while not episode.done:
    episode.step()
print(episode.result())
```

Die gzip-Fallarchive enthalten JSON-Arrays einschließlich Prüfsumme je Fall;
komprimierte und unkomprimierte SHA-256-Werte stehen in `results.json`.
Anleitungen: [Benchmark](ROBOT-BENCHMARK.md),
[Wahrnehmung](TEMPORAL-PERCEPTION.md), [Prozessgrenze](CONTROLLER-PROCESS.md).

## Nächste grundlegende Wahl

Alle drei unabhängigen Arbeitspakete sind umgesetzt. Die nächste zusätzliche
Simulationsbasis wäre eine Architekturentscheidung: optionales MuJoCo-Backend
oder externe Webots-Umgebung. Empfehlung und konkreter Folgeumfang stehen in
[DECISION-DYNAMICS.md](DECISION-DYNAMICS.md). Keine Engine wurde übernommen.
Sie würde Kontakt-/Antriebsdynamik ergänzen, aber die hier gemessene fehlende
seitliche Beobachtung nicht automatisch beheben. Gemeinsame PSI-Semantik und
reale Hardwarekalibrierung bleiben ebenfalls offen.
