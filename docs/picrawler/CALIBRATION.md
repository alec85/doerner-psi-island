# PiCrawler: Kalibrierprofil und lesende Betriebsdatenerfassung

Das Paket hält Herstellerangaben, Modellannahmen und Messungen getrennt fest. Es
liefert ein versioniertes Profil für Geometrie, Kanalzuordnung, Kamera,
Entfernungssensor sowie elektrische und thermische Modellparameter. Der Collector
liest verfügbare Raspberry-Pi-Betriebswerte. Er bewegt keine Servos und importiert
weder `robot_hat` noch GPIO-/I²C-Bibliotheken.

## Benutzung

Im installierten Projekt oder mit `PYTHONPATH=src`:

```bash
python -m psi_gw.body.picrawler.calibration template --output calibration/picrawler.json
python -m psi_gw.body.picrawler.calibration collect --output calibration/telemetry.json
```

`template` erzeugt ein ausdrücklich unkalibriertes Profil. `collect` schreibt
einen separaten Messdatensatz; es überschreibt keine Annahmen im Profil. Vorhandene
Ausgabedateien werden nur mit `--overwrite` ersetzt. Beide Befehle benötigen
selbst kein `sudo` und installieren keine Hardwarepakete. Fehlt dem Benutzer der
Zugriff auf eine Messquelle, steht das im Ergebnis.

Auf einem Rechner, der nicht als Raspberry Pi identifiziert wird, startet der
Collector keine Firmwarekommandos und übernimmt auch nicht dessen CPU-Temperatur
als vermeintlichen Roboterwert. Fehlende Werte bleiben JSON-`null`.

## Was tatsächlich gemessen werden kann

| Wert | Quelle | Bedeutung |
|---|---|---|
| `cpu_temperature_c` | Thermal-Sysfs, ersatzweise `vcgencmd measure_temp` | SoC-Temperatur in °C; keine Servo- oder Umgebungstemperatur. |
| `pmic_temperature_c` | `vcgencmd measure_temp pmic` | PMIC-Temperatur auf unterstützten Pi-4-/Pi-5-Geräten. |
| `arm_frequency_hz` | `vcgencmd measure_clock arm` | Aktuelle ARM-Taktfrequenz. |
| `core_voltage_v` | `vcgencmd measure_volts core` | Core-/VC4-Spannung; ausdrücklich keine Akkuspannung. |
| `supply_voltage_v` | Pi-5-PMIC, Kanal `EXT5V_V` | Spannung der Pi-Versorgung. |
| `pmic_rails` | `vcgencmd pmic_read_adc` | Einzelne PMIC-Schienen. Ihre Ströme enthalten direkt aus 5 V versorgte Lasten nicht. |
| `battery_voltage_v` | explizit bereitgestellter Batterie-Reader | Robot-HAT-Akkuspannung oder eine separat kalibrierte Quelle. |

