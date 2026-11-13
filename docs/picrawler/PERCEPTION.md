# Sensorbasierte Vorverarbeitung

`psi_gw.body.picrawler.perception` ist eine kleine, separat testbare Grundlage für die spätere Wahrnehmungsanbindung. Sie verarbeitet **RGB-Pixel, Ultraschallmessungen und Zeitstempel**. Das Modul erhält keine Welt, Objektliste, Position, Kollision oder Trefferidentität des Simulators. Es verändert weder den Körper noch den PSI-Zustand und benötigt keine zusätzliche Abhängigkeit.

Die Ergebnisse sind einfache Merkmale. Eine rote Farbfläche ist keine erkannte Nahrungsquelle; eine normierte Hindernisnähe ist keine Kollisionswahrscheinlichkeit. Die Zuordnung zu Situationen, Objekten, Handlungen und Bedürfnissen bleibt Aufgabe des späteren Wahrnehmungsadapters.

## Benutzung

```python
from psi_gw.body.picrawler.perception import perceive

observation = body.observe()
time_s = observation.tick * body.config.dt_s
features = perceive(
    observation.sensors,
    now_s=time_s,
    sample_time_s=time_s,  # explizit: dieses Body-Modell tastet synchron ab
)
recorded_frame["perception"] = features.to_dict()
```

Für den aktuellen Simulator ist der explizite gemeinsame Abtastzeitpunkt geeignet. Eine spätere Bridge liefert dagegen möglichst **pro Sensor den ursprünglichen Aufnahmezeitpunkt**:

```python
sensors = {
    "ultrasonic": {
        "distance_m": 0.24,
        "status": "ok",
        "captured_at_s": 12.10,
    },
    "camera": {
        "encoding": "rgb8",
        "rgb": rgb_pixels,
        "captured_at_s": 11.95,
    },
}
features = perceive(sensors, now_s=12.20)
```

`now_s` und `captured_at_s` müssen sich auf dieselbe Zeitbasis beziehen. Die spätere Bridge muss die Zeitbasen von Pi und PC ausdrücklich zuordnen. Der Empfangszeitpunkt ersetzt keinen alten Aufnahmezeitpunkt. `sample_time_s` ist ein Fallback für Daten, deren synchroner Abtastzeitpunkt tatsächlich bekannt ist; ein vorhandener Sensorzeitstempel hat immer Vorrang.

## Gültigkeit und Alter

Jeder Sensor erhält getrennte Angaben:

| Feld | Bedeutung |
|---|---|
| `valid` | Der Messwert bzw. das Bild ist formal gültig. Beim Echo muss außerdem der Sensorstatus `ok` sein. |
| `usable` | Die Daten sind gültig, der Aufnahmezeitpunkt ist bekannt und das maximale Alter ist eingehalten. |
| `freshness` | `fresh`, `stale`, `unknown`, `future` oder `invalid`. |
| `age_s` | Alter des Samples, soweit es sinnvoll berechnet werden kann. |
| `status` | Grund, z. B. `ok`, `dropout`, `missing_echo`, `invalid_image` oder `timestamp_stale`. |
| `stale` | Im Ergebnis von `to_dict()`: `true`/`false` für bekannte Frische, sonst `null`. |

Die Standardgrenze für das Alter beträgt **0,30 s**. Das ist eine konfigurierbare Testannahme, keine aus dem realen PiCrawler abgeleitete Frist. Zukünftige, negative, nicht endliche oder fehlende Zeitstempel werden nicht stillschweigend repariert. Eine numerische Toleranz von 1 ns verhindert lediglich Rundungsartefakte an gleichen Zeitpunkten.

Ein altes gültiges Echo bleibt als Diagnosewert sichtbar, liefert aber keine verwendbare Hindernisnähe. Ein altes gültiges Bild liefert keine Farbflächen. **Ein fehlendes oder veraltetes Echo bedeutet nicht, dass der Weg frei ist.**

## Distanzmerkmale

