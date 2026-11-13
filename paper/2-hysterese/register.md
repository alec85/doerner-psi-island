# Register der Abbildungen und Tabellen, Paper 2

Nummerierung im überarbeiteten Manuskript: Tabelle 1 Vorarbeiten, Tabelle 2 Inhaltsarten, Tabelle 3 Chronologie, Tabelle 4 Hypothesen (von Hand gesetzt, Zahlen aus `analysis/workspace/bestaetigung/tests.json`), Tabelle 5 Leistung (`tabellen/T2.tex`); Abbildung 1 = A2, Abbildung 2 = A4, Abbildung 3 = A3. Sensitivitätszahlen aus `analysis/revision/sensitivitaet/ergebnis.json`, nachträgliche Analysen aus `analysis/revision/paper2.json`.


Erzeugt von `scripts/paper_artifacts.py` (Funktion in der Spalte „Erzeugt von“). Ausgabe nach `paper/2-hysterese/tabellen/<Kürzel>.md|.tex` und `paper/2-hysterese/abbildungen/<Kürzel>.pdf|.png`. Die Workspace-Protokolle unter `runs/` stellt `python scripts/sync_workspace_runs.py restore` aus dem Repository wieder her.

| Kürzel | Inhalt | Datenquelle | Erzeugt von | Stand |
|---|---|---|---|---|
| T1 | Bestätigende Tests H1 bis H6 | `analysis/workspace/bestaetigung/tests.json` | `table_hypotheses` | erzeugt (Bestätigung) |
| T2 | P1 bis P6, Bedingungen B bis E gegen A | `analysis/workspace/bestaetigung/leistung.json` | `table_performance` | erzeugt (Bestätigung) |
| A1 | Schema des Workspace im Verhaltenszyklus | `paper/methoden/workspace.md` | von Hand | offen |
| A2 | Verweildauer je Inhaltsart und Bedingung | `runs/ws-<B..E>/seed*/raw/Workspace(1).jsonl` | `figure_dwell` | erzeugt (1001 bis 1100) |
| A3 | Arousal beim Eintritt gegen Verweildauer, B und D | wie A2 | `figure_arousal_dwell` | erzeugt (1001 bis 1100) |
| A4 | Zeitleiste der Workspace-Inhalte, Seed 1001, B und E | `runs/ws-B/seed1001`, `runs/ws-E/seed1001` | `figure_timeline` | erzeugt |
| A5 | Kapazität `K` und Arousal über ein Leben | `runs/ws-B/seed1001` | `figure_capacity` | erzeugt |
