# Ausgeführte Prüfungen

## Nachprüfung der integrierten Peripherie am 2026-11-11

Geprüfte Ausgangsrevision: `d3664b06141dd65827d09863f43ad8a7361a0fcc`,
Draft-PR #31, Branch `codex/30-picrawler-sim`. Der HTTPS-Clone hatte keine
Git-Zugangsdaten. Stattdessen wurden die benötigten Dateien über die bestehende
GitHub-Verbindung geladen und gegen sämtliche Git-Blob-Hashes geprüft.
Commit- und Baumobjekte wurden hashidentisch für einen isolierten, flachen
Checkout rekonstruiert; Referenz-/Trace-Blobs und fremde Tests wurden nicht
materialisiert. `main`, Claude-Branches und PSI-Kerndateien wurden nicht geändert.

Python 3.12.14; eigene venv; `pip install -e '.[dev]'` erfolgreich.
Installiert: NumPy 2.5.4, pytest 9.2.0. Keine Projektabhängigkeit geändert.

```bash
.venv/bin/python -m pytest -q tests/picrawler tests/test_smoke.py tests/test_random_source.py
# Vor der Korrektur: 628 passed
# Nach Korrektur und acht neuen Regressionen: 636 passed
```

622 PiCrawler-Tests sowie 14 vorhandene Body-/RNG-Tests wurden ausgeführt,
kein Fall übersprungen. Enthalten sind Lautsprecher, LEDs, Taster, Energie,
Snapshot-Versionen, Mock-Bridge, Kalibrierung, Sensorik und 3D-Replay.
Die vollständigen Insel-/Golden-Master-Läufe und CI wurden nicht gestartet.
`git diff --check` ist grün.

**Gefundener und behobener Fehler:** `inject_button()` änderte sofort den
internen Peripheriezustand, während der Sensorcache erst im nächsten Tick
erneuert wurde. Ein dazwischen erstellter Snapshot ließ sich deshalb mit
`ValueError: inconsistent peripheral sensor cache` nicht laden. Tastereingaben
werden nun bis zum erfolgreichen Tick geordnet vorgemerkt; Snapshot und
Wiederaufnahme erhalten die Warteschlange. Ungültige Aktionen verbrauchen sie
nicht. Bestehende v3-Snapshots ohne Warteschlangenfeld bleiben lesbar.

Neue Regressionen prüfen diesen Zwischenzustand, Fehleratomarität, alte v3-Daten,
die exakte Zusatzenergie aller drei Audioarten plus LED über die aktiven Ticks,
die Fortsetzung laufender Sprache mit wartender Reset-Eingabe im frischen
Python-Prozess (mit Kamera, Rauschen und Dropouts) und die tatsächliche
JavaScript-Ausgabe des Peripheriepanels inklusive wörtlichem `</script>`-Text.

```bash
.venv/bin/python -m psi_gw.body.picrawler --scenario peripherals \
  --output <neues-verzeichnis> --seed 42 --noise-m 0.002 --dropout 0.02
```

| Messgröße | Tatsächlich ausgeführter Lauf nach Korrektur |
|---|---:|
| Ticks / Simulationszeit | 1.461 / 73,05 s |
| Weg | 1,750 m |
| Checkpoint / identische Folgeticks | 730 / 731 |
| Replay-Frames | 294 |
| Unerreichbare Beinstellungen | 0 |
| Hinderniskontakt-Ticks | 34 (geskriptete Annäherung) |
| Audio-/LED-Ereignisse | 10 |
| Akku | 15 → 12,6921 % |
| CPU | 78 → 82,4728 °C |
| Lastenergie / Innenwiderstandsverluste | 1.098,4920 / 57,6473 J |
| Hunger / Schaden am Ende | 0,6923 / 0,8736 |

Die gesamte erzeugte `replay.html` wurde zusätzlich im vorhandenen Node-
DOM-/Canvas-Testgerüst ausgeführt: 294 Frames gescrubbt, synchroner
Lautsprecher-/LED-/Tasterstatus und Ereignistext geprüft; Playback, Overlay,
Rotation, Ansichten und Zoom ausgeführt. 397.504 Canvasaufrufe, 298
Kamerabild-Schreibvorgänge; keine Assertion fehlgeschlagen. Das ist eine
ausgeführte JavaScript-Funktionsprüfung, keine visuelle Layoutprüfung.

**Offene Browser-QA:** Lokales Chromium bricht beim Start mit
`socket() failed: Operation not permitted` ab. Der separate Cloud-Browser
verweigert `file://` per URL-Sicherheitsrichtlinie. Es wurden keine
Sicherheitsregeln umgangen und keine Screenshots oder visuelle Abnahme
behauptet. `replay.html` muss für die visuelle Freigabe in einer dafür
autorisierten Browserumgebung geöffnet werden. Der PR bleibt Draft.

