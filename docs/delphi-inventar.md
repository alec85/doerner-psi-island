# Inventar des Delphi-Originals

Stand: 2026-11-09, erstellt von Claude Code für Issue #1. Strukturdaten (Zeilen, Abhängigkeiten, Deklarationen) stammen aus `scripts/delphi_inventory.py` und lassen sich jederzeit neu erzeugen. Rollenbeschreibungen beruhen auf den Deklarationen, gezieltem Lesen der Kern-Units und der Originaldokumentation in `Reality/` und `History/`. Seitenangaben beziehen sich auf „Die Mechanik des Seelenwagens“.

Alle Units des Hauptprogramms tragen denselben Kopf: *Dietrich Dörner und Jürgen Gerdes: Psi 4.9.1.200, Version vom 17. Oktober 2003*.

## Die Programme im Archiv

| Programm | Projektdatei | Zweck |
|---|---|---|
| Psi | `PsiCode/Psi.dpr` | Das eigentliche PSI auf der Insel: Kognition, Welt und Oberfläche in einem Prozess, 40 Units |
| Execute | `PsiCode/Execute.dpr` | Batch-Starter für Parameterstudien: startet Psi mit Parameterdateien aus `Execute/*.Dat` und Protokollkennung (Bedienung in `History/Execute.Txt`) |
| PMot | `PsiCode/PMot.dpr` | Kleines Demonstrationsprogramm zur Motivation (`motivation.pas`, 50 Zeilen) |
| PsiGoal | `PsiMice-Goal/PsiGoal.dpr` | Eigenständiges, späteres Modell (2004 bis 2009): Population von „Mäusen“ mit Genom, Mutation, Emotionen, Freunden und Feinden, beweglichen Zielen |

Für die Portierung zählt zunächst nur **Psi**. PsiGoal ist ein eigenes Modell und wird unten kurz beschrieben.

## Architektur des Hauptprogramms

Das Original trennt Kognition und Welt bereits sauber, und zwar über ein Netzwerkprotokoll:

```
 Kognition                    Bridge                       Welt
 UPsiMain, UStrukturen,  <->  UPsiClient (TClientSocket) <-> UPsiServer (TServerSocket, Port 2000)
 UPercept, UAction            Textbefehle, siehe              TReality, TSituation, TPsi
                              History/Kommunikation.Txt       Daten aus Reality/<Insel>/
```

Die Kognition schickt Textbefehle wie `MoveToSituationWithDirection`, `MoveToObjekt` oder `Manipuliere`, die Welt antwortet mit Ereignissen wie `SituationChanged`, `InselChanged` und `OK`. Die Welt verändert außerdem selbst die Bedürfnisse: Fortbewegung kostet Energie und Wasser (`SetMotivation('Hunger', Distance*0.0002)`), unebener Boden und Unfälle verursachen Schaden.

Diese Trennung entspricht unserer `Body`-Schnittstelle (`docs/architecture.md`) und ist ein starkes Argument, sie in der Portierung beizubehalten: Die Inselwelt wird ein `Body`, der Befehlssatz aus `Kommunikation.Txt` liefert die Aktionsnamen.

## Der Verhaltenszyklus

Die Hauptschleife liegt nicht in einer Kern-Unit, sondern in der Formular-Unit `UFPsi.pas` (ab etwa Zeile 340). Ein Zyklus:

1. Lebensbilanz: Leistungszähler fortschreiben, bei leeren Speichern (Hunger, Durst, Schaden) „Exitus“ und Neustart der Speicher.
2. Wahrnehmung bei Neuorientierung: `Percept` (UPercept), Ergebnis ins Protokollgedächtnis (`Protocoll`).
3. `NeedAndCompetence` (UPsiMain): Bedürfnisse und Kompetenz aktualisieren.
4. `Motivation` (UPsiMain): aktuelles Motiv wählen, Handlungstendenzen berechnen.
5. `GoalGen` (UPsiMain): Zielliste `GoalList` bilden, abhängig von Motivstärken und Selektionsschwelle.
6. `LookAround` (UPsiMain): Gibt es in der aktuellen Situation ein Ziel oder eine zielführende Assoziation?
7. Falls nicht, die **Rasmussen-Leiter** (so im Quelltext kommentiert): gegebenenfalls `QuickMove`, dann `Automatismus`, dann `PlanenUndTun`, als letzte Stufe `WhatCouldBeDone` (Versuch und Irrtum).
8. Ohne aktives Motiv: `Ruhe`.

