# Übergabe: optionales MuJoCo-Backend

## Aktueller Stand

2026-11-12, Issue #42 / Draft-PR #43, Branch `codex/42-picrawler-mujoco`, Basis
`codex/37-picrawler-benchmark` (#38). Davor #36 auf #31; nichts nach main gemergt.
Alec hat MuJoCo ausdrücklich gewählt. Eigene ADR [ADR-mujoco.md](ADR-mujoco.md).
Claudes PSI-Kern/Paper, zentraler HANDOFF, Insel und CI wurden nicht verändert.
`pyproject.toml` erhält ausschließlich das optionale Extra `mujoco==3.3.7` vor `dev`.

Modell: frei beweglicher 0,602-kg-Körper, zwölf Gelenke/Motoren, eigene MJCF-Datei
als erzeugter XML-Text, angenommene Massen/Reibungen/Trägheiten/Regelwerte.
Motoren 0,35 Nm, Ziel-Slew 4 rad/s, PD 6/0,02; eigene Crawl-Fußtrajektorie und IK.
Keine vorgeschriebene Körpertranslation oder Lage-Stabilisierung aus Debugwahrheit.
Sensoren aus voller Körperorientierung via CPU-Strahlen; Controller sieht nur
Echo, Pixel und Bedürfniswerte. Bestehende Energie/Peripherie und Bridge-Vertrag.

Laufzeitcode für formale Abnahme vorab in `d35cdc58fc43b2fed3600138c2d63e26d55a7f52`
gesichert; alle erfassten Laufzeitdateien danach unverändert. Quellfingerabdruck
`19f51e0dafecea5fd48b8f9e29f76d6dd670bb617810e101beb3f5c727e5ed23`.
Ergebnisse in [MUJOCO-RESULTS.md](MUJOCO-RESULTS.md), Rohdaten und Replays unter
`mujoco-results-2026-11-12/`. Einstieg: [MUJOCO.md](MUJOCO.md).

## Teststatus

- 917 bestanden, keine übersprungen, finaler vollständiger pytest-Lauf im Checkout:
  864 bestehende +53 neue MuJoCo-Tests, 51,48 s; JUnit/Log gespeichert.
- 30/30 vorab festgelegte Gangfälle bestanden. 24 geschlossene Episoden:
  23 Timeouts, ein Kontaktbudget, **kein Zielerfolg**; keine Stürze/Abschaltungen,
  alle 24 Stop-Abnahmen bestanden. Keine Kriterien abgeschwächt.
- Drei frische Prozessfortsetzungen aus Entscheidung 150 bis 900 plus Stop
  exakt gleich, einschließlich Körperzustand- und Verlaufshash.
- Physische Peripherie/Mock-Bridge geprüft. Vier tatsächliche HTMLs mit 263 Frames
  im JavaScript-DOM/Canvas-Harness bestanden. Native EGL-Modellansichten von Stand,
  Gang und Drehung gerendert und visuell geprüft; keine Browser-Sichtabnahme.

## Nächster Schritt

Vor weiterer Steuerungsentwicklung unveränderte Rohdaten auswerten. Gewünschte
Geschwindigkeit ist nicht die tatsächliche: nominale offene Fahrt endet nach
Stop bei x=0,34808 m statt Ziel x≥0,35 m. Das knappe Scheitern bleibt ein Timeout.
Befehlswirkung/Verzögerung/Unsicherheit auf getrennten Entwicklungsfällen bestimmen;
danach robustere aktive Raumabtastung und Navigation auf **neuen** Seeds abnehmen.
Die jetzigen Validierungsseeds nicht nachträglich zu einem Erfolg hinoptimieren.

Optional später dynamische Gate-Schließung mit geprüfter kollisionsfreier
Modelländerung und erweitertem Snapshot-Vertrag. Geschlossene Exploration und
Energie-Stopp sind in der dynamischen v1 noch nicht enthalten. Kein Bedarf,
Claudes PSI-/Workspace-Code für diese Folgearbeiten anzufassen.

## Offene Fragen

Keine weitere grundlegende Entscheidung für diesen geprüften Ausgangsstand.
Echte Hardwaremassen, Servokennlinien, Reibung und Wärme-/Energieparameter fehlen
weiterhin; Modellannahmen dürfen nicht als identifiziert ausgegeben werden.

## Bekannte Fallstricke

- `pip install -e ".[dev,mujoco]"`; Basispaket und kinematische Referenz importieren
  ohne MuJoCo. Echte Integration nur mit exakt 3.3.7; sonst verständlicher Fehler.
- Anfangs zu hohes Kd=0,08 verursachte explizite PD-Sättigung im Gang. Entwicklung
  und gewähltes Kd=0,02 sind vor unabhängiger Abnahme dokumentiert.
- Gelenkgrenzen sind weich; Ziel-Slew ist keine harte Ist-Geschwindigkeitsgrenze.
  Eigenkollisionen und Selbstverdeckung der Sensoren sind deaktiviert.
- Energie ist ein diskretes Proxy-Modell, keine exakte elektromechanische Bilanz.
  Stromabschaltung lässt Gravitation/Kontakte weiterlaufen; Stop kann ausrollen.
- Snapshots benötigen dieselbe Engine/Modellbeschreibung. Kein Anspruch auf
  plattformübergreifende Bitidentität; numerische Fehlerzustände erfordern reset.
- Browserzugriff auf lokale HTMLs ist in dieser Umgebung blockiert. Frühere
  lokale Chromium-/Cloud-Datei-Versuche nicht über alternative URLs umgehen.
  EGL-Modellbilder und JS-Harness sind separat ausgewiesene Prüfungen.
- pytest.log wird vom allgemeinen Gitignore erfasst; bewusst als Testbeleg mit
  `git add -f` aufnehmen. Replays enthalten nur gespeicherte Daten, keine Engine.

## Log

2026-11-12: Optionales Modell/Body implementiert, Regler-Sättigung in Entwicklung
behoben, unabhängige Gang-/Sensorabnahme ausgeführt, exakte Prozessfortsetzung
und native Darstellung geprüft, Ergebnisse samt erfolgloser Navigation gesichert.
