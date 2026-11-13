# Akku, Betriebswärme und PSI-Bedürfnisse

Der Prototyp besitzt neben der Kinematik jetzt ein deterministisches elektrisches
und thermisches Modell. Es beschreibt eine **angenommene** 2S-Versorgung mit
Raspberry-Pi-artiger CPU-Last. Es ist noch kein am konkreten PiCrawler vermessenes
Modell. Alle Modellzahlen stehen in `EnergyConfig` und im Kalibrierprofil mit
Herkunft `assumed`; der Motivationskern wird nicht verändert.

## Was sich im Lauf verändert

- Akkuladung sinkt durch integrierten Stromverbrauch, auch beim Stehen.
- Bewegung und Blockade benötigen zusätzliche Servo-Leistung. Eine Blockade
  wird durch den konservativen Kollisions-/Arbeitsraumtest erkannt; es handelt
  sich nicht um berechnete Motor-Drehmomente.
- Last verursacht einen Spannungsabfall am Akku-Innenwiderstand.
- CPU-Last erwärmt die CPU; Wärme fließt an die Umgebung ab. Auch ein
  abgeschaltetes Modell kann im externen Simulator weiter abkühlen.
- Oberhalb der Drosselschwelle sinkt die angenommene dynamische CPU-Leistung.
  Die mechanische Sollgeschwindigkeit wird dadurch nicht willkürlich geändert.
- Leerer Akku, Last außerhalb der elektrischen Leistungsgrenze oder Unterschreiten
  der Modell-Abschaltspannung schalten die Versorgung bis `reset()` ab. Bewegung
  und `stand` sind dann gesperrt. Ein bei Abschaltung angebrochener Tick bewegt
  sich konservativ überhaupt nicht weiter.

`stop` bedeutet weiterhin Halten, nicht stromloses Ausschalten. `stand` ist eine
instantane kinematische Haltungsoperation; ihre Umlagerungsenergie wird noch
nicht berechnet. Ein Ladevorgang benötigt später eine modellierte Ladequelle;
es gibt keinen überall nutzbaren Ladebefehl.

## Standardannahmen

| Größe | Standard | Bedeutung |
|---|---:|---|
| Akkukapazität | 2 Ah | angenommener 2S-Akku |
| Leerlaufspannung leer / voll | 6,4 / 8,4 V | Endpunkte einer stückweise linearen Modellkurve |
| Innenwiderstand | 0,15 Ω | effektiver Pack-/Zuleitungswiderstand |
| Abschaltspannung | 6,0 V | lokale Schutzannahme, kein BMS-Nachbau |
| Versorgung / angenommene Reglergrenze | 5,0 / 6,5 V | einfacher Abfall unterhalb der Eingangsgrenze |
| Reglerwirkungsgrad | 90 % | gemeinsamer vereinfachter Verbrauchspfad |
| CPU Ruhe / dynamischer Anteil | 2,5 / bis 3 W | dynamischer Anteil proportional zur vorgegebenen CPU-Last |
| Kamera | 0,5 W | zusätzliche elektrische Last, falls aktiviert |
| Servo-Halten / Bewegung / Blockade | 0,8 / bis +8 / bis +12 W | Gesamtmodell, keine Einzelservo-Messung |
| Thermischer Widerstand / Wärmekapazität | 15 K/W / 10 J/K | CPU als ein thermischer Körper |
| Umgebung | 25 °C | über `set_environment()` veränderbar |
| Warnung / Drosselung / kritische Temperatur | 65 / 80 / 85 °C | lokale, austauschbare Schwellen |
| Dynamische CPU-Leistung beim Drosseln | 55 % | angenommener Faktor, kein Frequenzregler-Nachbau |

Die angenommene Unterspannungsschwelle der geregelten Versorgung beträgt 4,63 V.
Raspberry Pi dokumentiert diesen nominalen Wert mit ±5 % für viele Modelle;
die Zero-Reihe ist davon ausgenommen. Der konkrete Pi-Typ und die Versorgung
müssen später im Profil überprüft werden. Eine 80-°C-Schwelle ist hier ein
bewusstes generisches Experimentprofil, keine Behauptung identischer Firmware
auf allen Modellen.

