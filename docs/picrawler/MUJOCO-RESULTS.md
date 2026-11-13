# MuJoCo-Abnahme vom 2026-11-12

**Das optionale Backend trägt und bewegt den freien Körper in allen 30 vorab
festgelegten Gangfällen. Der unveränderte Referenzcontroller erreicht in den
24 geschlossenen Fahrten das Ziel noch nicht.** Das ist eine Grenze der bisher
geprüften Gesamtsteuerung, kein erfolgreicher Navigationsnachweis.

Issue #42, Draft-PR #43, gestapelt auf #38. Laufzeit MuJoCo 3.3.7,
Python 3.12.14, NumPy 2.5.4. Ausführungsbasis `d35cdc58fc43b2fed3600138c2d63e26d55a7f52`;
Quellfingerabdruck `19f51e0dafecea5fd48b8f9e29f76d6dd670bb617810e101beb3f5c727e5ed23`.
Nachträgliche Änderungen betreffen Tests, Dokumentation und Ergebnisdateien;
die erfassten Laufzeitdateien sind unverändert verifiziert.

## Tests und physikalische Abnahme

- **917 Tests bestanden**, keine übersprungen, 51,48 s im finalen Arbeitscheckout.
  Das sind 864 bestehende Tests plus 53 neue MuJoCo-Tests. Das ist keine Aussage
  über Claudes späteren, parallel weiterentwickelten PSI-/Paper-Branch.
- Vorwärtskinematik unabhängig gegen alle Modell-Sites geprüft; 19 Positions-
  und 18 Geschwindigkeitskoordinaten, zwölf Motoren, Gesamtmasse 0,602 kg.
- Passiv fällt der unbestromte Körper unter Gravitation; geregelt vier tragende
  Fußkontakte und 5,90562 N Gesamtnormalkraft, entsprechend der angenommenen Masse.
- Beide weichen Gelenkgrenzen aller zwölf Gelenke erzeugen die erwartete
  entgegenwirkende Zwangskraft. Begrenzte Zieländerung und Motormomente geprüft.
- `stop` teleportiert und friert den freien Körper nicht ein. Eine äußere Kraft
  verändert die Bewegung. Stromabschaltung deaktiviert Antriebe, nicht Gravitation.
- Ungültige Befehle verändern keinen Zustand. Sensorcache ist leserein; keine
  Pose, Kontakte oder Gelenkwahrheit in der Agentenbeobachtung.
- Snapshot-Fortsetzung mit Kontakten, Sensorzufall und wartenden Tastern geprüft,
  darunter eigener frischer Python-Prozess und Integration externer Kraft.

## 30 Gangfälle nach vorab festgelegten Kriterien

Sechs Kombinationen aus Startgierwinkel +0,3/−0,4 rad und Reibung 0,4/0,8/1,2,
mit je fünf Bewegungsbefehlen. Zwei Sekunden Stand, acht Bewegung, zwei Stop.
**30/30 bestanden**, kein Sturz oder numerischer Fehler. Maximal aufgezeichnetes
Motormoment 0,1412 Nm; nach Stop maximal 5,09 mm zusätzliche Verschiebung.

| Befehl | Signierter Fortschritt in 8 s | Größter Querfehler |
|---|---:|---:|
| Vorwärts 0,02 m/s | 134,6–149,5 mm | 3,88 mm |
| Rückwärts 0,02 m/s | 147,4–159,4 mm | 3,22 mm |
| Links 0,015 m/s | 108,7–117,1 mm | 3,01 mm |
| Rechts 0,015 m/s | 102,4–113,7 mm | 3,55 mm |
| Drehen links 0,15 rad/s | 1,021–1,077 rad | 15,57 mm Translation |

Diese Werte sind Modellmessungen, keine PiCrawler-Hardwaremessungen.
Die gewünschte Geschwindigkeit ist keine Zusicherung der tatsächlichen Geschwindigkeit.
Die anfängliche Dämpfung Kd=0,08 führte in Entwicklungsläufen zur durchgehenden
Sättigung und starken Abdrift. Kd=0,02 wurde vor Validierung gewählt; die vollständigen
explorativen Daten bleiben getrennt gespeichert. Kein Parameter wurde anhand der
30 Validierungsfälle nachgestellt.

## 24 geschlossene Fahrten