`range_features()` verarbeitet eine einzelne Messung. Der Standardbereich beträgt 0,02–4,0 m. Messwerte außerhalb dieses Bereichs, `None`, nicht endliche Zahlen und Fehlerstatus bleiben ungültig.

Die Hindernisnähe wird aus frischen Messungen berechnet:

\[
p=\operatorname{clip}\left(\frac{d_\mathrm{fern}-d}{d_\mathrm{fern}-d_\mathrm{nah}},0,1\right).
\]

Die Standardmarken sind `near_m=0.10` und `far_m=0.50`. Bei höchstens 10 cm ist die Nähe 1, bei mindestens 50 cm 0. Dazwischen wird linear interpoliert. Diese Marken dienen dem Testbett und lassen sich über `PerceptionConfig` ändern. Wenn die Messung nicht verwendbar ist, ist `proximity=None`, nicht 0.

### Explizites Fenster gegen Ausreißer

`median_range_window(samples, now_s=..., minimum_samples=3)` bietet eine zweite, ebenfalls zustandslose Basisfunktion. Die Aufrufstelle verwaltet das Fenster; jedes Sample muss einen Aufnahmezeitpunkt tragen. Ungültige, alte und zukünftige Samples werden ausgeschlossen. Bei zu wenigen verwendbaren Samples gibt es kein Ergebnis. Das gemeldete Alter entspricht dem ältesten beitragenden Sample.

Der Median dämpft einzelne Ausreißer. Er kann zugleich eine schnelle neue Distanzänderung verzögern. Er ist deshalb eine ausdrücklich wählbare Vorverarbeitung und ersetzt die unveränderten Rohmessungen nicht.

## Farbflächen aus RGB

`camera_features()` akzeptiert rechteckige Bilder mit drei ganzzahligen Kanälen von 0 bis 255 und dem Encoding `rgb8`. Eine angegebene Breite/Höhe muss zu den Pixeln passen. Die Standardgrenze von 262.144 Pixeln hält diese einfache Basisfunktion klein; ein echtes hochauflösendes Kamerabild kann eine vorgelagerte, explizite Verkleinerung benötigen.

Die Implementierung konvertiert RGB nach HSV, filtert dunkle und schwach gesättigte Pixel und sucht anschließend **vierfach zusammenhängende** Regionen. Die Standardbänder sind Rot, Gelb, Grün und Blau. Alle Schwellen sind konfigurierbar:

| Parameter | Standard | Bedeutung |
|---|---:|---|
| `minimum_saturation` | 0,35 | Mindest-Farbsättigung |
| `minimum_value` | 0,25 | Mindest-Helligkeit im HSV-Modell |
| `minimum_blob_pixels` | 4 | Kleinste ausgegebene zusammenhängende Fläche |
| `maximum_blobs` | 64 | Obergrenze der ausgegebenen Flächen |

Die Bänder verwenden einen kreisförmigen Farbtonabstand. Rot funktioniert dadurch auf beiden Seiten des Übergangs 0/1. Bei überlappenden benutzerdefinierten Bändern entscheidet deren angegebene Reihenfolge. Die Flächen werden nach Pixelzahl absteigend und bei Gleichstand nach Farbe und Bildposition sortiert.

Jede Fläche enthält:

- `color`: Name des Farbbandes, keine Objektklasse.
- `pixel_count` und `area_fraction`: Pixelzahl und Anteil am gesamten Bild.
- `centroid_x`, `centroid_y`: normierter Schwerpunkt aus Pixelmittelpunkten; x läuft von links nach rechts, y von oben nach unten.
- `bounds`: normierte linke/obere/rechte/untere Bildkante. Die rechten und unteren Maxima sind exklusive Kanten; ein Vollbild hat die Grenzen `(0, 0, 1, 1)`.

Eine Verdeckung kann eine sichtbare rote Fläche in zwei Regionen teilen. Die Basisfunktion behauptet keine gemeinsame verdeckte Objektidentität. Schatten, Beleuchtung, Kamerafarbabgleich und Bildrauschen verändern die Ergebnisse; es gibt weder ein trainiertes Modell noch eine belegte Erkennungsleistung auf Hardwareaufnahmen.

