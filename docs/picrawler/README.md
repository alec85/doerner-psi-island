# PiCrawler: 3D-Testbett für Bewegung, Sensoren und Bedürfnisse

Geschlossene Referenzsteuerung aus Issue #37: [Roboterbenchmark](ROBOT-BENCHMARK.md),
[zeitliche Wahrnehmung](TEMPORAL-PERCEPTION.md), [lokale Prozessgrenze](CONTROLLER-PROCESS.md),
[ausgeführte Ergebnisse](ROBOT-RESULTS.md) und [eigene Übergabe](HANDOFF-robot.md).

Zusätzliche Vorarbeit aus Issue #35: [Belastungsmatrix](VALIDATION-TOOLS.md),
[Messdatenimport und Modellschätzung](MEASUREMENT-FIT.md) sowie die
[eigene Übergabe](HANDOFF-validation.md). Auf PR #31 aufbauend, ohne Eingriff
in PSI-Kern oder Global Workspace.

Eine ausführbare Vorarbeit für Phase 4/5 aus [Issue #30](https://github.com/alec85/psi-gw/issues/30).
Vier Beine mit zwölf Gelenken, kontinuierliche Hindernisprüfung, modellierter
Ultraschall, synthetische Kamerabilder, Akku-/Temperaturmodell und ein
reproduzierbares interaktives 3D-Replay. Kalibrierpaket, Sensoraufbereitung und
eine Bridge mit simuliertem Gegenüber sind ebenfalls vorbereitet.
Die Bewegung ist kinematisch: Die Körperbewegung ist vorgeschrieben, Kräfte und
Stabilität werden nicht berechnet. Elektrische und thermische Zustände entwickeln
sich nach ausdrücklich angenommenen physikalischen Parametern. Die Grenzen stehen im
[lokalen ADR-Entwurf](ADR-prototype.md).

## Starten, ohne einen anderen Arbeitsbereich umzuschalten

Optional einen getrennten Git-Arbeitsbereich verwenden:

```bash
git fetch origin codex/30-picrawler-sim
git worktree add --detach ../psi-gw-picrawler origin/codex/30-picrawler-sim
cd ../psi-gw-picrawler
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Die Demo benötigt nur Python und das bereits im Projekt enthaltene NumPy:

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler \
  --output picrawler-run --seed 42 --noise-m 0.002 --dropout 0.02
```

Für sichtbare Energie-/Wärmebedürfnisse startet das zweite Szenario bereits
mit 15 % Akku und 78 °C CPU:

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler \
  --scenario resources --output picrawler-resources --seed 42 --noise-m 0.002 --dropout 0.02
```

`picrawler-run` muss neu oder leer sein. Danach `picrawler-run/replay.html` im
Browser öffnen. Die Datei enthält alle Bilder und Bewegungsdaten und benötigt
keinen Server, kein Internet und keine Python-Ausführung im Browser.

Die Ansicht bietet Abspielen/Pause, Zeitregler, Einzelbilder per Pfeiltasten,
Geschwindigkeit, Draufsicht, Drehung und Zoom. Neben der räumlichen Welt stehen
Kamerabild, Ultraschall, Farbflächen sowie Akku-/Temperatur-/Bedarfsverläufe.
Alle Ansichten verwenden dieselben gespeicherten Zustände. Sie liest nur gespeicherte Daten.
Die Bewegung wird von einem vorgegebenen Testskript erzeugt; sie ist kein
Nachweis einer PSI-gesteuerten oder gelernten Hindernisvermeidung.

Dateien eines Laufs:

| Datei | Inhalt |
|---|---|
| `replay.html` | Eigenständige Ansicht, standardmäßig jeder fünfte Tick inklusive Kamerabild |
| `trace.jsonl` | Jeder Tick mit Gelenkpunkten, Sensoren und Diagnosedaten, ohne RGB-Pixel |
| `checkpoint.json` | Vollständiger Zustand in der Mitte des Laufs, einschließlich RGB-Cache und RNG |
| `summary.json` | Ausgeführte Tickzahl, Weg, Grenzen, Konfiguration und Fortsetzungsprüfung |

Weitere Optionen: `--no-camera`, `--sample-every 10`, `--source-commit <revision>`.
`--noise-m` ist die halbe Breite eines uniformen Modellrauschens in Metern;
`--dropout` ist eine modellierte Ausfallwahrscheinlichkeit. Beide sind ohne
Option 0 und keine Herstellerkennlinien.

### Optional: PNG und Video aus derselben Aufzeichnung

Wer Matplotlib und FFmpeg mit H.264 bereits separat bereitgestellt hat, kann
die gespeicherten Zustände als koordinatengetreue PNG-/MP4-Ansicht exportieren:

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler.render_video \
  picrawler-resources/replay.html --png preview.png --video preview.mp4 --speed 3 --fps 12
```

Das Video kennzeichnet den Zeitfaktor (hier 3×). Der Renderer führt weder
HTML/JavaScript noch die Simulation erneut aus; er liest die gespeicherten
Gelenkpunkte, Welt, Kamerabilder und Betriebswerte. Matplotlib wird erst beim
Export importiert, FFmpeg nur für Video benötigt. Beide bleiben optionale
externe Werkzeuge; die normale Simulation und das HTML brauchen sie nicht.

## Gemeinsamer Peripherietakt: Audio, LEDs und Taster

Das zusätzliche Szenario `peripherals` startet wie der Ressourcenlauf
mit niedrigem Akkustand, verwendet aber zusätzlich symbolische
Sprach-, Sound- und Tonereignisse sowie die Benutzer-LED. Diese laufen
mit dem Bewegungs-/Energietakt und erscheinen in der drehbaren
3D-HTML-Wiedergabe in einem eigenen Ereignispanel:

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler --scenario peripherals \
  --output picrawler-peripherals --seed 42
```

Danach `picrawler-peripherals/replay.html` öffnen und durch die
Ereignisse springen. Audio ist im Modell **sichtbar, noch nicht hörbar**:
kein PCM, keine TTS-Engine und keine Ausbreitung des Schalls.
Die angenommenen 0,4 W Audio- und 0,04 W LED-Verbrauch werden
bei aktivierter Peripherie in jedem Tick der Energiebilanz zugerechnet.
Alte Szenarien bleiben unverändert ohne Peripherie. Die tatsächliche
HAT-Revision und Hardwarekalibrierung bleiben offen.

[Peripherieintegration und API](PERIPHERAL-INTEGRATION.md) ·
[Hardwareinventar](HARDWARE-INVENTORY.md)

## Verwendung als Körper

```python
from psi_gw.body import Action, Body
from psi_gw.body.picrawler import PiCrawlerSimBody, SimConfig, World

body = PiCrawlerSimBody(World(), SimConfig(camera_enabled=False), seed=42)
assert isinstance(body, Body)

initial = body.observe()
body.act(Action("drive", {"forward_mps": 0.02, "yaw_rps": 0.1}))
observation = body.observe()
body.act(Action("stop"))
```

Ein `act` entspricht genau einem Tick, standardmäßig 0,05 s. Ein `drive` gilt
nur für diesen Tick; es bleibt kein Geschwindigkeitsbefehl im Hintergrund
aktiv. Unbekannte Namen, nicht endliche Werte, unbekannte Parameter und
Geschwindigkeiten außerhalb der konfigurierten Grenzen werden abgewiesen.

| Aktion | Parameter / Semantik |
|---|---|
| `drive` | `forward_mps`, `lateral_mps`, `yaw_rps`, jeweils standardmäßig 0. Positive Querbewegung nach links, positive Drehung gegen den Uhrzeigersinn. |
| `stop` | Hält Körper und Füße sofort, auch einen angehobenen Fuß. Zeit/Sensorik laufen einen Tick weiter. |
| `stand` | Setzt die nominelle Fußhaltung und Gangphase sofort zurück. Körperposition bleibt erhalten. |

Die Standardgrenzen sind 0,03 m/s für die Norm der Translation und 0,30 rad/s
für die Drehung. Das sind Grenzen dieses Testmodells. `stop` und `stand` sind
keine geprüften Hardware-Bewegungsabläufe; ein realer Controller braucht
geeignete Übergänge und kalibrierte Servo-Zuordnungen.

Die Beobachtung enthält:

- `sensors["ultrasonic"]`: `distance_m` oder `None`, dazu `status` (`ok`,
  `out_of_range`, `too_close`, `dropout`). Ein ungültiger Wert ist keine freie
  Strecke und wird nicht auf eine scheinbar gültige Reichweite gekappt.
- Optional `sensors["camera"]`: `encoding="rgb8"`, Breite, Höhe und Pixel unter
  `rgb`. Es sind geometrisch gerenderte RGB-Bilder ohne Objektlabels.
- `sensors["telemetry"]`: als simuliert gekennzeichnete Akku-/Versorgungswerte,
  Strom, Leistung, CPU-Temperatur sowie aktuelle und historische Warnflags.
  Eine nicht modellierte CPU-Kernspannung bleibt `None`.
- `internal`: lokale normierte Eingänge `hunger` und `damage`; keine direkte
  Mutation des PSI-Motivationskerns. Siehe [Energie und Bedürfnisprofil](ENERGY.md).
  Mit `EnergyConfig(enabled=False)` entfallen Telemetrie und Bedarfe.

Weltpose, Gelenkgeometrie, Kollisionsgrenze und Bewegungsbegrenzung stehen nur
in `frame()` für Debugger und Replay. Der Agent bekommt diese Wahrheit nicht
über `observe()` geschenkt. Alle Rückgaben sind vom internen Zustand getrennt.
Beliebig häufiges Beobachten oder Darstellen verändert weder Zeit noch RNG.

## Geometrie und Welt

Die Herstellerwerte 33/48/78 mm werden als radialer Offset sowie oberer und
unterer Schenkel verwendet. Der quadratische Hüftabstand beträgt im Modell
77 mm. Die nominelle Höhe von 60 mm, lokale Fußreichweite von 85 mm,
Montageorientierungen und das Gangprofil sind explizite Modellentscheidungen.

Eigene Frames: Körper +x vorwärts, +y links, +z oben. Die Beine liegen in der
Reihenfolge rechts vorne, links vorne, links hinten, rechts hinten. Beinlokal
zeigt +x radial nach außen, +y tangential gegen den Uhrzeigersinn. Es gibt
keine stillschweigende Gleichsetzung mathematischer Winkel mit SDK-/PWM-Winkeln.

Die unabhängige Vorwärts-/Inverskinematik prüft Erreichbarkeit und lehnt
singuläre oder unerreichbare Ziele ab. Gezeichnet werden die Punkte der
berechneten Gelenkkette, nicht ungeprüfte Zielkoordinaten. Die Fußbahn ist ein
einfacher Vierertakt mit 75 % Standanteil; sie kopiert keine SDK-Gangtabellen.

`World` bietet rechteckige Hindernisse und Arenagrenzen. Ein standardmäßig
180 mm großer Kollisionsradius umfasst die im Modell zugelassenen
Beingelenkpunkte. Kontinuierliche Kollisionsprüfungen innerhalb fester
Unterschritte verhindern das Durchtunneln dünner Hindernisse. Alle Hindernisse
blockieren die Fortbewegung, unabhängig von ihrer Höhe; Übersteigen,
Selbstkollision, elastische Füße und dynamische Kontakte sind nicht modelliert.
Ultraschall und Kamera berücksichtigen die Hindernishöhen separat.

Die Kamera ist eine Lochkamera mit 48 × 32 Pixeln und modelliertem horizontalem
Blickwinkel 60°. Sie zeigt Boden, Wände und Boxen. Sie bildet weder die
Herstelleroptik noch Licht-/Materialeffekte realistisch ab.

## Sichern und exakt fortsetzen

```python
import json
from psi_gw.body.picrawler import PiCrawlerSimBody

payload = json.dumps(body.snapshot(), allow_nan=False)
resumed = PiCrawlerSimBody.restore(json.loads(payload))
```

Enthalten sind Welt, Konfiguration, Pose, alle laufenden Fußbahnen, Gangphase,
Tick, Sensorcache, Zufallszustand und in Version 2 auch elektrischer/thermischer
Zustand, Verbrauch, Umgebung und Warnhistorie. Version 1 wird mit deaktiviertem
Energiemodell gelesen. Das Format ist versioniert und für
vertrauenswürdige eigene JSON-Schnappschüsse vorgesehen. Es ist kein allgemeiner
Importer für beliebige fremde Dateien. Exakte Fortsetzung ist für dieselbe
Python-/NumPy-Umgebung geprüft; plattformübergreifende Float-Bitgleichheit wird
nicht zugesichert.

`reset(seed, random_source=...)` erlaubt die Quellen des Projekts, etwa
`ReplaySource` und `DelphiRandom`, für kontrollierte Experimente. Die Quelle
wird explizit an die Sensorik weitergegeben. Die Simulationsphysik selbst
verwendet keinen Zufall. Ein fehlgeschlagener Reset oder eine fehlgeschlagene
Aktionsmessung hinterlässt keinen teilweise fortgeschriebenen Körperzustand.

## Fertige Vorarbeiten für die Integration

| Paket | Was jetzt ausführbar ist | Anleitung |
|---|---|---|
| Akku / Wärme / Bedürfnisse | Ladungs- und Wärmebilanz, Last-/Blockadeverbrauch, normierte Hunger-/Schadenssignale, Snapshots | [ENERGY.md](ENERGY.md) |
| Kalibrierung / echte Telemetrie | Versioniertes Profil mit Herkunft jedes Parameters, lesender Pi-Collector, unbekannte Werte bleiben offen | [CALIBRATION.md](CALIBRATION.md) |
| Sensorwahrnehmung | Nähe, Messwertfrische, robuste explizite Echofenster, RGB-Farbflächen mit Schwerpunkt/BBox | [PERCEPTION.md](PERCEPTION.md) |
| Bridge / simuliertes Gegenüber | Versioniertes JSON, Sessions/Sequenzen, ACKs, Verzögerung/Verlust, Frische, Wiederholungsschutz und Stop/Watchdog | [BRIDGE.md](BRIDGE.md) |

Das Kalibrierprofil lässt sich bereits ohne angeschlossenen Roboter erzeugen:

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler.calibration template --output calibration.json
PYTHONPATH=src python -m psi_gw.body.picrawler.calibration collect --output telemetry.json
```

Die zweite Anweisung meldet auf einem Rechner ohne Raspberry Pi ehrliche
Nichtverfügbarkeit. Hardwarebibliotheken werden nicht automatisch importiert,
Servos oder GPIO-Ausgänge nicht angesteuert. Batterie-ADC-Lesen benötigt einen
später explizit eingesetzten Reader für die tatsächlich vorhandene HAT-Version.

## Was für die spätere PSI-Anbindung noch fehlt

1. **Perzeption:** Kamera/Distanz in PSI-Situationen, Objekte und Handlungsmöglichkeiten
   übersetzen. Die fertigen Nähe-/Farbmerkmale sind eine Sensorbaseline; der
   heutige Insel-Pixelparser ist dafür kein fertiger semantischer Adapter.
2. **Aktionen:** PSI-Absichten in zeitlich begrenzte Bewegungskommandos und deren
   Abschluss/Rückmeldung übersetzen; echte Haltungstransitionen ergänzen.
3. **Agentenvertrag:** Den tatsächlichen `IslandLife`-Zugriff auf Insel-Client und
   inselspezifische Methoden zusammen mit dem verantwortlichen Arbeitsstrang
   entkoppeln. Der vorliegende `Body`-Entwurf allein erledigt das nicht.
4. **Physik/Hardware:** Parameter am konkreten Gerät vermessen, passende
   Dynamik-Engine auswählen, Kamera und Servo-Zuordnungen kalibrieren sowie
   echten Transport und unabhängigen Motor-Watchdog implementieren. Die
   Mock-Bridge ist noch kein Netzwerkdienst und schickt nichts an Hardware.

Kinematik, Einheiten, Szenarien, Beobachtungsformat, Tests, Aufzeichnung und
Replay lassen sich dabei weiterverwenden. Ein späteres dynamisches Backend
kann schrittweise gegen dieselben Sensor-/Aktions-Vertragstests geprüft werden.

## Prüfung und Übergabe

```bash
PYTHONPATH=src python -m pytest -q tests/picrawler tests/test_smoke.py tests/test_random_source.py
```

Siehe [VALIDATION.md](VALIDATION.md) für die tatsächlich ausgeführten Prüfungen
und [HANDOFF.md](HANDOFF.md) für den isolierten Arbeitsstand. Der zentrale
`HANDOFF.md` wurde wegen des ausdrücklichen parallelen Arbeitsauftrags nicht
überschrieben. Diese Datei hier hält den neuen Arbeitsstrang nachvollziehbar.

## Optionales physikalisches Backend

Seit Issue #42 steht zusätzlich ein [MuJoCo-Backend](MUJOCO.md) mit freiem Körper,
zwölf begrenzten Antrieben und Bodenkontakten bereit. Installation, Modellannahmen
und Wiederaufnahme sind dort dokumentiert. [Ausgeführte Abnahme](MUJOCO-RESULTS.md):
30/30 Gangfälle bestanden; die 24 geschlossenen Navigationsfahrten erreichen das
Ziel noch nicht. Das oben beschriebene kinematische Testbett bleibt separat.

## Bewegungsprofil und aktive Navigation

Issue #49 ergänzt [Identifikation, aktive Abtastung und lokale Navigation](NAVIGATION.md).
[Ausgeführte Ergebnisse](NAVIGATION-RESULTS.md): 977 Tests, zwei unabhängige
Prüfserien mit unverändertem 900er-Endpunkt und separatem Langhorizont. Die
Befehlsschätzung ersetzt keine Odometrie; der zusätzlich geprüfte Bildabgleich
bleibt experimentell. [Übergabe](HANDOFF-navigation.md).
