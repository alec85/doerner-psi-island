# Determinismustest des Originals unter Wine

Zwei Läufe des Originals (Psi 4.9.1.200, `reference/delphi-runtime/PsiCode/Psi.exe`) mit identischen Einstellungen, erzeugt am 2026-11-09 mit

```bash
python scripts/run_original.py --seed 16 --max-life 100000 --out <r1|r2>
```

unter Wine 9.0 und Xvfb auf Ubuntu 24.04 (Cloud-Arbeitsbereich), Welt und Startwissen `InselIII`, `Geschwindigkeit=0.0`, Start über das Menü (siehe `docs/delphi-build.md`).

Ergebnis: Beide Läufe sind in allen 72 Zyklen und 647 Ereignissen identisch, einschließlich Alter, Bedürfnissen und Modulatoren (bit-gleich). Drei kürzere Läufe mit `MaxLife` 20.000 waren ebenfalls identisch und bilden exakt den Anfang dieser Läufe. `tests/test_original_runs.py` prüft den Befund an diesen Dateien.

`raw/` enthält alle Protokolle unverändert, wie Psi sie geschrieben hat; die `.jsonl.gz`-Dateien sind daraus konvertiert (ADR 0006).
