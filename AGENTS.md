# AGENTS.md

Gemeinsame Arbeitsanweisung für alle KI-Agenten in diesem Repository (Claude Code, OpenAI Codex und weitere). Codex liest diese Datei direkt, Claude Code über `CLAUDE.md`. Regeln werden nur hier gepflegt.

## Projekt in Kürze

Neuimplementierung der PSI-Theorie von Dietrich Dörner auf Basis des Delphi-Originals aus „Die Mechanik des Seelenwagens“, erweitert um eine Global-Workspace-Komponente. Langfristig kommen Spiking Neural Networks, eine allgemeine Robotersteuerung (Simulation und Sunfounder PiCrawler) und wissenschaftliche Publikationen hinzu.

- Roadmap und Phasen: `docs/roadmap.md`
- Architektur: `docs/architecture.md`
- Getroffene Entscheidungen: `docs/decisions/`
- Aktueller Arbeitsstand: `HANDOFF.md`

## Übergabeprotokoll

Dieses Repository ist das einzige gemeinsame Gedächtnis. Kein Agent kennt die Sessions eines anderen Agenten, und auch der eigene Kontext aus früheren Sessions ist weg.

**Zu Beginn jeder Session**

1. `git pull` auf `main`, dann den passenden Arbeitsbranch holen oder anlegen.
2. `HANDOFF.md` vollständig lesen.
3. Die ADRs in `docs/decisions/` lesen, die den Bereich betreffen, in dem du arbeitest.
4. Die Aufgabe aus „Nächster Schritt“ in `HANDOFF.md` oder ein offenes Issue übernehmen. Die Issue-Nummer gehört in den Branch-Namen.

**Während der Session**

- Klein und häufig committen, spätestens nach jedem abgeschlossenen Teilschritt, und jeden Commit sofort pushen. Usage Limits kommen ohne Vorwarnung; was nicht gepusht ist, existiert für den nächsten Agenten nicht.
- Entscheidungen mit Tragweite (Datenmodell, neue Abhängigkeit, Abweichung vom Delphi-Original, Änderung an Testtoleranzen) als ADR festhalten, bevor darauf aufgebaut wird. Vorlage: `docs/decisions/0000-vorlage.md`.
- Bereits getroffene Entscheidungen werden respektiert. Wer eine ADR für falsch hält, schreibt eine neue ADR, die sie ablöst, und notiert das in `HANDOFF.md` als offene Frage an Alec.

**Am Ende jeder Session, oder sobald der Kontext knapp wird**

1. `pytest` ausführen.
2. `HANDOFF.md` aktualisieren: die Abschnitte „Aktueller Stand“, „Nächster Schritt“, „Offene Fragen“, „Bekannte Fallstricke“ und „Teststatus“ überschreiben, im „Log“ einen Eintrag anhängen (Datum, Agent, was erledigt wurde, Branch).
3. Commit `chore(handoff): <kurze Beschreibung>` und push.

Lieber eine unvollständige Übergabe früh als eine vollständige, die wegen eines Limits nie gepusht wird.

## Branches und Reviews

- `main` ist immer lauffähig, Tests sind grün.
- Arbeitsbranches: `claude/<issue>-<kurzname>` bzw. `codex/<issue>-<kurzname>`.
- Änderungen gehen per Pull Request nach `main`. Wenn möglich reviewt der jeweils andere Agent den PR. Gemergt wird durch Alec.

## Konventionen

- Python 3.12 oder neuer, Paket unter `src/psi_gw/`, Tests unter `tests/`.
- Code, Bezeichner, Docstrings und Commit-Messages auf Englisch. Projektdokumentation (HANDOFF, ADRs, Roadmap, Architektur) auf Deutsch. Siehe ADR 0004.
- Commit-Format: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).
- Determinismus: Jede Simulation läuft mit explizitem Seed und diskretem Tick. Es gibt keinen globalen Zufallszustand; Zufall kommt ausschließlich aus einer explizit durchgereichten `RandomSource` (Standard: `numpy.random.Generator`, für Tests ein Wiedergabestrom, siehe ADR 0005).
- Dörners Terminologie bleibt erkennbar. Englische Bezeichner im Code tragen den deutschen Originalbegriff im Docstring, zum Beispiel `selection_threshold` mit „Selektionsschwelle“.
- Jede bewusste Abweichung vom Delphi-Original wird im Code markiert: `# DEVIATION(ADR-NNNN): <Begründung>`.
- Neue Abhängigkeiten nur mit ADR.

## Befehle

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Grenzen für Agenten

- `reference/` ist schreibgeschützte Referenz und wird nie verändert.
- Golden-Master-Tests werden nicht abgeschwächt, um sie grün zu bekommen. Toleranzen ändern sich nur per ADR.
- Ergebnisse werden nur behauptet, wenn ausgeführter Code sie belegt. Experimente laufen real und werden statistisch ausgewertet; beschriebene oder simulierte Ergebnisse gelten nicht.
- Keine Secrets, Tokens oder Zugangsdaten im Repository.
