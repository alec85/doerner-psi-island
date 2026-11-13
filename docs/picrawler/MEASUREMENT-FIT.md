# PiCrawler: Messdatenimport und Modellschätzung

Die Werkzeuge lesen Dateien, greifen nicht auf Hardware zu und ändern keine
laufende Simulation. Der bestehende Collector bleibt unverändert; einzelne
Telemetrie-Snapshots liefern nicht automatisch die benötigten Referenzgrößen.

## Daten und Aufruf

| Typ | CSV-Spalten zusätzlich zu `partition` | Geschätzte Größen |
|---|---|---|
| `battery_load` | `open_circuit_voltage_v,current_a,battery_voltage_v` | Innenwiderstand in Ω |
| `thermal` | `time_s,cpu_temperature_c,ambient_temperature_c,cpu_power_w` | Thermisches R in °C/W, C in J/°C |
| `range` | `reference_m,distance_m` | Additiver Offset, Standardabweichung, Ausfallquote |

`partition` ist ausdrücklich `train` oder `validation`. Nur leeres `distance_m`
ist als fehlendes Echo erlaubt. Andere Leerwerte, zusätzliche/doppelte Spalten,
falsche Einheiten, boolesche Zahlen, NaN/Inf und doppelte JSON-Schlüssel werden
abgewiesen. JSON trägt Typ `psi_gw.picrawler.measurements`, Version 1,
`kind`, `origin`, `source`, `method`, `device`, `recorded_at`, `units`, `samples`.
Der Zeitpunkt braucht eine ISO-Zeitzone; Einheiten sind im Schema festgelegt.

```bash
python -m psi_gw.body.picrawler.calibration_fit import-csv \
  --input eigene-akku-messung.csv --output runs/akku-messdaten.json \
  --kind battery_load --origin measured --source 'Messprotokoll Akku A' \
  --method 'Referenzspannung und Laststrom separat erfasst' \
  --device 'eigener-PiCrawler-A' --recorded-at '2026-11-11T12:00:00+01:00'

python -m psi_gw.body.picrawler.calibration_fit fit \
  --input runs/akku-messdaten.json --output runs/akku-fit.json \
  --profile-output runs/akku-profil.json
```

Erster Aufruf: Platzhalter für eigene Messdaten. Die mitgelieferten Beispiele
sind synthetisch und müssen als `--origin synthetic` importiert werden.
Ohne `--profile-output` entsteht nur ein Bericht. Mit `--base-profile` lässt
sich ein bestehendes Profil ergänzen; es erfordert `--profile-output`.
Ausgaben müssen neue, unterschiedliche Dateien sein. Eingaben, bestehende
Dateien und unabhängige Profilparameter werden nicht überschrieben.

## Verfahren und Grenzen

**Akku:** Kleinste Quadrate für `V_terminal = V_open − I × R`, ohne freien Offset.
Mindestens zwei positive und hinreichend verschiedene Lastströme sind nötig.
Leerlaufwert und Laststrom müssen als bekannte Referenzen geliefert werden.
Es wird kein SOC aus einer Momentanspannung bestimmt. PMIC-Schienenströme
werden nicht als vollständiger Akkustrom interpretiert.

**Temperatur:** Eingänge einer Zeile gelten bis zur nächsten Zeitmarke konstant.
Die exakte Intervalllösung mit `τ = R × C` lautet:

`T_next = T_ambient + P_cpu × R + (T_start − T_ambient − P_cpu × R) × exp(−dt/τ)`.

Für jedes τ wird R linear geschätzt; eine deterministische Suche über 0,1 bis
100.000 s bestimmt τ. C folgt aus τ/R. Randlösungen, ungeeignete Transienten
und nahezu kollineare Parametersensitivitäten werden abgewiesen. Erforderlich
sind mindestens 0,5 °C Temperaturvariation, vier Trainingsintervalle und ein
Prüfintervall. Zeiten müssen streng steigen. Intervalle über eine
Partitionsgrenze gehen weder in Schätzung noch Fehlerwerte ein.

Der Bericht trennt Ein-Schritt- und fortlaufende Vorhersage. Letztere verwendet
nur den ersten Messwert eines zusammenhängenden Abschnitts als Start und setzt
dann eigene Vorhersagen fort. Eine Änderung ausschließlich der Prüftemperaturen
verändert die Parameter nicht; dies ist als Regression geprüft.

