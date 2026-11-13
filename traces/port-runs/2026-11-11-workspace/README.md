# Läufe der Workspace-Experimente

Je fertigem Leben `metrics.json` und das Workspace-Protokoll (`Workspace(1).jsonl.gz`), Bedingungen A (nur 1001 bis 1020) und B bis E. Abgelegt mit `python scripts/sync_workspace_runs.py save`; jede Datei wird einmal geschrieben und danach nicht mehr verändert.

Fortsetzen in einer neuen Umgebung:

```bash
python scripts/sync_workspace_runs.py restore   # nach runs/ws-*/seed*/
scripts/workspace_runs.sh 1001-1100 2           # rechnet nur, was fehlt
python scripts/sync_workspace_runs.py save      # neue Leben ablegen, committen, pushen
```

Die vollständigen Rohprotokolle (`actu*.Prt` usw.) liegen nur in `runs/` der rechnenden Umgebung; Code-Stand und Seed reichen, um sie neu zu erzeugen.
