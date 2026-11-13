# Roadmap

Prüfstand: 13. November 2026, Basis `main` nach PR #53. Dieser Stand beschreibt vorhandene Implementierungen und dokumentierte Nachweise. Angenommene ADRs sind verbindlich; historische Planformulierungen sind keine zusätzlichen Erledigungsnachweise.

## Phase 0: Infrastruktur — umgesetzt

Repository, Übergabeprotokoll, Konventionen, ADRs und Python-Paket stehen. Gemeinsame Arbeitsregeln: [AGENTS.md](../AGENTS.md). Aktuelle Ergebnisse und Grenzen: [HANDOFF.md](../HANDOFF.md).

## Phase 1: Original verstehen und messbar machen — Grundlage vorhanden

Das Delphi-Original ist inventarisiert und läuft automatisiert unter Wine. Der Delphi-Zufallsgenerator ist nachgebildet; Originalmitschnitte erlauben Vergleiche bis auf Aufrufstelle und Generatorzustand (ADR 0008/0009). Parser und das versionierte Trace-Format sind implementiert.

Das früher geplante Free-Pascal-Gerüst ist durch ADR 0009 **zurückgestellt**. Es wird nur wieder aufgenommen, wenn Abweichungen mit den bestehenden Mitteln nicht eingegrenzt werden können. Die entsprechenden Schritte aus Issues #2/#4 sind deshalb kein unmittelbar ausstehendes Portierungspaket.

**Noch offen:** Ein allgemeiner statistischer Äquivalenznachweis nach vorab festgelegten Grenzen. Die dokumentierten exakten Referenzläufe ersetzen diesen Nachweis nicht. Zusätzliche Originalserien benötigen einen eigenen bestätigten Analyse-/Ressourcenplan; sie folgen nicht automatisch aus einem alten offenen Issue.

## Phase 2: PSI-Kern und Inselwelt — Referenzmodus implementiert

Gedächtnis, Motivation, Modulatoren, Wahrnehmung, Handlungen und Rasmussen-Regulation sind portiert. `IslandLife` verbindet den Agenten mit der Inselwelt und sichert den vollständigen Zustand einschließlich Zufallsquellen. Artefaktschalter nach ADR 0015 trennen Referenz- und modernisierte Varianten.

**Nachweise:** Seed 16 ist im dokumentierten Ganzlauf in Aktivitäts-/Handlungsprotokollen und Abschlussdateien gleich. Seed 901 hat eine dokumentierte abweichende Aktivitätsprotokollzeile bei gleichen Handlungen und Abschlussdaten (ADR 0014). Einzelne Zufallszüge sind nur im Umfang des jeweiligen Mitschnitts geprüft. Neue Änderungen müssen diese Golden-Master-Prüfungen erhalten; Toleranzen werden nicht still erweitert.

**Grenze:** Verteilungsgleichheit über beliebige Seeds ist nicht nachgewiesen. Die Implementierung ist keine pauschale Gleichheitsgarantie für alle Plattformen oder Originalzustände.

## Phase 3: Global Workspace — implementiert und untersucht

Kapazität abhängig vom Auflösungsgrad, Wettbewerb von Motiven/Zielen/Objekten/Erinnerungen/Plänen, Amtsinhaberbonus und Broadcast sind implementiert (ADR 0016). Die Ausführung innerhalb eines Agenten bleibt sequenziell. Die optionale zufällige Auflösung von Gleichständen nutzt einen eigenen gesicherten Zufallsstrom (ADR 0018); die ursprüngliche Bestätigung verwendet weiter die Namensregel.

**Nachweise:** Screening-, Bestätigungs- und nachträgliche Sensitivitätsläufe sind archiviert. H1/H4/H6 erreichen die vorhergesagte Signifikanz, H2/H3/H5 nicht; das kombinierte Kriterium ist nicht erfüllt. Daraus folgt kein allgemeiner Leistungs- oder Bewusstseinsnachweis.

