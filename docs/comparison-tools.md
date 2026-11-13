# Vergleichswerkzeuge

Issue #51. Die Werkzeuge ändern weder Simulation noch Referenzdaten oder Vergleichstoleranzen.

## Exitcodes

| Code | JSON-Status | Bedeutung |
|---|---|---|
| 0 | `identical` | Alle vorgesehenen Vergleiche vollständig gleich; bei `compare_life` ist zusätzlich das Leben beendet. |
| 1 | `different` | Inhalt oder Länge weicht ab. |
| 2 | `error` | Erforderliche Eingabe fehlt/ist ungültig, Ausführung oder Berichtsschreiben fehlgeschlagen. |
| 3 | `partial` | Keine gefundene Abweichung, aber nur ein Präfix geprüft, Leben nicht beendet oder Zufallsmitschnitt nicht ausgewählt. |

Bei mehreren Befunden hat Code 2 Vorrang vor 1 und 3. Die einzelnen Befunde bleiben im JSON sichtbar. Code 3 ist ausdrücklich kein vollständiger Gleichheitsnachweis. Ungültige CLI-Argumente liefern argparse-Code 2.

## Rohdateien vergleichen

```bash
python scripts/compare_raw.py --seed 16 --original ORIGINAL --port PORT --json vergleich.json
```

Alle sieben bisherigen Dateinamen sind erforderlich. Fehlende oder leere Dateien gelten als Eingabefehler. Die bisherigen Maskierungen der Wanduhrzeit bleiben unverändert; inhaltliche Unterschiede und zusätzliche/fehlende Zeilen zählen als Abweichung. Der JSON-Bericht ist jetzt ein versionierter Gesamtbericht statt der bisherigen reinen Dateizuordnung; Verbraucher müssen die Dateiergebnisse unter `checks` lesen.

## Portierung ausführen und vergleichen

```bash
python scripts/compare_life.py --cycles 28 --json vergleich.json
python scripts/compare_life.py --seed 16 --cycles 1000 --max-life 5000000 \
  --scope full --protocol ORIGINAL/actu16\(1\).Prt --draws RANDOM.tsv.gz --json vergleich.json
```

Standard ist `--scope prefix`: Der gemeinsame Anfang wird exakt verglichen, unterschiedliche Längen werden ausdrücklich als `prefix` ausgewiesen. Das gilt in beiden Richtungen, denn ein archivierter Zufallsmitschnitt kann mitten im Lauf enden. Ein ungleiches Zeichen in der letzten abgeschnittenen Protokollzeile bleibt eine Abweichung; es gibt keine automatische Abschwächung der Prüfung.

`--scope full` verlangt gleiche Längen. Bei beendetem Leben werden Aktivitätsprotokoll, Handlungsprotokoll und alle Abschlussdateien auch im Präfixmodus vollständig verglichen. Zufallsmitschnitte dürfen im Präfixmodus weiterhin kürzer sein; das Gesamtergebnis bleibt dann Code 3. Das Ende wird auch nach dem letzten angeforderten Zyklus geprüft.

Das Aktivitätsprotokoll und `Activities(1).Txt` sind immer erforderlich. Bei beendetem Leben sind zusätzlich `eAch(1).Prt`, `Inpro(1).Prt` und `Consum(1).Prt` erforderlich. Ohne angegebenen Zufallsmitschnitt wird bei Seed 16 das bisherige Standardarchiv verwendet; andere Seeds melden `draws: not_requested` und können daher keinen vollständigen Gesamtvergleich bestätigen. Ein ausdrücklich ausgewählter fehlender Mitschnitt ist ein Fehler. Ein unvollständiges oder fehlerhaftes TSV/Gzip wird nicht still übersprungen.

## JSON und Diagnose

`--json DATEI` schreibt UTF-8-JSON mit `format_version: 1`, `tool`, `seed`, `status`, `exit_code` und `checks`. `compare_life` ergänzt angeforderte/ausgeführte Zyklen, gewählten Umfang und Lebensende.

Jeder Sequenzvergleich nennt `original_count`, `port_count`, `compared_count`, `equal_prefix_count`, `uncompared_original`, `uncompared_port`, `differing`, `first_difference` und `context`. Indizes sind einsbasiert; ein fehlendes Element erscheint im Kontext als `null`. Die unvergleichbaren Enden eines passenden Präfixes sind keine inhaltlichen Abweichungen, werden aber gezählt. `compared_count` bezeichnet die gemeinsame Länge, einschließlich dort gefundener Abweichungen. `first_difference` ist bei einem reinen Präfix `null`.

`original_path` und gegebenenfalls `port_path` nennen die Eingaben. Eingabefehler enthalten eine Meldung statt erfundener Zählwerte. Laufzeitfehler stehen unter `checks.execution`. Abschlussergebnisse vor Lebensende heißen `not_applicable`.

JSON-Ausgaben dürfen keine Eingabe überschreiben, auch nicht über einen Symlink. Fehler beim Schreiben liefern Code 2 mit Konsolenmeldung; in diesem Fall steht kein verlässlicher neuer JSON-Bericht zur Verfügung.
