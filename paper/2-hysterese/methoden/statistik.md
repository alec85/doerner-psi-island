# Methodenbaustein: Versuchsplan und Statistik

Grundlage für Abschnitt 3.4. Verbindlich ist `docs/analyseplan-workspace.md` mit seinen Nachträgen; hier nur die Kurzfassung für das Manuskript.

- Bedingungen A bis E im modernen Modus, je ein volles Leben mit `MaxLife` 5.000.000 je Seed.
- Vorauswahl auf Seeds 1001 bis 1020 (Fehlersuche, Effektgrößen), Bestätigung auf Seeds 1001 bis 1100, gepaart je Seed. Leben, die abbrechen, gehen paarweise aus dem Vergleich.
- Workspace-Kennzahlen: W1 Verweildauer (je Inhaltsart), W2 Motivwechsel, W2b Zielwechsel (Nachtrag 1), W3 abgebrochene Pläne, W4 Gelegenheitsbefriedigungen, W5 Rangkorrelation Arousal beim Eintritt gegen Verweildauer, W6 Anteil geschichtsabhängiger Zyklen. Berechnung in `psi_gw.analysis.workspace_metrics`.
- Tests: gepaarte Differenz mit 95-%-Bootstrap-Intervall, Vorzeichen-Permutationstest mit 10.000 Ziehungen und festem Seed (`psi_gw.analysis.metrics.paired_comparison`), Holm-Korrektur über H1 bis H6, zweiseitig, Niveau 0,05.
- Hypothesen: H1 W2b B < E; H2 W3 B < E; H3 W5 B > D; H4 W1 (Nicht-Motive) B > C; H5 W4 B < E; H6 W6 B > E (Manipulationsprüfung).
- Kernaussage gestützt, wenn H1, H3 und H4 in vorhergesagter Richtung signifikant sind.
- Rechenumgebung: Python 3.13, Paketstand laut `pyproject.toml`; Commit der Läufe steht in `analysis/workspace/*/README.md`.
