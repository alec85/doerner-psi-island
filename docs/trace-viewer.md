# Trace-Viewer

Der Viewer erzeugt aus einem oder zwei vorhandenen ADR-0006-Läufen eine einzelne interaktive HTML-Datei. Er liest `.jsonl` und `.jsonl.gz`, startet keine Simulation und verändert keine Eingaben. Es werden keine zusätzlichen Laufzeitabhängigkeiten benötigt; die Ausgabe braucht nur einen Browser mit JavaScript.

## Erzeugen und öffnen

Nach der normalen Paketinstallation:

```bash
python -m psi_gw.ui.trace_viewer LAUF.jsonl.gz --output trace-viewer.html
python -m psi_gw.ui.trace_viewer LAUF_A.jsonl.gz LAUF_B.jsonl.gz --output vergleich.html
```

Ohne Installation kann im Repository `PYTHONPATH=src` vor den Befehl gesetzt werden. Die erzeugte Datei direkt im Browser öffnen; Server, CDN und Internetverbindung sind nicht erforderlich. Eine bestehende Ausgabe wird nur mit `--force` ersetzt. Eingaben und Symlink-Aliase darauf können auch damit nicht überschrieben werden. Erfolgreicher Export liefert Code 0, Eingabe-/Ausgabefehler Code 2.

Ein Beispiel mit zwei archivierten Originalwiederholungen:

```bash
python -m psi_gw.ui.trace_viewer \
  traces/original-runs/2026-11-09-determinismus/r1/inseliii__seed-16.jsonl.gz \
  traces/original-runs/2026-11-09-determinismus/r2/inseliii__seed-16.jsonl.gz \
  --output vergleich.html
```

## Bedienung

- Die Karten zeigen Lauf A/B, Herkunft, Seed, Welt sowie die Zahl tatsächlich gespeicherter Zyklus- und Ereignisdatensätze. Aufklappen liefert Parameter, Header, archivierte Zusammenfassung und SHA-256 der Eingabedatei einschließlich ihrer etwaigen Gzip-Kompression.
- **Messwert** wählt eine einzelne Reihe: Bedürfnisse/Modulatoren aus Ereignissen oder Bedürfnisprozente, Leistungszähler und Regulationszeiten aus Zyklusdatensätzen. Im Vergleich werden A durchgezogen und B gestrichelt überlagert.
- **Zeitachse** verwendet gespeichertes Alter oder gespeicherten Zyklus. **Von/Bis** begrenzen Kurve und Ereignistabelle. Leere Grenzen sind offen; ein umgekehrter Bereich wird als ungültig angezeigt.
- **Lauf/Aktion/Suche** filtern die Ereignistabelle; diese Filter stehen unter „Ereignisse erkunden“ und ändern die Messwertkurven nicht. Die Tabelle hat 50 Einträge pro Seite. Die Suche berücksichtigt auch die gespeicherten Parameter und weiteren Ereignisfelder.
- Ein Klick auf eine Aktion zeigt ihren vollständigen Datensatz. Pfeile und Schieberegler navigieren durch alle gefilterten Ereignisse. Eine senkrechte Markierung zeigt deren gespeicherte Zeitposition im Diagramm, sofern vorhanden.
- **Zurücksetzen** leert Bereich und Ereignisfilter; Messwert und Zeitachse bleiben gewählt.

## Daten und Grenzen

Das Format ist in [traces/README.md](../traces/README.md) und ADR 0006 beschrieben. Es ist ein anderes Format als `Workspace(1).jsonl` oder ein PiCrawler-Replay. Diese werden nicht als gewöhnliche Traces geraten oder still konvertiert.

Es gibt keine Ausrichtung nach Datensatzposition und keine Umrechnung von Alter in Sekunden. Fehlende Messwerte oder Zeitkoordinaten werden nicht als Null interpretiert. Für Messwertkurven unterbrechen fehlende Werte die Linie; einzelne Punkte und wiederholte Zeitkoordinaten bleiben sichtbar. Linien verbinden nur aufeinanderfolgende gültige Datensätze in Aufzeichnungsreihenfolge und behaupten keine Messungen zwischen ihnen. Bei Zyklusausrichtung können viele Ereignisse denselben Zyklus besitzen.

Nichtendliche Zahlen (`NaN`, `Infinity`) aus lesbaren Python-JSON-Archiven werden in der Anzeige zu `null`; die Anzahl wird als Hinweis angezeigt. Die Quelldatei bleibt unverändert. Normale Nullwerte bleiben Null. Nichtnumerische Werte werden nicht zu Zahlen umgedeutet.

Ereignis-Bedürfniswerte und gerundete Zyklus-Prozentwerte sind verschiedene Größen und werden getrennt angeboten. Beginnen und Beenden derselben Aktion sind zwei Ereignisdatensätze; der Viewer nennt ihre Summe nicht „Handlungszahl“. `cycle=0` und `seed=0` sind gültige Werte.

Ein fehlender Abschlussdatensatz bedeutet „Vollständigkeit unbekannt“. Auch ein vorhandener `summary` beweist nicht, dass alle Ereignisse eines ganzen Lebens archiviert sind. Der Viewer errechnet keine Ersatz-Zusammenfassung und behauptet keine statistische Äquivalenz. Für exakte Diagnostik dienen die [Vergleichswerkzeuge](comparison-tools.md).

Verglichen werden bis zu zwei vollständig eingebettete Dateien. Abweichende Seeds/Welten/Parameter werden als Metadatenhinweis gezeigt; die Darstellung gleicht solche Unterschiede nicht aus. Große Archive brauchen entsprechend Browserarbeitsspeicher. Es gibt keine automatische Stichprobe oder heimlich weggelassene Datensätze.

Der Bericht enthält Header, Parameter, Datensätze und Quellenangaben aus den Eingaben. Beim Weitergeben wird damit auch dieser Inhalt weitergegeben. Eingebettete Texte werden als Daten behandelt; der Bericht lädt keine externen Skripte und stellt keine Netzwerkverbindungen her.