**Entfernung:** Mittleres `distance_m − reference_m` liefert den Offset,
Stichproben-Standardabweichung die Streuung um diesen Offset. Fehlende Echos
zählen separat. Mehrere Referenzabstände und gültige Prüfechos sind erforderlich.
Es wird keine Gaußverteilung oder physische Echo-Kegelform vorausgesetzt.

Alle Berichte enthalten Einheiten, Dataset-SHA-256, Herkunft, getrennte
Trainings-/Prüfstatistiken und beobachtete/vorhergesagte Werte. Bias, MAE,
RMSE und maximaler Fehler sind deskriptiv; es gibt keine Konfidenzintervalle
oder Hardware-Gütebescheinigung. Messfehler der Eingänge, Drift und Modellfehler
werden nicht automatisch korrigiert. Akzeptanzgrenzen für echte Messungen
müssen vor dem Versuch festgelegt werden.

## Profil-Export

Der bestehende Profilvertrag bleibt Version 1. Übernommen werden Innenwiderstand,
thermisches R/C bzw. Ausfallwahrscheinlichkeit. Entfernungsoffset und empirische
Standardabweichung bleiben im Bericht: Das Strahlmodell besitzt keinen
gleichwertigen Bias-Parameter; Rausch-Halbbreite ist keine Standardabweichung.
Es erfolgt keine stillschweigende Umrechnung oder Änderung des Simulators.

Synthetische Ergebnisse erhalten Herkunft `assumed` und keinen Messzeitpunkt.
Bei `origin=measured` lautet die Herkunft `measured`; die Methode kennzeichnet
Werte ausdrücklich als aus Trainingsdaten geschätzt und nennt den Dataset-Hash.
Die Software bestätigt die Dokumentationsform, nicht die Wahrheit einer vom
Benutzer als Messung bezeichneten Datei.

## Ausführbares synthetisches Abnahmeexperiment

```bash
python -m psi_gw.body.picrawler.calibration_experiment \
  --output runs/picrawler-fit-fixture --seed 42
```

Erzeugt unabhängige analytische Vorwärtsdaten, CSV-/JSON-Rundläufe, drei
Schätzberichte, ein ausdrücklich synthetisches Profil und `summary.json`.
Das Ziel muss neu oder leer sein. Exitcode 1: Prüfgrenze verletzt.
Vorab im Code festgelegte Grenzen: höchstens 8 % R-/C-Parameterfehler, 2 mm
Offsetfehler; Validierungs-RMSE höchstens 5 mV, 0,15 °C bzw. 6 mm.
Das sind technische Fixture-Prüfungen, keine statistischen Äquivalenztests.

Tatsächlich ausgeführt auf `b6a38e6`: Seeds 0/1/42, alle bestanden.
Rauschfreie Vorgaben derselben Seeds wurden zusätzlich in Tests mit
`rel=1e-6, abs=1e-9` wiedergewonnen.

| Größe, Seed 42 mit Rauschen | Vorgabe | Geschätzt |
|---|---:|---:|
| Innenwiderstand | 0,230000 Ω | 0,229823 Ω |
| Thermischer Widerstand | 12,000000 °C/W | 12,002104 °C/W |
| Wärmekapazität | 18,000000 J/°C | 18,027370 J/°C |
| Entfernungsoffset | 12,000 mm | 11,961 mm |

| Zurückgehaltene Daten | RMSE, Seed 42 |
|---|---:|
| Akkuspannung | 1,253 mV |
| Temperatur, fortlaufende Vorhersage | 0,009914 °C |
| Entfernung nach Offsetkorrektur | 2,427 mm |

Thermisch: 100 Trainings- und 59 Prüfintervalle, ein Grenzintervall ausgeschlossen.
Entfernung: 50 Trainingssamples mit sechs Ausfällen, 30 Prüfsamples mit drei.

Archivierte [Rohdaten, CSV, Berichte und Profil für Seed 42](validation-2026-11-11/synthetic-seed42/summary.json)
liegen neben der verlinkten Zusammenfassung. Alle Seeds/Runtime-Fingerprints:
[results.json](validation-2026-11-11/results.json).
Gesamtabnahme: 767 Tests, davon 131 neu. Keine Hardwaremessung behauptet.
Belastungsmatrix: [VALIDATION-TOOLS.md](VALIDATION-TOOLS.md).
