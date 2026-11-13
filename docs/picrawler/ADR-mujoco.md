# Optionales MuJoCo-Dynamikbackend

- Status: angenommen; Alec hat MuJoCo am 2026-11-12 ausdrücklich gewählt.
- Bezug: Issue #42; Basis Draft-PR #38, Commit c74a59a.

## Entscheidung

MuJoCo 3.3.7 wird als exakt gepinntes optionales Extra `mujoco` eingeführt.
Die bestehende kinematische Referenz bleibt unabhängig davon nutzbar.
Ein eigenes MJCF-Modell verwendet die vorhandenen Segmentlängen, vier Beine,
zwölf begrenzte Gelenkantriebe und einen frei beweglichen Körper. Bewegung
entsteht ausschließlich durch Gelenkmomente, Schwerkraft und Kontakte.
`drive`, `stand` und `stop` dürfen die freie Körperpose nicht setzen.

Massen, Trägheiten, Reibung, Gelenkgrenzen, Regelparameter und elektrische
Verluste sind explizite Modellannahmen, keine identifizierten Hardwarewerte.
Eine lokale PD-Regelung verwendet Gelenkwinkel und Geschwindigkeiten nur im
Antrieb; Pose, Kontakte und Gelenkzustände bleiben Beobachterdiagnostik.
Es wird keine künstliche Körperstabilisierung über versteckte Lageinformation
in den Referenzcontroller eingebaut. Eigenkollisionen sind zunächst deaktiviert.

Physikschritte betragen 2 ms, Body-Ticks 50 ms. Ein eigener Ganggenerator
liefert Fußziele und inverse Kinematik liefert Gelenkziele. Motoren sind auf
0,35 Nm begrenzt; Zielwinkel werden mit höchstens 4 rad/s verändert. Das ist
keine harte Grenze der tatsächlichen Gelenkgeschwindigkeit. Die PD-Werte
sind Kp=6 Nm/rad und Kd=0,02 Nm·s/rad. Im Entwicklungstest führte Kd=0,08
zu durchgehender Sättigung bei Gangbewegungen; die niedrigere Dämpfung wurde
vor der unabhängigen Validierung gewählt.

Snapshots binden Engine-Version und SHA-256 der vollständigen Modellbeschreibung
und speichern den MuJoCo-Integrationszustand einschließlich Warmstart. Exakte
Fortsetzung wird innerhalb derselben Laufzeit geprüft; keine plattformübergreifende
Bitidentität wird zugesichert. Sensoren werden je Body-Tick einmal erfasst.

Dynamische Abnahmen erhalten eigene vorher dokumentierte Kriterien für Stand,
Sturz und Restgeschwindigkeit. Die bisherigen kinematischen Kriterien und
PSI-Golden-Master-Toleranzen werden nicht verändert. Erfolgreiche Gänge oder
physikalisch kalibrierter Energieverbrauch werden nur mit ausgeführten Nachweisen
behauptet. Ein fehlgeschlagener Gang ist ein Ergebnis, kein Anlass für Teleportation.

## Folgen und Abgrenzung

Die Installation bleibt `pip install -e ".[dev]"`; Dynamik zusätzlich mit
`pip install -e ".[dev,mujoco]"`. Import und kinematische Tests benötigen
MuJoCo nicht. Die Pin-Version ist ein reproduzierbarer Ausgangspunkt, keine
Behauptung zur neuesten verfügbaren Veröffentlichung.

Eigener Branch `codex/42-picrawler-mujoco`, gestapelt auf PR #38. Keine Änderungen
an PSI, Papers, Insel, zentralem HANDOFF oder CI. Hardwaretransport und reale
Servokalibrierung sind nicht enthalten. Die CPU-Strahlenkamera ist ein synthetischer
Sensor und benötigt keinen OpenGL-Kontext.

## Primärquellen

- https://mujoco.readthedocs.io/en/3.3.7/python.html
- https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html
- https://mujoco.readthedocs.io/en/3.3.7/programming/simulation.html

Die Dokumentation wurde am 2026-11-12 geprüft. MuJoCo 3.3.7 ist lokal installiert.
