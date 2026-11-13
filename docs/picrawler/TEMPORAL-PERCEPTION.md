# Zeitliche Wahrnehmung: Entfernungsverlauf und Farbregionen

`temporal.py` verarbeitet ausschließlich freigegebene Sensordaten mit
Erwerbszeit. Kein Body-/Weltzugriff, keine Objektidentität und kein globaler
Zufall. Die kognitive PSI-Wahrnehmung bleibt unverändert.

## Entfernung

Bis zu drei frische Messungen werden gespeichert. Aktuelle Nähe gewinnt stets
gegen die geglättete Historie. Die Entfernung wird um eine explizite Unsicherheit
und maximalen eigenen Vortrieb seit Acquisition konservativ vermindert.
Ein Ausfall darf höchstens 0,15 s mit `range_source=held_estimate` überbrückt
werden; danach bleibt die Entfernung unbekannt. Duplizierte/ältere Zeitstempel
erneuern weder Erwerbszeit noch Evidenz.

Nach einer Drehung verfällt die alte Strahlrichtung. Eine verzögerte Messung
von vor dieser Drehung darf auch dann nicht wiederverwendet werden, wenn ihr
Alter allein noch akzeptabel wäre. Erst eine neue passende Acquisition gibt
die Entfernung frei. Die Schätzung setzt begrenzte Annäherung und keine neu
auftauchenden beweglichen Hindernisse voraus. Sie ist keine Kollisionsgarantie.

## Farbregionen

Vorhandene HSV-Farbflächen werden zwischen neuen Bildern deterministisch über
Farbe und Bildnähe zugeordnet. Zuordnungen sind eins zu eins. Alter und eine
linear abfallende Konfidenz bleiben sichtbar; nach 0,30 s verfallen Tracks.
Die Anzahl ist auf 32 begrenzt. Duplizierte Bilder erhöhen keine Trefferzahl;
zukünftige oder veraltete Bilder erzeugen keine neuen gültigen Tracks.

Ein Track bezeichnet eine zugeordnete Bildregion, kein erkanntes reales Objekt.
Bei großen Sprüngen, ähnlichen Farben oder langer Verdeckung kann eine neue ID
entstehen. Eine kurz gehaltene Position ist keine Vorhersage verdeckter Bewegung.
Diese Tracks werden im Benchmark diagnostisch aufgezeichnet; sie sind noch
keine visuelle Navigationskarte oder neuronale Objekterkennung.

## Eigenständigen Störkorpus ausführen

```bash
python -m psi_gw.body.picrawler.perception_experiment \
  --output runs/temporal-perception --seeds 0 1 42
```

Erzeugt 18 gelabelte Distanzsequenzen und 12 Bildsequenzen: begrenztes Rauschen,
positive Ausreißer, kurze/lange Ausfälle, alte/duplizierte Messungen sowie
kurze Verdeckung, Verdunkelung und lange Bildausfälle. Rohdaten und Schätzungen
werden als synthetisch gespeichert. Die Labels dienen ausschließlich der
Auswertung, nicht der Wahrnehmung.

Die tatsächlich ausgeführte Serie auf `76c923b` ergibt für die drei Seeds:

| Distanzfall | Einzelmessung | Zeitliche Verarbeitung |
|---|---:|---:|
| Positive Ausreißer: falsche „frei“-Frames | 17 | 0 |
| Kurzer Ausfall: verfügbare Werte | 354 / 360 | 360 / 360 |
| Langer Ausfall: verfügbare Werte | 312 / 360 | 321 / 360 |

Die längere Verfügbarkeit endet ausdrücklich nach dem Haltefenster. Die
konservative Unsicherheit kann den mittleren Distanzfehler bei sauberem Rauschen
vergrößern; das ist im vollständigen Bericht sichtbar. Bei drei kurz verdeckten
Bildframes bleiben Regionen kurz verfügbar, ihre gehaltenen Positionen sind
jedoch teilweise falsch. Lange Ausfälle erzeugen nach Ablauf neue IDs.
Die Ergebnisse sind deskriptiv für diesen synthetischen Korpus und belegen
keine allgemeine Wahrnehmungsüberlegenheit auf realen Kamerabildern.

Snapshot und Wiederaufnahme sind für jede Distanzsequenz geprüft. Zusätzliche
Regressionen prüfen alte Strahlen nach Drehungen, doppelte Bilder, zukünftige
Zeitstempel, Einzelzuordnung und Ablauf. Bericht mit Rohdaten entsteht im
gewählten Ausgabeverzeichnis; archivierte Zusammenfassung folgt im Ergebnisordner
des Arbeitspakets.
