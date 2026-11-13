Delphi-Original einchecken und inventarisieren
---
## Ziel

Der Delphi-Quellcode liegt unverändert unter `reference/delphi-original/`, und ein Inventar beschreibt, welche Unit was tut.

## Schritte

1. **Alec:** Quelldateien nach `reference/delphi-original/` kopieren und committen (nur im privaten Repository).
2. **Agent:** `docs/delphi-inventar.md` anlegen: je Unit Zweck, wichtigste Typen und Prozeduren, Abhängigkeiten zu anderen Units, Zuordnung zu Kapiteln in „Die Mechanik des Seelenwagens“.
3. **Agent:** Zufallsquellen (`Random`, `Randomize`) und globalen Zustand gesondert auflisten; das ist für reproduzierbare Traces entscheidend.

## Abnahmekriterien

- [ ] Original vollständig eingecheckt
- [ ] Inventar deckt alle Units ab
- [ ] Zufallsquellen und globaler Zustand dokumentiert
- [ ] HANDOFF.md aktualisiert
