# ADR 0001: Git-Repository als Übergabeplattform zwischen KI-Agenten

- Status: angenommen
- Datum: 2026-11-09
- Autor: Alec, Claude Code

## Kontext

Das Projekt wird abwechselnd mit Claude Code und OpenAI Codex entwickelt, damit die Arbeit bei Usage Limits eines Anbieters weitergehen kann. Keiner der Agenten hat Zugriff auf die Sessions des anderen.

## Entscheidung

Das GitHub-Repository ist das einzige gemeinsame Gedächtnis. Es besteht aus `AGENTS.md` (Regeln, von beiden Agenten gelesen), `HANDOFF.md` (aktueller Stand, nächster Schritt, Log), ADRs unter `docs/decisions/` (dauerhafte Entscheidungen), GitHub Issues (Aufgaben in Session-Größe) und Tests (überprüfbarer Vertrag). Das Protokoll steht in `AGENTS.md`.

## Betrachtete Alternativen

- Gemeinsames Dokument außerhalb des Repositorys (Notion, Google Doc): getrennt vom Code, nicht versioniert zusammen mit dem Stand, den es beschreibt.
- Getrennte Instruktionsdateien je Agent: Regeln würden auseinanderlaufen. Deshalb verweist `CLAUDE.md` per Import auf `AGENTS.md`.

## Konsequenzen

Jede Session endet mit Commit und Push. Abgebrochene Sessions verlieren nur Arbeit seit dem letzten Push, deshalb wird klein committet. Kreuz-Reviews zwischen den Agenten werden möglich.
