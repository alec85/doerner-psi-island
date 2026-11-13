# Getrennter Folgeversuch: visuelle Richtungskorrektur

- Status: für technische Vorarbeit angenommen, 2026-11-13, Issue #49 / Draft-PR #52.
- Grundlage: abgeschlossene v1-Prüfung aus Freeze 31f6ecf: aktiv 10/12 Ziele,
  beide verrauschten Slalomfahrten am Kontaktbudget; alte Varianten jeweils 8/12.

Die v1-Dateien und Ergebnisse bleiben unverändert. Das vollständige Abnahmeziel
ist verfehlt. Bereits Entwicklungsseed 10 zeigte bei verrauschten Stop-/Startfolgen
starke Befehlsschätzungsabweichung. Konstante Befehlsverstärkungen ersetzen keine
sensorische Bewegungsmessung; neue Fitparameter auf Prüfseeds sind keine Lösung.

Ein separater Controller darf die vorhandenen RGB-Bilder vor/nach einer stationären
Echo-Abtastung horizontal abgleichen. Bekannte synthetische Pinhole-Intrinsik bildet
Bildspalten auf Winkel ab. Der Abgleich liefert nur eine relative Richtungsänderung
mit expliziter Güteprüfung; gleichförmige/mehrdeutige Bilder werden verworfen.
Die annähernd stationäre Kamera und eine unveränderte Szene sind Annahmen. Das ist
keine gemessene Translation, keine IMU, kein allgemeines Visual-SLAM und keine
kalibrierte visuelle Odometrie. Der Controller bekommt weiterhin keine Modellpose.

Die Korrektur wird am Erwerbszeitpunkt des aktuellen Bildes mit der dortigen
Befehlsschätzung verglichen. Nur eine begrenzte, bildgestützte Richtungsabweichung
wird übernommen; neue Befehle beziehen diese Korrektur ein. Historische Karten-
unsicherheit bleibt bestehen. Keine Änderung an MuJoCo, Basisprofil, Sensoren oder
der eingefrorenen v1-Navigation. Kein neuer Paketbedarf oder Hardwaretransport.

Entwicklung des Bildabgleichs nur auf synthetischen Fixtures und Seeds 10/11.
Neue unabhängige Prüfung auf **3000/3001** nach eigenem Code-Freeze: offen/Slalom,
nominal/verrauscht/verzögert, jeweils eingefrorene aktive v1 und visuelle Variante,
insgesamt 24 Fälle. Gleiches 900er-Endpunkt-/2400er-Diagnosebudget und dieselben
Kontakt-/Sturz-/Stopkriterien. Ziel: alle sechs offenen Fälle innerhalb 900, alle
zwölf Fälle innerhalb 2400, alle Stopprüfungen bestanden, keine Stürze/Abschaltungen.
V1-Ergebnisse auf 2000/2001 bleiben geschlossen; keine Optimierung der v1 darauf.
Bei Verfehlen des neuen Ziels ebenfalls keinen vollständigen Erfolg behaupten.

Beide Varianten erhalten vollständige Checkpoints; mindestens drei visuelle
Slalomfortsetzungen in frischen Prozessen müssen exakt gleich sein. Kein Merge
nach main, keine Änderung an Claudes PSI-/Paper-Arbeit oder zentrale neue Architektur.
