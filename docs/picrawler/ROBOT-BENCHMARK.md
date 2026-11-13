# Geschlossener PiCrawler-Benchmark

Issue #37, Branch `codex/37-picrawler-benchmark`, Draft-PR #38 auf PR #36.
Vorab festgelegter Plan: [ADR-closed-loop.md](ADR-closed-loop.md), Commit `3248fee`.
Controller und Auswertung wurden bei `76c923b` für die Serien eingefroren.
Keine Parameteränderung nach Beginn der zurückgehaltenen Prüfläufe.

## Was hier tatsächlich gesteuert wird

Ein Controller erhält pro Tick eine abgetrennte `Observation`: Ultraschall,
gegebenenfalls RGB, ihre Erwerbszeiten und die lokalen Hunger-/Schadensinputs.
Hinzu kommt die zuletzt tatsächlich ausgegebene Aktion. Er bekommt keine Welt,
Körperposition, Hindernisnamen, Kollision, Zielkoordinate oder Erfolgsmeldung.
Eine ausdrückliche Positivliste verwirft zusätzliche Debugfelder.
Diese Trennung ist ein Datenvertrag für vertrauenswürdige Referenzcontroller,
keine Betriebssystem-Sandbox für fremden Code.

Beide Controller sind technische Baselines, kein PSI und kein Lernverfahren:

- `reactive`: Einzelmessung, vorwärts bei ausreichender Distanz, sonst drehen;
  unbekanntes Echo führt zum Halt.
- `memory`: konservative Entfernungshistorie, kurze Überbrückung, Ausweichphase,
  begrenztes Umfahren und Rückkehr zur geschätzten Ausgangsrichtung. Richtung
  entsteht aus eigenen Befehlen, ausdrücklich nicht aus gemessener Odometrie.

Beide halten bei Hunger ≥ 0,85 bzw. Schaden ≥ 0,95 und bleiben bis zum Reset
im Energiehalt. Übergänge können eine gezählte `stand`-Aktion auslösen.
Ihre instantane Kinematik ist keine reale Servo-/Haltungsdynamik.
Zeitliche Farbregionen laufen in der Memory-Baseline als Diagnose mit; sie
liefern weder Tiefen noch eine visuelle Navigationskarte.

## Parcours, Störungen und Aufgaben

Vier seeded Familien: offen, versetzte Hindernisse (`slalom`), Sackgasse
(`dead_end`), Tor (`gate`). 0,15-m-Rasterzellen werden mit der Körperhülle geprüft;
auch diagonale Verbindungen müssen den kontinuierlichen Sweep-Test bestehen.
Vom Start muss ein freier Rasterweg zur Fortschrittsregion existieren.
Das beweist geometrische Erreichbarkeit, nicht Erreichbarkeit durch eine
bestimmte Policy innerhalb ihres Zeitbudgets.

Beim Tor kann Tick 300 ein Hindernis einsetzen. Falls dadurch die aktuelle
Körperposition überdeckt würde, wird das Ereignis als `skipped_occupied`
protokolliert; kein Körper wird teleportiert. Die Karte im Replay stammt
pro Frame aus der tatsächlich aufgezeichneten Welt. Andere Läufe bleiben
mit dem bisherigen statischen Replayformat kompatibel.

| Aufgabe | Vorab festgelegtes Kriterium |
|---|---|
| `progress` | Körperzentrum erreicht x ≥ 0,35 m, höchstens 900 Ticks |
| `explore` | Mindestens 8 % der anfangs erreichbaren Rasterzellen besucht, höchstens 900 Ticks |
| `energy_stop` | Spätestens zwei Entscheidungen nach dem Risikosignal halten und zehn aufeinanderfolgende Haltticks; höchstens 30 Ticks |

Zusätzlich: höchstens 1 % Kontakt-Ticks, keine Arbeitsraumverletzung,
kein verspäteter Energiehalt oder unerwarteter Stromausfall. Das Erreichen
eines Ziels allein ist deshalb noch kein Erfolg. Die Kontaktgrenze bewertet
den konservativen Körper-Sweep, keine berechneten Kontaktkräfte.

| Sensorprofil | Verhalten |
|---|---|
| `nominal` | Idealer Entfernungssensor, synthetisches RGB |
| `noisy` | 3 mm Rausch-Halbbreite, 8 % Echoausfälle |
| `delayed` | Entfernung vier Ticks verzögert; alle 17 Ticks zusätzlich ältere Acquisition; ursprünglicher Zeitstempel bleibt erhalten |

Kamera: 24×16 Pixel, Erwerb alle fünf Ticks (4 Hz bei dt = 0,05 s).
Die Körperaufnahme kann intern häufiger berechnet werden; die Policy erhält
nur die freigegebenen Acquisitions. Hunger/Schaden sind in dieser Matrix frisch;
die Störung betrifft Kamera/Ultraschall. Die gesamte Controller-Prozessstörung
wird separat geprüft.

## Serien ausführen

Installation: `python -m pip install -e '.[dev]'`; keine neue Abhängigkeit.

```bash
python -m psi_gw.body.picrawler.robot_benchmark \
  --output runs/robot-development --seeds 0 1 --progress

python -m psi_gw.body.picrawler.robot_benchmark \
  --output runs/robot-validation --split validation --progress
```

