# PiCrawler-Peripherie: Integration mit Bewegung, Energie und 3D-Replay

Stand: 2026-11-11, Branch `codex/30-picrawler-sim`, Draft-PR #31.

## Gemeinsamer Takt

`SimConfig(peripherals_enabled=True)` aktiviert die Zubehörfunktionen
im **gleichen** `PiCrawlerSimBody`; die vorhandenen Szenarien sind
standardmäßig unverändert (`False`). `PeripheralConfig.dt_s` muss dem
Körpertakt entsprechen. Jedes `body.act(...)` führt genau **einen**
Bewegungs-/Energie-/Peripherietick aus. Ein Sprach- oder LED-Befehl bedeutet
in diesem Tick körperlich `stop`; die Audioausgabe läuft während
nachfolgender `drive`-Ticks ohne zusätzliche Aktion weiter.

Die Aktionsnamen sind `tone(hz, duration_s)`, `sound(id, duration_s)`,
`speak(text, duration_s)`, `stop_audio()`, `led(on)`. Alle
Audioaktionen beschreiben **symbolische** Ereignisse, nicht PCM, TTS
oder physikalische Schallausbreitung. Ein Sound-`id` lädt keine Datei.
Tasterzustände werden nur über `body.inject_button(button, down)` als
Experiment-Eingang vorgegeben und **erst beim folgenden Tick** in die
Sensorbeobachtung übernommen. Die Reset-Taste löst keinen unkontrollierten
Neustart aus.

Ausstehende Tastereingaben werden getrennt vom zuletzt erfassten Sensorcache
gespeichert und erst mit einem erfolgreichen Tick übernommen. Ein Snapshot
zwischen Eingabe und Tick erhält beide Zustände sowie die Eingabereihenfolge.
Das optionale Feld `pending_buttons` ergänzt v3; bestehende v3-Snapshots ohne
dieses Feld bleiben lesbar.

```python
from psi_gw.body import Action
from psi_gw.body.picrawler import PiCrawlerSimBody, SimConfig

body = PiCrawlerSimBody(config=SimConfig(peripherals_enabled=True))
body.act(Action("speak", {"text": "Ich brauche Energie", "duration_s": 2.0}))
body.act(Action("drive", {"forward_mps": 0.02}))
print(body.observe().sensors["peripherals"]["speaker"])
print(body.frame()["peripheral_events"])
```

## Energie und Versionierung

`PeripheralSim.additional_power_w()` wird in jeder aktiven
Energiebilanz **einmal** als zusätzliche elektrische Verbraucherleistung
vor dem Wirkungsgrad des Reglers berücksichtigt. Anfangsannahmen:
Lautsprecher 0,4 W, Benutzer-LED 0,04 W. Beide sind kalibrierbar,
keine Hardware-Messungen. Ein Stromausfall beendet laufende
Audioausgabe und schaltet die angezeigte LED aus. Ein nicht
modellierter Lautsprecher erzeugt keinen falschen Mikrofon-Eingang.

Bei aktivierter Peripherie verwendet `snapshot()` Version 3 mit
Peripheriezustand und kompletter Ereignishistorie; die Wiederaufnahme
prüft Tickgleichheit und den Sensorcache. Version 1/2 bleiben wie bisher
lesbar. `observe()` und `frame()` bleiben lesend.

Die simulierte Session-Bridge unterstützt die neuen Aktionsnamen
und die optionale `sensors["peripherals"]`-Beobachtung. Die
Status-/Sicherheitsgrenzen der Bridge bleiben bestehen; es
gibt keinen Hardwaretransport.

## Interaktive 3D-Welt

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler \
  --scenario peripherals --output picrawler-peripherals \
  --seed 42 --noise-m 0.002 --dropout 0.02
```

`picrawler-peripherals/replay.html` enthält Welt, Beinbewegung,
Kamerabild, Energiekurven und das neue Panel
„Audio, LED und Taster“ mit dem zum gewählten Frame gehörenden
Status und den letzten Ereignissen. Abspielen, Scrubbing, Rotation
und Zoom bleiben wie gehabt. Die Audio-Timeline zeigt ausdrücklich
**keine hörbare Musik, Sprachsynthese oder akustische Simulation**.

Die separate `peripheral_events`-Liste in `summary.json` und
den Replay-Frames ist nur für Debugging und menschliche Interpretation.
Dem künftigen PSI-Agenten steht über `observe()` der
Peripheriesensorzustand zur Verfügung, keine vollständige
Vergangenheits- oder Weltwahrheit.

## Validierungsgrenzen

Neu unter `tests/picrawler/test_peripheral_integration.py`:
Aktions-/Sensorvertrag, gleichzeitiger Mehrverbrauch, atomare
Fehlaktionen, Checkpoint während Sprachausgabe, Tasteneingänge,
Stromausfall, Bridge-Replies und Replay-HTML-Daten.

**Ausgeführt am 2026-11-11:** 636 gezielte Tests bestanden, davon 622 unter
`tests/picrawler/` und 14 Body-/RNG-Tests. Das vollständige Peripherie-Demo
lief mit Kamera, Rauschen und Dropouts über 1.461 Ticks; alle 731 Folgeticks
ab Checkpoint 730 waren identisch. Die 294 Replay-Frames wurden zusätzlich
mit dem tatsächlich eingebetteten JavaScript im DOM-/Canvas-Testgerüst
ausgeführt. Der Taster-Snapshot-Fehler wurde reproduziert, behoben und mit
Regressionen einschließlich einer Fortsetzung im frischen Python-Prozess
abgesichert. Details und die weiterhin blockierte visuelle Browserprüfung
stehen in [VALIDATION.md](VALIDATION.md). Kein CI-Lauf wurde gestartet.

Für den realen Roboter fehlen weiterhin dynamische
Schall-/Lautsprecherphysik, TTS/PCM, PWM-/Servo-Kalibrierung,
Hardware-Transport, ein unabhängiger Watchdog und die
Bestätigung der HAT-Revision. Weder der PSI-Kern noch Claudes
Branch wurden geändert.
