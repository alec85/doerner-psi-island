# Methodenbaustein: Artefakte und moderner Modus

Grundlage für Abschnitt 3.2 und die Tabellen T2 und T3.

Das Original enthält Implementierungsartefakte, die das Verhalten verändern, ohne Teil der Theorie zu sein: Seiteneffekte der Anzeige, Speicherreste, eine verdeckte Variable, Wines Umgang mit Dateinamen, eine Regel für Hintergrundziele, die der Beschreibung im Buch widerspricht. Jedes davon ist einzeln abschaltbar (ADR 0015, `psi_gw.variant.Variant`). Der moderne Modus schaltet alle ab (`Variant.from_names("all")`) und ist die Grundlage der Workspace-Experimente (ADR 0016, Entscheidung Q4).

Die Wirkung des modernen Modus wurde gepaart über 100 Seeds gemessen (Seeds 1001 bis 1100; drei Leben brechen im Referenzmodus mit einem nil-Zugriff ab und gehen paarweise aus dem Vergleich, es bleiben 97). Zahlen und Statistik in `analysis/varianten/all-100/vergleich.json`, Tabelle T3 wird daraus erzeugt.

Die Einzelwirkungen der Schalter (je 20 Seeds) stehen in `analysis/varianten/<schalter>/` und `analysis/varianten/README.md`.

Kennzahlen P1 bis P6 sind im Analyseplan der Referenzläufe definiert (`docs/analyseplan-referenzlaeufe.md`):

| Kürzel | Kennzahl |
|---|---|
| P1 | Exitus je 1.000 Zyklen |
| P2 | Nukleotide je 100 Zyklen |
| P3 | entdeckte Orte |
| P4 | Erfolgsquote der Manipulationen |
| P5 | Anteil der Zyklen mit Versuch und Irrtum |
| P6 | mittlerer Schaden in Prozent |
