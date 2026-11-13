# traces/

Vergleichsdaten für den Abgleich mit dem Delphi-Original nach ADR 0005. Das Format ist in ADR 0006 entschieden und hier spezifiziert. Lesen und Schreiben übernimmt `psi_gw.tracing`.

## Ablage

| Ordner | Inhalt |
|---|---|
| `original-runs/<kennung>/` | Läufe des Originals, konvertiert aus dessen Protokollen (Ebene 2) |
| `python-runs/<kennung>/` | Läufe der Python-Implementierung (Ebene 2) |
| `procedures/<prozedur>/` | Prozedur-Testfälle aus dem Free-Pascal-Gerüst (Ebene 1) |

Dateinamen für Läufe: `<welt>__seed-<seed>__<laufnummer>.jsonl` bzw. `.jsonl.gz`. Rohprotokolle des Originals werden zusätzlich unverändert neben den konvertierten Dateien abgelegt, damit jede Konvertierung nachprüfbar bleibt.

Traces werden nie von Hand bearbeitet.

## Laufdaten (JSON Lines)

Kodierung UTF-8, eine JSON-Zeile pro Datensatz. Feldnamen in `snake_case`. Fehlende Werte sind `null`.

### `run` (erste Zeile, genau einmal)

| Feld | Typ | Bedeutung |
|---|---|---|
| `type` | `"run"` | |
| `format_version` | int | derzeit `1` |
| `source` | `"delphi"` oder `"python"` | |
| `program_version` | str | z. B. `"Psi 4.9.1.200"` bzw. Version von `psi_gw` |
| `world` | str oder null | Weltdaten, z. B. `"InselIII"` |
| `psi_data` | str oder null | Startwissen, z. B. `"InselIII"` |
| `seed` | int oder null | |
| `started_at` | str oder null | Zeitpunkt des Laufs, ISO 8601 |
| `params` | object | Parameter des Laufs (frei) |
| `source_files` | list[str] | Dateien, aus denen konvertiert wurde |
| `extra` | object | alles Weitere aus den Kopfzeilen des Originals |

### `cycle` (ein Datensatz pro Verhaltenszyklus)

| Feld | Typ | Delphi | Bedeutung |
|---|---|---|---|
| `cycle` | int | Zeilennummer in `ach*.Prt` | Zyklus `k` enthält die Stände nach Abschluss von Takt `k` und entspricht damit `cycle` der Ereignisse; Zyklus 0 ist der Startzustand |
| `life_pct` | int | `round(age/MaxLife*100)` | Alter in Prozent der maximalen Lebensdauer |
| `age` | int | `Leistung[Life]` | Alter |
| `age_diff` | int | `Leistung[DiffLife]` | Alterszuwachs seit dem letzten Zyklus |
| `counters` | object | `Leistung[...]` | Leistungszähler, siehe unten |
| `need_pct` | object | `Leistung[Hun..Affil]` | Bedürfnisstärke in Prozent, `round((1-Store)*100)`, für `hunger`, `thirst`, `damage`, `affiliation` |
| `stage_times` | object oder null | `IntTimes` | Zeit je Rasmussen-Stufe in Alterseinheiten, über alle Durchläufe des Zyklus summiert: `look_around`, `automatism`, `plan`, `what_could_be_done` |
| `extra` | object | | `stage_passes`: Zahl der Durchläufe laut `IntTimes`; `activities`: motorische Handlungen des Zyklus aus `Activities` mit `nr`, `act` (`Aggr`, `Mani`, `Loco`, `Regr`), `age` bei Abschluss und `steps` (Liste von Prozedurkürzel und Dauer in Alterseinheiten) |

Leistungszähler (`counters`), kumulativ über den Lauf:

| Name | Delphi | Gezählt wird in |
|---|---|---|
| `successful_locomotions` | `NSucLoc` | `UAction`, Ortswechsel gelungen |
| `unsuccessful_locomotions` | `NUsuLoc` | `UAction`, Ortswechsel misslungen |
| `locations_discovered` | `NLoc` | `UAction`, `UFPsi`: erster Besuch eines Ortes, inklusive Startort |
| `exitus` | `NExit` | `UFPsi`: Tod durch leere Speicher |
| `aggressions` | `NAgg` | `UAction` |
| `successful_manipulations` | `NSucMan` | `UAction` |
| `unsuccessful_manipulations` | `NuSuMan` | `UAction` |
| `nucleotides_collected` | `NNukleotide` | `UAction`; Startwert 5 (`UStrukturen`) |

### `event` (ein Datensatz pro Ereignis)

Feld für Feld aus dem Ereignisprotokoll des Originals (`Protokoll*.Dat`, geschrieben von `USmallProtokoll.WritePrt`).

