# Zufallsmitschnitt, Seed 16, 20.000 Züge

Erzeugt am 2026-11-10 mit

```bash
python scripts/trace_random.py --seed 16 --max-draws 20000 --out <dir>
```

im Cloud-Arbeitsbereich (Wine 9.0, gdb 15.1). Die ersten 20.000 Zufallszüge eines Laufs mit Seed 16 umfassen die Zyklen 1 bis 29. Psi wurde am Haltepunkt des 20.000. Zugs beendet; `raw/` enthält die bis dahin geschriebenen Protokolle. Methode, Prüfungen, Befunde und Format: `docs/zufallsmitschnitt.md`.
