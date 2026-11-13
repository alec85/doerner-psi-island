# Bestätigung der Workspace-Experimente

Seeds 1001 bis 1100, Bedingungen B bis E (`scripts/workspace_runs.sh 1001-1100 2`, gerechnet am 2026-11-11). Code unter `src/` seit der Vorauswahl unverändert (Commit c0194b6). Bedingung A: `runs/ws-A` für 1001 bis 1020, sonst die bytegleiche Grundlinie des modernen Modus (`analysis/workspace/a-pruefung/`). Kein Leben brach ab. Die Läufe (je Leben `metrics.json` und Workspace-Protokoll) liegen unter `traces/port-runs/2026-11-11-workspace/`.

Auswertung nach `docs/analyseplan-workspace.md` mit den Nachträgen 1 bis 3: `tests.md` (Tabellen), `tests.json`, `leistung.json`, `beschreibung.json`, `kennzahlen.csv`.

## Ergebnis

Signifikant in vorhergesagter Richtung (Holm über sechs Tests, jeweils p (Holm) 0,0006):

- **H1:** Mit Bonus gleich Selektionsschwelle für alle Inhalte (B) wechselt das führende Ziel seltener als ohne Bonus (E), im Mittel 4,78 Wechsel je 100 Zyklen weniger (95-%-KI −5,20 bis −4,34; B 3,74, E 8,52).
- **H4:** Nicht-Motive bleiben in B länger im Workspace als in C, wo nur Motive den Bonus bekommen, im Mittel 20,5 Zyklen länger (KI 18,8 bis 22,2; B 33,7, C 13,2).
- **H6 (Manipulationsprüfung):** In B weicht der Workspace in 37 % der Zyklen von der gedächtnislosen Auswahl ab, in E nie.

Nicht signifikant:

- **H3:** Die Kopplung von Verweildauer und Arousal beim Eintritt ist in B nicht stärker als mit festem Bonus (D): Differenz 0,011 (KI −0,017 bis 0,040). Nach dem Analyseplan heißt das: Die Kopplung des Bonus ans Arousal bringt gegenüber einem festen Bonus keinen messbaren Vorteil. B und D unterscheiden sich auch in den übrigen Workspace-Kennzahlen kaum; die Selektionsschwelle schwankt auf der Insel zu wenig (Standardabweichung 0,009 um 0,065), um sich von einer Konstanten abzuheben.
- **H2:** abgebrochene Pläne, B gegen E, −0,18 je 100 Zyklen (KI −0,44 bis 0,08).
- **H5:** Gelegenheitsbefriedigungen, B gegen E, −0,23 je 100 Zyklen (KI −0,72 bis 0,29).

**Kernaussage nach dem vorab festgelegten Kriterium (H1, H3 und H4): nicht gestützt**, weil H3 nicht signifikant ist. Gestützt ist der schwächere Teil: Ein Amtsinhaber-Bonus in der Größe der Selektionsschwelle stabilisiert alle Inhaltsarten des Workspace und macht seinen Inhalt geschichtsabhängig (Hysterese). Dass gerade die Kopplung an das Arousal dabei eine Rolle spielt, zeigen die Daten nicht.

Beschreibend: P1 bis P6 unterscheiden sich in keiner Workspace-Bedingung nach Holm-Korrektur von A (kleinste p (Holm) 0,053 für P6 in B und 0,055 für P5 und P6 in D). Motivwechsel (H1 in Fassung 1) bleiben in allen Bedingungen selten (0 bis 0,04 je 100 Zyklen) und unterscheiden sich zwischen B und E nicht (p 0,21).

Hinweis zu den Mittelwerten von A in `tests.md`: Die W-Kennzahlen von A stammen nur aus den 20 Leben von `runs/ws-A`, weil die Grundlinie kein Workspace-Protokoll hat. Für die Tests spielt A nur bei P1 bis P6 eine Rolle.
