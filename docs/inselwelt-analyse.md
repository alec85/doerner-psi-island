# Inselwelt: Analyse für die Portierung

Stand: 2026-11-10, Issue #20. Grundlage für ADR 0012. Zeilenangaben beziehen sich auf `reference/delphi-original/PsiCode`.

## Aufbau im Original

Die Welt läuft im selben Prozess wie die Kognition, ist aber als Server (`UPsiServer.pas`, Klassen `TReality`, `TSituation`, `TPsi`) über einen TCP-Socket auf Port 2000 vom Client (`UPsiClient.pas`, `TPsiClient`) getrennt. Der Client gehört zu Psi: Er baut aus den Nachrichten der Welt das Bild der aktuellen Situation, führt die Liste der zeitversetzten Objektänderungen und meldet Psis Handlungen an den Server.

Die Welt ist in Textdateien beschrieben (`Reality/InselIII`, Format in `Reality/Dateiformate.Txt`):

- `Situationen.dat`: 101 Situationen mit Inselposition, Himmels- und Bodenfarbe, Horizontpolygon, Objekten (Position und Bitmapname) und Fortbewegungen (Richtung, Zielsituation, Distanz, Unfallwahrscheinlichkeit, Glätte).
- `Manipulation.Dat`: Handlungen an Objekten (Art, Objekt vorher, Objekt nachher, Ton, Bedürfniswirkungen).
- `Aktionen.Dat`: zeitversetzte Rückverwandlungen von Objekten (z. B. nachwachsende Pflanzen).
- `Umgebung.dat`, `Behaviour.Dat`: Inselkarte und Verhalten.

Der Nachrichtenablauf ist in `Reality/Kommunikation.Txt` dokumentiert. Nachrichten sind Text in spitzen Klammern; der Client zerlegt sie in `TPsiClient.ReceiveText` (`UPsiClient.pas`, Zeile 393) und kennt `SituationChanged`, `ChangeObject`, `SetManipulationen`, `NewSituation`, `SetUmgebung`, `SetMotivation`, `UmgebungChanged`, `Sound`, `Info`, `Echo`, `SetID`, `SetBehaviour`, `DoManipuliere`, `OK`, `Moved`, `GetGravity`.

## Was Psi sieht

Wahrnehmung (`Percept`, `UPercept.Pas`, Zeile 694) tastet ein Bild Pixel für Pixel ab und sucht schwarze Linien (24 Zugriffe auf `Pixels[...]`, verglichen mit `clBlack`). Das Bild kommt aus `TPsiClient.ActSit` (Zeile 1188): Steht Psi an einem Objekt, ist es die Bitmap dieses Objekts, sonst das Bild der Situation (`bmActSit`).

Das Situationsbild entsteht in `BuildbmActSit` (Zeile 587): Boden und Himmel als GDI-Polygone in den Farben aus `Situationen.dat`, darüber die Objekte als maskierte Bitmaps (`DrawBitmapMaskAndSprite`, `UBitmaps.pas`). In allen 101 Situationen der Insel ist keine Himmels- oder Bodenfarbe schwarz (geprüft durch Auswertung der Datei). Schwarze Pixel stammen also nur aus den Objektbitmaps. Für die Wahrnehmung muss deshalb das Einsetzen der Bitmaps pixelgenau stimmen; die Rasterung der GDI-Polygone spielt für die schwarzen Pixel keine Rolle, solange sie keine Objektpixel überdeckt (Polygone werden zuerst gezeichnet).

Die Bitmaps liegen unter `reference/delphi-runtime/PsiCode/Bitmaps`.

## Zufall in der Welt

`TReality.MoveToSituation` (`UPsiServer.pas`, Zeile 456) zieht bei jeder gelungenen Fortbewegung eine Zahl (`if Accident > Random`). Das ist die Aufrufstelle `UPsiServer.SetMotivation#1` im Mitschnitt. Sie zieht aus demselben Generator wie die Kognition.

