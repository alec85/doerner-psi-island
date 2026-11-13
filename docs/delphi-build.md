# Das Original zum Laufen bringen

Stand: 2026-11-09, Issue #2. Dieses Dokument beschreibt, wie das Delphi-Original ohne Windows-Rechner läuft. Das Free-Pascal-Testgerüst ohne Oberfläche (Ebene 1 aus ADR 0005) folgt in einem eigenen Abschnitt, sobald es existiert.

## Windows-Programm unter Wine

Das mitgelieferte `Psi.exe` (Psi 4.9.1.200, siehe `reference/delphi-runtime/HERKUNFT.md`) läuft unter Wine 9.0 auf Ubuntu 24.04 mit einem virtuellen Bildschirm (Xvfb), vollständig mit Oberfläche: Inselkarte, Gesicht, Zeitreihen und Protokollfenster. Kognition und Welt kommunizieren dabei wie unter Windows über TCP auf `localhost:2000`.

### Einrichtung

```bash
sudo scripts/setup_wine.sh        # Wine 32 Bit, Xvfb, xdotool, ImageMagick
```

Das Skript ist idempotent. Im Cloud-Arbeitsbereich der Agenten läuft es als root ohne `sudo` in etwa 40 Sekunden.

### Ein Lauf

```bash
python scripts/run_original.py --seed 16 --max-life 20000 --out runs/seed16
```

Das Skript

1. setzt mit `scripts/assemble_original.sh` aus `reference/delphi-original/` und `reference/delphi-runtime/` ein Laufverzeichnis zusammen (die Referenzordner bleiben unberührt),
2. schreibt eine Parameterdatei `Execute/<id>.Dat` mit `MaxLife` und Seed, so wie sie auch das Batchprogramm `Execute.exe` verwendet,
3. startet `Psi.exe Daten=InselIII PsiDaten=InselIII Protokoll=<id> Geschwindigkeit=0.0 Param=<id> Stop` auf einem eigenen virtuellen Bildschirm,
4. startet die Simulation über das Menü „Start“ (Mausklick per `xdotool`),
5. wartet, bis Psi am Lebensende seine Abschlussprotokolle schreibt und sich wegen `Stop` selbst beendet,
6. kopiert alle Protokolle nach `<out>/raw/` und schreibt eine Trace-Datei nach ADR 0006 (`<out>/inseliii__seed-<seed>.jsonl.gz`).

Ein Lauf mit `MaxLife` 20.000 (18 Zyklen) dauert etwa eine Minute. Läufe müssen nacheinander erfolgen, weil der Weltserver des Originals immer Port 2000 belegt. Für parallele Läufe bräuchte es getrennte Netzwerk-Namensräume.

`MaxLife` wird in Alterseinheiten angegeben. Wie viele Zyklen ein Leben umfasst, lässt sich nicht einfach umrechnen, weil das Alter pro Zyklus im Lauf stark steigt: im Messlauf vom 2026-11-10 (Seed 16, `MaxLife` 1.000.000) von etwa 1.250 Einheiten in den ersten 40 Zyklen auf etwa 6.100 nach 280 Zyklen. Der Lauf erreichte 316 Zyklen in 7,5 Minuten. Die Parameterdateien des Originals in `Execute/` verwenden 5.000.000. Ein solches volles Leben hatte mit Seed 16 739 Zyklen und dauerte ohne Fehlerdialog rund 19 Minuten (`traces/original-runs/2026-11-10-volles-leben/`). Gegen Lebensende steigt das Alter pro Zyklus auf über 30.000 Einheiten, überwiegend Denkzeit.

Die Wanduhrzeit pro Zyklus steigt deutlich schwächer: in den ersten 400 Zyklen 1,2 bis 1,5 s, in den letzten 100 Zyklen des vollen Lebens etwa 2 s. Die Laufzeit hängt also vor allem an der Zahl der Zyklen, weniger am Alter. Der letzte Zyklus dauert wegen der Abschlussprotokolle zusätzlich gut 20 Sekunden.

### Fehler im Original: Kommandozeilenschalter `Start`

Mit dem Schalter `Start` (so dokumentiert in `History/Execute.Txt` und so verwendet von `Execute.exe`) endet jeder Lauf in einer Zugriffsverletzung statt in einem sauberen Abschluss. Ursache in `UFPsi.pas`, Prozedur ab Zeile 672:

```pascal
if CmdLineExists('Start')
then SimulRun:=TRUE;               // Setter ruft ThreadTimer.Resume auf
ThreadTimer:=TThreadTimer.Create(TRUE);
```

