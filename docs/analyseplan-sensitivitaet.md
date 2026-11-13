# Analyseplan: Sensitivitätsläufe zur Workspace-Studie (Revision nach Review)

- Status: Fassung 1 vom 2026-11-12 (Issue #45), committet vor den Läufen
- Anlass: Reviewbericht `paper/2-hysterese/REVIEW_REPORT.md`, Punkte P2-06, P2-09 und P2-10
- Charakter: **nachträglich und explorativ.** Die bestätigende Studie (`docs/analyseplan-workspace.md`, Code-Stand c0194b6) bleibt unverändert und wird nicht neu bewertet. Ergebnisse dieses Plans werden im Paper als Sensitivitätsanalysen berichtet, nie als Teil der Bestätigung.

## Code

Gegenüber c0194b6 zwei Ergänzungen (Issue #45):

1. Diagnosefelder im Workspace-Protokoll: Zahl der Kandidaten, freie Plätze, Abstand zwischen letztem Gewinner und erstem Verlierer (effektive Stärke), Gleichstand an der Kapazitätsgrenze, und ob die Auswahl mit irgendeiner gedächtnislosen Auswahl bei beliebiger Auflösung von Gleichständen vereinbar ist (`differs_from_any_memoryless`). Die Auswahl selbst ändert sich nicht.
2. ADR 0018: Schalter `workspace_ties=random`, Gleichstände an der Kapazitätsgrenze per Zufall aus einer eigenen Quelle (aus dem Seed abgeleitet). Standard bleibt `name`.

## Läufe (Seeds 1001 bis 1020, moderner Modus, `MaxLife` 5.000.000)

| Kürzel | Variante | Zweck |
|---|---|---|
| S1-B, S1-E | `all,workspace=threshold` bzw. `all,workspace=none` (Namensregel) | Diagnose: Gleichstände und Margen. Prüfung: Inhalte je Zyklus identisch mit den archivierten Logs der Bestätigung |
| S2-B, S2-E | wie S1, mit `workspace_ties=random` | Hängen die Effekte B gegen E an der Namensregel? |
| S3-lo, S3-hi | `all,workspace=fixed,workspace_fixed_bonus=0.02` bzw. `0.2` | Bonusgröße: zusammen mit E (Bonus 0) und D (0,064642) aus der Bestätigung eine Dosis-Wirkungs-Reihe |

## Auswertung

- S1: Anteil der Zyklen mit Gleichstand an der Kapazitätsgrenze; Verteilung der Margen; Anteil der Zyklen, in denen die Auswahl mit keiner gedächtnislosen Auswahl vereinbar ist (W6 ohne Namensregel). Identitätsprüfung gegen die Bestätigungslogs (Inhalte und Zyklenzahl je Seed).
- S2: W2b, W1 der Nicht-Motive, W6 (beide Fassungen) je Bedingung; gepaarte Differenz B − E mit Bootstrap-Intervall und Vorzeichen-Permutationstest wie in der Bestätigung, ohne Holm-Familie und ohne Entscheidungsregel; Vergleich mit den Differenzen derselben 20 Seeds unter Namensregel.
- S3: W2b, W1 der Nicht-Motive, W6, P1 bis P6 über die Bonusreihe 0, 0,02, 0,0646, 0,2 (Seeds 1001 bis 1020), beschreibend.
- Ergebnisse nach `analysis/revision/sensitivitaet/`.

## Nachtrag 1 (2026-11-12, vor S1-E)

S1-E entfällt. Die Diagnosefelder (Gleichstand an der Kapazitätsgrenze, Margen) werden vor einer zufälligen Auflösung erfasst und liegen deshalb für E auch aus S2-E vor; die Inhalte von E unter Namensregel liegen aus der Bestätigung vor. Grund ist Rechenzeit. Reihenfolge danach: S2-B, S2-E, S3-lo, S3-hi.

## Klarstellung zu Nachtrag 1 (2026-11-13, zweite Review-Runde)

Die Diagnosefelder aus S2-E beschreiben Bedingung E **mit zufälliger** Gleichstandsauflösung. Sie werden zwar in jedem Zyklus vor der Auflösung erfasst, die vorangegangenen zufälligen Auswahlen haben aber Agent und Welt bereits verändert. Sie sind deshalb kein Ersatz für eine Diagnose von E mit Namensregel; eine solche Diagnose liegt nicht vor. Die Manuskripte berichten die 96 % Gleichstände ausdrücklich für E mit Zufallsregel.
