Delphi-Original lauffähig machen
---
## Ziel

Das Original lässt sich reproduzierbar bauen und starten, mit dokumentierter Anleitung.

## Schritte

1. Prüfen, ob der Code mit Free Pascal/Lazarus (Delphi-Modus, `{$mode delphi}`) kompiliert. Fehler kategorisieren: fehlende VCL-Komponenten, Sprachfeatures, Plattformabhängigkeiten.
2. Falls nötig, minimale Anpassungen in einer Kopie unter `reference/delphi-instrumented/`, das Original bleibt unberührt.
3. Fallback dokumentieren: ältere Delphi-Version unter Windows.
4. Build-Anleitung in `docs/delphi-build.md`.

## Abnahmekriterien

- [ ] Original startet und zeigt die Inselwelt
- [ ] Jede Anpassung ist als Diff zum Original nachvollziehbar
- [ ] Build-Anleitung vorhanden
- [ ] HANDOFF.md aktualisiert

## Hinweise

Hängt von Issue „Delphi-Original einchecken“ ab. Ein GUI-Lauf ist für den Anfang ausreichend; ein Headless-Modus wäre für viele Trace-Läufe wertvoll und kann ein Folge-Issue werden.