## Rechenmodell und Einheiten

Die Leerlaufspannung `Voc(SOC)` benutzt normierte Stützstellen
`(0,0), (0.1,0.25), (0.5,0.55), (0.9,0.85), (1,1)` zwischen leerer und voller
Spannung. Die Kurve ist eine ersetzbare Annahme, insbesondere **keine** verlässliche
Umkehrabbildung einer real gemessenen Spannung auf Prozent.

Für angeforderte elektrische Batterieleistung `P` gelten

```text
Vterminal = Voc - I * R
P = Vterminal * I
ΔQ [Ah] = I * Δt [s] / 3600
SOCneu = SOCalter - ΔQ / Kapazität [Ah]
```

Der kleinere Stromzweig der quadratischen Gleichung wird numerisch stabil
gelöst. Für `R = 0` gilt `I = P / Voc`. Oberhalb `Voc²/(4R)` gibt es keinen
stationären Betriebspunkt; das Modell schaltet ab und gibt `power_limited` aus.
Die aufsummierte Lastenergie ist `P Δt`, der Akkuverlust `I²R Δt`. Zusammen
entsprechen sie `Voc I Δt`. Bei leer werdendem Akku ist die aktive Restzeit durch
die tatsächlich verbleibende Ladung begrenzt; negative Ladung oder kostenlose
Mehrenergie werden vermieden.

Für die CPU gilt

```text
dT/dt = (Pcpu - (T - Tumgebung) / Rtherm) / Ctherm
```

Pro konstantem Lastintervall wird die exponentielle Lösung verwendet. Die
CPU-Leistung wird bei Tickbeginn aus Last und Drosselzustand bestimmt; der neue
Temperaturzustand und die aktuellen Flags stehen am Tickende fest. Es gibt noch
keine thermische Hysterese und keine Wärmeleitung zwischen CPU, HAT, Servos und
Akku. Luftströmung, Zellalterung, SoC-Schätzfehler und Batterieselbsterwärmung
sind nicht modelliert.

`current_a`, `power_w`, `cpu_power_w` und `servo_power_w` im Tickcache sind
Intervallmittel; Akku- und Leerlaufspannung beschreiben den Last-Betriebspunkt
am Intervallanfang. Versorgungsspannung und Einschaltstatus gelten am
Intervallende, ebenso Temperatur und Ladung. Tick 0 zeigt den
anfänglichen stationären Verbrauch ohne bereits aufsummierte Energie.

## Welche Spannung ist welche?

`battery_voltage_v` bezeichnet den Akku, `supply_voltage_v` die angenommene
geregelte Pi-Versorgung. `core_voltage_v` bleibt im Simulator `None`, weil kein
DVFS-/Kernspannungsmodell vorliegt. `vcgencmd measure_volts core` misst laut
Raspberry-Pi-Dokumentation eine Kernspannung, **nicht** den Akkustand.

Beim Pi 5 kann `pmic_read_adc` unter anderem `EXT5V_V` liefern. PMIC-Ströme
erfassen weder alle direkt an 5 V angeschlossenen Verbraucher noch den
Gesamtbatteriestrom einschließlich Servos. Der Collector in `telemetry.py`
trennt deshalb diese Größen und lässt nicht verfügbare Werte offen.

Aktuelle Unterspannungs-/Drosselflags und historische Ereignisse bleiben
getrennt. Nur aktuelle Gefährdung erhöht den lokalen Schutzbedarf; ein alter
Flag hält ihn nicht dauerhaft hoch. Bei tatsächlicher Hardware liefert der
Collector Herkunft und Status pro Messwert; die simulierten Werte tragen
`source="simulated"`.

## Lokales Bedürfnisprofil

`need_signals(telemetry, config)` ist eine reine Funktion. `observe().internal`
und `frame()["needs"]` enthalten im aktivierten Simulator:

| Ausgabe | 0 | 1 | Zwischenschritt |
|---|---|---|---|
| `hunger` – Hunger/Energie | SOC ≥ 30 % | SOC ≤ 5 % | linearer Ladungsmangel |
| `damage` – Schaden/Integritätsbedarf | CPU ≤ 65 °C, keine Unterspannung | CPU ≥ 85 °C oder aktuelle Unterspannung | normierter thermischer Schutzbedarf |

`damage` ist ein Bedarf an körperlicher Unversehrtheit und behauptet keine
irreversible Beschädigung. Die Abbildung bleibt lokal vorgeschlagen; ihre
Skalierung auf die vorhandenen PSI-Zustände ist der spätere Integrationsschritt.
Durst/Nukleo und kognitive Bedürfnisse werden nicht ohne begründete Semantik
aus Strom oder Temperatur erzeugt.

Bei fehlendem SOC gibt die Funktion `hunger=None` aus. Eine vorhandene
Akkuspannung allein wird nicht zu einem erfundenen Ladestand umgerechnet.
Sind sowohl Temperatur als auch aktueller Unterspannungszustand unbekannt,
bleibt auch `damage=None`. Bei gemischter Verfügbarkeit ist `damage` das Maximum
der bekannten Risiken; unbekannte Risiken bleiben außerhalb dieser Abschätzung.

## Nutzung und Reproduzierbarkeit

```python
from psi_gw.body import Action
from psi_gw.body.picrawler import EnergyConfig, PiCrawlerSimBody, SimConfig

body = PiCrawlerSimBody(config=SimConfig(
    energy=EnergyConfig(battery_initial_soc=0.15, initial_cpu_temperature_c=78.0,
                        cpu_load=1.0)), seed=42)
body.act(Action("drive", {"forward_mps": 0.02}))
print(body.observe().sensors["telemetry"])
print(body.observe().internal)

# Experimentbedingungen für den nächsten Tick, keine Roboteraktion:
body.set_environment(cpu_load=0.1, ambient_temperature_c=20.0)
body.act(Action("stop"))
```

`set_environment()` ändert keinen Tick und schreibt keine alten Sensorwerte um.
Erst `act()` produziert die nächste Beobachtung. Beobachten, Darstellen und
Speichern ziehen keine Energie und keinen Zufall. Snapshot-Version 2 enthält
den elektrischen/thermischen Zustand, kumulierten Verbrauch, Umgebung und
Warnhistorie. Version 1 wird mit deaktiviertem Energiemodell migriert; so bleibt
die alte kinematische Fortsetzung erhalten. `EnergyConfig(enabled=False)` ist
auch für isolierte Vergleiche verfügbar.

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler --scenario resources --output picrawler-resources
PYTHONPATH=src python -m psi_gw.body.picrawler --scenario obstacles --output picrawler-obstacles
```

Die ressourcenarme Variante startet sichtbar mit 15 % Akku, 78 °C CPU und
100 % vorgegebener CPU-Last. Es läuft derselbe 72,75-s-Parcours, keine heimliche
Zeitbeschleunigung. Kamera, Ultraschall, Bewegungs-/Energiedaten und Wahrnehmung
stammen aus demselben Lauf. Die HTML-Ansicht ist eine interaktive Wiedergabe;
neue Experimente werden durch erneutes Ausführen des Python-Modells erzeugt.
Auch nach einer modellierten Stromabschaltung bleibt der externe Simulator
beobachtbar; das ist keine Zusicherung, dass ein stromloser echter Pi weiterhin
Telemetrie senden könnte.

## Quellen

- [Raspberry Pi: `vcgencmd`, Temperatur, Kernspannung und aktuelle/historische Flags](https://www.raspberrypi.com/documentation/computers/os.html#vcgencmd)
- [Raspberry Pi: Versorgung, nominale Unterspannungsschwelle und PMIC-Grenzen](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply-warnings)
- [SunFounder Robot HAT V4: Versorgung und Akku-ADC](https://docs.sunfounder.com/projects/robot-hat-v4/en/stable/hardware_introduction.html)
- [Lokaler Kalibrierplan und Herkunft jedes Parameters](CALIBRATION.md)
- [Architekturentscheidung für dieses isolierte Testbett](ADR-prototype.md)
