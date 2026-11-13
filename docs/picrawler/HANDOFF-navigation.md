# Übergabe: Bewegungsprofil und aktive Navigation

## Aktueller Stand

2026-11-13, Issue #49 / Draft-PR #52, Branch `codex/49-picrawler-navigation`,
auf #43 bei `e8eed9926acc7d4563a6571b6d0f17e45b97a566`. Kein Merge, keine Änderung
an Claudes PSI-/Paper-Code, Insel, zentralem HANDOFF, Abhängigkeiten oder CI.

Implementiert und ausgeführt: Bewegungsidentifikation, kausale aktive Abtastung,
lokale Navigation und separater relativer RGB-Richtungsabgleich. Die Bildvariante
ist experimentell; empfohlener Ausgangspunkt bleibt `ActiveNavigator`.

## Geprüfter Stand

- 977 Tests bestanden, keine übersprungen, 46,53 s. 917 vorhandene +60 neue Tests.
- Profil: 36 Entwicklungs-/24 getrennte Prüffälle, alle 24 im empirischen Bereich,
  größter relativer Gainfehler 7,48 %. Alle 60 Fälle vollständig erneut ausgeführt,
  Messwerte exakt gleich; Profil aus archivierten Entwicklungsdaten exakt refittet.
- V1-Freeze `31f6ecf7df481d3967db639b752a97c93202dbca`: 48 neue Prüffahrten auf
  2000/2001. Reaktiv/Gedächtnis/schnelles Gedächtnis je 8/12 Langhorizontziele,
  aktiv 10/12. Alte 900er-Endpunkte separat: 2/4/6/6 Ziele. Zwei aktive verrauschte
  Slalomfälle am Kontaktbudget. Vollständiges Abnahmeziel **verfehlt**.
- Getrennter visueller Freeze `cbba33d0d75444a2fec4e60826ba6ff05a042366`, 24 Fälle
  auf neuen Seeds 3000/3001: unveränderte aktive v1 12/12, visuelle Variante 11/12
  Langhorizontziele; jeweils 6/12 bis 900. Bildkorrektur nicht als Verbesserung
  übernehmen. Ein gepaarter verrauschter Slalomfall verschlechtert sich zum Abbruch.
- Insgesamt 72 Stopprüfungen bestanden, keine Stürze/Abschaltungen/numerischen
  Fehler in den formalen Matrizen. Zielerfolg bedeutet nicht kontaktfreie Fahrt.
- Sechs vollständige Slalomfortsetzungen aus Entscheidung 250 in frischen Prozessen
  exakt gleich: Endbericht, Body-/Tracehash. 9897 zusätzliche Entscheidungen +Stop.
- Beide Varianten des verschlechterten Kamerafalls zusätzlich für echte Replays
  erneut gerechnet und vollständig gegen Originalbericht verifiziert.

V1-Laufzeitdateien seit ihrem Freeze unverändert. Der visuelle Versuch ergänzt nur
separate Module; Quellfingerprints vor und nach Ausführung geprüft. Die früheren
24 Prüfepisoden aus #43 sowie Seeds 1000/1001 bleiben unverändert.

## Dateien und Befehle

- Einstieg: [NAVIGATION.md](NAVIGATION.md).
- Bericht mit Kriterien, Budgets und Grenzen: [NAVIGATION-RESULTS.md](NAVIGATION-RESULTS.md).
- Entscheidung vor Implementierung: ADR-navigation.md; Folgeversuch ADR-visual-heading.md.
- Profil, vollständige gzip-Messreihe, sieben v1-/zwei visuelle Entwicklungsstände,
  beide unabhängigen Matrizen, Checkpoints/Fortsetzungen, Replays, Grafiken,
  JUnit/Log, Provenienz/Verifikation unter `navigation-results-2026-11-13/`.

```bash
.venv/bin/python -m psi_gw.body.picrawler.navigation_experiment \
  --profile docs/picrawler/navigation-results-2026-11-13/motion-profile.json \
  --split development --output /tmp/navigation-new-development
.venv/bin/python -m psi_gw.body.picrawler.visual_experiment \
  --profile docs/picrawler/navigation-results-2026-11-13/motion-profile.json \
  --split development --output /tmp/visual-new-development
```

Wiederaufnahme: passendes Modul mit `--resume checkpoint.json --output result.json`.
Visuelle Checkpoints enthalten eine Wrapperstruktur und dürfen nicht mit dem
v1-Modul verwechselt werden. Auswertungsgrafiken lesen nur gespeicherte Frames.

## Nächster Schritt

Das volle Robustheitsziel bleibt offen. Standard-v1 erreicht über beide getrennten
Seedsätze 22/24 Langhorizontziele, aber nur 12/24 bis 900 (alle offenen Fälle).
Konstante Befehlswirkung trägt bei Stop-/Start-/Schlupfzuständen nicht zuverlässig.
Nächste technische Forschung: Bildtranslation und Rotation verlässlicher trennen,
intermittierende Befehlsfolgen separat identifizieren. Neue Varianten wieder auf
neuen Prüfseeds abnehmen; bereits geprüfte 2000/2001 und 3000/3001 nicht als
unberührte Testsätze ausgeben. Keine Kriterien im Nachhinein verschieben.

## Offene Fragen

Keine weitere Grundsatzentscheidung in diesem Auftrag getroffen. Zusätzliche reale
IMU-/Encoder-Rückmeldung wäre eine eigene Hardware-/Beobachtungsvertragsentscheidung.
Die vorhandene einfache Bildkorrektur ist kein hinreichender Ersatz. Allgemeine
Navigation/SLAM und Hardwaretauglichkeit sind nicht nachgewiesen.

## Bekannte Fallstricke

- Entwicklung nur 10/11. Zwischenstände enthalten dokumentierte Timeouts/Kontakte;
  ihre Fingerprints können uncommittete Dateien bezeichnen. Formale Matrizen sind
  vor Ausführung vollständig gesichert; keine Parameteroptimierung darauf.
- Freie Einzelstrahlen löschen keine benachbarten Hindernispunkte. Hüllen und
  Unsicherheiten sind heuristisch, keine garantierte Kollisionsfreiheit.
- Bei umsortierten Paketen bleibt der echte Capture-Zeitstempel erhalten;
  widersprüchliche Captures führen Halt. Snapshots nach Scanende brauchen Index 0.
- Bildkorrektur setzt annähernden Stillstand, unveränderte Szene und angenommene
  Intrinsik voraus. Translation/Teilverdeckung können Fehlkorrekturen erzeugen.
  Der negative Prüffall bleibt gespeichert; nicht stillschweigend zum Default machen.
- Positions-/Richtungsfehler nach Stop enthalten den letzten unbeobachteten Schritt
  und Ausrollen. Keine reine Odometrie-Kennzahl oder Konfidenzintervalle behaupten.
- Browserblockade aus #43 unverändert. JS-Harness und Weggrafiken sind keine
  Browser-Sichtabnahme; keine alternative URL zum Umgehen verwenden.
- Die vollständige pytest-Aussage gilt für diesen gestapelten Robotik-Checkout,
  nicht für Claudes parallel späteren main-/Paper-Stand.

## Log

2026-11-13: Profil gemessen, technische Fehler behoben, aktive Navigation entwickelt,
48er-Prüfung abgeschlossen, negatives/teilweise hilfreiches visuelles Folgeexperiment
separat mit 24 neuen Fällen geprüft, sechs frische Fortsetzungen und zwei zusätzliche
Fallreproduktionen verifiziert, Ergebnisse und Einschränkungen dokumentiert.
