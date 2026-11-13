# ADR 0006: Formate für Laufdaten und Prozedur-Testfälle

- Status: angenommen
- Datum: 2026-11-09
- Autor: Claude Code
- Bezieht sich auf: ADR 0003, ADR 0005

## Kontext

ADR 0005 verlangt zwei Arten von Vergleichsdaten: exakte Testfälle einzelner Prozeduren (Ebene 1) und Daten ganzer Inselläufe für statistische Vergleiche (Ebene 2). Beide müssen vom Original und von der Python-Implementierung gleichermaßen erzeugt bzw. gelesen werden können.

Das Original schreibt bereits mehrere Protokolle (`docs/delphi-inventar.md`, Abschnitt „Daten und vorhandene Protokolle“). Zwei davon sind für Ebene 2 besonders ergiebig:

- `ach*.Prt`: pro Verhaltenszyklus eine Zeile mit Alter in Prozent der Lebensdauer und den 14 Leistungszählern (`TLeistung`).
- `Protokoll*.Dat` (geschrieben von `USmallProtokoll`): ein Ereignis pro Aktion mit Beginn und Ende, Zyklus, Situation, Objekt, Position, Inventar, allen sieben Bedürfnissen und allen drei Modulatoren.

Weitere Dateien liefern Summen je Lauf (`Consum.Prt`, `Inpro.Prt`, `eAch.prt`, `Execute.Dat`) bzw. Zeiten der Rasmussen-Stufen je Zyklus (`IntTimes.txt`, `Activities.txt`).

## Entscheidung

**Laufdaten** werden als JSON Lines gespeichert, eine Datei pro Lauf, optional gzip-komprimiert. Jede Zeile ist ein Datensatz mit dem Feld `type`:

- `run`: genau einmal, als erste Zeile. Herkunft (`delphi` oder `python`), Programmversion, Welt, Startwissen, Seed, Parameter, Quelldateien.
- `cycle`: ein Datensatz pro Verhaltenszyklus mit den Leistungszählern und, soweit vorhanden, Zeiten der Rasmussen-Stufen.
- `event`: ein Datensatz pro Ereignis aus dem Ereignisprotokoll, inklusive Bedürfnissen und Modulatoren.
- `summary`: höchstens einmal, am Ende, Summen über den Lauf.

Die Struktur der Ereignisse übernimmt die des Originals (`Protokoll*.Dat`) Feld für Feld. Aktionsnamen bleiben im Wortlaut des Originals (`Locomotion`, `Manipuliere`, `Aggression`, ...), denn sie sind zugleich das Befehlsvokabular zwischen Kognition und Welt und werden später die Aktionsnamen der `Body`-Schnittstelle.

**Prozedur-Testfälle** werden als einzelne JSON-Dateien gespeichert, eine pro Fall, mit Prozedurname, Zahlenstrom für den injizierten Zufall, Eingangszustand, Argumenten, erwartetem Ergebnis, erwartetem Folgezustand und den Vergleichsregeln (exakt bzw. relative Toleranz).

**Vokabular.** Feldnamen sind englisch (ADR 0004). Eine Tabelle in `traces/README.md` und das Modul `psi_gw.tracing.vocabulary` ordnen jedem Namen das Delphi-Original zu, zum Beispiel `thirst` zu `Durst`, `selection_threshold` zu `SelectThreshold`, `locations_discovered` zu `Leistung[NLoc]`.

**Versionierung.** Jede Datei trägt `format_version`. Der Reader lehnt unbekannte Versionen ab, statt sie zu raten.

**Verlustfreiheit gegenüber dem Original.** Konverter für Originalprotokolle übernehmen alle Felder. Was sich keinem Feld zuordnen lässt, landet unverändert in `extra`. Zeitangaben der Wanduhr (`wall_ms`, `wall_time`) bleiben erhalten, auch wenn die Python-Implementierung sie nicht erzeugt.

## Betrachtete Alternativen

- **Das Format des Originals direkt verwenden** (Semikolon-CSV, feste Spaltenbreiten). Verworfen: Sieben verschiedene Dateiformate pro Lauf, uneinheitliche Kodierung und Spaltenköpfe, keine Herkunftsangaben.
- **Parquet oder HDF5.** Effizienter für große Datenmengen, aber eine zusätzliche Abhängigkeit und schlecht lesbar in Diffs und Reviews. Kann später für Auswertungen als abgeleitetes Format dazukommen; die JSONL-Dateien bleiben die Quelle.
- **Ein festes JSON-Schema mit `jsonschema` validieren.** Verworfen für jetzt: neue Abhängigkeit (AGENTS.md verlangt dafür eine ADR) bei geringem Nutzen gegenüber Dataclasses mit eigener Prüfung.

## Konsequenzen

- Die Python-Implementierung muss dieselben Ereignisse und Zyklusdaten schreiben, die der Konverter aus dem Original erzeugt. Das ist eine Anforderung an die Inselwelt in Phase 2.
- Der Zustand in Prozedur-Testfällen ist zunächst nur für Bedürfnisse, Modulatoren und Ziellisten festgelegt. Die Darstellung des Gedächtnisnetzes wird mit dem ersten Testfall präzisiert, der sie braucht (voraussichtlich `Connect` oder `ReInforce`), und dann hier nachgetragen.
- Konverter für `Consum.Prt`, `Inpro.Prt`, `IntTimes.txt` und `Activities.txt` folgen mit Issue #7.
