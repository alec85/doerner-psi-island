# Controller in einem eigenen lokalen Prozess

`controller_process.py` trennt Referenzcontroller und Simulator über begrenztes
JSONL auf stdin/stdout. Es gibt keinen Socket, Netzwerkserver, ROS-/MQTT-/ZeroMQ-
Adapter und keine Festlegung auf den späteren Hardwaretransport. Der Host besitzt
die Body-Taktung; der Kindprozess erhält nur den freigegebenen Sensorvertrag.

## Protokoll und Fehlergrenze

Version 1: Initialisierung mit Policy, Seed, Konfiguration und optionalem
Controllercheckpoint; danach `choose` mit Observation und vorheriger Aktion.
Jeder Request hat Sitzung und Sequenz. Identische Wiederholungen bekommen
dieselbe zwischengespeicherte Antwort; Konflikte oder falsche Reihenfolge
sperren die Sitzung. Der Elternprozess prüft Antwortkorrelation, Aktionsgrenzen,
Clock und Übereinstimmung von Aktion, Entscheidung und logischem Checkpoint.

Sowohl Pipe-Schreiben als auch -Lesen sind nichtblockierend. Eine monotone
Wanduhr begrenzt I/O: standardmäßig 5 s Initialisierung, 0,5 s je Entscheidung.
Teilweise Antworten, ein nicht lesender Worker, EOF, falsche Sitzung, ungültiges
JSON oder eine zu große Nachricht können keinen unbegrenzten Read/Write erzeugen.
Maximal 2.000.000 Bytes pro Record; doppelte JSON-Schlüssel und NaN/Inf sind
ungültig. Aktionen dürfen die bestehenden Body-Grenzen nicht überschreiten.

Bei Fehlern gibt der Elternprozess `Action("stop")` zurück und beendet den
Kindprozess. Die Sperre bleibt bis zum expliziten `restart()` bestehen.
Eine Neustart-Sitzung verwendet einen neuen Zähler. Ein frischer Neustart
rekonstruiert keine fehlende Bewegungsgeschichte; ein explizit übergebener
Checkpoint benötigt passende bekannte Folgeaktionen und logische Zeit.
Das ist kein unabhängiger realer Motor-Watchdog und keine sichere Ausführung
beliebigen fremden Codes. `worker_command` ist nur eine ausdrücklich vertrauenswürdige
Argumentliste für Testinstrumentierung, kein Shellkommando.

## Verwendung

```bash
python -m psi_gw.body.picrawler.robot_benchmark --output runs/controller-process \
  --seeds 0 --families open --tasks energy_stop --sensors nominal --execution process

python -m psi_gw.body.picrawler.process_experiment --output runs/process-proof
```

Das Prozessexperiment führt sechs Episoden für beide Policies und drei
Sensorprofile direkt und im echten Kindprozess aus; sämtliche Ergebnisse
müssen identisch sein. Anschließend werden bei beiden Policies echte
Kindprozesse beendet: Host-Stop, unveränderte Position, bleibende Sperre und
expliziter Neustart in neuer Sitzung/neuem Prozess werden beobachtet.
Die kurzen Äquivalenzepisoden sind technische Prozessprüfungen, keine
900-Tick-Aufgabenabnahme.

Ausgeführt auf `76c923b`: sechs von sechs Ergebnisvergleichen identisch,
zwei von zwei Kill-/Restart-Prüfungen bestanden. Weitere ausgeführte Tests
belegen Timeout bei blockiertem Schreiben einer großen Kameranachricht,
unvollständige Antworten ohne Newline, falsche Sitzungen/Sequenzen, zu große
Aktionswerte, nichtendliche Daten, identische Request-Wiederholung und
Prozessinitialisierung aus einem Controllercheckpoint.

Die Modellenergie ist weiterhin eine angenommene elektrische/thermische Bilanz.
Sie misst nicht die reale CPU-Last dieses Testrechners oder den Energiebedarf
des zusätzlichen Python-Prozesses.
