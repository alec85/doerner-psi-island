# Nachträgliche Analysen zur Überarbeitung beider Paper (Issue #45)

Stand 2026-11-12. Alle Zahlen hier sind **nach** den bestätigenden Auswertungen berechnet, als Antwort auf die Reviews (`paper/*/REVIEW_REPORT.md`). Sie ersetzen keine vorab festgelegte Auswertung und werden in den Manuskripten als nachträglich gekennzeichnet.

## Reproduktion

`scripts/reproduce_revision.sh [Zielordner]` prüft die Baseline-Archive gegen `SHA256SUMS`, entpackt sie nach `runs/`, stellt die Workspace- und Sensitivitätsläufe wieder her, rechnet Bestätigung, Revisionsanalysen und Sensitivitätsanalysen in den Zielordner, vergleicht jeden Wert mit den committeten Ergebnissen (`scripts/compare_json.py`) und erzeugt die Tabellen beider Paper neu. Läuft ohne `reference/`. Geprüft in einer frischen Kopie (`git archive`, ohne `reference/`) am Commit `ecc08a0`: alle Werte identisch.

Eingaben, die die Laufarchive nicht enthalten, liegen in `eingangsdaten/` (einmalig aus den vollständigen Läufen erzeugt mit `scripts/extract_revision_inputs.py`, mit SHA-256 jeder Quelldatei): `leben-paper1.csv` (Handlungen, Motivmeldungen, Stillstand, nil-Eingriffe, Zyklen, Alter je Leben), `handlungen-paper2.csv` (Handlungen je Leben der Bedingungen B bis E), `parameter-inseliii.json` (Parameterschnappschuss mit Hash von `Param.Dat`).

`eingaben.csv` und `eingaben.sha256` listen die 274 benötigten Dateien aus `reference/` mit gewöhnlichem SHA-256 je Datei (`sha256sum -c analysis/revision/eingaben.sha256` im Repository-Wurzelverzeichnis).

## Dateien

| Datei | Inhalt | Erzeugt mit |
|---|---|---|
| `paper1.json` | Ausfallfluss, Mittelwerte beider Modi, Exposition (Zyklen, Tode je Leben, je 1.000 Handlungen, je Million Zeiteinheiten, zeitgewichteter Schaden), gemeinsames Zyklusfenster, Motivdominanz je Leben, Parameter | `python scripts/revision_analysis.py --only paper1` (braucht `runs/baseline`, `runs/variant-all`, wiederherstellbar aus `traces/port-runs/2026-11-11-baseline/`) |
| `laufmanifest-paper1.csv` | je Seed und Modus: Schalter, Stillstand, Eingriffe des nil-Schutzes, Zyklen, Alter, SHA-256 der Laufdatei | ebenso |
| `paper2.json` | Tests H1 bis H6 nur auf Seeds 1021 bis 1100; Vorzeichen-Rang-Permutationstest; fehlgeschlagene Pläne je ausgeführtem Plan; Gelegenheitsbefriedigungen je 1.000 Handlungen; Zensierung; gemeinsames Fenster für W1; festes Fenster für W5; realisierte Boni und Kapazitäten; A gegen B und E auf 1001 bis 1020; Artwechsel | `python scripts/revision_analysis.py --only paper2` (braucht `runs/ws-*` mit Rohdateien) |
| `eingaben.csv`, `eingaben.sha256` | 274 Eingabedateien aus `reference/` mit SHA-256 je Datei | `python scripts/input_manifest.py` |
| `sensitivitaet/ergebnis.json` | Sensitivitätsläufe nach `docs/analyseplan-sensitivitaet.md` | `scripts/sensitivity_runs.sh`, dann `python scripts/sensitivity_analysis.py` |

## Wichtigste Befunde

Paper 1:

- Referenzmodus: 97 von 100 Leben vollständig, drei Stillstände (1035, 1061, 1073); moderner Modus: 100 von 100, nil-Schutz griff je einmal in 1025 und 1030. Die ersten 20 Läufe des modernen Modus liefen ohne den Schalter; da er nur bei einem nil-Zugriff wirkt und keiner auftrat, sind sie gleichwertig.
- Exposition: Zyklen je Leben 925,5 ± 72,0 (Referenz) und 929,4 ± 68,7 (modern). Die Abnahme der Tode bestätigt sich je 1.000 Handlungen (−0,78), je Million Zeiteinheiten (−0,47) und im gemeinsamen Zyklusfenster (−2,51 je 1.000 Zyklen); der zeitgewichtete Schaden sinkt um 9,1 Prozentpunkte.
- Motivdominanz je Leben: Mittel 99,89 % (SD 0,30 Prozentpunkte, Minimum 97,6 %) im Referenzmodus.

Paper 2:

- Seeds 1021 bis 1100 allein: dasselbe Muster (H1, H4, H6 signifikant; H2, H3, H5 nicht).
- A ändert sein führendes Ziel seltener (0,58 je 100 Zyklen) als B (3,67) und E (8,08) auf denselben 20 Seeds. Stabilität gilt also nur relativ zum Workspace ohne Bonus.
- Zensierung: 3,5 % der Aufenthalte von Nicht-Motiven in B laufen bei Lebensende noch, aber 45 % der Aufenthaltszyklen. Im gemeinsamen Zyklusfenster bleibt der H4-Kontrast fast gleich (19,7 Zyklen).
- H3 mit festem Beobachtungsfenster je Aufenthalt (200 Zyklen): weiter kein Unterschied.
- Kapazität K nimmt nur die Werte 4, 5, 6 an; der realisierte Bonus in B hat SD 0,010.
- Diagnose S1 (B, 1001 bis 1020, Inhalte identisch mit der Bestätigung): Gleichstand an der Kapazitätsgrenze in 9,9 % der Zyklen; Abstand zwischen letztem Gewinner und erstem Verlierer in 57 % der Zyklen kleiner als der Bonus; Abweichung von der namensgeordneten gedächtnislosen Auswahl 36 %, von jeder gedächtnislosen Auswahl nur 6,1 %. Der größte Teil von W6 entsteht also an Gleichständen.
- S2 (zufällige Gleichstandsauflösung, B und E, 1001 bis 1020): B kaum verändert (3,3 Zielwechsel je 100 Zyklen statt 3,7; Verweildauer 41,9 statt 33,6), E bricht ein (Gleichstand in 96 % der Zyklen, 68,0 Zielwechsel, Verweildauer 1,8). Die Stabilität von E in der Bestätigung beruhte auf der Namensregel.
- S3 (konstanter Bonus 0,02 und 0,2): Sättigung. Schon 0,02 bringt Zielwechsel von 8,1 auf 3,6 und Verweildauer von 13,5 auf 31,6; 0,2 nur noch 3,4 und 39,4. Keine Leistungsunterschiede gegenüber E, auch nicht bei 0,2.
