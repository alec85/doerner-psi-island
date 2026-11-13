# Volles Leben des Originals mit Seed 901

Lauf des Originals (Psi 4.9.1.200) unter Wine am 2026-11-10, `MaxLife` 5.000.000:

```bash
python scripts/run_original.py --seed 901 --max-life 5000000 --out <dir>
```

912 Zyklen, 1.086 Sekunden. Kein Fehlerdialog.

## Vergleich mit der Portierung

```bash
python scripts/run_port.py --seed 901 --max-life 5000000 --out <dir>
```

Ergebnis (2026-11-10): `Activities.Txt` (3.293 Handlungen mit Alter), `eAch`, `Inpro` und `Consum` sind identisch. Im Aktivitätsprotokoll `actu901(1).Prt` weicht eine von 90.698 Zeilen ab (Zeile 68.281 ohne Kopfzeile):

```
original:   5 OD:3.927 LokoMotion:       lS
portierung: 6 OD:4.712 LokoMotion:       lS
```

Das ist der in ADR 0014 beschriebene Fall: `RememberDir` liest für `lS` ein Byte einer Heapadresse. Die gewählte Lokomotion ist dieselbe, der weitere Lauf bleibt gleich.

`raw/` enthält die Protokolle unverändert (Windows-1252, CRLF); die `.jsonl.gz`-Datei ist daraus konvertiert (ADR 0006).
