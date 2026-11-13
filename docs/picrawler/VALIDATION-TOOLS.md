# PiCrawler: reproduzierbare Belastungsmatrix

Issue #35, Branch `codex/35-picrawler-validation`, Draft-PR #36 gegen den
PR-31-Branch. Keine Änderung an Claudes Global-Workspace-, Versuchs- oder
Paper-Arbeit. Installation: `python -m pip install -e '.[dev]'`.

## Start und Profile

```bash
python -m psi_gw.body.picrawler.stress \
  --output runs/picrawler-stress --seeds 0 1 42 --ticks 80
```

| Achse | Profile |
|---|---|
| Seed | 0, 1, 42; frei wählbar |
| Energie | normal; heiß (84 °C, 15 % SOC); niedrige Ladung; leer; hohe Innenresistenz/Leistungsgrenze; sehr kleine Kapazität |
| Sensorik | ideal; 5 mm Rausch-Halbbreite und 15 % Dropout; vollständiger Echoausfall mit deaktivierter Kamera |
| Verbindung | normal; Request-/ACK-Verlust mit identischem Retry; verspätete Requests/ACKs; Disconnect/Reconnect |

Standard: 216 Kombinationen. Jeder Fall führt den tatsächlichen Body und die
vorhandene Mock-Bridge aus. Die Kamera verwendet hier ausdrücklich 12×8 Pixel;
48×32-Pixel-Kamera und Checkpoints sind durch vorhandene Tests abgedeckt.
Der Start liegt knapp vor dem vorhandenen Block, damit Kollisionsstopps
tatsächlich auftreten. Sprache, LED, Bewegung, Taster und Umgebung werden kombiniert.

`--ticks` ist die Bridge-Schleifenlänge. Hinzu kommen 14 direkte Body-Aktionen,
Connect, 12 Drain-Ticks und bei Reconnect zwei weitere Ticks. Daher umfasst
ein Fall mit `--ticks 80` insgesamt 107 bzw. 109 Körperticks.

## Geprüfte Eigenschaften

- Ein Tick je Aktion, synchroner Peripherietakt; begrenzter SOC und lokale
  Hunger-/Schadensinputs; Ladungsbilanz und Energiezuwachs gleich Leistung × dt.
- Verbrauchszähler fallen nicht; Stop oder Abschaltung verändern keine Position;
  bei Abschaltung sind Audio/LED aus. Körperposition bleibt kollisionsfrei.
- JSON-Checkpoint mit noch wartender Reset-Eingabe; vollständiger Body-Zustand
  nach jedem folgenden Tick identisch. Der Bridge-Transport wird nicht gesichert.
- Beobachten/Rendern verändert weder Zustand noch RNG.
- Identische Retry-ACKs und keine doppelte Ausführung; Fristen, alte Beobachtungen,
  Sitzungssperre nach Reconnect, geleerte Queues und Watchdog am Ende.

Exitcode 0: alle Fälle bestanden; 1: Invariantenfehler; 2: Bedien-/Dateifehler.
Erwartete Modellabschaltungen sind kein Testfehler.

## Berichte und Wiederaufnahme

`manifest.json` enthält Fallliste, Python-/NumPy-Version, Git-Revision und
SHA-256-Fingerprints der PiCrawler-Module, Body-Basis und Zufallsquelle.
`cases/<fall-id>.json` enthält Konfiguration, Kennzahlen, Status und Prüfsummen;
bei Fehlern zusätzlich Anfangs-/Endzustand, Fehlertyp und Aktions-/Eingabespur.
Nichtendliche Fehlerwerte erscheinen als `invalid_number`; solche Diagnosedaten
sind keine ladbaren Snapshots. `summary.json` fasst Status und Fall-Hashes zusammen.

```bash
python -m psi_gw.body.picrawler.stress \
  --output runs/picrawler-stress --seeds 0 1 42 --ticks 80 --resume

# Einzelnen Fall mit derselben gespeicherten Konfiguration nachstellen:
python -m psi_gw.body.picrawler.stress --output runs/picrawler-single \
  --seeds 42 --energy hot --sensors noisy --links lossy --ticks 80
```

Ohne `--resume` muss das Ziel neu oder leer sein. Wiederaufnahme verlangt
dieselbe Fallliste, Quellrevision, Codefingerprints und Runtime. Nur passende,
unbeschädigte Erfolgsberichte werden übersprungen. Fehlerfälle laufen erneut;
beschädigte Daten oder abweichende Manifeste führen zum Abbruch. Dateien werden
atomar veröffentlicht. Nach einem Code-/Revisionswechsel ein neues Ziel verwenden.

## Ausgeführte Abnahme

Implementierungscommit `b6a38e62d2fd7a5293ea538569f6f5eb4ce1d3f7`;
Python 3.12.14, NumPy 2.5.4, pytest 9.2.0. Nachfolgende Dokumentationscommits
ändern die Revisionsbeschriftung, nicht den hier ausgeführten Implementierungscode.

```bash
python -m pytest -q tests/picrawler tests/test_smoke.py tests/test_random_source.py
# 767 passed, keine übersprungen; 131 neue Testfälle
```

| Ergebnis | Gemessen |
|---|---:|
| Bestandene Kombinationen | 216 / 216 |
| Körperticks | 23.220 |
| Identische Folgeticks nach Checkpoint | 14.580 |
| Unerwartete Arbeitsraumverletzungen | 0 |
| Ticks mit Hinderniskontakt / Echo-Dropout | 486 / 8.826 |
| Ticks mit abgeschaltetem Modell | 11.538 |
| Eindeutig abgeschlossene Bridge-Befehle | 1.620 |
| Abgelaufene Rückmeldungen | 540 |
| Abgewiesene veraltete Beobachtungen | 810 |
| Injizierte Request-/ACK-Verluste | 270 / 270 |

Vollständiger Lauf wiederholt: alle 216 Fallbericht-Hashes identisch.
Anschließende Wiederaufnahme: alle 216 Erfolgsdateien bytegleich.
Gezielt injizierter nichtendlicher Energiezähler: im Test als Fehler erkannt
und als gültiges JSON-Diagnoseartefakt ausgegeben. Weitere Tests prüfen
Berichtsmanipulation, geänderte Runtime und Wiederholung fehlgeschlagener Fälle.

Archivierte Evidenz: [Ergebnisse](validation-2026-11-11/results.json),
[Manifest](validation-2026-11-11/matrix-manifest.json),
[Zusammenfassung mit Fall-Hashes](validation-2026-11-11/matrix-summary.json).
Die vollständigen Einzelfallberichte sind mit obigem Befehl reproduzierbar.
Fall-Hashes sind unabhängig von der Git-Revisionsbeschriftung; das Manifest
trägt zusätzlich die tatsächlich geprüfte Revision.

Keine Kontaktphysik, Hardware- oder Netzwerkabnahme. Keine Insel-/Golden-Master-
Läufe oder CI gestartet. Die visuelle Browser-QA-Grenze aus PR #31 bleibt offen.
Messdatenwerkzeuge: [MEASUREMENT-FIT.md](MEASUREMENT-FIT.md).
