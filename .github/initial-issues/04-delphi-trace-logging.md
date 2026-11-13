Trace-Logging im Delphi-Original
---
## Ziel

Das instrumentierte Original schreibt pro Tick eine Zeile im festgelegten Trace-Format und lässt sich mit festem Seed starten.

## Schritte

1. In `reference/delphi-instrumented/` einen Logging-Aufruf am Ende jedes Simulationsschritts ergänzen.
2. `Randomize` durch einen festen, per Parameter setzbaren Seed ersetzen.
3. Referenzläufe für mindestens drei Seeds erzeugen und unter `traces/` ablegen.
4. Zweimal mit gleichem Seed laufen lassen und prüfen, dass die Traces identisch sind.

## Abnahmekriterien

- [ ] Gleicher Seed ergibt identische Traces
- [ ] Mindestens drei Referenz-Traces eingecheckt
- [ ] HANDOFF.md aktualisiert
