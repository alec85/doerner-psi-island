# Optionales MuJoCo-Backend

Das zweite Body-Backend berechnet eine frei bewegliche Modellmasse mit zwölf
Gelenken, Schwerkraft und Kontakten. Es ist ein eigenes angenommenes Modell,
kein kalibrierter digitaler Zwilling des SunFounder-Roboters. Die bisherige
kinematische Referenz und der PSI-Kern sind davon unabhängig.

## Installation und Start

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev,mujoco]"
.venv/bin/python -m pytest
.venv/bin/python -m psi_gw.body.picrawler.mujoco_experiment --output /tmp/mujoco-new-run
```

Jede vollständige Abnahme benötigt einen neuen Ausgabeordner. Ein gespeicherter
Versuch wird in einem frischen Prozess so fortgesetzt:

```bash
.venv/bin/python -m psi_gw.body.picrawler.mujoco_experiment \
  --resume /tmp/mujoco-new-run/checkpoint-delayed.json --output /tmp/mujoco-resumed.json
```

```python
from psi_gw.body.base import Action
from psi_gw.body.picrawler.mujoco_body import MujocoBody

body = MujocoBody(seed=42)
for _ in range(40):
    body.act(Action("stand"))
for _ in range(160):
    body.act(Action("drive", {"forward_mps": 0.02}))
observation = body.observe()  # Echo, Pixel, Betriebswerte, Peripherie, Bedürfnisse
snapshot = body.snapshot()
resumed = MujocoBody.restore(snapshot)
frame = body.frame()  # Nur Beobachter: Pose, Gelenke, Kontakte und Modellwahrheit
```

`stop` und `stand` liefern die nominalen Gelenkziele mit begrenzter Zieländerung.
Der Körper kann ausrollen, rutschen oder fallen. `relax` deaktiviert die lokalen
Antriebe für Experimente; es ist kein Bridge-Befehl. Peripheriebefehle lassen
die Beine ebenfalls zur nominalen Haltung zurückkehren. Die Mock-Bridge nutzt
denselben Vertrag; Retry, Timeout und Disconnect werden nicht umgangen.

## Modellannahmen

| Größe | Wert im Ausgangsmodell | Bedeutung |
|---|---|---|
| Segmente / Hüftabstand | 33/48/78 mm / 77 mm | Vorhandene Geometrie, eigene Winkelkonvention |
| Chassis / Gesamtmasse | 0,350 / 0,602 kg | Angenommene Massen; Trägheiten aus primitiven Geometrien |
| Beinmassen | Coxa 15, Oberteil 20, Unterteil 25, Fuß 3 g | Je Bein; keine Wägung der Hardware |
| Gleitreibung | 0,8 | Isotroper Kontaktparameter, kein gemessener Boden |
| Gelenkbereiche | Gier ±1,2; Hüfte ±1,6; Knie −2,8…−0,15 rad | Angenommene Bereiche in der eigenen Konvention |
| Drehmoment / Zieländerung | 0,35 Nm / 4 rad/s | Momentbegrenzung und Ziel-Slew, keine harte Ist-Geschwindigkeitsgrenze |
| PD-Regler | Kp 6, Kd 0,02 | Lokales Gelenkfeedback; keine Körperlage-Regelung |
| Taktung / Gang | 2 ms / 50 ms; Zyklus 1,2 s, Standanteil 0,85, Hub 12 mm | Physik / Body; eigener Crawl-Ansatz |

MuJoCo-Gelenkgrenzen sind **weiche Kontaktbedingungen**. Unter Last können Winkel
den angegebenen Bereich etwas überschreiten. Die Tests prüfen an beiden Grenzen
aller zwölf Gelenke die entgegenwirkende Zwangskraft. Eine externe Last von
0,6 Nm am ersten Giergelenk ergab beispielsweise 1,2228 rad bei Obergrenze 1,2 rad.
Das ist kein harter mechanischer Anschlag. Eigenkollisionen sind deaktiviert;
Robotergeometrie kollidiert mit Boden, Wänden und Hindernissen.

Die CPU-Kamera strahlt aus der tatsächlichen räumlichen Körperlage auf Weltgeometrie.
Eigene Roboterteile verdecken Kamera/Echo zunächst nicht. Sie ist synthetisch,
ohne Belichtungs-/Linsen-/Materialmodell. `observe` und `frame` lesen Caches und
verbrauchen weder Physikzeit noch Zufall.

## Energie und Wiederaufnahme

Zusätzlich zur vorhandenen CPU-/Kamera-/Servo-Leerlauflast wird pro Physikschritt
`sum(max(torque * joint_velocity, 0)) / 0.65 + 8 * sum(torque**2)` als angenommene
Motorlast verwendet. Negative Arbeit wird separat aufgezeichnet und nicht
regeneriert. Peripherie und Reglerverluste werden einmal hinzugefügt. Das ist
eine linksseitige diskrete Leistungsnäherung, keine gemessene Servokennlinie.
`servo_power_w` enthält die Motor-Näherung einschließlich Grundlast; der bestehende
kinematische Bewegungszuschlag wird hier auf null gesetzt.

Bei Abschaltung werden Antriebe im spätestens folgenden 2-ms-Schritt ausgeschaltet;
auch ein nur teilweise versorgter letzter Schritt erhält konservativ kein Moment.
Schwerkraft und Kontakte laufen weiter. Der elektrische Bericht und das mechanische
Arbeitsintegral sind deshalb kein exaktes gemeinsames Energiebilanzmodell.

Snapshots enthalten `mjSTATE_INTEGRATION` einschließlich Warmstart, Antriebsziele,
Gangphase, Zufall/Sensorcache, Energie, Peripherie und wartende Taster. Engine-Version
3.3.7 und Modellhash müssen passen. Nach einer numerischen Warnung/NaN wird weitere
Ausführung bis `reset` gesperrt; ein solcher Zustand wird nicht als fortsetzbarer
Snapshot ausgegeben. Bitidentität gilt nur für die geprüfte identische Laufzeit.

## Ergebnisse und Darstellung

Abnahmekriterien: [MUJOCO-VALIDATION.md](MUJOCO-VALIDATION.md).
Messwerte und Einschränkungen: [MUJOCO-RESULTS.md](MUJOCO-RESULTS.md).
Entscheidung: [ADR-mujoco.md](ADR-mujoco.md).

Native Modellansichten und Peripherie-/Bridge-Smoke-Test lassen sich separat erzeugen:

```bash
MUJOCO_GL=egl .venv/bin/python docs/picrawler/mujoco-smoke.py --output /tmp/mujoco-smoke
.venv/bin/python docs/picrawler/mujoco-replay-check.py \
  /tmp/mujoco-smoke/peripherals.html --output /tmp/replay-checks.json
```

EGL ist eine optionale lokale Darstellungsfähigkeit, keine Voraussetzung für Body,
Strahlenkamera oder die Physiktests. Stand-, Gang- und Drehbilder wurden direkt von
MuJoCo gerendert und visuell geprüft. HTML-Replays wurden mit ihrem tatsächlichen
JavaScript im DOM/Canvas-Harness ausgeführt. Das ist keine Browser-Sichtabnahme;
diese bleibt in der aktuellen Umgebung blockiert.
