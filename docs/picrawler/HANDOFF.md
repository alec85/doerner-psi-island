# Übergabe: PiCrawler-Vorarbeit

Stand: 2026-11-11. Issue #30, Branch `codex/30-picrawler-sim`, Draft-PR #31.

## Aktuelle Nachprüfung 2026-11-11

Ausgangsrevision `d3664b0` lokal hashidentisch ausgecheckt; Python-Abhängigkeiten
in eigener venv installiert. 636 gezielte Tests bestanden (622 PiCrawler,
14 Body/RNG), keine übersprungen. Taster-Snapshot zwischen Eingabe und Tick
reproduzierbar defekt gefunden und durch eine persistierte Eingabewarteschlange
behoben. Acht neue Regressionen einschließlich frischem Python-Prozess,
exaktem Audio-/LED-Verbrauch und tatsächlicher Replay-JavaScript-Ausführung.

Das Peripherie-Demo lief nach der Korrektur mit Kamera, Rauschen und Dropouts:
1.461 Ticks, 73,05 s, 1,75 m, 0 Arbeitsraumverletzungen; alle 731 Folgeticks
ab Checkpoint 730 identisch. Alle 294 HTML-Frames durch das Node-DOM-/Canvas-
Testgerüst geprüft. Visuelle Browser-QA bleibt wegen Socket-/URL-Richtlinien
blockiert. Keine visuelle Freigabe behauptet, kein CI-Lauf und kein Merge.
Vollständiger Bericht: [VALIDATION.md](VALIDATION.md).

**Nächster Schritt:** visuelle Prüfung der erzeugten `replay.html` in einer
autorisierten Browserumgebung; danach fachliches Review. Kern, zentrale
Übergabe, `main` und Claude-Branches unverändert. Die folgenden Abschnitte
enthalten die vorherige Übergabe und ihre historischen Testergebnisse.

## Auftrag und Parallelität

Alec möchte eine vorgezogene PiCrawler-Simulation ohne Interferenz mit Claudes
laufender Portierungs-/Vergleichsarbeit. Im Folgeauftrag wurden eine anschauliche
3D-Welt, Raspberry-Pi-Betriebswerte samt PSI-Bedürfnisabbildung, ausdrücklich
angenommene physikalische Parameter und die vorgeschlagenen drei Vorarbeiten
(Kalibrierung, Sensor-/Wahrnehmungstests, Mock-Bridge) bestätigt.

Basis bleibt `main` bei `ed62d4a4c158219084e202248df1de5bceea0358`. Zuletzt erneut
geprüft: `claude/28-vergleichsbasis` bei
`7766d714ceb09656fa343b19a50d9b1b4fb53191`. Beide Stände waren unverändert;
die drei neuen Präfixe überschneiden sich nicht mit dem sichtbaren Claude-Stand.
Ungespushte Arbeit ist darüber nicht sichtbar.

Alle Änderungen liegen ausschließlich in:

- `src/psi_gw/body/picrawler/`
- `tests/picrawler/`
- `docs/picrawler/`

Der zentrale `HANDOFF.md` wird wegen des ausdrücklichen Parallelitätsauftrags
nicht überschrieben. Diese eigene Übergabe dokumentiert die Ausnahme. Kern,
Inselwelt, Body-Basis, Abhängigkeiten und CI bleiben im bisherigen Zustand.
Keine Änderung an `main` oder Claude-Branches, kein Merge.

## Aktueller Stand

- Vier Beine / zwölf Gelenke, belegte Segmentlängen, eigene Frames und IK/FK.
- Eigenständiger Body mit festen Ticks, vorgeschriebener Körperbewegung,
  weltfesten Standfüßen, kontinuierlicher Hindernisgrenze und validiertem
  Arbeitsraum. Keine Berechnung dynamischer Kontaktkräfte oder Standsicherheit.
- Ultraschall mit optionalem Rauschen/Dropout und synthetische RGB-Lochkamera.
  Weltwahrheit und Beobachtungen bleiben getrennt.
- Akku-Innenwiderstand, Ladungs-/Leistungsbilanz, lastabhängiger Verbrauch,
  thermisches CPU-RC-Modell und explizite Experimentumgebung. Modellannahmen
  stehen in [ENERGY.md](ENERGY.md) und `EnergyConfig`.
