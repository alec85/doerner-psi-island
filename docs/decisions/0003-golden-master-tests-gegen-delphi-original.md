# ADR 0003: Golden-Master-Tests gegen das Delphi-Original

- Status: angenommen, konkretisiert durch ADR 0005 (zweistufiger Abgleich)
- Datum: 2026-11-09
- Autor: Alec, Claude Code

## Kontext

Für wissenschaftliche Aussagen muss belegbar sein, dass die Neuimplementierung Dörners PSI reproduziert und nicht nur davon inspiriert ist. Eine Portierung allein aus Lektüre von Code und Buch würde unbemerkt abweichen.

## Entscheidung

Das Delphi-Original wird lauffähig gemacht und um Trace-Logging ergänzt. Jeder Tick wird als eine JSON-Zeile geschrieben (Format in `traces/README.md`). Die Python-Implementierung wird mit identischen Startbedingungen gegen diese Referenz-Traces getestet. Toleranzen sind je Größe dokumentiert und ändern sich nur per ADR. Bewusste Abweichungen werden im Code mit `DEVIATION(ADR-NNNN)` markiert.

## Betrachtete Alternativen

- Portierung ohne Referenzläufe: schneller, aber ohne Nachweis der Treue.
- Automatische Übersetzung Delphi nach Python: liefert unidiomatischen Code und ersetzt den Verhaltensabgleich nicht.

## Konsequenzen

Phase 1 kostet Zeit, bevor Python-Code entsteht. Dafür ist jede spätere Änderung am Kern gegen das Original abgesichert, und Paper 1 kann eine Reproduktion belegen. Zufallsquellen im Original müssen identifiziert werden, damit Läufe vergleichbar sind; wo das nicht exakt gelingt, wird statistisch über viele Läufe verglichen.