| Feld | Typ | Delphi-Spalte | Bedeutung |
|---|---|---|---|
| `seq` | int | `Nr` | laufende Nummer der Aktion; Beginn und Ende einer Aktion teilen sich die Nummer |
| `wall_time` | str oder null | `Zeit` | Wanduhrzeit seit Start, `hh:mm:ss` |
| `wall_ms` | int oder null | `msec` | Wanduhr in Millisekunden seit Start |
| `age` | int | `Age` | |
| `cycle` | int | `Takt` | Verhaltenszyklus, ab 1 |
| `action` | str | `Aktion` | Wortlaut des Originals: `Start`, `Stop`, `Locomotion`, `Manipuliere`, `Aggression`, `Regression`, `Motivation`, `Take`, `Give`, `Bag`, `Open`, `Close`, `Pause` |
| `status` | int oder null | `Status` | `0` Beginn, `1` Ende, `-1` Mitteilung, leer bei Aktionen ohne Phasen |
| `params` | list[str] | `Para1..Para3` | z. B. Richtung, Manipulationsart, Koordinaten, Motivname und Änderung |
| `situation` | str oder null | `Situation` | |
| `object` | str oder null | `Objekt` | Objekt, an dem Psi gerade ist |
| `position` | [int, int] oder null | `PosX`, `PosY` | |
| `bag` | object | `Bag`, `Open`, `Bag1..Bag3` | Inventar: `count`, `open`, `items` |
| `needs` | object | `Hunger`..`Affiliation` | sieben Bedürfnisse, siehe Vokabular |
| `nucleotides_scaled` | float oder null | `Nuk/100` | |
| `modulators` | object | `Arousal`, `ResLevel`, `SelectThresh` | `arousal`, `resolution_level`, `selection_threshold` |
| `extra` | object | | nicht zugeordnete Spalten |

### `summary` (höchstens einmal, letzte Zeile)

| Feld | Typ | Bedeutung |
|---|---|---|
| `cycles` | int | Zahl der Zyklen |
| `events` | int | Zahl der Ereignisse |
| `counters` | object | Endstände der Leistungszähler |
| `action_counts` | object | Ereignisse je Aktion (Beginn und Mitteilung gezählt, Ende nicht) |
| `extra` | object | `each`: Endstände und mittlere Bedürfnisstärken aus `eAch` (`counters`, `need_pct_mean`); `consum`: Verbrauch und Zugewinn je Motiv aus `Consum` (`consumption`, `intake`); `inpro`: Zähler der internen Prozesse `TIntProc` aus `Inpro` (`int_proc`, `proc_times`, `check_freq`); `trailing_cycles`: Daten von Zyklen nach der letzten `ach`-Zeile, nach Zyklusnummer |

## Vokabular

| Englisch | Delphi | Deutsch |
|---|---|---|
| `hunger` | `Hunger` | Hunger |
| `thirst` | `Durst` | Durst |
| `nucleotides` | `Nukleo` | Nukleotide |
| `damage` | `Schaden` | Schaden (Unversehrtheit) |
| `certainty` | `Bestimmtheit` | Bestimmtheit |
| `competence` | `Kompetenz` | Kompetenz |
| `affiliation` | `Affili`, `Affiliation` | Affiliation |
| `arousal` | `Arousal` | Aktiviertheit |
| `resolution_level` | `ResolutionLevel`, `ResLevel` | Auflösungsgrad |
| `selection_threshold` | `SelectThreshold`, `SelectThresh` | Selektionsschwelle |

Die vollständige Zuordnung steht in `src/psi_gw/tracing/vocabulary.py`.

## Prozedur-Testfälle (JSON)

Eine Datei pro Fall: `procedures/<prozedur>/<fall-id>.json`.

```json
{
  "format_version": 1,
  "procedure": "GoalGen",
  "unit": "UPSIMain.Pas",
  "case_id": "goalgen-hunger-strong-001",
  "harness": {"commit": "<git-sha>", "notes": ""},
  "random": {"stream": [0.31, 0.77], "int_rule": "floor(value*n)", "consumed": 2},
  "inputs": {"args": {"motive": "hunger"}, "state": {"needs": {}, "modulators": {}}},
  "expected": {"result": null, "state": {"goal_list": ["Sdab"]}},
  "compare": {"exact": ["state.goal_list"], "approx": [], "rel_tol": 1e-9}
}
```

- `random.stream`: Zahlen in [0, 1), die die Prozedur der Reihe nach zieht. Ganzzahlige Ziehungen `Random(n)` ergeben `floor(value*n)`. `consumed` ist die Zahl der tatsächlich gezogenen Werte und wird mitgeprüft.
- `inputs.state` und `expected.state` enthalten nur die Teile des Zustands, die die Prozedur liest bzw. schreibt. Festgelegt sind bisher `needs` (je Motiv `activity`, `store`, `weight`, `increment`, `decrement`), `modulators` (je Modulator `value`, `g`, `min`, `max`), `competence`, `actual_motive` und `goal_list` (Liste von Neuronennamen). Die Darstellung des Gedächtnisnetzes folgt mit dem ersten Fall, der sie braucht (ADR 0006).
- `compare.exact` und `compare.approx` sind Pfade in Punktnotation relativ zu `expected`. Toleranz nach ADR 0005.
