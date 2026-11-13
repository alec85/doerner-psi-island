# Lokale Entscheidung: geschlossener Roboterbenchmark

- Datum: 2026-11-11; Issue #37
- Status: für isolierte Vorarbeit angenommen, vor Versuchsserien festgelegt
- Basis: PR #36 bei `2ba20b2`; eigener Branch/Draft-PR; kein Merge

## Abgrenzung

Nur PiCrawler-Code, Tests und Dokumentation. Keine Änderungen an Claudes
Workspace, seinen laufenden Bestätigungsläufen/Paper, PSI-Kern, Insel, zentraler
Übergabe, Abhängigkeiten, CI oder `main`. Die Controller sind technische
Referenzen, keine PSI-Integration oder vorgezogene Motivationsarchitektur.

## Aufgaben und Trennung der Daten

Version-1-Parcoursfamilien: offen, versetzte Hindernisse, Sackgasse und Tor mit
einem zwischen Ticks einsetzbaren Hindernis. Geometrie/Variationen sind seeded.
Ein konservatives Raster prüft zusammenhängenden freien Raum für die Körperhülle.
Sensorstörungen: nominal, Rauschen/Ausfälle, verzögerte Messung.

Entwicklungsseeds 0..3; zurückgehaltene Prüfseeds 1000..1003. Nach dem ersten
Prüflauf werden Controllerparameter nicht anhand dieser Ergebnisse optimiert.
Notwendige Fehlerkorrekturen und erneute Läufe werden ausdrücklich dokumentiert.

Aufgaben: Vorwärtsfortschritt bis x ≥ 0,35 m; Exploration bis mindestens 8 % der
vom Start erreichbaren 0,15-m-Rasterzellen besucht; Halt bei Hunger ≥ 0,85 oder
Schaden ≥ 0,95 spätestens zwei Entscheidungen nach dem Signal. Fortschritt und
Exploration haben höchstens 900 Ticks, Energietests 30. Zielerreichung allein
genügt nicht: höchstens 1 % Kontakt-Ticks, keine Arbeitsraumverletzung und kein
unerwarteter Ausfall. Diese Grenzen beurteilen nur das Modell.

## Controller- und Wahrnehmungsvertrag

Beide Controller erhalten ausschließlich freigegebene Messwerte, Erwerbszeiten,
lokale Bedürfnisinputs und die zuletzt tatsächlich ausgegebene Aktion. Welt,
Pose, Hindernisnamen, Kollisionen und Aufgaben-Erfolg gehören nur in die
Evaluation. Geschätzte Richtung aus eigenen Befehlen ist ausdrücklich keine
gemessene Odometrie. Der Referenzpunkt x=0,35 wird dem Controller nicht übergeben.

Verglichen werden eine reaktive Einzelmessungsbaseline und eine zustandsbehaftete
Baseline mit konservativer Entfernungshistorie, Ausweichphase und geschätzter
Rückkehr zur ursprünglichen Richtung. Unbekanntes Echo bedeutet nicht freie
Fahrt. Alte Messungen dürfen nur kurz und ohne zwischenzeitliche Drehung als
konservativ verringerte Schätzung dienen. Akute Nähe wirkt ohne Glättungsverzug.
Bei Übergängen ist eine explizite `stand`-Aktion erlaubt und wird mitgezählt;
deren instantane Kinematik ist keine reale Haltungsdynamik.

Zeitliche Farbregionen werden anhand beobachteter Farbe/Bildposition zugeordnet.
Tracks enthalten Alter/Unsicherheit und laufen ab. Keine Objektidentitäten oder
Tiefen aus Weltwahrheit. Ein separater synthetischer Bild-/Distanzkorpus prüft
Rauschen, kurzzeitigen Ausfall, Verdeckung und verspätete/duplizierte Frames.

## Messung und Abnahme

Pro Episode: Zielstatus, Fehlergrund, besuchte/erreichbare Zellen, Weg, Energie,
Kontakt-/Grenz-Ticks, Ausfall/Frische, Aktionswechsel/Postureresets, Lauf- und
Quellfingerprints. Entwicklungs- und Prüfergebnisse separat; gepaarte Controller-
Vergleiche deskriptiv, keine neue Paper-Hypothese oder Überlegenheitsbehauptung.
Vollständige Checkpoints sichern Body, Controller, Wahrnehmung, Messwertverzögerung
und Auswertung; Fortsetzung muss nach jedem Tick identisch sein. Beispiel-Replays
verwenden dieselbe tatsächliche Episode. Keine visuelle Browserabnahme behauptet.

## Lokale Prozessgrenze

Als zusätzliches Testinstrument darf der Controller in einem eigenen Python-
Prozess über begrenztes JSONL auf stdin/stdout laufen. Version, Sitzung, Sequenz,
Timeouts und Antwortvalidierung werden geprüft. Ein Fehler führt im Elternprozess
zu `stop` und gesperrtem Controller bis zum expliziten Neustart. Teilweise Pipe-
Writes/-Reads und Prozessende müssen begrenzt behandelt werden.
I/O-Fristen verwenden eine echte monotone Uhr; Modellentscheidungen bleiben
tickbasiert. Pipes sind hier keine Entscheidung über ROS/MQTT/ZeroMQ oder einen
Hardwaretransport. Prozessneustart startet ausdrücklich eine neue Sitzung.

## Grenzen

Keine neuen Sensoren, keine Ladestation/Ladeaktion, kein realer Motor-Watchdog,
keine Dynamik-Engine. Reale Hardwareanbindung und endgültige Wahrnehmungs-/PSI-
Semantik bleiben spätere Architekturentscheidungen. Die bestehende lokale
Beobachtbarkeit eines abgeschalteten Modells bleibt als Modellgrenze sichtbar.
