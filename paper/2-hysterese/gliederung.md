# Gliederung Paper 2: Hysterese im Global Workspace

**Stand nach der Überarbeitung (2026-11-12, Issue #45):** Arbeitstitel *Generalising Dörner's selection threshold to a limited-capacity workspace: an incumbency bonus makes contents history-dependent in a PSI island agent*. Die Gliederung des Manuskripts (`manuskript.tex`) weicht von der folgenden ersten Fassung ab: Einleitung mit Vorarbeiten (Bach, OpenPsi, Dossa) und eingegrenzter Neuheit; Modell mit Inhaltsarten-Tabelle, Zyklusablauf, formaler Hysterese des Selektors und GWT-Abgleich; Design mit Chronologie; Ergebnisse mit Vergleich zu A, Gleichstandsdiagnose (S1), zufälliger Gleichstandsauflösung (S2), Bonus-Reihe (S3) und Robustheit; Diskussion mit der Lesart „Bonus wirkt vor allem als Auflösung von Gleichständen“. Die Titelvorschläge unten sind überholt.


Arbeitstitel (englisch): *The selection threshold as hysteresis: a Global Workspace extension of Dörner's PSI agent*

## Kernaussage

Dörners Selektionsschwelle ist der Sonderfall eines allgemeinen Amtsinhaber-Bonus im Wettbewerb um einen Global Workspace mit begrenzter Kapazität. Bekommt jeder Inhalt des Workspace diesen Bonus, hängt die Stabilität aller Inhalte vom Arousal ab, und der Workspace zeigt Hysterese: Bei gleicher Lage bestimmt die Vorgeschichte, was im Workspace steht (ADR 0016, Entscheidung Q1).

Gestützt ist die Kernaussage, wenn H1, H3 und H4 des Analyseplans in vorhergesagter Richtung signifikant sind (`docs/analyseplan-workspace.md`, Nachtrag 1 für H1).

**Ergebnis der Bestätigung (2026-11-11, `analysis/workspace/bestaetigung/README.md`):** H1, H4 und H6 signifikant in vorhergesagter Richtung, H2, H3 und H5 nicht. Die Kernaussage ist nach dem Kriterium damit nicht gestützt. Tragfähig für das Paper ist die schwächere Fassung: Ein Amtsinhaber-Bonus in der Größe der Selektionsschwelle stabilisiert alle Inhaltsarten und erzeugt Hysterese; die Kopplung an das Arousal ist auf der Insel nicht von einem festen Bonus zu unterscheiden. Ob der Titel und die Rahmung angepasst werden, entscheidet Alec.

## Titelvorschläge (zur Entscheidung durch Alec)

Rahmung A, empfohlen: Hysterese der Aufmerksamkeit ohne Folgen für das Verhalten.

- *Sticky attention, unchanged behaviour: A preregistered test of workspace hysteresis in Dörner's PSI agent*
- *When the workspace remembers: Hysteresis from a generalized selection threshold leaves a PSI agent's behaviour unchanged*

Rahmung B: Die Selektionsschwelle als allgemeiner Mechanismus.

- *Dörner's selection threshold as a general incumbency mechanism: Hysteresis in a Global Workspace extension of PSI*
- *One rule for motives and attention: Generalizing the selection threshold of the PSI theory to a Global Workspace*

Rahmung C (Reproduzierbarkeit) ist seit der Aufteilung (2026-11-12) Thema von Paper 1.

## Abschnitte

### 1 Einleitung

- PSI als Architektur motivierter Kognition (Dörner 1999, 2002; Bach 2009; Dörner und Güss 2013).
- Global-Workspace-Theorie (Baars 1988; Dehaene et al. 1998; Mashour et al. 2020) und ihre Rolle in Kriterienkatalogen für Bewusstsein in KI-Systemen (Butlin et al. 2023).
- Lücke: Die Selektionsschwelle stabilisiert in PSI nur Motive. Ob ein Arousal-gekoppelter Bonus auch Ziele, Objekte, Erinnerungen und Pläne stabilisiert, wurde nicht untersucht.
- Beitrag: Erweiterung des portierten Agenten (Paper 1) um einen Workspace mit Hysterese und vorab registrierter Test der Hysterese-Hypothese.

### 2 PSI und die Selektionsschwelle

- Motivwahl mit Selektionsschwelle im Original (`select_motive`, `psi_gw.motivation.system`; Mechanik des Seelenwagens, Kapitel zur Motivation).
- Modulatoren Arousal, Auflösungsgrad, Selektionsschwelle und ihre Kopplung.
- Befund aus den Läufen: Auf der Insel wechselt das Motiv fast nie (Nachtrag 1); die Schwelle wirkt dort praktisch nicht. Das ist Motivation für die Verallgemeinerung auf andere Inhalte.

### 3 Methode

- 3.1 Agent und Welt: portierter PSI-Agent im modernen Modus, Verweis auf Paper 1 (`../1-portierung/`).
- 3.2 Global Workspace: `methoden/workspace.md`. Abbildung A1 (Schema, von Hand zu zeichnen).
- 3.3 Versuchsplan und Statistik: `methoden/statistik.md`. Bedingungen A bis E, Kennzahlen W1 bis W6 und W2b, Tests H1 bis H6.

### 4 Ergebnisse

- 4.1 Bestätigende Tests H1 bis H6: Tabelle T1.
- 4.2 Verweildauer nach Inhaltsart und Bedingung: Abbildung A2.
- 4.3 Arousal und Stabilität: Abbildung A3 (Arousal beim Eintritt gegen Verweildauer, B und D).
- 4.4 Ein Leben im Zeitverlauf (Seed 1001, B und E): Abbildung A4.
- 4.5 Was der Workspace für Überleben und Leistung bedeutet (P1 bis P6, B bis E gegen A): Tabelle T2, beschreibend.

### 5 Diskussion

- Hysterese über Motive hinaus gestützt (H1, H4, H6); die Rolle des Arousal nicht (H3). Mögliche Gründe: Die Selektionsschwelle schwankt auf der Insel kaum (Standardabweichung 0,009 um 0,065); Nukleo dominiert die Motivation, so dass das Arousal wenig variiert. Prüfbar in einer Welt mit wechselnden Bedürfnislagen oder mit stärker modulierter Schwelle (Folgestudie, nicht Teil dieses Plans).
- Keine messbaren Folgen für Pläne (H2), Gelegenheitsbefriedigungen (H5) und Leistung (P1 bis P6): Der Workspace verändert, was Psi beachtet, auf dieser Insel aber kaum, wie gut Psi lebt.
- Grenzen: eine Welt (Insel), ein Parametersatz, Nukleo dominiert die Motivation; Kandidatenstärken sind gesetzt, nicht gelernt; Kapazität als lineare Funktion des Auflösungsgrads.
- Bezug zu Butlin et al. (2023): Welche Indikatoren der GWT der erweiterte Agent erfüllt und welche nicht. Ausdrücklich keine Aussage über Bewusstsein.
- Ausblick: Spiking-Umsetzung, Roboter (PiCrawler), siehe `docs/roadmap.md`.

### 6 Verfügbarkeit

- Repository, Commit der Läufe, Befehle zur Reproduktion (`HANDOFF.md`, Schritt 5), Archive unter `traces/port-runs/`.

## Offene Punkte für das Manuskript

- Zielzeitschrift oder Konferenz festlegen (Alec).
- Lizenz des Codes vor Veröffentlichung klären (ausgeklammert, Alec).
- Abbildung A1 als Schema zeichnen.