Seeds 1000/1001, offene Arena und Slalom, reaktiver bzw. Gedächtniscontroller,
nominale/verrauschte/verzögerte Sensoren; höchstens 900 Entscheidungen pro Fall.
Die Controller und Sensorzustellungslogik aus #38 sind unverändert.

| Ergebnis | Fälle |
|---|---:|
| Ziel x≥0,35 m während Controllerphase | **0** |
| Zeitlimit | 23 |
| Kontaktbudget | 1 |
| Sturz / Stromabschaltung / numerischer Fehler | 0 / 0 / 0 |
| Stop-Abnahme bestanden | **24** |

21.396 Controllerentscheidungen; mit Anfangsstand und Stop 23.316 Body-Ticks.
Zusammen mit den Gangfällen 30.516 Body-Ticks bzw. 762.900 Physikschritte.
Die größte Restgeschwindigkeit nach Stop beträgt 1,12e−9 m/s, die größte
Drehgeschwindigkeit 6,17e−10 rad/s; zusätzliche Verschiebung höchstens 6,58 mm.

Die nominale offene Fahrt endet nach Ausrollen bei x=0,34808 m, knapp vor der
Zielgrenze. Das wird ausdrücklich **nicht** als Zielerfolg umgedeutet. Verrauschung,
Verzögerung und Hindernisse können deutlich größere Abweichungen verursachen.
Die Daten belegen weder einen allgemeinen Vorteil des Gedächtniscontrollers noch
robuste physische Navigation. Gate, Exploration und Energie-Stopp sind nicht Teil
dieser geschlossenen v1-Abnahme; die frühere kinematische Abnahme bleibt separat.

## Wiederaufnahme, Peripherie und Darstellung

Drei vollständige Slalom-Gedächtnisepisoden wurden bei Entscheidung 150 gespeichert
und in jeweils einem frischen Python-Prozess fortgesetzt: nominal, verrauscht und
verzögert. Je 750 weitere Entscheidungen plus 40 Stop-Ticks; Endbericht,
Körperzustand-Hash und Verlaufshash sind **exakt gleich**. Insgesamt 2.250 zusätzliche
Controllerentscheidungen in diesen Fortsetzungen. Keine Aussage über Bitidentität
auf einer anderen Engine-Version, CPU oder Plattform.

Der zusätzliche physische Peripherietest umfasst 81 Frames mit Ton, Sprache,
Sound, LED sowie Drücken/Loslassen beider Taster. Mock-Bridge: Completion,
Retry ohne Doppelausführung, Watchdog und Disconnect erfolgreich.

Vier tatsächliche HTML-Aufzeichnungen wurden mit ihrem eingebetteten JavaScript
im DOM/Canvas-Harness ausgeführt: 263 gespeicherte Frames, 210.596 Canvas-Aufrufe,
280 Kamera-Schreibvorgänge; Scrubbing, Peripherieanzeigen und Bedienelemente geprüft.
Native MuJoCo-EGL-Ansichten von Stand, Gang und Drehung wurden zusätzlich gerendert
und visuell geprüft. **Keine Browser-Sichtabnahme**: der Browserzugriff auf diese
lokalen HTML-Dateien bleibt in der aktuellen Umgebung blockiert.

## Dateien und Reproduktion

Alle Rohdaten liegen in [mujoco-results-2026-11-12](mujoco-results-2026-11-12/):
`gaits.json`, `closed-loop.json`, `summary.json`, drei Checkpoints und drei
Fortsetzungsergebnisse, `resume-checks.json`, `smoke.json`, `replay-checks.json`,
Testlog/JUnit, Provenienz und Quellverifikation. HTML-Dateien enthalten ausschließlich
aufgezeichnete Daten und benötigen keine externe Ressource.

[Installation und Befehle](MUJOCO.md), [vorab festgelegte Kriterien](MUJOCO-VALIDATION.md),
[Modellentscheidung](ADR-mujoco.md). Die Modellansichten `stand.png`, `walk.png`,
`turn.png` zeigen primitive angenommene Geometrien, kein hardwaregetreues Gehäuse.

Nächster unabhängiger Schritt: tatsächliche Befehlswirkung samt Verzögerung und
Unsicherheit aus Entwicklungsläufen identifizieren, dann aktive Raumabtastung und
physische Navigation auf neuen Seeds prüfen. Zielgrenze und Zeitbudget dieses
abgeschlossenen Berichts bleiben erhalten.
