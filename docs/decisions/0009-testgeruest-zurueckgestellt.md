# ADR 0009: Free-Pascal-Testgerüst zurückgestellt, Zufallsmitschnitt statt Prozedurtests

- Status: angenommen
- Datum: 2026-11-10
- Autor: Alec (Zustimmung), Claude Code
- Ändert: ADR 0005 (Ebene 1)

## Kontext

ADR 0005 sah als Ebene 1 exakte Tests einzelner Prozeduren in einem Free-Pascal-Gerüst ohne Oberfläche vor, mit injiziertem Zufall. Begründung war damals, dass ganze Läufe des Originals als nicht reproduzierbar galten. Inzwischen ist belegt, dass das Original unter Wine vollständig deterministisch läuft, über volle Leben und auch über Fehlerdialoge hinweg (`docs/delphi-build.md`), und der Zufallsgenerator ist bit-genau nachgebildet (ADR 0008). Das Gerüst wäre aufwendig: Rund 30 Oberflächen-Units müssten durch Platzhalter ersetzt werden, und Delphi-7-Code kompiliert unter Free Pascal nicht ohne Anpassungen.

## Entscheidung

1. Das Free-Pascal-Testgerüst wird zurückgestellt. Es wird nur gebaut, wenn sich Abweichungen der Neuimplementierung mit den Mitteln unten nicht eingrenzen lassen.
2. An seine Stelle tritt ein **Zufallsmitschnitt** des Originals: Jeder Aufruf der beiden Zufallsroutinen in `Psi.exe` wird unter Wine per Debugger mit Aufrufstelle und `RandSeed` protokolliert (Issue #14). Die Neuimplementierung protokolliert ihre Züge ebenso; verglichen wird Zug für Zug.
3. Zusammen mit den exakten Ganzlauf-Vergleichen (ADR 0008) und den feinen Protokollen des Originals (`Activities`, `IntTimes`, Ereignisprotokoll) ist das die Grundlage, um Abweichungen auf Zyklus, Prozedur und einzelnen Zufallszug einzugrenzen.
4. Prozedur-Testfälle (ADR 0006) bleiben als Format erhalten und werden aus dem Mitschnitt oder aus Läufen der Neuimplementierung erzeugt, wo sie nützlich sind.

## Betrachtete Alternativen

- **Gerüst wie geplant bauen.** Verworfen für jetzt: hoher Aufwand bei inzwischen geringem Zusatznutzen.
- **Nur Ganzlauf-Vergleiche ohne Mitschnitt.** Verworfen: Eine Abweichung wäre nur auf den Zyklus genau sichtbar, nicht auf die Aufrufstelle.

## Konsequenzen

- Issue #2 Teil 2 und die Gerüst-Schritte von Issue #4 ruhen.
- Die Neuimplementierung braucht eine protokollierende `RandomSource`, die jeden Zug mit Aufrufstelle festhält.