Der Setter `SetSimulRun` (Zeile 990 ff.) ruft `ThreadTimer.Resume` auf, bevor der Thread in der nächsten Zeile erzeugt wird. Der Aufruf scheitert an einem Nil-Objekt, die Ausnahme überspringt die Erzeugung, und der Thread existiert für den Rest des Laufs nicht. Folgen:

- Die Zeitreihen `Motive`, `Emotionen` und `Modulationen` bleiben leer, das Gesicht wird nicht aktualisiert.
- Am Lebensende setzt `CheckMaxLife` `SimulRun:=FALSE`; der Setter ruft `ThreadTimer.Suspend` auf und scheitert erneut. `eAch`, `Inpro`, `Consum` und der Eintrag in `Execute.Dat` werden nie geschrieben, das Programm beendet sich nicht.

Belegt durch Disassemblieren von `Psi.exe`: Beide Absturzadressen (`0x415B24` schreibend auf Offset 13, `0x415B37` lesend auf Offset 4) liegen in `TThread.Suspend` bzw. `TThread.Resume` der Delphi-Klassenbibliothek. Der Fehler hängt nicht von Wine ab. Der archivierte Lauf von 2014 enthält gefüllte Zeitreihen und wurde demnach vermutlich über das Menü gestartet.

Umgehung ohne Eingriff ins Original: den Schalter weglassen und die Simulation über das Menü starten. Genau das tut `run_original.py`.

### Reproduzierbarkeit unter Wine

Drei Läufe mit Seed 16 und `MaxLife` 20.000 (18 Zyklen, 145 Ereignisse) und zwei Läufe mit `MaxLife` 100.000 (72 Zyklen, 647 Ereignisse), gestartet wie oben beschrieben, waren jeweils vollständig identisch: gleiche Aktionen, Parameter, Situationen und Objekte, gleiches Alter, und jeder Bedürfnis- und Modulatorwert bit-gleich. Die kurzen Läufe bilden exakt den Anfang der langen. Die beiden langen Läufe liegen mit allen Rohprotokollen unter `traces/original-runs/2026-11-09-determinismus/`, `tests/test_original_runs.py` hält den Befund fest.

Das schränkt die Erwartung aus dem Inventar ein: Die Mechanismen für Nichtdeterminismus (gemeinsamer Zufallsgenerator mit der Oberfläche, Socket, Timer, Wanduhr) existieren im Code, wirken sich mit `Geschwindigkeit=0.0` unter Wine aber zumindest über 72 Zyklen nicht aus. Das Alter hängt in diesem Modus offenbar nicht an der Wanduhr. Unter Windows kann das anders sein; ein Vergleich mit einem Windows-Lauf steht aus.

Bedeutung für ADR 0005: Ebene 2 kann neben dem statistischen Vergleich auch exakte Referenzläufe ganzer Leben nutzen, ohne das Original umzubauen. Ob und wie das in die Teststrategie eingeht, ist eine eigene Entscheidung (offene Frage in `HANDOFF.md`).

## Bekannte Grenzen

- Fehlerdialoge: Das Original zeigt gelegentlich modale Fehlermeldungen (Fenstertitel „Fehler“) und wartet auf OK. Beobachtet wurde im vollen Leben mit Seed 16 in Zyklus 571 „GravityList: Fluglava1b ...“, ausgelöst durch eine Wettlaufsituation beim Nachrichtenempfang in `UPsiServer.pas` (Details in `traces/original-runs/2026-11-10-volles-leben/README.md`). `run_original.py` bestätigt solche Dialoge automatisch und vermerkt sie im Kopf der Trace-Datei unter `extra.dialogs_dismissed`, mit Screenshot unter `raw/dialogs/`. Bei einer Wiederholung trat der Dialog wieder in Zyklus 571 auf, und der Lauf blieb vollständig identisch, obwohl der Dialog einmal 5,5 Minuten und einmal wenige Sekunden stand. Die automatische Bestätigung ist damit auch im echten Lauf erprobt.

- Ton: Wine meldet fehlende ALSA-Geräte. Psi läuft trotzdem; die Sprachausgabe (`USound`) zieht aber Zufallszahlen und könnte sich je nach Tonumgebung anders verhalten. Unter Wine ohne Tongerät ist das Verhalten über Läufe hinweg gleich.
- Die Position des Menüpunkts „Start“ ist für das Standardfensterlayout bei 1280 × 1024 fest eingetragen (`START_MENU_XY`). Bei anderer Auflösung muss sie angepasst werden.
- Die Oberfläche meldet beim Laden der Situationen Debug-Fehler der Art `NameValue.GetValue(Blumen1): Name nicht gefunden` in `Tmp/Debug(Psi1).Txt`. Sie treten auch in den archivierten Läufen auf und beeinflussen den Lauf nicht erkennbar.
