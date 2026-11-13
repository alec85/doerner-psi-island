# Übergabe: Belastungsmatrix und Messdaten-Kalibrierung

Stand: 2026-11-11, Codex. Issue #35, `codex/35-picrawler-validation`,
Draft-PR #36 gegen `codex/30-picrawler-sim` (PR #31).

## Aktueller Stand

`stress.py` prüft sechs Energie-, drei Sensor- und vier Linkprofile mit
explizitem Seed, Body-/Bridge-Invarianten und JSON-Checkpoint-Fortsetzung.
Atomare Berichte, Fingerprints, Wiederaufnahme und Fehlerartefakte sind enthalten.
`calibration_fit.py` importiert striktes CSV/JSON und schätzt Innenwiderstand,
thermisches R/C und Entfernungsfehler. Trainings-/Prüfdaten bleiben getrennt;
Berichte vergleichen Messung und Modell, Profil-Export bleibt explizit.
`calibration_experiment.py` erzeugt unabhängige analytische Vorwärtsfixtures.

Lokale Entscheidung vor Implementierung gepusht:
[ADR-validation-tools.md](ADR-validation-tools.md). Keine neue Abhängigkeit,
keine Änderung am Profilvertrag oder den bestehenden Modellgleichungen.

## Teststatus

Implementierungscommit `b6a38e62d2fd7a5293ea538569f6f5eb4ce1d3f7`:
767 Tests bestanden, keine übersprungen, 131 neu. Python 3.12.14, NumPy 2.5.4,
pytest 9.2.0. 216/216 Matrixfälle, 23.220 Körperticks, 14.580 identische
Folgeticks nach Checkpoint, null Arbeitsraumverletzungen. Wiederholung: 216
identische Fall-Hashes. Resume ließ sämtliche Erfolgsdateien unverändert.
Synthetische Fits für Seeds 0/1/42 bestanden alle festgelegten Grenzen.
`git diff --check` grün.

Anleitungen/Evidenz: [VALIDATION-TOOLS.md](VALIDATION-TOOLS.md),
[MEASUREMENT-FIT.md](MEASUREMENT-FIT.md), [results.json](validation-2026-11-11/results.json).

## Nächster Schritt

1. Draft-PR #36 prüfen. Zunächst auf PR #31 gestapelt, damit das Diff nur diese
   Vorarbeit zeigt. Kein Merge durch Codex.
2. Für echte Kalibrierung Zielgerät, Instrumente und Referenzgrößen dokumentieren;
   Trainings-/Prüfreihen und anwendungsbezogene Grenzen vorab festlegen.
3. Reale CSV-Daten importieren, Residuen bewerten und ein Geräteprofil exportieren.
4. Visuelle Browserabnahme von PR #31 bleibt separat offen.

## Offene Fragen

Keine blockierende Architekturentscheidung. Für den Geräteeinsatz fehlen reale
Messdaten und Geräteidentität. Physik-Engine, Hardwaretransport und PSI-Semantik
bleiben spätere gemeinsame Entscheidungen.

## Bekannte Fallstricke

- RC-Schätzung braucht bekannte CPU-Verlustleistung und Umgebung je Intervall;
  CPU-Auslastung allein ist keine Leistungsmessung.
- Akku-Fit benötigt Leerlaufreferenz und Laststrom; SOC wird nicht erfunden.
- Synthetische Fits bleiben `assumed`; Bias/Standardabweichung werden nicht
  in unpassende Simulationsparameter übernommen.
- Resume benötigt gleiche Revision, Fingerprints, Runtime und Matrix.
- Offline nach Abschaltung beobachtbare Modelldaten sind kein Nachweis,
  dass ein stromloser Pi Daten/ACKs liefern könnte.
- Keine Hardware-/Netzwerk-/Motor-Watchdog-Abnahme oder visuelle Browserfreigabe.

## Log

- 2026-11-11, Codex: aktuellen Claude-Stand geprüft, Issue #35 und separaten
  Branch angelegt. Keine Änderung an Kern, Workspace, Insel, Paper, Referenzen,
  zentralem HANDOFF, Abhängigkeiten, CI, `main` oder Claude-Branches.
- Lokale Entscheidung zuerst gepusht (`2eee2c4`), getestete Implementierung
  anschließend (`b6a38e6`). Matrix zweimal, Resume und drei verrauschte
  Kalibrierversuche ausgeführt. Draft-PR #36 und eigene Ergebnisübergabe angelegt.
