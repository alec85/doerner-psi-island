# ADR 0004: Sprachen in Code und Dokumentation

- Status: angenommen
- Datum: 2026-11-09
- Autor: Claude Code

## Kontext

Die Projektsprache im Alltag ist Deutsch, Publikationen und eine mögliche spätere Veröffentlichung des Codes richten sich an ein internationales Publikum. Dörners Begriffe sind deutsch und teils schwer übersetzbar.

## Entscheidung

Code, Bezeichner, Docstrings und Commit-Messages auf Englisch. Projektdokumentation (HANDOFF, ADRs, Roadmap, Architektur) auf Deutsch. Englische Bezeichner tragen den deutschen Originalbegriff im Docstring.

## Betrachtete Alternativen

- Alles Deutsch: erschwert die spätere Veröffentlichung des Codes.
- Alles Englisch: verlangsamt die tägliche Arbeit und entfernt die Dokumentation von Dörners Begriffswelt.

## Konsequenzen

Eine spätere Übersetzung der Dokumentation ins Englische bleibt möglich, wenn das Repository öffentlich wird.
