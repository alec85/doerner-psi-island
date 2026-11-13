# Paper

Seit 2026-11-12 (Issue #40) zwei Paper in eigenen Arbeitsordnern:

| Ordner | Paper | Inhalt |
|---|---|---|
| `1-portierung/` | Paper 1 | PSI vorstellen, quelltextgetreue Portierung des Delphi-Originals, Nachweis der Treue, Befunde über das Original, moderner Modus |
| `2-hysterese/` | Paper 2 | Global Workspace mit Hysterese, vorab registrierte Tests (Paket C, Issue #33) |

Je Ordner: `gliederung.md`, `register.md` (Abbildungen und Tabellen mit Datenquelle), `literatur.md` (Recherche), `referenzen.bib`, `methoden/` (Bausteine mit Belegen im Repository), `manuskript.tex` (Entwurf, englisch), `tabellen/`, `abbildungen/`.

## Erzeugen

```bash
pip install -e ".[paper]"                                 # matplotlib, ADR 0017
python scripts/paper_artifacts.py --stage bestaetigung    # Tabellen und Abbildungen beider Paper
cd paper/1-portierung && latexmk -pdf manuskript.tex      # bzw. 2-hysterese
```

Das Skript liest nur Auswertungsergebnisse (`analysis/...`) und Workspace-Protokolle (`runs/...`, wiederherstellbar mit `python scripts/sync_workspace_runs.py restore`). Ausgaben ohne Zeitstempel.

## Regeln

- Zahlen im Text nur aus `tabellen/`, aus den JSON-Dateien unter `analysis/` oder aus Tests im Repository, mit Fundstelle in `methoden/`.
- Bestätigende Aussagen in Paper 2 nur aus H1 bis H6 nach `docs/analyseplan-workspace.md` mit Nachträgen.
- Literatur: in `literatur.md` steht, welche Angaben gegen eine Quelle geprüft sind und welche noch nicht.
- Manuskripte englisch, Arbeitsdateien deutsch (ADR 0004).
- Veröffentlichung: `reference/` (Delphi-Original, Laufzeitdateien) kommt nie in ein öffentliches Repository. Ein öffentliches Repository ohne `reference/` entsteht erst zur Einreichung (Alec, 2026-11-12).