Die folgenden Abschnitte dokumentieren den früheren Stand vom 2026-11-10.

Datum: 2026-11-10. Basis: `main` bei
`ed62d4a4c158219084e202248df1de5bceea0358`. Python 3.12.14.

## Tests

```text
PYTHONPATH=src python -m pytest -q tests/picrawler tests/test_smoke.py tests/test_random_source.py
609 passed
```

595 Testfälle betreffen den neuen Bereich; 14 vorhandene Fälle prüfen den
gemeinsamen Body-Entwurf und die Zufallsquellen. Die Testumgebung stellte
`pytest` separat bereit, ohne `pyproject.toml` zu ändern.

Geprüft wurden insbesondere:

- Analytische Gelenkgeometrie, IK/FK-Rundläufe, Segmentlängen, Beintransformationen,
  ungültige und singuläre Ziele.
- Kontinuierliche Kollision an Seiten und gerundeten Ecken, Tangenten, Rückzug
  aus Kontakt und eine nur einen Mikrometer dünne Wand bei freiem Start-/Endpunkt.
- Raycast-Distanzen, Höhe, Verdeckung, Kameraorientierung und RGB-Datentyp.
- Modellrauschen/Ausfälle mit kontrollierten Zufallszahlen, fehlende Messungen
  ohne irreführendes Kappen, Trennung von Beobachtung und Wahrheit.
- Ein Tick pro Aktion, Translation/Rotation/Kreisbahn, weltfeste Standfüße,
  lange Drehungen, abrupte Befehlswechsel und konservative Körperhülle.
- Lesende Beobachtung/Replay ohne RNG- oder Zustandsänderung, unabhängige
  Rückgaben, ungültige Aktionen und fehlgeschlagene Messungen/Resets atomar.
- JSON-Wiederaufnahme mitten in einer Schwungphase mit vorversetzter NumPy-
  und Delphi-Zufallsquelle. Ein zusätzlicher Test startet einen frischen
  Python-Prozess aus anderem Arbeitsverzeichnis und vergleicht den gesamten
  Zustand einschließlich Kamera/RNG nach jedem folgenden Tick.
- Elektrische Leistungs- und Ladungsbilanz einschließlich Innenwiderstands-
  verlusten, begrenzte Restladung, stabile passive Abkühlung, thermisches
  Gleichgewicht, Drosselung, aktuelle/historische Warnflags und Abschalt-Latch.
- Bedarfsschwellen, echte Unbekannt-Werte, reine Beobachter, explizite
  Umweltänderung und Energie-/Bedürfnisfortsetzung nach JSON-Rundlauf.
- Pi-4-/Pi-5-Fixtures, PMIC-/Core-/Versorgungstrennung, fehlende Hardware,
  Firmwarefehler, injizierte Batteriequelle und lesende Collector-Pfade.
- Kalibrierprofile mit Version, Einheiten und Provenienz, vollständiger Abgleich
  mit `EnergyConfig`, CLI-Rundlauf sowie Ablehnung doppelter JSON-Schlüssel
  auch in verschachtelten Parameter-/Herkunftsobjekten.
- Sensorfrische, fehlende Echos, Medianfenster mit Ausreißern, Farbflächen,
  Verdeckung und unveränderte Ergebnisse bei geänderten Weltmetadaten.
- Mock-Bridge bei verzögerten/verlorenen Requests und ACKs, identische Retries,
  Cache-Verdrängung, abgelaufene Fristen, Reconnect, Queue-Grenzen und Watchdog.
  Fehler während ACK-Erzeugung nach ausgeführter Bewegung sperren die Sitzung,
  erhalten den realen Modellzustand und verhindern doppelte Ausführung.

Die vollständigen Insel-Golden-Master-Läufe wurden für diese additive
Vorarbeit nicht erneut ausgeführt. Der unveränderte PSI-Kern und die
Referenzartefakte wurden nicht neu bewertet. Es wurde kein CI-Workflow gestartet.

## Tatsächlich ausgeführte Szenarien

```bash
PYTHONPATH=src python -m psi_gw.body.picrawler \
  --scenario resources --output <neues-verzeichnis> --seed 42 --noise-m 0.002 --dropout 0.02
```

Die gleiche Route lief als `obstacles` ohne Kamera und als `resources` mit
synthetischer Kamera, 2 mm Rausch-Halbbreite und 2 % Dropout-Wahrscheinlichkeit.
Die Körpertrajektorie war gleich. Unterschiedliche CPU-/Startbedingungen und
Kameralast sind in den jeweiligen `summary.json`-Konfigurationen festgehalten.