- Lokale normierte Signale `hunger` / `damage` für Energiemangel und thermische/
  elektrische Gefährdung. Keine Änderung am PSI-Kern; gemessener Hardware-SOC
  bleibt ohne geeigneten Schätzer/Sensor unbekannt.
- Version-2-Snapshots einschließlich Verbrauch, Umgebung und Warnhistorie;
  Version 1 migriert mit deaktiviertem Energiemodell.
- Interaktive, offline nutzbare 3D-Replays mit Kamera, Farbmerkmalen,
  Betriebswerten, Verlaufskurven und Bedarfen. Zwei ausführbare Szenarien:
  `obstacles` und `resources`. Optionaler PNG-/MP4-Datenexport.
- **Kalibrierpaket:** Versioniertes, streng validiertes Profil mit Herkunft je
  Wert; lesender Pi-Collector mit echten Unbekannt-Werten und injizierbarem
  Akku-Reader. Keine automatischen HAT-/GPIO-/Servo-Imports.
- **Wahrnehmung:** Sensorfrische, Nähe, explizite Medianfenster, HSV-Farbflächen,
  Schwerpunkte und BBox; wiederverwendbare Rohsensor-Testfälle.
- **Mock-Bridge:** Versioniertes JSON, Sessions/Sequenzen, Fristen, ACK-Cache,
  deterministische Verzögerung/Verlust, Wiederholungsschutz, Stop/Watchdog.
  Fehler bei Rückmeldung nach bereits ausgeführter Aktion sperren die Sitzung;
  Bewegung/Energie werden nicht rückwirkend erfunden oder doppelt ausgeführt.

## Teststatus

609 gezielte Tests grün: 595 im PiCrawler-Bereich sowie 14 vorhandene Body-/RNG-
Tests. Dazu zwei vollständig ausgeführte Szenarien mit 1.455 Ticks, 72,75 s und
je 1,75 m Weg; alle 728 Folgeticks nach dem Checkpoint identisch. Das enthält
Energiezustand, Sensorcache und Zufallsquelle. Wiederaufnahme im frischen
Python-Prozess ist zusätzlich abgedeckt.

Ressourcenlauf: Akku 15 → 12,7099 %, CPU 78 → 82,4633 °C; Hunger
0,60 → 0,6916, Schaden 0,65 → 0,8732. Das sind Modellresultate, keine
Hardwaremessungen oder Ergebnisse angebundener Kognition.

Details und verbleibende Browser-QA-Grenze: [VALIDATION.md](VALIDATION.md).

## Nächster Schritt

1. Draft und lokalen [ADR-Entwurf](ADR-prototype.md) gemeinsam prüfen. Keine
   globale ADR-Nummer wurde beansprucht. Alec entscheidet über den Merge.
2. Den realen Pi-/HAT-Typ identifizieren und das mitgelieferte Kalibrierprofil
   anhand von Messungen füllen: Akku, Kühlung, Kamera, Servo-Montage und -Offsets.
3. Mit dem `IslandLife`-Arbeitsstrang Wahrnehmungs-/Aktionssemantik und die
   Skalierung der beiden Bedürfnisinputs festlegen. Der vorhandene Body-Entwurf
   ist noch nicht der durchgängig benutzte Agentenvertrag.
4. Erst danach Hardwaretransport/Bootkennung/unabhängigen Watchdog einsetzen
   und anhand des tatsächlichen Untersuchungsziels eine Dynamik-Engine wählen.
   Szenarien, Sensortests, Protokollfälle und Replays bleiben wiederverwendbar.

## Offene Fragen

- Welches konkrete Raspberry-Pi-Modell, welche HAT-Version und welcher Akku?
- Welche realen thermischen/elektrischen Parameter ersetzen die Annahmen?
- Wie werden Merkmale und Aktionen auf die gemeinsame PSI-Semantik abgebildet?
- Genügt Kinematik für die nächsten Experimente oder sind Kontaktkräfte,
  Standsicherheit bzw. Schlupf bereits Forschungsgegenstand?

Diese Fragen blockieren die fertige Vorarbeit nicht; sie bestimmen die spätere
Kalibrierung und Integration.

## Bekannte Fallstricke

