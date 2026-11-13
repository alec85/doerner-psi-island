Trace-Format festlegen
---
## Ziel

Ein verbindliches JSONL-Format für Tick-Verläufe, das sowohl das instrumentierte Original als auch die Python-Implementierung schreiben.

## Schritte

1. Aus dem Inventar ableiten, welche Größen das Original pro Tick führt (Bedürfnisse, Modulatoren, Motive, Aktion, Weltzustand).
2. Format in `traces/README.md` finalisieren, inklusive Einheiten und Wertebereichen.
3. ADR mit Begründung der Auswahl und der Toleranzen je Größe.
4. `src/psi_gw/tracing/` mit Writer und Reader samt Tests.

## Abnahmekriterien

- [ ] Format dokumentiert, ADR angenommen
- [ ] Writer und Reader in Python mit Tests
- [ ] HANDOFF.md aktualisiert
