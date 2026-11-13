# ADR 0017: matplotlib als optionale Abhängigkeit für Abbildungen

- Status: angenommen (Claude Code, 2026-11-11, im Rahmen von Alecs Auftrag)
- Datum: 2026-11-11
- Autor: Claude Code
- Bezieht sich auf: Issue #33, `paper/`

## Kontext

Für Paper 1 sollen Tabellen und Abbildungen mit geringem Aufwand aus den Auswertungen entstehen und jederzeit neu erzeugbar sein. Abbildungen brauchen eine Plot-Bibliothek. Neue Abhängigkeiten brauchen eine ADR (AGENTS.md).

## Entscheidung

`matplotlib` (ab 3.8) wird optionale Abhängigkeit im Extra `paper` (`pip install -e ".[paper]"`). Das Paket `psi_gw` selbst importiert es nicht; nur `scripts/paper_artifacts.py` nutzt es. Abbildungen werden als PDF (Vektor, für das Manuskript) und PNG (Vorschau) geschrieben, mit festen Schriftgrößen und ohne Zeitstempel in den Metadaten, damit sie reproduzierbar bleiben.

## Betrachtete Alternativen

- **Keine Abbildungen, nur Tabellen.** Verworfen: Verweildauern und Verteilungen sind als Abbildung deutlich lesbarer.
- **Plotly, seaborn.** Verworfen: größer, für statische Druckabbildungen kein Vorteil.

## Konsequenzen

- Die Simulation und die Tests bleiben ohne `matplotlib` lauffähig.
- `pyproject.toml` bekommt das Extra `paper`.