- Mathematische Gelenkwinkel sind keine PWM-Winkel. Unbekannte Modell-zu-Servo-
  Zuordnungen stehen im Kalibrierprofil ausdrücklich auf `None`.
- `stop` hält, `stand` setzt die Haltung instantan zurück. Reale Haltungs-
  Übergänge und die Energie einer solchen Umlagerung sind noch nicht modelliert.
- `measure_volts core`, Pi-Versorgung und Roboterakku sind verschiedene Größen.
  PMIC-Schienenströme ergeben nicht den Gesamtbatterie-/Servostrom.
- Alte Drossel-/Unterspannungsflags sind keine aktuellen Fehler. Der Collector
  und das Modell trennen Gegenwart und Historie.
- Die Mock-Bridge besitzt die Körper-Taktung exklusiv. Connect/Disconnect
  verursachen je einen Stop-Tick. Wiederholungsschutz gilt für die Lebensdauer
  des Endpunkts; reale Neustarts benötigen Bootkennung bzw. persistentes Fencing.
- Ein offline beobachtbarer abgeschalteter Modellkörper ist kein weiterhin
  sendefähiger stromloser Pi. `source="simulated"` bleibt sichtbar.
- Die HTML-Datei ist interaktive Wiedergabe gespeicherter Daten. Geänderte
  Szenarien werden im Python-Simulator neu gerechnet. Der aktuelle Fahrplan
  wird nicht von PSI gelernt oder ausgewählt.
- Keine SDK-Gangtabellen oder Hersteller-Quelltexte übernommen. Keine Behauptung
  kalibrierter Motorlast, Laufzeit oder Sim-to-real-Übertragbarkeit.

## Log

- 2026-11-10, Codex, `codex/30-picrawler-sim`: isolierten Simulator, Kinematik,
  Sensoren, Checkpoint-Replay und Draft-PR #31 angelegt; 323 gezielte Tests.
- 2026-11-10, Codex mit getrennten Teilreviews, gleicher Branch: Akku-/CPU-Modell,
  lokale Bedürfnisinputs, sichtbare Betriebsverläufe, Kalibrierung, Pi-Telemetrie,
  Sensorbaseline und Mock-Bridge ergänzt. 609 gezielte Tests; zwei ausgeführte
  Szenarien. In Reviews doppelte Profil-JSON-Schlüssel und unvollständige
  Fehlergrenze beim Bridge-ACK erkannt, behoben und mit Regressionen abgesichert.

## Ergänzung 2026-11-11: zusammengeführte Peripherie

- Hersteller-Hardwarematrix in [HARDWARE-INVENTORY.md](HARDWARE-INVENTORY.md),
  HAT-V4-/V5-Unterscheidung, keine erfundenen Erweiterungssensoren.
- Peripherie als opt-in `SimConfig(peripherals_enabled=True)` in
  den Körper-/Energietakt integriert. `speak`, `tone`, `sound`,
  `stop_audio` und `led` sind Body-Aktionen; Taster nur externe Eingaben.
- Der modellierte Audio-/LED-Verbrauch wird in der Akkubilanz mitgeführt,
  laufende Töne und Ereignisse werden in v3-Snapshots festgehalten.
  V1/V2-Snapshots bleiben lesbar.
- Die JSON-Mock-Bridge akzeptiert die neuen Befehle und den optionalen
  Peripheriesensorstatus; die HTML-3D-Ansicht zeigt ein synchrones
  Audio-/LED-/Tasterpanel. Neues Demo-Szenario: `--scenario peripherals`.
- [PERIPHERAL-INTEGRATION.md](PERIPHERAL-INTEGRATION.md) dokumentiert
  API, Modellannahmen, Tests und Grenzen. Akustik, PCM/TTS, echte
  GPIO-/I2S-Ansteuerung und hardwarekalibrierte Leistung bleiben offen.
- Die neuen Integrations- und Peripherietests sind geschrieben, jedoch
  mangels zugänglichem privaten Repository im Container in diesem Schritt
  **nicht ausgeführt**. Der frühere Nachweis von 609 Tests gilt
  ausschließlich für den vorherigen Stand. Eine GitHub-Actions-Workflow-
  Ausführung wurde für den aktuellen Commit nicht gefunden.
- Der PR bleibt Draft, `main` und Claudes Branch unangetastet.