Grundlage sind die offiziellen
[Raspberry-Pi-Firmwarekommandos](https://www.raspberrypi.com/documentation/computers/os.html#vcgencmd)
und die
[Thermal-Sysfs-Beschreibung](https://www.raspberrypi.com/documentation/computers/config_txt.html).
Der Collector summiert PMIC-Ströme nicht zu einem vermeintlichen Akku- oder
Servostrom. Auch der PMIC-Kanalname `BATT_V` wird nicht als Robot-HAT-Akku ausgegeben.

`get_throttled` wird in zwei getrennte Gruppen zerlegt:

| Flag | Aktuell | Historisch aufgetreten |
|---|---:|---:|
| Unterspannung | Bit 0 | Bit 16 |
| ARM-Takt begrenzt | Bit 1 | Bit 17 |
| Throttling | Bit 2 | Bit 18 |
| Weiche Temperaturgrenze | Bit 3 | Bit 19 |

Ein historisches Unterspannungsbit bedeutet keinen gegenwärtigen Spannungseinbruch.
Bei fehlgeschlagenem Auslesen sind Flags `null`, nicht fälschlich `false`.
Unbekannte Bits bleiben zusätzlich im Rohwert erhalten.

### Robot-HAT-Akku

Beim dokumentierten Robot HAT V4 liegt die Akkuspannung über einen Teiler am
internen ADC-Kanal A4. Die nominelle Umrechnung lautet
`raw / 4095 × 3.3 V × 3`. Sie stammt aus der
[Hardwaredokumentation](https://docs.sunfounder.com/projects/robot-hat-v4/en/stable/hardware_introduction.html#adc).
Die aktuelle Herstellerbibliothek 2.5.x bietet dafür
[`robot_hat.device.get_battery_voltage()`](https://github.com/sunfounder/robot-hat/blob/2.5.x/robot_hat/device.py);
die ältere Funktion in `utils` leitet dorthin weiter.

Das Paket initialisiert die Bibliothek nicht automatisch. Ein bereits
eingerichteter Hardwareadapter kann seine lesende Funktion ausdrücklich als
`battery_reader` an `collect_telemetry()` übergeben. Die reine Funktion
`battery_voltage_from_adc()` konvertiert vorhandene Rohwerte ohne Hardwarezugriff.
Bei einer anderen HAT-Version müssen Messquelle, Referenzspannung und Teiler
erneut bestätigt werden.

Eine Momentanspannung bestimmt den Ladezustand nicht eindeutig. Deshalb liefert
der Collector `battery_state_of_charge = null`. Ohne zusätzliche Messhardware
bleiben auch Akkustrom, Servostrom und Gelenkrückmeldung unbekannt. Die
[PiCrawler-Hardwareübersicht](https://docs.sunfounder.com/projects/pi-crawler/en/latest/hardware/cpn_hardware.html)
listet keine IMU; ein später ergänztes IMU-Modul braucht einen eigenen Reader.
Eine Softwareliste zuletzt befohlener Servowinkel gilt nicht als Winkelmessung.

### Messdatenschema

Jeder Messwert enthält `value`, `unit`, `status`, `source` und `detail`.

- `measured`: erfolgreich aus der angegebenen Quelle gelesen.
- `unavailable`: die Quelle war nicht erreichbar oder nicht konfiguriert.
- `unsupported`: der Collector oder das identifizierte Gerät unterstützt die Quelle nicht.
- `error`: die Antwort war nicht als gültiger Messwert interpretierbar.

`observed_at` trägt einen ISO-Zeitpunkt mit Zeitzone. Für reproduzierbare Tests
sind Dateileser, Kommandoausführung, Batterie-Reader und Zeitpunkt injizierbar.
Die Firmwarekommandos verwenden Argumentlisten ohne Shell und haben ein Timeout.

## Herkunft im Kalibrierprofil

Profiltyp ist `psi_gw.picrawler.calibration`, Version `1`. Jeder Parameter besitzt
eine Einheit und folgende Herkunftsangaben:

```json
{
  "value": 8.32,
  "unit": "V",
  "provenance": {
    "kind": "measured",
    "source": "Messprotokoll des eigenen Roboters",
    "method": "Multimeter, drei Messungen im dokumentierten Betriebszustand",
    "measured_at": "2026-11-10T14:00:00+01:00"
  }
}
```

Die Zahl ist ein Schema-Beispiel, keine Messung dieses Projekts.
Erlaubte Herkunftsarten sind `manufacturer`, `assumed`, `measured` und `unknown`.
`measured` verlangt Quelle, Methode und Zeitpunkt mit Zeitzone. `unknown` verlangt
einen leeren Wert. Der Validator prüft außerdem Einheiten, Wertebereiche,
Kanal-Eindeutigkeit und zusammengehörige Grenzen. Er bestätigt die Form der
Aufzeichnung; die Richtigkeit einer eingetragenen Messung muss das Messprotokoll
belegen.

## Praktischer Kalibrierablauf

### 1. Zielgerät und Mechanik festhalten

Das Profil erhält einen Namen für das konkrete Exemplar. Raspberry-Pi-Modell,
HAT-Version, Kamera, Akku und Umbauten gehören ins Messprotokoll. Die drei
kinematischen Längen werden von Gelenkachse zu Gelenkachse erfasst; außerdem
werden die Abstände der Beinansätze geprüft. Die Startwerte 33/48/78 mm und
77 mm Körpermaß stammen aus dem
[Hersteller-SDK](https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler/picrawler.py)
und dessen
[Parameterbeschreibung](https://github.com/sunfounder/picrawler/blob/14a54bc1909d4ce8f73e95d0fc09514c974910ce/picrawler-control/references/api.md).
Die Interpretation des Körpermaßes als quadratischer Ansatzabstand muss am
Exemplar geprüft werden. Nominale Standhöhe und Ausladung sind Modellannahmen.

### 2. Verdrahtung und Winkel getrennt kalibrieren

Das Profil enthält die SDK-Beinreihenfolge rechts vorne, links vorne, links
hinten, rechts hinten. Die jeweiligen Kanaltripel sind 9/10/11, 3/4/5, 0/1/2 und
6/7/8. Gespeichert sind die SDK-Richtungszeichen und die SDK-Slotnamen
`beta`, `alpha`, `gamma`; eine eigene gemessene Verdrahtung darf diese ersetzen.

SDK-Kalibrierungs-Offsets bleiben zunächst `null`. Ebenso offen bleiben die
Zuordnung zu unseren Modellgelenken `yaw`, `hip`, `knee`, Richtung, Nullversatz und
gemessener Winkelbereich. Die mathematischen Gelenkwinkel der Simulation sind
**keine PWM-Winkel**. Das Profil führt keine automatische Umrechnung oder
Bewegung aus. Die Zuordnung wird erst nach einem dokumentierten Abgleich am
Exemplar vollständig eingetragen.

### 3. Kamera und Entfernungssensor vermessen

Kameraauflösung, Brennweiten `fx/fy`, Bildhauptpunkt `cx/cy`, Verzeichnung und
Montagepose werden gemeinsam erfasst. Ein bekanntes Kalibriermuster in mehreren
Positionen liefert die Daten für eine optische Kalibrierung. Die Kameraachsen
sind im Profil ausdrücklich definiert; Bildrechts und Bildunten unterscheiden
sich von den Körperachsen.

Das Startprofil beschreibt die synthetische 48×32-Pinhole-Kamera mit 60°
horizontalem Bildfeld. Es behauptet keine Kalibrierung einer OV5647-Kamera.
Vorhandene Verzeichnungsparameter werden gespeichert; der jetzige kleine
Renderer wendet noch keine Objektivverzeichnung an.

Für den Entfernungssensor werden bekannte Abstände wiederholt gelesen, darunter
Fälle ohne gültiges Echo. Offset, Streuung und Ausfallhäufigkeit werden mit
Messaufbau und Material dokumentiert. Die Simulationswerte für Rauschen und
Ausfälle sind zunächst Annahmen. Der ideale Strahl bildet keinen realen
Ultraschallkegel und keine Materialantwort nach.

### 4. Elektrik und Temperatur kalibrieren

Die Profilabschnitte `electrical` und `thermal` tragen dieselben Feldnamen wie
`EnergyConfig`. Alle Startwerte sind ausdrücklich angenommen: beispielsweise
2 Ah, 6.4/8.4 V, 0.15 Ω, 15 °C/W und 10 J/°C. Auch die Schwellen 65/80/85 °C
sind Parameter des Experiments und keine zugesicherten Grenzwerte des konkreten
Geräts.

Kapazität und Ladezustand brauchen eine passende Akkuangabe oder Referenzmessung.
Für einen Widerstandsansatz aus Spannungsabfall wird zusätzlich ein bekannter
Strom benötigt. Die Leistungsannahmen für CPU, Kamera und Servos werden anhand
geeigneter separater Messungen ersetzt; PMIC-Raildaten werden dabei nicht als
vollständige Leistungsbilanz behandelt.

Für das thermische Ersatzmodell werden Umgebungstemperatur, Verlauf der
CPU-Temperatur und zugehörige Verlustleistung aufgezeichnet. Stationäre
Temperaturerhöhung pro Watt ergibt den Widerstandsansatz; die zeitliche Reaktion
bestimmt zusammen damit die Wärmekapazität. Eine einzelne Temperaturmessung
reicht für beide Parameter nicht aus. Vorhandene historische Throttling-Flags
werden getrennt von aktuell aktiven Flags festgehalten.

## Verwendung im Simulator

```python
from psi_gw.body.picrawler.calibration import load_profile, profile_values
from psi_gw.body.picrawler.energy import EnergyConfig
from psi_gw.body.picrawler.kinematics import Geometry

profile = load_profile("calibration/picrawler.json")
geometry = Geometry(**profile_values(profile, "geometry"))
energy = EnergyConfig(
    **profile_values(profile, "electrical"),
    **profile_values(profile, "thermal"),
)
```

Das Laden setzt keine Hardwarewerte. Kamera-Intrinsik und vollständige Pose sind
ein Kalibrierprotokoll für die spätere Modellanpassung, kein direkter Ersatz für
die heutige `CameraConfig`. Änderungen der physikalischen Annahmen gehören in das
gespeicherte Versuchsprofil, damit die Ergebnisse nachstellbar bleiben.

## Prüfung

Die Tests arbeiten mit eingespeisten Dateiinhalten und Firmwareantworten. Sie
prüfen getrennte historische Flags, Pi-4-/Pi-5-Verfügbarkeit, falsche oder fehlende
Antworten, Einheiten, Batterieabgrenzung, Herkunftspflichten, Kanalzuordnung sowie
Profil-Rundläufe. Ein eigener Prozess prüft den Modul-CLI. Es wird kein realer
Raspberry Pi und kein physischer PiCrawler als vorhanden vorausgesetzt.