Das Buch beschreibt genau diese Prozeduren und nennt sie mit Unit (Kapitel 1, S. 28 bis 30). Die Formeln für Handlungstendenzen und Motivstärke finden sich auch im zweiten Projektdokument (`psi-oup-version-draft-jan-08.pdf`, Abschnitt zur Motivverwaltung).

## Kerndatenstrukturen (UStrukturen)

| Struktur | Deklaration | Bedeutung |
|---|---|---|
| Neuron | `record activity, namneuron, axon: array[TAxon] of ToSyn` | Knoten des Gedächtnisnetzes; jede Achsenart hat eine eigene Synapsenliste |
| Synapse | `record weight, timup, ThisNeuron, lastsyn, nextsyn, SpaT` | Gewichtete Verbindung mit Zeitstempel und räumlich-zeitlicher Relation (`TSpat`: x, y, z, t) |
| Achsen | `TAxon = (por, ret, sub, sur, toSatis, toGoal, toNeed, ToAvers, Lan, Pic)` | Die vier Quad-Richtungen (S. 44 ff.) plus Verbindungen zu Befriedigung, Ziel, Bedürfnis, Aversion, Sprache und Bild |
| Neuronentypen | `TNeuron = (Sensory, Motor, Need, Protocol, Control, ShortTerm)` | |
| Motive | `TMotiv = (NilMotiv, Hunger, Durst, Nukleo, Schaden, Bestimmtheit, Kompetenz, Affili)` | Drei existenzielle, ein „Sammel“-Bedürfnis (Nukleotide), zwei informationelle, ein soziales |
| Modulatoren | `TModulat = (Arousal, ResolutionLevel, SelectThreshold)` | Aktiviertheit, Auflösungsgrad, Selektionsschwelle (S. 98 f.) |
| Tendenzen | `TTendenz = (Safeguard, Aggression, Flight, SpecExplo, DivExplo)` | Sicherung, Angriff, Flucht, spezifische und diversive Exploration |
| Arbeitsgedächtnis | `KZG: array[0..7]`, `Prefront: array[0..9]`, `Situation`, `Objekt`, `GoalList`, `ShortTermList`, `Uncertainty` | Globale Variablen |
| Bedürfnisse | `BedIn[hunger..affili]` (Bedürfnisneuronen), `Store`, `motivgewicht`, `inkrement`, `dekrement` | Globale Arrays |
| Modulation | `modulat`, `modulatg`, `modulatmin`, `modulatmax: array[TModulat]` | Globale Arrays |

