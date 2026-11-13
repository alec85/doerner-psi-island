# Hardware-Inventar: PiCrawler und Robot HAT V4 (Stand 2026-11-11)

Die konkrete Version des vom Nutzer besessenen HAT sowie eventuelle
Erweiterungen sind noch nicht am Gerät verifiziert. Dies ist die
**Herstellerkonfiguration PiCrawler + Robot HAT V4**, keine erfundene
Bestandsaufnahme des individuellen Roboters. Status:

- **integriert**: im existierenden kinematischen Simulator.
- **Peripheriemodell**: im separaten, deterministischen `peripherals.py`.
- **Telemetrie**: modelliert/lesend vorbereitet, hardwareabhängig.
- **frei/optional**: Anschlussmöglichkeit, KEIN Sensor/Aktuator ohne Hardware.
- **offen**: nicht als direkt messbar oder kalibriert behaupten.

| Gerät / Anschluss | Herstellerkonfiguration | Simulationsstatus | Grenze |
|---|---|---|---|
| 12 Beinservos (PWM P0–P11) | 12 Gelenkaktuatoren | integriert | Sollkinematik; keine realen Encoder, Kräfte oder PWM-Kalibrierung |
| Frontkamera | RGB-Kamera | integriert | synthetische Lochkamera, kein echtes Gesichtserkennungsmodell |
| Ultraschall | Distanzsensor | integriert | modelliertes Echo, Rauschen/Dropout |
| HAT Mono-Lautsprecher (I2S) | Audioausgabe | **Peripheriemodell** | `tone`, `sound`, `speak` als zeitliche Ereignisse; keine PCM/TTS-Audioerzeugung |
| User-LED (GPIO26) | steuerbare Anzeige | **Peripheriemodell** | ein/aus, optionaler angenommener Strombedarf |
| USR-Taster (GPIO25) | digitaler Eingang | **Peripheriemodell** | explizite Experimentinjektion |
| RST-Taster (GPIO16) | digitaler Eingang | **Peripheriemodell** | Eingabeereignis; setzt PSI nicht selbsttätig zurück |
| Zwei Akku-Anzeige-LEDs | spannungsabhängige Anzeige | **Peripheriemodell** | 0/1/2 Stufen aus Akkuspannung; keine Ladestandmessung |
| Akku-ADC A4 | Batteriespannung | Telemetrie | realer Reader benötigt konkrete HAT-Version; Spannung != SOC |
| Pi CPU-Temperatur, Firmware-Throttle | Betriebsüberwachung | integriert + lesender Collector | Raspberry-Pi-Modell prüfen |
| Pi Core/PMIC-Spannungen | teils auslesbar | lesender Collector | Kernspannung != Versorgung != Akku |
| Lautstärke, Klangspektrum, Schall im Raum | physikalische Akustik | offen | Audioausgabe wird NICHT vom Roboter als Gehör wahrgenommen |
| Mikrofon | nicht als PiCrawler V4 Kit-Komponente nachgewiesen | **nicht modelliert** | V5-HAT-Doku nennt Mikrofon; nur mit nachgewiesener Hardware ergänzen |
| ADC A0–A3 | freie Eingänge | frei/optional | kein angeschlossener Sensor angenommen |
| D0–D3 | digitale Ein-/Ausgänge | frei/optional | keine Sensor-/Aktuatorsimulation ohne Beschaltung |
| zusätzliche PWM/Motorports | Erweiterungsports | frei/optional | zwei Motorports nicht als verbauter Fahrantrieb behaupten |
| I2C, SPI, UART, Raspberry-Pi GPIO | Erweiterungsbusse | frei/optional | keine IMU, GPS, Mikrofon, Licht- oder Tastsensoren erfunden |
| HAT-Lade-/Power-Indikatoren | Statusleuchten | dokumentiert, offen | Ladeelektronik / externe Stromquelle nicht dynamisch modelliert |
| Akku-/Servo-Temperatur, Motorstrom, Encoder | keine gesicherte Messrückmeldung | offen | werden nicht aus der Bewegung als Sensorwerte erzeugt |

## Isoliertes API-Beispiel

```python
from psi_gw.body.picrawler.peripherals import PeripheralSim
hat = PeripheralSim()
hat.command("speak", text="Energie wird knapp", duration_s=2.0)
hat.command("led", on=True)
for _ in range(40):
    hat.advance(powered=True)  # ein Tick pro Body-Tick
print(hat.observe(battery_voltage_v=7.4))
print(hat.events)
```

Der `PiCrawlerSimBody` besitzt jetzt die optionale Konfiguration
`peripherals_enabled=True`. Dann laufen Audio/LED/Taster und Bewegung mit
demselben Tick, die zusätzliche angenommene Leistung wird genau einmal in
der Energiebilanz berücksichtigt, Version-3-Snapshots speichern den
laufenden Audiozustand, die Mock-Bridge transportiert Peripheriebefehle,
und der 3D-HTML-Replay zeigt Status sowie Ereignisse. Die alten
Bewegungsszenarien bleiben bei `peripherals_enabled=False` unverändert.

**Nicht implementiert:** hörbare PCM/TTS-Ausgabe, Schallausbreitung,
echte GPIO-/I2S-Ansteuerung und eine vom Roboter hörbare Wahrnehmung.
Details: [Peripherieintegration](PERIPHERAL-INTEGRATION.md).

## Dokumentation / Versionswarnung

- [PiCrawler Kit – Robot HAT V4](https://docs.sunfounder.com/projects/pi-crawler/en/latest/hardware/cpn_robot_hat.html)
- [Robot HAT V4 – vollständige Hardware und Pinbelegung](https://docs.sunfounder.com/projects/robot-hat-v4/en/latest/robot_hat_v4/hardware_introduction.html)
- [Robot HAT V5 – andere Version, Mikrofon nicht übertragbar](https://docs.sunfounder.com/projects/robot-hat-v4/en/latest/robot_hat_v5/hardware_introduction.html)

Vor Hardwarezugriff muss anhand der Aufschrift bzw. des HAT-Boards
die genaue Revision bestätigt werden.