## Bedürfniswirkungen der Welt

Die Welt meldet Bedürfnisänderungen als Text: `SetMotivation <Name> <Wert>`. Bei Fortbewegung formatiert der Server den Wert mit `Format('%f', ...)`, also mit zwei Nachkommastellen: Hunger `Distanz * 0.0002`, Durst `Distanz * 0.0004`, Schaden `(1 - Glätte) * Distanz * 0.07`, bei Unfall zusätzlich Schaden 0,07. Werte unter 0,005 kommen als `0.00` an. Die Rundung durch das Textformat gehört damit zum Verhalten des Originals. Bei Manipulationen werden die Werte aus `Manipulation.Dat` unverändert als Text weitergereicht.

## Zeit in der Welt

- Der Server hat eine Wanduhr (`TReality.msec`, Zeile 498), mit der er Zeitpunkte von Objektänderungen vermerkt. Die zeitgesteuerte Aktualisierung, die sie benutzen würde (`UpdateSit`), ist auskommentiert.
- Zeitversetzte Rückverwandlungen schickt der Server als `ChangeObject <dt> ...`. Der Client rechnet sie in Psis Alter um (`bUseLifeTime` ist gesetzt, Zeile 297): fällig bei `Round(Age + dt * 3600000 / 2500000)` (Zeile 1254).
- Ausgelöst werden sie in `OnTimer3` (Zeile 1259), einem Fenster-Timer: Bei jedem Timerereignis werden alle fälligen Änderungen an den Server geschickt. Timerereignisse kommen nur in der Nachrichtenschleife an, also an den Stellen mit `Application.ProcessMessages`. Ob an einer solchen Stelle ein Timerereignis anliegt, hängt von der Wanduhr ab. Die beobachtete Gleichheit wiederholter voller Leben spricht dafür, dass in der Praxis bei jedem Durchlauf eines anliegt. Das ist zu prüfen.
- Weitere Timer (`OnTimer1`, `OnTimer2`, `OnTimer4`, Zoom-Timer) dienen nach erstem Lesen der Animation der Anzeige. Zu prüfen ist, ob einer davon Nachrichten an den Server schickt oder Zustand ändert, den die Kognition liest.

## Timer und Nachrichtenschleife (Stand nach weiterem Lesen)

**Geschwindigkeit.** Die Referenzläufe starten mit `Geschwindigkeit=0.0`; damit ist `PsiClient.Fast = 0` (`UFPsi.pas`, Zeile 669). Alle Timer, deren Intervall über `SetTimer` gesetzt wird, bekommen dann `Max(1, Round(0 * Intervall)) = 1` Millisekunde (`UPsiClient.pas`, Zeile 1747). `autonomspeed`, das `Fast` an das Arousal koppeln würde, wird nirgends gesetzt und bleibt `false`.

**Die Timer im Einzelnen.**

| Timer | Auslöser | Wirkung | relevant für die Kognition |
|---|---|---|---|
| `Timer1` | Nachricht `NewSituation` | fragt die Situation neu an | nein: der Server sendet `NewSituation` nie (alle Aufrufe auskommentiert) |
| `Timer2` | `DoManipuliere` | spielt das Verhalten einer Manipulation ab und schickt am Ende `Manipuliere` an den Server | ja, aber nur innerhalb einer Warteschleife, während die Kognition blockiert ist |
| `Timer3` | läuft immer | schickt fällige zeitversetzte Objektänderungen an den Server | ja |
| `Timer4`, Zoom-Timer | Ortswechsel, Annäherung | Animation; solange sie laufen, ist der Client „beschäftigt“ (`Busy`) | indirekt: `UAction.Wait` wartet, bis sie fertig sind |