Die Liste der internen Prozesse `TIntProc` (Operatorsuche, Automatismen, Pläne, Aggression, Regression, Lernen appetitiver und aversiver Ziele) ist zugleich das Vokabular der Prozessprotokolle und eignet sich als Grundlage für das Trace-Format (Issue #3).

## Die Units im Einzelnen

**Rolle:** K = Kern der Kognition, W = Welt, B = Bridge zwischen Kognition und Welt, P = Protokolle und Ein-/Ausgabe, H = allgemeine Hilfsfunktionen, G = Oberfläche und Visualisierung, X = nicht im Build von `Psi.dpr`.

### Kern, Welt und Bridge

| Unit | Zeilen | Rolle | Inhalt |
|---|---:|---|---|
| `UStrukturen.Pas` | 2849 | K | Datenstrukturen (s. o.), Netzoperationen (`Connect`, `ReInforce`, `Decay`, `Junction`, `Trace`, `LookFor`), Listenoperationen auf Synapsenlisten (`LSection`, `LUnion`, `LDifferenz`), Protokollgedächtnis (`Protocoll`, `ReInforceRetro`), Bewertungsfunktionen für Pläne (`S_Aufwand`, `S_Gewissheit`, `S_Nutzen`), Initialisierung inklusive Seed. Etwa 80 globale Variablen im Interface |
| `UPSIMain.Pas` | 2557 | K | Handlungsregulation: `NeedAndCompetence`, `Motivation`, `GoalGen`, `InterMedGoals`, `LookAround`, `Association`, `Confirmation`, `Automatismus`, `Planen`, `Actiplan`, `PlanenUndTun`, `WhatCouldBeDone`, `Ruhe` |
| `UPercept.Pas` | 1075 | K | Wahrnehmung (`Percept`): Situation abtasten, sensorische Schemata bilden und wiedererkennen |
| `UAction.pas` | 432 | K | Ausführung: `SingularLocoMot`, `SingularManipul`, `Aggress`, `Regress` |
| `UParam.pas` | 175 | K | Parameter aus Datei und Kommandozeile prüfen und setzen (`CheckParams1`), Protokolldateien öffnen |
| `UPsiServer.pas` | 1251 | W | Die Insel: `TReality` (liest `Situationen.Dat`, `Manipulation.Dat` usw.), `TSituation`, Wirkung von Bewegung und Manipulation auf die Bedürfnisse, TCP-Server auf Port 2000 |
| `UPsiClient.pas` | 1767 | B | Gegenstück auf Seite der Kognition: Socket, Befehle senden, Ereignisse empfangen, Bilder der Situation aufbauen, Timer für Animation und zeitgesteuerte Objektveränderungen |
| `UBag.pas` | 249 | B | Inventar von Psi (`TBag`) und Listen für Nehmen und Geben (`TTakeList`, `TGiveList`) |

### Protokolle, Hilfsfunktionen

| Unit | Zeilen | Rolle | Inhalt |
|---|---:|---|---|
| `USmallProtokoll.pas` | 209 | P | CSV-Zeitreihen von Motiven, Emotionen, Modulationen (`OpenPrt`, `WritePrt`) |
| `Ucsv.pas` | 167 | P | Klasse für das CSV-Format der Protokolle |
| `UHtml.pas` | 416 | P | HTML-Ausgabe, wird von keiner Unit verwendet |
| `UInfo.pas` | 152 | P | Textausgabe in ein Memo-Fenster |
| `UGeneral.pas` | 664 | H | Debug-Ausgaben, Ini-Datei (`Ini`), Kommandozeile, JPEG |
| `UStrList.Pas` | 426 | H | Erweiterte Stringliste, Parser für das Textprotokoll |
| `Menue.Pas` | 717 | H | Geometrie (Distanz, Winkel, Polarkoordinaten), Zeichenhilfen, Zeitmessung; Name irreführend |
| `UDefine.pas` | 87 | H, X | Alternative Motivtypen, wird von keiner Unit verwendet |

### Oberfläche und Visualisierung

Für die Portierung nur insoweit relevant, als hier Verhalten versteckt sein kann. Das gilt ausdrücklich für `UFPsi.pas`, das die Hauptschleife enthält, und für `UFace.Pas`, das ein eigenes Gesichtsmodell für den Emotionsausdruck enthält.

| Unit | Zeilen | Inhalt |
|---|---:|---|
| `UFPsi.pas` | 1107 | Hauptformular, **Hauptschleife**, Start, Protokolldateien, 500-ms-Thread für Anzeigen |
| `UFace.Pas` | 1468 | Gesichtsmodell mit Muskeln und Fasern (`TMuskel`, `TFaser`); bildet Bedürfnisse, Aktiviertheit, Furcht und Hilflosigkeit auf Mimik ab |
| `UFNetMon.pas` | 844 | Monitor des Gedächtnisnetzes |
| `UFValues.pas` | 733 | Wiederverwendbare Zeitreihen-Anzeige (Basis für Motive, Emotionen, Modulationen) |
| `UFValChange.pas` | 615 | Werte zur Laufzeit ändern |
| `UFSituation.pas` | 262 | Anzeige der aktuellen Situation |
| `UFEEG.pas` | 258 | Pseudo-EEG der Neuronentypen; zieht beim Neuzeichnen Zufallszahlen (s. u.) |
| `UFFace.Pas`, `UFFaceDlg.Pas` | 200, 30 | Fenster für das Gesicht |
| `UFEmotionen.pas`, `UFMotive.pas`, `UFModulationen.pas` | 111, 115, 122 | Zeitreihenfenster |
| `UFAction.pas`, `UFPercept.pas`, `UFShowBitmap.pas`, `UFUmgebung.pas` | 101, 77, 161, 87 | Weitere Anzeigefenster |
| `UFListe.pas`, `UFMemo.pas`, `UFDlgInput.pas` | 113, 41, 137 | Listen, Textausgabe, Eingabedialog |
| `UBitmaps.pas`, `Upb.pas`, `UpbPsi.pas`, `UBar.pas` | 311, 194, 153, 141 | Zeichenhilfen; `UBar` wird nicht verwendet |
| `USound.Pas` | 140 | Töne und Sprachausgabe (`Speak`, `SpeakRandom`, `Utter`) |

### Nicht im Build von Psi.dpr

| Unit | Zeilen | Bemerkung |
|---|---:|---|
| `UPsiMainxy.Pas` | 2423 | Zweite Fassung von `UPsiMain` mit gleichem Unit-Namen; Versionskommentare bis 17.5.03, 294 abweichende Zeilen. Vermutlich Vorgänger, für Vergleiche aufbewahren |
| `UFNet.pas` | 526 | Netzanzeige von 1998/99, von keiner Unit verwendet |
| `UFSchema.pas` | 409 | Schema-Anzeige, nicht im Build |
| `UFExecute.pas` | 318 | Gehört zu `Execute.dpr` |
| `motivation.pas` | 50 | Gehört zu `PMot.dpr` |

## Zufallsquellen

**Seed.** `UStrukturen.Pas` liest den Seed beim Start aus `Psi.Ini`, Abschnitt `[Psi]`, Schlüssel `RandSeed` (Vorgabe 2, im Archiv steht 16), und merkt ihn sich als `BatNr` (Zeilen 2716 bis 2718; `UParam.pas` Zeile 109 wiederholt die Zuweisung). Es gibt kein `Randomize`. Der Seed ist also reproduzierbar setzbar.

**Ein einziger globaler Generator für alles.** Delphis `Random` ist global. Ihn nutzen:

| Bereich | Aufrufe | Wo |
|---|---:|---|
| Kognition | 33 | `UPSIMain.Pas` (18, u. a. Suchtiefe, Abbruch von Assoziation und Planung über `random > ResolutionLevel`), `UStrukturen.Pas` (12, u. a. `RandomChoice`), `UFPsi.pas` (3, `QuickMove`) |
| Welt | 1 | `UPsiServer.pas`: Unfall bei Bewegung (`Accident > Random`) |
| Oberfläche | 21 | `UFEEG.pas` (18, im Zeichen-Handler `PBEEGPaint`), `USound.Pas` (3, zufällige Äußerungen) |

Weil die EEG-Anzeige bei jedem Neuzeichnen Zufallszahlen verbraucht, hängt die Zufallsfolge der Kognition davon ab, wie oft Windows dieses Fenster neu zeichnet, und ob es überhaupt sichtbar ist.

## Echtzeitabhängigkeiten

- Kognition und Welt kommunizieren asynchron über einen Socket; die Hauptschleife ruft zwischendurch `Application.ProcessMessages` auf.
- `UPsiClient` arbeitet mit vier Timern und zwei Zoom-Timern, deren Intervalle mit `Fast` (Kommandozeilenparameter `Geschwindigkeit`) skaliert werden, sowie mit Warteschleifen über die Systemuhr (`Delay`, `Wait`).
- Das Alter `Age`, an dem zeitgesteuerte Objektveränderungen der Welt hängen, ist Wanduhrzeit in Millisekunden, sofern nicht `bUseLifeTime` gesetzt ist.
- `TReality.msec` misst ebenfalls Wanduhrzeit.
- Ein Thread-Timer schreibt alle 500 ms die CSV-Zeitreihen und aktualisiert das Gesicht.

**Empirischer Befund.** Im Archiv liegen zwei Läufe mit Seed 16: `Protokoll/Test/ach16.Prt` (26.05.2003) und `ach16(1).Prt` (09.03.2014). Die Zykluszeiten unterscheiden sich ab dem ersten Zyklus (2080 gegen 2108 ms), die Leistungszähler nach dem zweiten Takt: Zähler der erfolglosen Manipulationen 3 gegen 2. (Die erste der 15 Spalten ist das Alter in Prozent von `MaxLife`, geschrieben in `UFPsi.pas` vor den 14 Leistungszählern.) **Einschränkung:** Die beiden Läufe stammen aus verschiedenen Programmversionen, Psi 4.9.0.201 im Jahr 2003 (Kopf von `vprot16.prt`) und Psi 4.9.1.200 im Jahr 2014 (Kopf von `Protokoll(1).Dat`). Die Abweichung kann also auch am Code liegen und ist für sich genommen kein Beleg für Nichtdeterminismus. Belastbar sind die oben beschriebenen Mechanismen; ob sie sich in der Praxis auswirken, zeigt die Vorabmessung aus ADR 0005 (mehrere Läufe mit gleichem Seed und gleicher Version).

**Nachtrag (2026-11-09).** Unter Wine mit `Geschwindigkeit=0.0` und Start über das Menü sind Läufe mit gleichem Seed über 72 Zyklen bit-identisch (`docs/delphi-build.md`, Abschnitt „Reproduzierbarkeit unter Wine“). Die unten beschriebenen Mechanismen wirken sich in diesem Modus also zumindest nicht kurzfristig aus.

**Konsequenz für ADR 0003.** Ein fester Seed allein macht das Original nicht reproduzierbar. Für exakte Referenz-Traces müsste die instrumentierte Kopie mindestens (1) die Welt synchron statt über den Socket ansprechen, (2) der Kognition einen eigenen Zufallsgenerator geben oder die Zufallsnutzung der Oberfläche abschalten, (3) `bUseLifeTime` erzwingen und die Timer durch einen Taktzähler ersetzen. Gelingt das nicht oder verfälscht es das Verhalten, bleibt der statistische Vergleich über viele Läufe, den ADR 0003 bereits als Rückfallebene vorsieht. Diese Abwägung gehört in eine eigene ADR, bevor Issue #4 beginnt.

## Globaler Zustand

Nahezu der gesamte Zustand von Psi liegt in globalen Variablen, vor allem im Interface von `UStrukturen` (etwa 80): Arbeitsgedächtnis, Bedürfnisse und Speicher, Modulatoren, Handlungstendenzen, Leistungszähler, offene Protokolldateien und Verzeichnisse. Weitere Globale haben `Menue` (14), `UPercept` (`LocSit`), `USmallProtokoll` (`StartTime`, `PlayTakt`) und die Formular-Units. Für die Portierung heißt das: Der Python-Kern braucht ein explizites Zustandsobjekt (etwa `PsiState`), in dem diese Variablen gebündelt und durch die Prozeduren gereicht werden. Die Zuordnung der globalen Variablen zu Feldern dieses Objekts ist ein sinnvoller erster Schritt von Phase 2.

## Daten und vorhandene Protokolle

| Ordner | Inhalt |
|---|---|
| `Reality/Insel`, `Reality/InselIII`, `Reality/Kanal` | Weltdefinitionen; Formate in `Reality/Dateiformate.Txt` |
| `PsiDaten/` | Startwissen und Parameter von Psi (`Param.Dat`, `origParam.Dat`, `Vorwissen.Dat`, `Take.Dat`, `Give.Dat`, `Utter.Dat`, `Face.Dat`) sowie Varianten (`InselIII`, `johanna`, `Viola`, `vari1`, `ForgetIt`) |
| `Execute/` | 22 Parameterdateien für Batchläufe |
| `History/`, `Reality/*.Txt` | Originaldokumentation: Bedienung, Dateiformate, Kommunikationsprotokoll, Fenster |
| `Protokoll/Test/`, `Protokoll/depress/` | Protokolle früherer Läufe mit den Seeds 1, 16 und 30, unter anderem aus 2003 und 2014 |
| `../PsiCode-zip-laufdaten/` | Abweichende Laufdaten aus der zweiten Kopie im Archiv |

Die Protokollarten (`ach*.Prt` Leistungsbilanz je Zyklus, `actu*.prt` Ablaufprotokoll, `consum.Prt` Verbrauch und Gewinn, `vprot*.prt`, `Inpro*.Prt`, `IntTimes`, `Activities`) beschreibt das Buch in Kapitel 6 (um S. 310). Die CSV-Dateien (`Motive`, `Emotionen`, `Modulationen`) sind im 500-ms-Takt der Wanduhr abgetastet, also nicht zyklussynchron.

Am ergiebigsten ist das Ereignisprotokoll `Protokoll*.Dat` aus `USmallProtokoll`: ein Eintrag pro Aktion mit Beginn und Ende, Takt, Situation, Objekt, Position, Inventar, allen sieben Bedürfnissen und allen drei Modulatoren. Ältere Versionen (4.9.0.100) schreiben es ohne die Spalte `Nr`. Für den Lauf von 2014 stimmen die Leistungszähler aus `ach16(1).Prt` in jedem Takt exakt mit den abgeschlossenen Aktionen im Ereignisprotokoll überein. Konverter für beide Formate liegen in `psi_gw.tracing.delphi_protocols` (ADR 0006).

Der Lauf von 2014 entstand laut den Kopfzeilen der CSV-Dateien unter Windows 7 auf einem Rechner namens `AS-LAPTOP`.

## PsiMice-Goal

Eigenständiges Modell in 12 Units, Versionskommentare von November 2004 bis 2009. Kern ist `UEmoStructures.pas` (4391 Zeilen): Mäuse mit Genom (`TGeneralParam`, Mutationsgrenzen), Bedürfnissen, Emotionen, Plänen, Hilferufen (`TCryForHelp`), Freund- und Feindbeziehungen. `URealityStructures.pas` modelliert eine kontinuierliche 2D-Welt mit Polygonen und Zielen. Der Seed ist fest auf 1 gesetzt. Auffällig: Zu `UFReality.dfm` fehlt die `.pas`-Datei, und `UFAngle.pas` gehört nicht zum Build.

Für das Projekt ist PsiGoal später interessant (Populationen, Evolution von Parametern, soziale Motive), für die Portierung von PSI aber nicht nötig.

## Zuordnung zu den Buchkapiteln

Die Kapitelstruktur stammt aus der Einleitung des Buches, die Seitenangaben aus dem Register. Die Zuordnung der Units ist eine erste Einschätzung und sollte beim Portieren der jeweiligen Teile präzisiert werden.

| Kapitel | Thema | Units und Prozeduren |
|---|---|---|
| 1 | Handlungsregulation im Überblick, die Insel | `UFPsi` (Hauptschleife), `UPsiMain` (Motivation, GoalGen, LookAround, PlanenUndTun, WhatCouldBeDone), `UPsiServer` |
| 2 | Datenstrukturen, Schemata, Quads (S. 44 ff.), sensorische Schemata (S. 50 ff.) | `UStrukturen` (Neuron, Synapse, `TAxon`), `UPercept` |
| 3 | Operationen in neuronalen Netzen: Feldprozesse, Zielauswahl (3.2.1, S. 93), Selektionsschwelle (S. 98 f.), Planen (S. 144 ff.), Verhaltensprogramme (S. 153 ff.), Protokollgedächtnis (S. 155 ff.) | `UStrukturen` (Listen- und Netzoperationen, `Protocoll`), `UPsiMain` (`GoalGen`, `Planen`, `ActivateAuto`, `Association`) |
| 4 | Handlungsregulation im Detail | `UPsiMain`, `UAction` |
| 5 | Emotionale Regulation | `UStrukturen` (Modulatoren, `SetModulat`), `UPsiMain` (`NeedAndCompetence`, Tendenzen in `Motivation`), `UFace` (Ausdruck) |
| 6 | Empirische Prüfung, Inselversuche, Protokolldateien | `UFPsi`, `UParam`, `USmallProtokoll`, `Execute`, Protokolle unter `Protokoll/` |
| 7 | Abschließende Würdigung | |

## Strukturdaten neu erzeugen

```bash
python scripts/delphi_inventory.py --json /tmp/inventar.json
```

Das Skript ist ein heuristischer Scanner. Bekannte Grenzen: Methoden innerhalb von Klassen werden teils nicht als Routinen gezählt (deshalb zeigt `UPsiClient` 0), und typisierte Konstanten können als globale Variablen erscheinen (deshalb die hohe Zahl bei `UFace`).