Die Publikationsarbeit ist inzwischen in [Paper 1: Portierung](../paper/1-portierung/) und [Paper 2: Hysterese](../paper/2-hysterese/) getrennt. Die zweite Review-Runde ist über PR #50 eingearbeitet. Vor Einreichung bleiben die in den Paperordnern dokumentierten Quellen-/Metadatenfragen sowie Lizenz und Veröffentlichungsrechte zu klären.

## Diagnose und Visualisierung — ergänzt

Die [Vergleichswerkzeuge](comparison-tools.md) unterscheiden vollständige Gleichheit, Abweichung, Fehler und Teilvergleich. Der [Trace-Viewer](trace-viewer.md) visualisiert ein oder zwei ADR-0006-Läufe ausschließlich lesend, mit Herkunft, Datenlücken und Filterung. Er ersetzt weder Golden-Master-Tests noch wissenschaftliche Auswertung und benötigt keine Simulation.

## Phase 4: Allgemeiner Körpervertrag und 3D-Simulation — teilweise umgesetzt

Auf `main` liegen ein generischer `Body`-Entwurf und das [kinematische PiCrawler-Testbett](picrawler/README.md): Gelenkgeometrie, Sensorbilder, Distanz, Energie/Wärme, Peripherie, Kalibrierwerkzeuge, Mock-Bridge, Snapshots und Replay.

Der integrierte Inselagent nutzt weiterhin `IslandBody` und dessen Client-/Wahrnehmungsmethoden. **Offenes Abschlussziel:** Dieselbe PSI-Instanz steuert Insel und Robotiksimulation über einen tatsächlich gemeinsamen Wahrnehmungs-/Aktionsvertrag. Dazu fehlen die semantische Sensoranbindung und die Übersetzung von PSI-Absichten in zeitlich begrenzte Roboteraktionen.

**Getrennte, ungemergte Arbeit:** [PR #38](https://github.com/alec85/psi-gw/pull/38) ergänzt geschlossene Benchmarks und Controllerprozesse; darauf baut [PR #43](https://github.com/alec85/psi-gw/pull/43) mit dem gewählten MuJoCo-Backend auf. Die dort dokumentierten 24 dynamischen Sensorfahrten hatten 0 Zielerfolge. [Issue #49 / PR #52](https://github.com/alec85/psi-gw/pull/52) bearbeitet Bewegungsprofil, aktive Raumabtastung und physische Navigation. Der jeweilige Branch ist die Quelle für aktuelle Ergebnisse; hier wird kein laufendes Paket vorweggenommen.

Neuronale Kameraverarbeitung bleibt ein möglicher späterer Schritt aus ADR 0012 und benötigt eine eigene Entscheidung und Prüfung.

## Phase 5: Realer PiCrawler — offen

Ziel bleibt ein schlanker Körper auf dem Raspberry Pi mit Kognition auf einem PC. Vorhandene Mock-/Kalibrierwerkzeuge sind Vorarbeiten. Noch erforderlich sind Gerätevermessung, Servo-/Sensorzuordnung, realer Transport, unabhängiger Motor-Watchdog und Hardwareabnahme.

**Abschlusskriterium:** Der reale Crawler zeigt dokumentiert motivgesteuertes Verhalten, etwa Exploration und Rückzug bei Hindernissen. Eine Simulationsabnahme erfüllt dieses Kriterium nicht.

## Phase 6: Spiking Neural Networks — Ausblick

SNN-Komponenten zuerst in Sensorik und Motorik, etwa Gang-CPG oder Ultraschall-/Kameraverarbeitung, mit klarer Schnittstelle zur Motivation und Handlungsregulation. Die Übertragung der Kognition auf Spiking-Dynamik bleibt eine eigene Forschungsfrage.

**Abschlusskriterium:** Vergleich einer tatsächlich ausgeführten SNN-Komponente mit einer klassischen Referenz unter vorher festgelegten Bedingungen. Noch keine Implementierung oder Abnahme auf `main`.