Entwicklungsseeds sind 0..3, Prüfseeds 1000..1003; Mischen wird abgewiesen.
Erster Befehl: 144 Fälle. Zweiter Befehl: 288 Fälle. Beide vergleichen dieselben
Umgebungen paarweise zwischen Policies. Die 900-Tick-Grenze darf für technische
Kurztests mit `--max-ticks` verkürzt werden; solche Ergebnisse tragen
`preregistered_budget=false` und sind keine vollständige Aufgabenabnahme.

```bash
# Exakt dieselbe Fallliste/Revision/Runtime wiederaufnehmen:
python -m psi_gw.body.picrawler.robot_benchmark \
  --output runs/robot-validation --split validation --progress --resume

# Lokalen Kindprozess anstelle des direkten Controllers verwenden:
python -m psi_gw.body.picrawler.robot_benchmark --output runs/robot-process \
  --seeds 0 --families open --sensors nominal --tasks energy_stop --execution process
```

`manifest.json` hält Fälle, Quellfingerprints, Revision und Runtime fest.
Fallberichte werden atomar gespeichert und vor dem Überspringen geprüft.
Beschädigte oder abweichende Daten brechen die Wiederaufnahme ab.
Ohne `--resume` muss das Ziel neu/leer sein. `--progress` schreibt Zwischenstände
nach stderr. Exitcode 0 bedeutet, dass der Benchmark ausgeführt wurde;
`success=false` bleibt eine korrekt gemessene Aufgaben-Nichterfüllung.
Programm-/Dateifehler dürfen nicht als negative Versuchsergebnisse verschwinden.

## Checkpoints und Replays

Logischer Snapshot: Body, Controller einschließlich Sensorhistorie, verzögerte
Messwertpuffer, ursprünglicher Parcours, tatsächliche Welt, Auswertung, vorherige
Aktion und fortlaufender Trace-Hash. Die Fortsetzung vergleicht nach jedem Tick
die vollständige JSON-semantische Zustandsdarstellung.

Standardmäßig prüft die Suite beim ersten Seed alle Tor-/Policy-/Sensor-/Task-
Kombinationen. `--verify-checkpoints` prüft sämtliche Episoden. Zusätzlich testen
Regressionen die Fortsetzung in frischen Python-Prozessen aus anderem
Arbeitsverzeichnis. Ein Kamerabild oder gleicher Endpunkt allein genügt nicht.

`--record-examples` erzeugt für den ersten Seed die nominalen Fortschrittsläufe
aller Familien/Policies mit `result.json`, `course.json`, `trace.json`, optionalem
`checkpoint.json` und `replay.html`. Der gesamte Beispielordner wird erst nach
vollständigem Export veröffentlicht; ein fehlgeschlagener Export hinterlässt
keinen halbfertigen Ordner. Die unterbrochene Ausgabe und der erfolgreiche
erneute Versuch sind als Regression ausgeführt.

3D, Kamerabild und Distanzstrahl zeigen Körperaufnahmen zum gespeicherten Tick.
Die gegebenenfalls verzögerten Controllerwerte stehen separat in den
Entscheidungsfeatures mit Alter/Quelle und im Input-Hash. Das Replay behauptet
nicht, das gezeigte aktuelle Körperbild sei ein frisches Policy-Eingangsbild.
Eine visuelle Browserabnahme ist in dieser Umgebung weiterhin blockiert;
das tatsächliche eingebettete JavaScript wird im DOM-/Canvas-Testgerüst geprüft.

## Auswertung ohne nachträgliche Auswahl

Erfasst werden Erfolg/Grund, Budget, Weg, Energie, besuchte/erreichbare Zellen,
Kontakte, Arbeitsraumgrenzen, Unbekannt-/Überbrückungs-Ticks, Aktionswechsel,
Postureresets und Energie-Reaktionszeit. Eine zusätzliche Diagnose zählt
Körperkontakte trotz nach vorne ausreichend weiter Entfernungsmessung.
Die maximale Abweichung der befehlsintegrierten Richtung von der Weltwahrheit
wird ausschließlich in der Evaluation berechnet.
Diese Diagnose vergleicht die Pose nach der Body-Aktion mit der zuletzt
gespeicherten Entscheidungsschätzung. Sie enthält daher bis zu einen Tick
Aktionslatenz und ist keine isolierte Odometrie-Driftmessung.

Controllervergleiche sind deskriptiv. Energieunterschiede werden nur für
paarweise erfolgreiche Aufgaben ausgewiesen; Fehlerfahrten werden nicht
als besonders effizient dargestellt. Es gibt keine Überlegenheits- oder
PSI-/Paper-Hypothese und keine nachträgliche Lockerung der Erfolgskriterien.
Ergebnisbericht und eigene Übergabe werden mit den abgeschlossenen Serien
gespeichert. Zeitliche Wahrnehmung: [TEMPORAL-PERCEPTION.md](TEMPORAL-PERCEPTION.md).
Prozessgrenze: [CONTROLLER-PROCESS.md](CONTROLLER-PROCESS.md).
