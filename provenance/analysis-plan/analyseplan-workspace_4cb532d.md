# Analyseplan: Global Workspace mit Hysterese (Phase 3, Paper 1)

- Status: Fassung 1 vom 2026-11-11 (Issue #33), committet vor dem ersten Lauf mit Workspace
- Grundlage: ADR 0016 (Architektur, Kernaussage), ADR 0015 (moderner Modus), `docs/analyseplan-referenzlaeufe.md` (Kennzahlen P1 bis P6, Statistik der Varianten)
- Regel: Änderungen nach Beginn der bestätigenden Läufe nur als datierte Nachträge am Ende; sie gelten für danach erhobene Daten.

## Hypothese

Die Selektionsschwelle in Dörners PSI ist der Sonderfall eines allgemeinen Amtsinhaber-Bonus im Wettbewerb um einen Global Workspace mit begrenzter Kapazität. Gibt man jedem Inhalt im Workspace diesen Bonus, so hängt die Stabilität aller Inhalte vom Arousal ab, und der Workspace zeigt Hysterese: Bei gleicher Lage hängt sein Inhalt von der Vorgeschichte ab.

## Bedingungen

Alle Bedingungen im modernen Modus (`Variant.from_names("all")`), je ein volles Leben mit `MaxLife` 5.000.000. Die Bedingungen unterscheiden sich nur im Workspace.

| Kürzel | Workspace | Bonus des Amtsinhabers |
|---|---|---|
| A | aus | entfällt (Motivwahl wie im Original mit Selektionsschwelle) |
| B | an | Selektionsschwelle, für alle Inhaltsarten (Hypothese) |
| C | an | Selektionsschwelle nur für Motive, andere Inhalte ohne Bonus |
| D | an | fester Bonus für alle Inhaltsarten, gleich dem Mittel der Selektionsschwelle in Bedingung A über alle Zyklen und Seeds der Grundlinie |
| E | an | kein Bonus, auch nicht für Motive |

Bedingung A ist die Grundlinie `analysis/grundlinie-modern/` (bereits gerechnet). Der feste Bonus für D wird vor den Läufen aus dem ach-Protokoll der Grundlinie bestimmt und in einem Nachtrag festgehalten. Weil die ach-Datei die Selektionsschwelle nicht enthält, wird er aus neu gerechneten Läufen von A mit Workspace-Protokoll (Workspace aus, nur Protokoll) über die Seeds 1001 bis 1020 bestimmt.

Die Ansteuerung des Arousal, der Selektionsschwelle für die Freigabe eines Motivs (kein Motiv, wenn Arousal unter Schwelle) und alle übrigen Mechanismen bleiben in allen Bedingungen gleich.

## Seeds und Ablauf

1. Vorauswahl: Seeds 1001 bis 1020 in B, C, D, E. Zweck: Fehler finden, Effektgrößen schätzen. Wird berichtet, aber nicht bestätigend ausgewertet.
2. Bestätigung: Seeds 1001 bis 1100 in B, C, D, E (die Vorauswahl-Läufe werden mitverwendet, weil der Code zwischen beiden Schritten nicht geändert werden darf; wird er geändert, werden alle Läufe neu gerechnet).
3. Gepaart wird je Seed. Leben, die abbrechen, werden gemeldet und gehen paarweise aus dem Vergleich (wie in ADR 0015).

## Kennzahlen

P1 bis P6 wie im Referenzplan. Dazu Workspace-Kennzahlen, erhoben aus dem Protokoll `Workspace(1).jsonl` (je Zyklus Inhalte, Stärken, Arousal, Selektionsschwelle, Kapazität, gedächtnislose Auswahl) und aus Ereigniszählern, die in allen Bedingungen mitlaufen:

- **W1 Verweildauer:** mittlere Zahl aufeinanderfolgender Zyklen, die ein Inhalt im Workspace bleibt, je Inhaltsart (Motiv, Ziel, Objekt, Erinnerung, Plan) und über alle Inhalte. Inhalte, die bei Lebensende noch im Workspace sind, zählen mit ihrer bis dahin erreichten Dauer.
- **W2 Motivwechsel** pro 100 Zyklen (Wechsel des aktuellen Motivs zwischen zwei Zyklen, ohne Wechsel von oder zu „kein Motiv“). In allen Bedingungen messbar.
- **W3 abgebrochene Pläne** pro 100 Zyklen: Pläne, deren Ausführung (`Actiplan`) ohne Zielerreichung endet. In allen Bedingungen messbar.
- **W4 Gelegenheitsbefriedigungen** pro 100 Zyklen: Bedürfnisbefriedigungen (`Consum` mit negativem Ausmaß) eines Bedürfnisses, das nicht das aktuelle Motiv ist. In allen Bedingungen messbar.
- **W5 Arousal-Kopplung:** je Leben die Rangkorrelation (Spearman) zwischen dem Arousal beim Eintritt eines Inhalts und seiner Verweildauer, über alle Inhalte außer Motiven.
- **W6 Geschichtsabhängigkeit:** Anteil der Zyklen, in denen die Inhalte des Workspace von der Auswahl ohne Bonus (die `K` stärksten Kandidaten) abweichen.

## Bestätigende Tests

Gepaart über Seeds (1001 bis 1100), Differenz mit 95-%-Bootstrap-Intervall, Vorzeichen-Permutationstest (10.000 Ziehungen, fester Seed), Holm-korrigiert über alle sechs Tests zusammen; Signifikanzniveau 0,05.

- **H1 Hysterese stabilisiert Absichten:** W2 ist in B kleiner als in E.
- **H2 Hysterese schützt Pläne:** W3 ist in B kleiner als in E.
- **H3 Kopplung ans Arousal:** W5 ist in B größer als in D.
- **H4 Hysterese wirkt über Motive hinaus:** W1 für Nicht-Motive ist in B größer als in C.
- **H5 Preis der Konzentration:** W4 ist in B kleiner als in E.
- **H6 Geschichtsabhängigkeit:** W6 ist in B größer als in E. (In E ist W6 per Konstruktion nahe null; der Test prüft, dass B davon deutlich abweicht. Er ist damit eher eine Manipulationsprüfung als ein Befund und wird so berichtet.)

Gerichtete Hypothesen werden zweiseitig getestet; ein signifikanter Effekt gegen die vorhergesagte Richtung gilt als Widerlegung.

## Beschreibende Auswertungen

- P1 bis P6 für B, C, D, E gegen A (gepaart, Holm je Bedingung). Sie zeigen, was der Workspace für Überleben und Leistung bedeutet, sind aber nicht Gegenstand der Hypothese.
- W1 je Inhaltsart und Bedingung, Verteilungen (Abbildung).
- Kapazität `K` über das Leben und ihr Zusammenhang mit dem Arousal (Abbildung).
- Ein Beispielleben (Seed 1001) als Zeitleiste der Workspace-Inhalte in B und E (Abbildung).

## Was als Ergebnis gilt

- Die Kernaussage gilt als gestützt, wenn H1, H3 und H4 in vorhergesagter Richtung signifikant sind.
- Sind H1 und H2 signifikant, H4 aber nicht, gilt nur die Hysterese auf Ebene der Motive als gestützt (das kleinere Ergebnis aus der Beschreibung der Hypothese).
- Ist H3 nicht signifikant, wird berichtet, dass die Kopplung ans Arousal gegenüber einem festen Bonus keinen messbaren Vorteil bringt.
- Ergebnisse der Vorauswahl werden nicht als Bestätigung berichtet.

## Vorab bekannte Festlegungen der Umsetzung (ADR 0016 und Umsetzungsnotiz)

- Das aktuelle Motiv steht immer im Workspace; es ist der Sieger des Wettbewerbs unter den Motiven. Die übrigen `K − 1` Plätze teilen sich alle anderen Kandidaten einschließlich der nicht aktuellen Motive.
- `K` = `round(K_min + (K_max − K_min) × Auflösungsgrad)` mit `K_min` = 2 und `K_max` = 7.
- Die Stärken der Kandidaten werden ohne Seiteneffekte gelesen (keine Zufallszüge, keine Zeit), damit der Workspace das Verhalten nur über den Broadcast verändert.
- Broadcast: Ziele im Workspace stehen am Anfang der Zielliste und werden immer aufgenommen; Objekte im Workspace werden in `LookAround` zuerst geprüft und in `WhatCouldBeDone` mit voller Wahrscheinlichkeit erwogen.

## Nachtrag 1 (2026-11-11, vor den Vorauswahl-Läufen von B bis E)

**Anlass.** Beim Verdrahten des Workspace fiel auf, dass das aktuelle Motiv auf dieser Insel fast nie wechselt. Belege aus bereits vorhandenen Daten der Bedingung A und des Referenzmodus, keine aus B bis E:

- Im modernen Modus ist das aktuelle Motiv in den Leben 1001, 1002 und 1003 (`runs/variant-all`) in jedem Zyklus Nukleo (`AktMot:` im Protokoll).
- Im Referenzmodus (`runs/baseline`, 105 Leben einschließlich Pilot) wechselt das Motiv in 72 Leben nie.
- Ein volles Leben 1001 im modernen Modus mit Workspace-Protokoll: Die Motivstärke von Nukleo liegt im Mittel bei 0,469 (Maximum 0,49), die stärkste andere Motivstärke erreicht höchstens 0,424. Die Selektionsschwelle liegt zwischen 0,034 und 0,088. In keinem Zyklus übertrifft ein anderes Motiv Nukleo.
- Offenlegung: Vor diesem Nachtrag lief eine Funktionsprobe über je 300 Zyklen von Seed 1001 in allen fünf Bedingungen, um die Verdrahtung zu prüfen. Motivwechsel waren dort in allen Bedingungen null. Weitere Kennzahlen aus B bis E wurden nicht ausgewertet.

W2 hat damit einen Bodeneffekt; H1 in der Fassung 1 kann B und E nicht unterscheiden, und die Kernaussage wäre per Konstruktion nicht stützbar.

**Änderung.** Absicht wird in PSI durch Motiv und Ziel bestimmt. Weil das Motiv konstant ist, wird H1 auf die Ebene der Ziele verlegt:

- **W2b Zielwechsel** pro 100 Zyklen: Wechsel des führenden Ziels (erster Eintrag der Zielliste nach dem Broadcast, Feld `lead_goal` im Workspace-Protokoll) zwischen zwei aufeinanderfolgenden Zyklen, in denen beide ein Ziel haben. In allen Bedingungen messbar.
- **H1 (neu):** W2b ist in B kleiner als in E.
- W2 (Motivwechsel) wird weiter erhoben und beschreibend berichtet, aber nicht bestätigend getestet.
- Die Holm-Korrektur läuft weiter über sechs Tests (H1 neu, H2 bis H6).
- Das Kriterium für die Kernaussage bleibt H1, H3 und H4, mit H1 in der neuen Fassung.

**Zusätzlich protokolliert** (ändert keine Hypothese): je Zyklus die Motivstärken aller Bedürfnisse (`motive_strengths`) und das führende Ziel (`lead_goal`).

**Umsetzungsänderungen seit Fassung 1, ohne Wirkung auf das Verhalten in A:** Zwischenspeicher für den Sortierschlüssel von `AnsiCompareText` und ein schnellerer Weg in `add_real` (beide mit allen Golden-Master-Tests geprüft); der Broadcast behält Gewicht und Raumbezug eines Ziels, das `GoalGen` schon aufgenommen hat.

Dieser Nachtrag ist eine offene Frage an Alec (`HANDOFF.md`), weil er das Kriterium der Kernaussage berührt. Die Läufe sind so angelegt, dass beide Fassungen von H1 aus denselben Daten auswertbar bleiben.

## Nachtrag 2 (2026-11-11, vor den Läufen von D)

Fester Bonus für Bedingung D: **0,064642**, das Mittel der Selektionsschwelle über alle 18.095 Zyklen der Bedingung A in den Seeds 1001 bis 1020 (`analysis/workspace/a-pruefung/README.md`). Aufruf: `--variant all,workspace=fixed,workspace_fixed_bonus=0.064642`.

Bedingung A mit Workspace-Protokoll ist in diesen 20 Leben bytegleich mit der Grundlinie des modernen Modus; die Auswertung nimmt für A deshalb die Grundlinie `runs/variant-all`, wo `runs/ws-A` fehlt.
