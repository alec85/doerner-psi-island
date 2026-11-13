# Volles Leben des Originals unter Wine

Ein Lauf des Originals (Psi 4.9.1.200) am 2026-11-10 mit `MaxLife` 5.000.000, der Lebensdauer aus Dörners Parameterdateien in `Execute/`:

```bash
python scripts/run_original.py --seed 16 --max-life 5000000 --out <dir> --timeout 7200
```

Cloud-Arbeitsbereich, Wine 9.0, Xvfb, 2 CPU-Kerne.

## Ergebnis

- 739 Zyklen, 7.148 Ereignisse, Endalter 4.977.469, acht Exitus (Zyklen 150, 220, 304, 387, 516, 583, 638, 722).
- Gesamtdauer 24,5 Minuten, davon etwa 5,5 Minuten Stillstand durch einen Fehlerdialog (siehe unten). Ohne den Dialog rund 19 Minuten.
- Die Zyklen 1 bis 315 sind identisch mit dem Messlauf unter `../2026-11-10-messlauf/` (ohne Wanduhrfelder).

Wanduhrzeit und Alter pro Zyklus in Blöcken von 80 Zyklen:

| Zyklen | s/Zyklus | Alter/Zyklus | davon Denkzeit |
|---|---:|---:|---:|
| 1–81 | 1,23 | 1.511 | 338 |
| 81–161 | 1,45 | 2.862 | 905 |
| 161–241 | 1,22 | 3.641 | 1.196 |
| 241–321 | 1,30 | 5.109 | 2.260 |
| 321–401 | 1,34 | 5.290 | 2.576 |
| 401–481 | 1,89 | 8.194 | 4.719 |
| 481–561 | 1,48 | 5.852 | 3.266 |
| 561–641 | 1,53* | 5.706 | 2.550 |
| 641–721 | 2,00 | 16.940 | 12.987 |
| 721–738 | 2,14 | 33.362 | 27.375 |

\* ohne die 328 Sekunden Stillstand durch den Dialog in Zyklus 571.

Denkzeit ist die Zeit der Rasmussen-Stufen aus `IntTimes`, die das Original in Alterseinheiten verbucht. Gegen Lebensende macht sie bis zu 80 % des Alterszuwachses aus.

## Fehlerdialog in Zyklus 571

Das Original zeigte einen modalen Dialog „GravityList: Fluglava1b 26 34 / Fluglava1b 22 30“ und wartete auf OK (Screenshot `raw/dialogs/cycle-571-1.png`). Ursache in `UPsiServer.pas`, `TPsi.GetGravityPoint` und `TGravityList.Add`: Die Welt fragt den Schwerpunkt eines Bildes beim Client an und verarbeitet während des Wartens weiter Nachrichten (`Application.ProcessMessages`). Dabei kann dieselbe Anfrage ein zweites Mal entstehen; die zweite Antwort trifft auf einen vorhandenen Eintrag, das Original meldet das und verwirft den doppelten Wert. Der Dialog wurde nach etwa 5,5 Minuten von Hand bestätigt; danach lief Psi normal weiter. Seitdem bestätigt `scripts/run_original.py` solche Dialoge automatisch und vermerkt sie im Kopf der Trace-Datei (`extra.dialogs_dismissed`).

## Wiederholung

Unter `wiederholung/` liegt derselbe Lauf, am selben Tag mit dem erweiterten Runner wiederholt (17 Minuten). Der Dialog trat erneut in Zyklus 571 auf und wurde nach wenigen Sekunden automatisch bestätigt. Beide Läufe sind in allen 739 Zyklen, allen 7.148 Ereignissen und der Zusammenfassung identisch, obwohl der Dialog im ersten Lauf 5,5 Minuten stand. Die Wettlaufsituation tritt unter Wine also deterministisch auf, und die Wartezeit am Dialog beeinflusst den Lauf nicht. `tests/test_original_runs.py` hält das fest.

`raw/` enthält alle Protokolle unverändert; die `.jsonl.gz`-Datei ist daraus konvertiert (ADR 0006), der Dialog wurde im Kopf nachgetragen.
