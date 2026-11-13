# Gliederung Paper 1: Portierung

Arbeitstitel (englisch, seit der Überarbeitung nach dem Review vom 2026-11-12): *Reconstructing Dörner's 2003 PSI island agent: trace-level validation and implementation-dependent behaviour* (Vorschlag des Reviews). Frühere Fassung: *Re-running Dörner's Psi: A faithful port of the 2003 island agent and what it reveals about the original*.

Weitere Titelvorschläge zur Entscheidung durch Alec:

- *Re-running Dörner: A faithful port of the PSI agent and a preregistered baseline for extensions*
- *The theory as written and the theory as run: Porting Dörner's PSI agent draw for draw*

## Kernaussagen

1. Das Inselprogramm von Dörner und Gerdes (Psi 4.9.1.200, 2003) lässt sich Zug für Zug nach Python übertragen; die einzige nicht nachgebildete Ursache von Abweichungen ist ein Speicherrest (ADR 0014).
2. Das Programm enthält Artefakte, die nicht aus der Theorie folgen, darunter eine Regel für Hintergrundziele, die der Beschreibung im Buch widerspricht. Zusammen senken sie die Überlebensleistung messbar.
3. Auf der Insel dominiert das Nukleotid-Motiv fast vollständig; wer die Insel für Studien zur Motivwahl nutzt, muss das berücksichtigen.

## Abschnitte im Entwurf (`manuskript.tex`)

| Abschnitt | Inhalt | Belege |
|---|---|---|
| 1 Introduction | PSI, Bekanntheit, Altcode, Replikationsliteratur, Beitrag | `literatur.md` |
| 2 The PSI agent on the island | Theorie in Kürze, Zyklus, Insel, Aufbau des Originals | `docs/delphi-inventar.md`, Buch S. 97 bis 99 |
| 3 Porting strategy | zwei Stufen der Treue, Zufall und Zeit, x87, Stringordnung, Oberfläche, Tests | ADR 0005, 0010, 0011; `methoden/portierung.md` |
| 4 How faithful is the port? | Tabelle 1, Speicherrest, Stichprobe | `analysis/referenzlaeufe/stichprobe/` |
| 5 What the port reveals | Tabelle 2 (Artefakte), Tabelle 3 (Wirkung), Motivdominanz | ADR 0015; `analysis/varianten/`; `analysis/referenzlaeufe/motivdominanz.json` |
| 6 Discussion | Stufen der Gleichheit, Bedeutung für frühere Befunde, Grenzen | |
| Availability | öffentliches Repository ohne `reference/` zur Einreichung | Alec, 2026-11-12 |

## Offen

- Bestätigung der einzelnen Schalter mit 100 Seeds (bisher Vorauswahl mit 20 Seeds); im Entwurf als Grenze genannt.
- Zielzeitschrift (Kandidaten: ReScience C, Cognitive Systems Research, Journal of Open Research Software).
- Ein Schema des Verhaltenszyklus als Abbildung.
- Rechte am Original für die Beschreibung des Ausgangsmaterials klären.
