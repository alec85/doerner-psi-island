# Zufallsmitschnitt, Seed 16, 75.000 Züge

Verlängerung von `../2026-11-10-zufallsmitschnitt/` (20.000 Züge) bis in Zyklus 70, erzeugt am 2026-11-10 mit

```bash
python scripts/trace_random.py --seed 16 --max-draws 75000 --out <dir>
PSI_TRACE_NAMES=64900-67000 python scripts/trace_random.py --seed 16 --max-draws 67000 --out <dir>
```

- `random_draws.tsv.gz`: alle 75.000 Züge, Format wie in `docs/zufallsmitschnitt.md`.
- `random_draws_names_64900-67000.tsv.gz`: die ersten 67.000 Züge eines zweiten Laufs; für die `Junction`-Züge 64.900 bis 67.000 enthält die Spalte `names` die beiden Neuronen (`In>Out`). Beide Läufe sind in den gemeinsamen 67.000 Zügen identisch.

Mit den Namen wurde gefunden, dass `PlanenUndTun` nach einer Fortbewegung in seinem Parameter `situation` sucht, der die globale `Situation` verdeckt (Zyklus 65). Die Portierung zieht seitdem alle 75.000 Züge identisch (`tests/test_life.py`).
