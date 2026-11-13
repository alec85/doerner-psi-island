# Methodenbaustein: Global Workspace mit Hysterese

Grundlage für Abschnitt 3.3 und Abbildung A1. Umsetzung in `src/psi_gw/workspace/__init__.py`, Architektur in ADR 0016.

## Ablauf in einem Zyklus

1. `Motivation` wählt das aktuelle Motiv. In den Bedingungen B und C wie im Original mit Selektionsschwelle; in D mit festem Bonus, in E ohne Bonus (`Motivation.switch_bonus`). Die Freigabe eines Motivs (Arousal über Schwelle) bleibt in allen Bedingungen gleich.
2. `GoalGen` baut die Zielliste.
3. Broadcast der Ziele: Ziele im Workspace (aus dem Wettbewerb des Vorzyklus) werden an den Anfang der Zielliste gestellt und immer aufgenommen (`agent._broadcast_goals`).
4. Wettbewerb um den Workspace (`Workspace.update`):
   - Kapazität `K = round(2 + 5 × Auflösungsgrad)`, also 2 bis 7.
   - Das aktuelle Motiv hält immer einen Platz.
   - Kandidaten für die übrigen `K − 1` Plätze: nicht aktuelle Motive (Motivstärke); Ziele (Bedürfnisaktivität × Gewicht × Zielverbindung; ein Zwischenziel aus `InterMedGoals` erbt den Wert des Endziels, dem es dient); Objekte der aktuellen Situation (Neuheit `1/(1+n)` oder Bedrohung über Aversionsverbindungen, das Größere); von `Association` erinnerte Situationen (Wert des Ziels, das sie enthalten); das Ende des letzten Plans (Wert des Ziels, das `Planen` dort gefunden hat). Ein Neuron kandidiert einmal, mit seiner stärksten Lesart, bei gleicher Stärke in seiner spezifischsten Art (Plan vor Erinnerung vor Ziel).
   - Inhalte, die schon im Workspace sind, bekommen einen Bonus: in B die Selektionsschwelle für alle Arten, in C nur für Motive, in D einen festen Wert, in E keinen.
   - Gewählt werden die stärksten nach Stärke plus Bonus; Gleichstand nach Neuronenname (`Workspace.choose`).
5. Broadcast an die Handlungsregulation: `LookAround` prüft Objekte im Workspace, die zugleich Ziele sind, zuerst; `WhatCouldBeDone` erwägt Objekte im Workspace immer und mit voller Wahrscheinlichkeit.

Die Stärken werden ohne Seiteneffekte gelesen (keine Zufallszüge, keine Zeit). In Bedingung A (Workspace aus) protokolliert der Workspace nur; das Verhalten ist das des modernen Modus. Prüfung: Läufe von A mit Protokoll gegen die Grundlinie des modernen Modus (`HANDOFF.md`, Schritt 5a).

## Protokoll

Je Zyklus eine Zeile in `Workspace(1).jsonl`: Zyklus, Alter, Arousal, Selektionsschwelle, Auflösungsgrad, aktuelles Motiv, Motivstärken, führendes Ziel, Ereigniszähler; bei eingeschaltetem Workspace dazu `K`, Inhalte mit Art, Stärke, Eintrittszyklus und Arousal beim Eintritt und ob die Auswahl von der gedächtnislosen (ohne Bonus) abweicht. Die letzte Zeile enthält die Ereigniszähler des Lebens.

## Ereigniszähler (alle Bedingungen)

- Motivwechsel: aktuelles Motiv wechselt zwischen zwei Zyklen, beide nicht leer (`agent.run_cycle`).
- Ausgeführte und abgebrochene Pläne: `Actiplan` aufgerufen; Plan endet ohne Zielerreichung (`Regulation.planen_und_tun`).
- Gelegenheitsbefriedigung: `Consum` mit negativem Ausmaß für ein Bedürfnis, das nicht das aktuelle Motiv ist (`action.consum`).

## Festlegungen, die als Grenzen zu berichten sind

- Kandidatenstärken sind gesetzt (Zielwert, Neuheit, Bedrohung), nicht gelernt.
- Kapazität linear im Auflösungsgrad, Grenzen 2 und 7 frei gewählt.
- Der Broadcast wirkt nur an den genannten Stellen der Regulation.
- Gleichstände zwischen Kandidaten entscheidet der Neuronenname. Weil alle Ziele des Nukleo-Motivs denselben Wert haben (0,49 bei voller Bedürfnisaktivität), kommt das häufig vor; die gedächtnislose Auswahl ist dann durch die Namen bestimmt und stabil.