**Bild für die Wahrnehmung.** Der Server schickt die Situation immer in 160 × 160 Pixeln. Ist Psi an keinem Objekt, ist der Ausschnitt `r1` das ganze Bild, und `bmActSit` ist eine unverzerrte Kopie (`TReality.GetSituation`, `UPsiServer.pas`, Zeile 313). Ist Psi an einem Objekt, ist der Ausschnitt 50 × 50 und wird gestreckt; die Wahrnehmung nimmt dann aber nicht `bmActSit`, sondern die Bitmap des Objekts selbst (`ActSit`). Ein Strecken muss für die Wahrnehmung also nicht nachgebildet werden.

**Durchläufe der Nachrichtenschleife.**

| Ort | Stellen | Art |
|---|---|---|
| `TFPsi.Simulation` | Zeilen 246, 393, 424, 470, 517 | einzelner Durchlauf |
| `Association`, `Planen`, `Automatismus` (2), `WhatCouldBeDone`, `LookAround` | `UPSIMain.Pas`, Zeilen 535, 1212, 1650, 1656, 2021, 2470 | einzelner Durchlauf |
| `UAction.Wait` (aus `Aggress`, `Regress`, `SingularLocoMot`, `SingularManipul`) | `UAction.pas`, Zeile 35 | Schleife, solange der Client beschäftigt ist |
| `TPsiClient.Wait` (aus `Start`, `Aggression`, `Regression`, `MoveToSituationWithDirection`, `Manipuliere1`) | `UPsiClient.pas`, Zeile 1195 | Schleife bis zur Antwort `OK` |
| `TPsi.Wait` (Server, aus `GetGravityPoint`) | `UPsiServer.pas`, Zeile 985 | Schleife bis zur Antwort des Clients; Ort des beobachteten Fehlerdialogs „GravityList“ |
| `TFNetMon` (Netzanzeige), `TFPsi.SetSimulRun`, Konstruktor des Clients | | Anzeige bzw. Start |

In den Warteschleifen ist die Kognition blockiert; ihr Alter ändert sich dort nicht. Was in ihnen geschieht, hängt deshalb nicht davon ab, wie viele Durchläufe die Wanduhr erzwingt, solange nur Animation, Nachrichten und fällige Objektänderungen verarbeitet werden. Die Zufallszüge der Welt (Unfall bei Fortbewegung) fallen ebenfalls in eine solche Warteschleife.

**Präzisierte Hypothese für `pump()`.** Bei jedem Durchlauf werden alle wartenden Nachrichten in beide Richtungen bis zur Ruhe verarbeitet, und `Timer3` feuert. Für die einzelnen Durchläufe ist das plausibel, weil sein Intervall 1 ms beträgt und zwischen zwei Durchläufen fast immer Kognitionsarbeit liegt. Nicht sicher ist, ob eine Antwort über den Socket schon im selben Durchlauf ankommt, in dem sie abgeschickt wurde. Prüfen lässt sich das mit dem Mitschnittwerkzeug: Haltepunkte auf `TApplication.ProcessMessages` und `TPsiClient.OnTimer3`, jeweils mit Psis Alter.

## Offene Fragen für die Portierung

1. Hypothese zu `pump()` mit dem Mitschnittwerkzeug prüfen (siehe oben). Dafür die Adressen von `TApplication.ProcessMessages`, `TPsiClient.OnTimer3` und `TPsiClient.ReceiveText` im Maschinencode bestimmen.
2. Golden-Master-Bilder: Pixeldaten von `bmActSit` und von Objektbitmaps aus dem laufenden Original lesen und mit dem Python-Renderer vergleichen.

Geklärt: `TFPsi.OnSituationChanged` ruft `FAction.pbUpdate` und `FSituation.pbUpdate` auf. Beide lösen nur ein Neuzeichnen aus; die Zeichenroutinen (`pbPaint`) kopieren Bitmaps des Clients (`DrawSit`, `DrawActSitWithBehaviour`) und rufen keine Funktionen der Kognition auf. Anders als bei der Werteanzeige (ADR 0011) gibt es hier keine Seiteneffekte.
