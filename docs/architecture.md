# Architektur

Prüfstand: 13. November 2026. Beschrieben wird `main` nach PR #53 plus der lesende Trace-Viewer dieses Arbeitspakets. Verbindlich sind die [ADRs](decisions/); dieses Dokument unterscheidet implementierte Abläufe und offene Integrationsziele.

## Module und Verantwortung

| Modul | Implementierte Verantwortung |
|---|---|
| `random_source`, `clock`, `counters` | Explizite Zufallsquellen mit Mitschnitt/Snapshot, simuliertes Alter, Prozess- und Leistungszähler |
| `state.PsiState`, `params`, `variant` | Kognitiver Zustand, Parameter, Referenz-/Artefakt-/Workspace-Schalter |
| `memory` | Geordnete Listen, Gedächtnisnetz, Namen und Protokollgedächtnis |
| `motivation` | Bedürfnisse, Kompetenz, Modulatoren, Motivwahl und Zielbildung |
| `perception`, `action`, `regulation` | Inselwahrnehmung, Handlungsausführung und Rasmussen-Leiter |
| `agent.run_cycle` | Feste Reihenfolge des Verhaltenszyklus, Aufrufe über `Faculties`, Workspace-Anbindung |
| `life.IslandLife` | Aufbau des Inselagenten, Lebensende, vollständige Snapshots und Ausgabe der Protokolldateien |
| `body.island` | Inselwelt, Client, Nachrichtenwarteschlangen, Bitmaps, Delphi-Zeichenketten und x87-Numerik |
| `body.base` | Generischer Entwurf von `Body`, `Observation`, `Action`; noch nicht alleiniger Vertrag des Inselagenten |
| `body.picrawler` | Eigenständiges kinematisches Robotik-Testbett samt Sensorik, Energie, Peripherie, Mock-Bridge und Kalibrierwerkzeugen |
| `workspace` | Begrenzte Kapazität, Kandidatenwettbewerb, Amtsinhaberbonus, Broadcast, eigene Gleichstands-Zufallsquelle |
| `tracing`, `analysis` | Versionierte Trace-Datensätze/Konverter und wissenschaftliche Kennzahlen |
| `ui.trace_viewer` | Lesender Offline-HTML-Bericht aus einem oder zwei bestehenden Traces |
| `scripts/` | Läufe, Archivierung, Vergleiche, Reproduktions- und Analysewerkzeuge |

Die Herkunft der portierten Module ist in [ADR 0010](decisions/0010-architektur-der-portierung.md) dokumentiert. Die Zielschichtung hält Visualisierung und Dateiverarbeitung außen. Im heutigen Referenzmodus sammeln Kernmodule weiterhin Textprotokolle in `state.prn`; `IslandLife` schreibt sie und ein Konverter erzeugt ADR-0006-Traces. Die vollständige Ablösung dieser Texte durch reine Beobachterereignisse ist kein bereits abgeschlossener Umbau.

## Tatsächlicher Ablauf eines Inselzyklus

Quelle: `agent.run_cycle`; `IslandLife.check_max_life` prüft das Lebensende außerhalb dieses Zyklus.

1. Welt-/Clientnachrichten abgleichen (`pump`), Zyklusbuchführung sowie Leistungs-/Bedürfnisstände und Exitus verarbeiten.
2. Falls erforderlich neu orientieren und das Protokollgedächtnis ergänzen; erneut mit der Welt abgleichen.
3. Bedürfnisse und Kompetenz fortschreiben, Motiv wählen, Ziele erzeugen. Workspace-Ziele der Vorperiode in die Zielliste übertragen; anschließend den aktuellen Workspace-Wettbewerb ausführen.
4. Gegebenenfalls umschauen, dann die Rasmussen-Leiter ausführen: abhängig von Zustand/Erfolg QuickMove, Automatismus, Planen und Tun oder Versuch und Irrtum. Weltabgleiche bleiben an den vorgesehenen Stellen.
5. Im Referenzmodus die Gedächtnis-/Zufallsseiteneffekte der ehemaligen Werteanzeige erhalten (ADR 0011); Taktdauer und Regulationszeiten protokollieren, abschließend `pump`.

Die genaue Reihenfolge ist Bestandteil der Reproduktion. Ein Verhaltenszyklus ist kein einzelner generischer `observe`/`act`-Tick: Er kann mehrere Inselaktionen, Rückmeldungen und Altersfortschritte umfassen.

## Zustand, Zufall und Fortsetzung

`PsiState` hält Kognition, Gedächtnis, Motivation, Zähler und Workspace. `IslandBody` hält Welt und Client. `IslandLife.snapshot()` verbindet beide zwischen Zyklen; die Zufallszustände gehören dazu. Tests vergleichen die fortgesetzten Zustände und Züge mit einem ununterbrochenen Lauf, auch in frischen Prozessen.