| Messgröße | Ergebnis |
|---|---:|
| Ticks | 1.455 |
| Simulierte Zeit | 72,75 s |
| Zurückgelegter Weg | 1,750 m |
| Endposition | x = 0,700 m; y = 0,450 m; Ausrichtung ≈ 0 rad |
| Ticks an der Hindernisgrenze | 34, im absichtlich blockierten ersten Abschnitt |
| Ticks mit unerreichbarer Beinstellung | 0 |
| Checkpoint | Tick 727 |
| Exakt verglichene Fortsetzung | alle 728 folgenden Ticks |
| Aufgezeichnete Replay-Frames | 292 |

Zusätzlich gemessene Modellausgaben:

| Größe | Hindernisparcours ohne Kamera | Ressourcenlauf mit Kamera |
|---|---:|---:|
| Anfangs-Ladung | 80 % | 15 % |
| End-Ladung | 78,1462 % | 12,7099 % |
| Anfangs-CPU-Temperatur | 40 °C | 78 °C |
| End-/Maximaltemperatur | 57,2936 °C | 82,4633 °C |
| Minimale Akku-Klemmenspannung | 7,5703 V | 6,5162 V |
| Lastenergie | 1.021,97 J | 1.090,34 J |
| Innenwiderstandsverluste | 37,29 J | 56,90 J |
| Ticks mit thermischer Drosselung | 0 | 1.245 |
| Ticks mit Unterspannung | 0 | 0 |
| Hunger am Ende | 0 | 0,6916 |
| Schaden / Schutzbedarf am Ende | 0 | 0,8732 |

Das sind Ausgaben des ausgeführten kinematischen Modells. Die Route wurde
geskriptet; sie belegt weder einen kognitiven Lernfortschritt noch eine reale
Gehgeschwindigkeit oder dynamische Stabilität des PiCrawlers.
Auch Kapazität, Leistungsbedarf und Kühlung sind Modellannahmen. Die Tabelle
ist kein Laufzeit-/Temperaturnachweis für den konkreten Roboter.

## Replay-Prüfung

Python-Tests prüfen Offline-Einbettung, JSON-Rundlauf, sichere Behandlung von
`</script>`, Eingabevalidierung und unveränderte Eingabedaten. JavaScript-Syntax
und DOM-/Canvas-Ausführung wurden zusätzlich in Node geprüft, einschließlich
Playback, Zeitregler, Perspektive, kleiner Canvasgröße und endlicher Projektion.
Die fertige Aufzeichnung mit allen 292 Frames wurde ebenfalls durchgespielt,
einschließlich Schwungphase, Kollision und letztem Tick. Sämtliche RGB-/Alpha-
Werte der 292 Kamerabilder stimmten mit den gespeicherten Pixeln überein.
Der neue Ressourcenlauf wurde zusätzlich mit seinen optionalen Telemetrie-,
Bedürfnis-, Wahrnehmungs- und Historienfeldern durchgespielt: 249 gedrosselte,
7 Kollisions- und 3 ungültige Echo-Frames innerhalb der 292 aufgezeichneten
Samples; 393.562 endliche Canvasoperationen. Diese Framezahlen sind aufgrund
der Ausdünnung ausdrücklich nicht die Tickzahlen des vollständigen Laufs.

Eine visuelle Prüfung in einem echten Browser war hier nicht möglich:
Chromium im Executor konnte keine benötigten Sockets öffnen; der verfügbare
Cloud-Browser erlaubt keine lokalen Dateiprotokolle. Es wurde kein Schutz
umgangen. Die fehlende Browserprüfung bleibt als konkrete QA-Grenze dokumentiert.

## Optionaler PNG-/MP4-Export

`render_video.py` wurde am selben Ressourcen-HTML ausgeführt, ohne Simulation
oder eingebettetes JavaScript erneut auszuführen. Die PNG wurde visuell geprüft
und zeigt Tick 470 bei 23,50 s: Hindernisgrenze, CPU-Drosselung, Nahansicht der
Gelenke, synthetisches Kamerabild sowie die bis dahin aufgezeichneten Kurven.
Das ist ein Zwischenstand; die Werte müssen deshalb von den Endwerten oben
abweichen. Der orange Block liegt außerhalb der vier Standardfarbbänder und
erzeugt korrekt keine behauptete Farb-/Objekterkennung.

Der ausgeführte Videoexport wurde mit `ffprobe` geprüft: H.264, yuv420p,
1.600 × 900 Pixel, 12 fps, 292 Frames, 24,333 s und 2.085.862 Byte. Er enthält
den kompletten aufgezeichneten Lauf, als 3×-Wiedergabe gekennzeichnet. PNG und
Video sind eigenständige Darstellungen der Daten, keine Browser-Screenshots
und kein Nachweis einer visuellen Prüfung des HTML-Layouts.