## Replay und Betriebswerte

Die HTML-Ansicht zeigt optional die gespeicherten Merkmale: Nutzbarkeit/Alter von Echo und Bild, Hindernisnähe sowie Farbfläche, Schwerpunkt und Begrenzungsrechteck. Die Markierungen lassen sich abschalten. Die ursprünglichen RGB-Daten bleiben in der Aufzeichnung erhalten.

Davon getrennt zeigt das Replay die optionalen Felder `telemetry` und `needs`:

- Akku- und Versorgungsspannung, Ladestand, CPU-Temperatur, Strom und Leistung.
- CPU-Kernspannung nur, wenn ein Wert aufgezeichnet wurde; `None` erscheint ausdrücklich als nicht modelliert/erfasst.
- Gespeicherte Flags für Unterspannung, Temperaturdrosselung, Leistungsbegrenzung und leeren Akku sowie optionale historische Flags.
- **Hunger (Energie)** und **Schaden (therm./elektr.)**, jeweils von 0 „kein Bedarf“ bis 1 „maximal“.
- Drei Verlaufskurven bis zum ausgewählten Zeitpunkt. Fehlende Messwerte bleiben Lücken.

Die Kennzeichnung `source="simulated"` bleibt sichtbar. Hunger und Schaden werden als **lokale vorgeschlagene Abbildung** gekennzeichnet; die Darstellung greift nicht in den PSI-Kern ein. Das Replay berechnet weder den thermisch-elektrischen Zustand noch die Wahrnehmung erneut, sondern liest ausschließlich die aufgezeichneten Werte. Alte Aufzeichnungen ohne diese Felder bleiben nutzbar.

## Reproduzierbare Testfälle

`tests/picrawler/test_perception.py` enthält die wiederverwendbaren Generatoren `rgb_image()` und `sensor_scenarios()`. Jeder Aufruf liefert neue Rohdaten. Die Fälle umfassen:

| Fall | Erwartete Aussage |
|---|---|
| Fehlendes Echo / Dropout | Kein verwendbarer Nähewert; keine Interpretation als freier Weg. |
| Messrauschen mit Ausreißer | Das explizite frische Fenster liefert einen reproduzierbaren Median. |
| Verdeckte Farbfläche | Sichtbare getrennte Regionen bleiben getrennt; keine versteckte Objektidentität. |
| Mehrere Farben | Fläche, Schwerpunkt und Begrenzung sind analytisch prüfbar. |
| Verzögerte Frames | Alte Pixel/Echos liefern keine verwendbaren aktuellen Merkmale. |
| Geänderte Weltmetadaten | Gleiche Sensorsamples ergeben identische Merkmale. |

Zusätzliche Prüfungen decken Hue-Übergänge, diagonale Nachbarschaft, fehlerhafte Bilder, unbekannte Zeitstempel und die Veränderungsfreiheit der Eingaben ab. Replay-Tests führen das tatsächlich eingebettete JavaScript in einer DOM-/Canvas-Testumgebung aus, wenn Node verfügbar ist. Das prüft Datenfluss, Bedienzustände und endliche Projektionskoordinaten; es ist kein Ersatz für eine visuelle Browserprüfung.

```bash
PYTHONPATH=src python -m pytest tests/picrawler/test_perception.py tests/picrawler/test_replay.py
```

## Spätere Anbindung

Die nächsten klaren Anschlussarbeiten sind eine Zeitzuordnung für die Hardware-Bridge, Kalibrierung der Sensorgrenzen und eine Vereinbarung darüber, wie visuelle/räumliche Merkmale zu PSI-Schemata werden. Ein neuronales Bildmodell kann die Farbflächenbasis später ergänzen oder ersetzen. Rohsensoren, Vorverarbeitung und Kognition bleiben getrennt prüfbar.