Im Referenzmodus teilen Inselwelt und Kognition die explizite `DelphiRandom`-Quelle. `RecordingSource` protokolliert Züge mit Aufrufstelle. Der Hauptablauf bleibt sequenziell: Gedächtnislesen kann Gewichte verändern und Zufallszahlen verbrauchen. Andere Seeds/Läufe können in eigenen Prozessen parallel berechnet werden; die Workspace-Module laufen nicht als nebenläufige Threads.

`Variant()` erhält den Referenzmodus. Die Artefaktschalter nach ADR 0015 aktivieren bewusst andere Verhaltensregeln. Der Workspace ist separat abschaltbar. Mit `workspace_ties=random` nutzt er eine eigene, aus dem Lebensseed abgeleitete und gesicherte Quelle (ADR 0018); `name` bleibt für die historische Bestätigung verfügbar. Es gibt keine automatische Umstellung bestehender Ergebnisse auf eine andere Gleichstandsregel.

Exakte Gleichheit ist im dokumentierten Referenzumfang geprüft; eine plattformübergreifende Float-Bitgleichheit oder statistische Äquivalenz beliebiger Läufe wird nicht zugesichert.

## Körper: zwei heute unterschiedliche Anbindungen

| Aspekt | Inselagent | PiCrawler-Testbett auf `main` |
|---|---|---|
| Aufbau | `IslandLife` / `IslandFaculties` / `IslandBody` | `PiCrawlerSimBody` erfüllt den generischen `Body`-Entwurf |
| Wahrnehmung | Insel-Client, Objektbitmaps und inselspezifische Zustände | Distanz, gerenderte RGB-Pixel, Telemetrie und lokale Bedürfnisindikatoren |
| Aktionen | Inselmethoden wie `manipulate`, `aggression`, Ortswechsel; Nachrichten mit `pump`/`wait` | Zeitlich begrenzte `Action`, etwa `drive` oder `stop`; ein Aufruf entspricht einem Modell-Tick |
| Kontrolle | PSI-Motivation und Handlungsregulation integriert | Eigenständige Demo-/Testansteuerung; keine abgeschlossene semantische PSI-Anbindung |
| Persistenz | Gesamtes Inselleben mit Kognition und Welt | Eigener Körper-/Peripherie-/Sensorzustand |

**Offenes Integrationsziel:** Roboterbeobachtungen in PSI-Situationen/Handlungsmöglichkeiten und PSI-Absichten in Roboteraktionen mit Abschlussrückmeldung übersetzen. Dazu muss der tatsächliche Zugriff auf Insel-Clientmethoden entkoppelt werden. Ein gemeinsames `Body`-Protocol allein erfüllt dieses Ziel nicht.

Die [PiCrawler-Dokumentation](picrawler/README.md) beschreibt den aktuellen kinematischen Vertrag. Weltpose, Gelenke und Kollisionswahrheit dienen dort Debugging/Replay und werden dem Controller nicht als Sensorbeobachtung geschenkt. Die Mock-Bridge ist kein produktiver Hardwaretransport.

## Trace-Viewer und Diagnostik

`python -m psi_gw.ui.trace_viewer` liest ADR-0006-JSONL bzw. Gzip über den vorhandenen `tracing`-Reader und erzeugt ein selbständiges HTML. Es wird weder ein Agent aufgebaut noch eine Zufallsquelle verwendet. Beide Eingaben bleiben unverändert. Einzelheiten: [Trace-Viewer](trace-viewer.md).

Die Darstellung richtet Läufe ausschließlich nach gespeichertem Alter oder Zyklus aus. Event-Bedürfnisse, Zyklus-Prozentwerte, Modulatoren und kumulative Zähler bleiben getrennte Messwerte. Fehlende Felder und fehlende Abschlussdatensätze werden angezeigt; es wird weder ein Workspace-Verlauf aus gewöhnlichen Traces erfunden noch eine Äquivalenzprüfung ausgeführt.

`compare_raw.py` vergleicht vorhandene Rohdateien, `compare_life.py` führt eine Portierung gegen Referenzdaten aus. Ihre [Exitcodes und JSON-Berichte](comparison-tools.md) trennen vollständige Gleichheit, Abweichung, Fehler und Präfixprüfung.

## Noch nicht integrierte Robotikstränge

Am Prüfstand sind [PR #38](https://github.com/alec85/psi-gw/pull/38) (geschlossener Benchmark, zeitliche Wahrnehmung, Controllerprozess), [PR #43](https://github.com/alec85/psi-gw/pull/43) (optionales MuJoCo-Backend) und [PR #52](https://github.com/alec85/psi-gw/pull/52) (Bewegungsprofil, Raumabtastung, Navigation) eigene gestapelte Arbeitsstände. Deren Erweiterungen und MuJoCo-Abhängigkeit sind keine Behauptung über die auf `main` verfügbare Installation.

Langfristig sollen Kognition und Workspace auf einem PC laufen, während der Raspberry Pi Sensoren und Servos bedient. Reale Transportwahl, Hardwarekalibrierung, unabhängiger Motor-Watchdog und durchgängige Hardwareabnahme bleiben offen. SNNs sind ein späteres Forschungs-/Implementierungsvorhaben, keine bestehende Komponente.
