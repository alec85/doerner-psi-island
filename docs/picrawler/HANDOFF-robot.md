# Übergabe: geschlossener Roboterbenchmark und unabhängige Vorarbeiten

Stand: 2026-11-11, Codex. Issue #37, `codex/37-picrawler-benchmark`.
Draft-PR #38 gegen `codex/35-picrawler-validation` (PR #36).

## Aktueller Stand

Alle drei beauftragten unabhängigen Pakete umgesetzt:

1. Seeded Parcours, zwei sensorbeschränkte Referenzcontroller, getrennte
   Entwicklungs-/Prüfseeds, Aufgaben/Kennzahlen, vollständige logische
   Checkpoints, fortsetzbare Serien und tatsächliche Replay-Beispiele.
2. Zeitliche Entfernungsverarbeitung und Farbregionen-Zuordnung mit
   Frische/Unsicherheit/Ablauf sowie eigenständigem gelabeltem Störkorpus.
3. Echter lokaler Controllerprozess über begrenzte nichtblockierende Pipes,
   Sitzung/Sequenz/Antwortprüfung, Host-Stop bei Fehler und expliziter Neustart.

Plan vor Versuchen gepusht (`3248fee`), erste Implementierung (`f8cfd60`),
Prozess-/Durabilitätsstand für Serien eingefroren (`76c923b`). Danach keine
Controllerparameter oder Quellmodule anhand zurückgehaltener Daten geändert.
Zusätzliche Tests/Dokumentation/Evidenz ändern den ausgeführten Code nicht.

## Teststatus

864 gezielte Tests bestanden, keine übersprungen; 97 neu. 144 Entwicklungs-
und 288 Prüffahrten tatsächlich ausgeführt: 233.131 Körperticks, 252 erfüllte
Aufgaben, 150 Kontaktbudget- und 30 Zeitbudget-Nichterfüllungen. Keine
Arbeitsraumverletzung, kein verspäteter Energiehalt oder unerwarteter Stromausfall.
19.740 nach Checkpoints identische Folgeticks; sechs Frischprozessfälle.
Resume aller 432 Fallberichte bytegleich; vier Beispiel-Episoden exakt neu
gefahren. HTML-Skriptprüfung aller 179 Beispiel-Frames bestanden.

Sechs direkte/Prozess-Ergebnisse identisch; zwei echte Kill-/Restarts bestanden.
Wahrnehmungskorpus mit Seeds 0/1/42 ausgeführt. Details und alle Fehlerfälle:
[ROBOT-RESULTS.md](ROBOT-RESULTS.md), Archiv `robot-results-2026-11-11/`.
Kein PSI-/Workspace-/Insel-/Golden-Master-Lauf oder CI gestartet.

## Nächster Schritt

1. Draft-PR #38 prüfen; die Stapelbasis bleibt PR #36. Kein Merge durch Codex.
2. Architekturwahl für zusätzliches Dynamikbackend: Empfehlung MuJoCo,
   Alternative Webots; [DECISION-DYNAMICS.md](DECISION-DYNAMICS.md) ist ausdrücklich
   offen. Keine neue Abhängigkeit installiert oder Engine eingeführt.
3. Vor PSI-Integration gemeinsame Wahrnehmungs-/Aktionssemantik abstimmen;
   Referenzcontroller sind keine kognitive Architektur.
4. Reales Gerät und Messdaten für Kalibrierung/Transport identifizieren.
5. Visuelle Browserabnahme bleibt separat offen.

## Offene Fragen

Soll eine neue physikalische Simulationsbasis als optionales MuJoCo-Backend
oder als externe Webots-Umgebung aufgebaut werden? Die Vorlage beschreibt
den vorgeschlagenen Folgeumfang und die noch angenommenen Modellparameter.
Diese Wahl wurde nicht stellvertretend für Alec getroffen.

## Bekannte Fallstricke

- Erinnerung verbesserte im vorliegenden Benchmark die Erfolgszahl nicht.
  Seitliche Hüllenkontakte blieben bei weiter vorderer Entfernungsmessung möglich.
- Richtung aus Befehlen ist keine Odometrie. Farbregionen sind keine realen
  Objektidentitäten, gehaltene Werte keine Prognose verdeckter Bewegung.
- 900 Ticks reichen nicht zwangsläufig für einen geometrisch vorhandenen Umweg.
  Die Erfolgsgrenzen wurden nach den Ergebnissen nicht gelockert.
- Ein frischer Prozessneustart ist eine neue Policy-Sitzung, keine erfundene
  Wiederherstellung nicht erfasster Bewegung. Kein realer Motor-Watchdog.
- Gruppen-Energiemittel enthalten auch Fehlerfahrten; nur gepaarte erfolgreiche
  Aufgaben dürfen als gleich erfolgreiche Kostenvergleiche interpretiert werden.
- Resume verlangt dieselbe Code-/Runtime-/Revisionsmanifestierung. Für das
  Wiederaufnehmen archivierter Serien den eingefrorenen Stand verwenden;
  nach Dokumentationscommits neue Ausgabeverzeichnisse für neue Serien wählen.
- Prozess-/Kamerareplays bleiben Simulation; keine Hardware-/Browserfreigabe.

## Log

- 2026-11-11, Codex: aktuellen Claude-Stand gelesen, Issue #37/eigenen Branch
  angelegt. Plan zuerst gespeichert. Keine Änderung an Kern, Workspace, Insel,
  Paper, zentralem HANDOFF, Abhängigkeiten, CI, `main` oder Claude-Branches.
- Vier Parcoursfamilien auf konservative Raster-Erreichbarkeit geprüft;
  Controller-, Wahrnehmungs- und vollständige Checkpoint-Regressionsfälle gebaut.
- Lokale Prozessgrenze inklusive Schreibstau/Teilantwort/EOF/Sessionfehlern
  getestet; Beispielausgabe atomar gemacht und Abbruch/Wiederholung geprüft.
- Code bei `76c923b` eingefroren. 432 Episoden, Wahrnehmungskorpus und echte
  Prozessversuche ausgeführt; Fortschritt an Alec berichtet. Evidenz, eigene
  Übergabe, Replays und offene Entscheidungsvorlage ergänzt. Kein Merge.
